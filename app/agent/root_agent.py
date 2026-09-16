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
4. SAFETY_REFUSAL: Prompt injection and jailbreak isolation.

Produces a 3-tier response contract clearly distinguishing:
1. Retrieved Knowledge (chunks, filenames, sections, scores)
2. MCP Tool Results (tool name, parameters, execution payload)
3. LLM-Generated Explanation (synthesized grounded reasoning)
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
from app.agent.schemas import (
    ConversationTurn,
    RetrievedKnowledgeItem,
    ToolExecutionResult,
)
from app.agent.llm_service import LLMService
from app.mcp import EnterpriseMCPClient

logger = logging.getLogger("enterprise_agent.root_agent")


class WorkflowType(str, enum.Enum):
    """Enumeration of available execution workflows."""
    RAG_ONLY = "RAG_ONLY"
    TOOL_ONLY = "TOOL_ONLY"
    HYBRID_RAG_TOOL = "HYBRID_RAG_TOOL"
    SAFETY_REFUSAL = "SAFETY_REFUSAL"


class AgentResponse(BaseModel):
    """
    Unified response contract emitted by the RootAgent orchestrator.
    Exposes explicit distinction between retrieved knowledge, tool actions, and LLM explanation.
    """

    workflow: WorkflowType = Field(..., description="Selected execution workflow")
    response_text: str = Field(..., description="Final conversational answer delivered to the user")
    retrieved_knowledge: List[RetrievedKnowledgeItem] = Field(
        default_factory=list, description="1. Retrieved official policy knowledge chunks and citations"
    )
    tool_results: List[ToolExecutionResult] = Field(
        default_factory=list, description="2. Operational action outputs executed via MCP tools"
    )
    llm_explanation: Optional[str] = Field(
        default=None, description="3. Synthesized natural language explanation from LLM"
    )
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
    Top-level Google ADK Orchestrator.
    Coordinates sub-agents and manages execution workflows and multi-tier response assembly.
    """

    def __init__(
        self,
        mcp_client: Optional[EnterpriseMCPClient] = None,
        context_engine: Optional[ContextEngine] = None,
        llm_service: Optional[LLMService] = None,
        model_name: Optional[str] = None,
    ):
        settings = get_settings()
        self.model_name = model_name or settings.gemini_model
        self.mcp_client = mcp_client or EnterpriseMCPClient(server_url=settings.MCP_SERVER_URL)
        self.context_engine = context_engine or ContextEngine()
        self.llm_service = llm_service or LLMService(model_name=self.model_name)

        # Initialize specialized sub-agents with shared LLM and context components
        self.rag_agent = RAGAgent(
            mcp_client=self.mcp_client,
            context_engine=self.context_engine,
            llm_service=self.llm_service,
            model_name=self.model_name,
        )
        self.tool_agent = MCPToolAgent(
            mcp_client=self.mcp_client,
            llm_service=self.llm_service,
            model_name=self.model_name,
        )

        # Official Google ADK Agent orchestrator with registered sub-agents
        self.adk_agent = Agent(
            name="root_agent",
            model=self.model_name,
            description="Root orchestrator delegating enterprise knowledge and operational tasks.",
            instruction=ROOT_AGENT_INSTRUCTION,
            sub_agents=[self.rag_agent.adk_agent, self.tool_agent.adk_agent],
        )

    # --------------------------------------------------------------------------
    # Multi-Signal Reasoning & Dynamic Routing
    # --------------------------------------------------------------------------

    def determine_workflow(self, query: str) -> WorkflowType:
        """
        Determines the appropriate workflow using multi-signal linguistic and semantic reasoning.
        """
        analysis = self.context_engine.analyze_query(query)

        # 0. Safety / Adversarial Prompt Injection Check
        if analysis.is_potential_injection:
            logger.warning("[RootAgent] Query flagged as potential injection: '%s'", query)
            return WorkflowType.SAFETY_REFUSAL

        q_lower = query.lower()

        # Action signals
        action_keywords = [
            "create", "open", "file", "submit", "raise", "ticket",
            "status", "check", "lookup", "find employee", "who is",
            "report issue", "broken", "not working", "fails to connect",
        ]
        has_action_indicator = any(kw in q_lower for kw in action_keywords)

        # Policy / Knowledge signals
        knowledge_keywords = [
            "policy", "rules", "guidelines", "allowance", "procedure",
            "how to", "what is", "how do i", "qualify", "eligibility",
            "entitled", "days", "pto", "vpn", "expense", "remote work",
            "password", "laptop", "security",
        ]
        has_knowledge_indicator = any(kw in q_lower for kw in knowledge_keywords)

        # 1. Composite / Hybrid Workflow
        conditional_conjunctions = [
            "and create", "and open", "and file", "if my issue",
            "if eligible", "if i qualify", "then create", "then open",
        ]
        has_conditional_intent = any(conj in q_lower for conj in conditional_conjunctions)

        if (has_knowledge_indicator and has_action_indicator) or has_conditional_intent or analysis.intent == "HYBRID":
            if "and" in q_lower or "if" in q_lower or has_conditional_intent:
                return WorkflowType.HYBRID_RAG_TOOL

        # 2. Specific Ticket Status Action
        if "TCK-" in query.upper() or ("ticket" in q_lower and "status" in q_lower):
            return WorkflowType.TOOL_ONLY

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
        Orchestrates request execution across specialized sub-agents with full audit logging
        and a 3-tier response contract distinguishing knowledge, tools, and explanation.
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
                retrieved_knowledge=[],
                tool_results=[],
                llm_explanation=rag_res.answer,
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
                retrieved_knowledge=rag_res.retrieved_knowledge,
                tool_results=[],
                llm_explanation=rag_res.answer,
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

            tool_executions = [tool_res.tool_execution] if tool_res.tool_execution else []

            logger.info("[RootAgent] Completed Tool workflow via '%s'.", tool_res.tool_name)
            return AgentResponse(
                workflow=workflow,
                response_text=tool_res.human_readable_summary,
                retrieved_knowledge=[],
                tool_results=tool_executions,
                llm_explanation=tool_res.human_readable_summary,
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

        tool_executions = [tool_res.tool_execution] if tool_res.tool_execution else []

        logger.info("[RootAgent] Completed Hybrid RAG+Tool workflow.")
        return AgentResponse(
            workflow=workflow,
            response_text=final_text,
            retrieved_knowledge=rag_res.retrieved_knowledge,
            tool_results=tool_executions,
            llm_explanation=final_text,
            rag_result=rag_res,
            tool_result=tool_res,
            audit_logs=audit_log,
        )
