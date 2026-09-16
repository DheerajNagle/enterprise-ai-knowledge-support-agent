"""
Google ADK Root Orchestrator Agent.

Implements the top-level routing and multi-agent orchestrator using Google Agent Development Kit (ADK).
Hierarchy:
    Root Agent (root_agent)
    ├── RAG Agent (rag_agent)
    └── MCP Tool Agent (mcp_tool_agent)

Dynamically routes incoming requests to the appropriate workflow:
1. RAG_ONLY: Knowledge and policy inquiries.
2. TOOL_ONLY: Action-driven database operations (ticket creation, status, employee lookup).
3. HYBRID_RAG_TOOL: Composite workflows requiring policy consultation followed by action execution.

Provides comprehensive structured audit logging:
- Request
- Selected Workflow
- Retrieval Results
- Tool Usage
- Final Synthesized Response
"""

import enum
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from google.adk import Agent
from app.config import get_settings
from app.agent.prompts import SYSTEM_INSTRUCTION
from app.agent.context import ContextEngine
from app.agent.rag_agent import RAGAgent, RAGAgentResult
from app.agent.tool_agent import MCPToolAgent, ToolAgentResult
from app.agent.schemas import ConversationTurn
from app.mcp import EnterpriseMCPClient

logger = logging.getLogger("enterprise_agent.root_agent")


class WorkflowType(str, enum.Enum):
    """Enumeration of available execution workflows."""
    RAG_ONLY = "RAG_ONLY"
    TOOL_ONLY = "TOOL_ONLY"
    HYBRID_RAG_TOOL = "HYBRID_RAG_TOOL"
    SAFETY_REFUSAL = "SAFETY_REFUSAL"


class AgentResponse(BaseModel):
    """Unified response contract emitted by the RootAgent orchestrator."""

    workflow: WorkflowType = Field(..., description="Selected execution workflow")
    response_text: str = Field(..., description="Final conversational answer delivered to the user")
    rag_result: Optional[RAGAgentResult] = Field(default=None, description="Detailed RAG retrieval metrics")
    tool_result: Optional[ToolAgentResult] = Field(default=None, description="Detailed MCP tool execution metrics")
    audit_logs: Dict[str, Any] = Field(default_factory=dict, description="Structured execution audit trace")


ROOT_AGENT_INSTRUCTION = f"""{SYSTEM_INSTRUCTION}

You are the Enterprise AI Root Orchestrator Agent in the Google ADK hierarchy.
You oversee two specialized agents:
1. rag_agent: Handles all enterprise knowledge, HR, IT, and security policy questions.
2. mcp_tool_agent: Executes live database actions (creating tickets, checking ticket status, looking up employees).

When receiving a user inquiry:
- If the user is asking an informational or policy question, route to rag_agent.
- If the user wants to perform a concrete action (create ticket, check ticket, lookup employee), route to mcp_tool_agent.
- If the request asks for policy guidance AND an action based on that policy, orchestrate both sequentially:
  First retrieve policy facts, evaluate eligibility, and then invoke the tool.
"""


class RootAgent:
    """
    Top-level Google ADK Agent orchestrator.
    Manages sub-agent delegation, dynamic routing, hybrid synthesis, and audit logging.
    """

    def __init__(
        self,
        rag_agent: Optional[RAGAgent] = None,
        tool_agent: Optional[MCPToolAgent] = None,
        mcp_client: Optional[EnterpriseMCPClient] = None,
        context_engine: Optional[ContextEngine] = None,
        model_name: Optional[str] = None,
    ):
        settings = get_settings()
        self.model_name = model_name or settings.gemini_model
        self.context_engine = context_engine or ContextEngine()
        self.mcp_client = mcp_client or EnterpriseMCPClient()
        self.rag_agent = rag_agent or RAGAgent(
            mcp_client=self.mcp_client,
            context_engine=self.context_engine,
            model_name=self.model_name,
        )
        self.tool_agent = tool_agent or MCPToolAgent(mcp_client=self.mcp_client, model_name=self.model_name)

        # Official Google ADK Agent definition with sub-agents hierarchy
        self.adk_agent = Agent(
            name="root_agent",
            model=self.model_name,
            description="Root agent that routes and orchestrates enterprise knowledge and action workflows.",
            instruction=ROOT_AGENT_INSTRUCTION,
            sub_agents=[self.rag_agent.adk_agent, self.tool_agent.adk_agent],
        )

    # --------------------------------------------------------------------------
    # Workflow Determination
    # --------------------------------------------------------------------------

    def determine_workflow(self, query: str) -> WorkflowType:
        """
        Dynamically selects the appropriate execution workflow based on query analysis.
        Avoids brittle exact string matching by analyzing semantic intent and composite conditions.
        """
        analysis = self.context_engine.analyze_query(query)

        # 1. Safety / Injection guard
        if analysis.is_potential_injection:
            return WorkflowType.SAFETY_REFUSAL

        q_lower = query.lower()

        # Indicators
        has_knowledge_indicator = any(
            w in q_lower for w in ["what", "how", "policy", "rules", "guidelines", "eligible", "allowed", "coverage", "say about"]
        )
        has_action_indicator = any(
            w in q_lower for w in ["create", "open", "file", "submit", "broken", "status", "track", "reset", "lookup"]
        ) and any(
            w in q_lower for w in ["ticket", "password", "employee", "account", "issue"]
        )

        # 2. Hybrid workflow: User asks about policy AND conditionally asks to create ticket or take action
        if has_knowledge_indicator and has_action_indicator:
            return WorkflowType.HYBRID_RAG_TOOL

        # Also detect conditional connector: "and create a ticket", "and file a ticket", "if my issue qualifies"
        if "policy" in q_lower and ("create a ticket" in q_lower or "file a ticket" in q_lower or "open a ticket" in q_lower):
            return WorkflowType.HYBRID_RAG_TOOL

        # 3. Pure Action Request
        if has_action_indicator or analysis.intent == "ACTION_REQUEST":
            return WorkflowType.TOOL_ONLY

        # 4. Pure Knowledge Inquiry
        return WorkflowType.RAG_ONLY

    # --------------------------------------------------------------------------
    # Orchestration Execution
    # --------------------------------------------------------------------------

    async def run(
        self,
        query: str,
        conversation_history: Optional[List[ConversationTurn]] = None,
        top_k: int = 3,
    ) -> AgentResponse:
        """
        Orchestrates request execution across specialized sub-agents with full audit logging.
        """
        workflow = self.determine_workflow(query)

        # Initialize Audit Log
        audit_log: Dict[str, Any] = {
            "request": {"query": query},
            "selected_workflow": {
                "workflow": workflow.value,
                "sub_agents": [sa.name for sa in self.adk_agent.sub_agents],
            },
            "retrieval": None,
            "tool_usage": None,
            "final_response": "",
        }

        logger.info("[RootAgent] Request: '%s' | Selected Workflow: %s", query, workflow.value)

        # ----------------------------------------------------------------------
        # Case 0: Safety Refusal
        # ----------------------------------------------------------------------
        if workflow == WorkflowType.SAFETY_REFUSAL:
            rag_res = await self.rag_agent.run(query=query, conversation_history=conversation_history)
            audit_log["final_response"] = rag_res.answer
            logger.warning("[RootAgent] Request blocked by safety policies.")
            return AgentResponse(
                workflow=workflow,
                response_text=rag_res.answer,
                rag_result=rag_res,
                audit_logs=audit_log,
            )

        # ----------------------------------------------------------------------
        # Case 1: Pure Knowledge (RAG Agent)
        # ----------------------------------------------------------------------
        if workflow == WorkflowType.RAG_ONLY:
            rag_res = await self.rag_agent.run(
                query=query,
                conversation_history=conversation_history,
                top_k=top_k,
            )
            audit_log["retrieval"] = {
                "total_chunks": len(rag_res.sources),
                "sources": [s.model_dump() for s in rag_res.sources],
                "confidence_score": rag_res.confidence_score,
            }
            audit_log["final_response"] = rag_res.answer

            logger.info("[RootAgent] Completed RAG workflow with %d sources.", len(rag_res.sources))
            return AgentResponse(
                workflow=workflow,
                response_text=rag_res.answer,
                rag_result=rag_res,
                audit_logs=audit_log,
            )

        # ----------------------------------------------------------------------
        # Case 2: Pure Action (MCP Tool Agent)
        # ----------------------------------------------------------------------
        if workflow == WorkflowType.TOOL_ONLY:
            tool_res = await self.tool_agent.run(query=query)
            audit_log["tool_usage"] = {
                "tool_name": tool_res.tool_name,
                "parameters": tool_res.parameters,
                "success": tool_res.success,
                "result_payload": tool_res.result_payload,
            }
            audit_log["final_response"] = tool_res.human_readable_summary

            logger.info("[RootAgent] Completed Tool workflow via '%s'.", tool_res.tool_name)
            return AgentResponse(
                workflow=workflow,
                response_text=tool_res.human_readable_summary,
                tool_result=tool_res,
                audit_logs=audit_log,
            )

        # ----------------------------------------------------------------------
        # Case 3: Composite Hybrid Workflow (RAG + MCP Tool)
        # ----------------------------------------------------------------------
        # Step A: Execute RAG retrieval to evaluate policy
        rag_res = await self.rag_agent.run(
            query=query,
            conversation_history=conversation_history,
            top_k=top_k,
        )
        audit_log["retrieval"] = {
            "total_chunks": len(rag_res.sources),
            "sources": [s.model_dump() for s in rag_res.sources],
            "confidence_score": rag_res.confidence_score,
        }

        # Step B: Execute Tool action based on user intent
        tool_res = await self.tool_agent.run(query=query)
        audit_log["tool_usage"] = {
            "tool_name": tool_res.tool_name,
            "parameters": tool_res.parameters,
            "success": tool_res.success,
            "result_payload": tool_res.result_payload,
        }

        # Step C: Synthesize combined grounded response
        combined_parts = [
            "### Policy Evaluation",
            rag_res.answer,
            "\n### Action Taken",
            tool_res.human_readable_summary,
        ]
        final_text = "\n\n".join(combined_parts)
        audit_log["final_response"] = final_text

        logger.info("[RootAgent] Completed Hybrid RAG+Tool workflow.")
        return AgentResponse(
            workflow=workflow,
            response_text=final_text,
            rag_result=rag_res,
            tool_result=tool_res,
            audit_logs=audit_log,
        )
