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
import re
from typing import Any, Dict, List, Optional, Tuple
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


# ------------------------------------------------------------------------------
# Targeted Regex Patterns for Dynamic Intent Classification
# ------------------------------------------------------------------------------

TICKET_ID_PATTERN = re.compile(r"\bTCK-\d{4}-[A-Za-z0-9]+\b", re.IGNORECASE)
EMPLOYEE_ID_PATTERN = re.compile(r"\bEMP-[A-Za-z0-9]+\b", re.IGNORECASE)

TICKET_CREATE_PATTERNS = [
    re.compile(r"\b(create|open|file|submit|raise|log)\s+(an?\s+)?([a-z0-9_-]+\s+){0,3}(ticket|support\s+request)\b", re.IGNORECASE),
    re.compile(r"\b(report|file)\s+(an?\s+)?(issue|problem|incident|bug)\b", re.IGNORECASE),
    re.compile(r"\b(laptop|screen|keyboard|charger|monitor|hardware|vpn|wifi|connection)\s+(is\s+)?(broken|not working|down|failing|damaged)\b", re.IGNORECASE),
    re.compile(r"\b(fails?|unable)\s+to\s+connect\b", re.IGNORECASE),
]

TICKET_STATUS_PATTERNS = [
    re.compile(r"\b(check|get|track|view|show|find)\s+(the\s+)?status\s+of\b", re.IGNORECASE),
    re.compile(r"\bticket\s+status\b", re.IGNORECASE),
    re.compile(r"\bstatus\s+of\s+(the\s+|my\s+)?(support\s+)?ticket\b", re.IGNORECASE),
    re.compile(r"\bstatus\s+and\s+priority\b", re.IGNORECASE),
    re.compile(r"\b(check|track)\s+(the\s+|my\s+)?(support\s+)?ticket\b", re.IGNORECASE),
]

EMPLOYEE_LOOKUP_PATTERNS = [
    re.compile(r"\b(find|lookup|look\s+up|search|get|show)\s+(the\s+)?(directory\s+information|profile|info|details)?\s*(for|of)?\s*(employee|staff)\b", re.IGNORECASE),
    re.compile(r"\b(check|view|show|get)\s+the\s+profile\s+for\s+(employee|staff|user)\b", re.IGNORECASE),
    re.compile(r"\bwho\s+is\s+(employee\s+)?(EMP-[A-Za-z0-9]+|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", re.IGNORECASE),
    re.compile(r"\b(look\s*up|find|search)\s+EMP-[A-Za-z0-9]+\b", re.IGNORECASE),
    re.compile(r"\bemployee\s+(directory|profile|lookup)\b", re.IGNORECASE),
]

HYBRID_PATTERNS = [
    re.compile(r"\b(and|then|also)\s+(please\s+)?(create|file|open|submit|raise|log|check|look\s*up|find)\b", re.IGNORECASE),
    re.compile(r"\bif\s+(my\s+issue\s+qualifies|eligible|i\s+qualify|needed|appropriate)\b", re.IGNORECASE),
]

KNOWLEDGE_INQUIRY_PATTERNS = [
    re.compile(r"\b(what\s+is|what\s+are|what\s+does|how\s+do\s+i|how\s+to|how\s+can|how\s+does|when\s+is|where\s+can|is\s+there|can\s+i|explain|describe|tell\s+me\s+about)\b", re.IGNORECASE),
    re.compile(r"\b(policy|policies|guidelines?|rules?|allowance|procedure|standards?|handbook|sla|eligibility|entitled|requirements?)\b", re.IGNORECASE),
    re.compile(r"\b(pto|vacation|leave|per\s+diem|stipend|reimbursement|core\s+hours|refresh\s+cycle|device\s+health)\b", re.IGNORECASE),
]


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

        # Tool Action checks (grounded in system capabilities: ticket creation, ticket status, employee lookup)
        has_ticket_create = any(p.search(query) for p in TICKET_CREATE_PATTERNS)
        has_ticket_status = any(p.search(query) for p in TICKET_STATUS_PATTERNS) or bool(TICKET_ID_PATTERN.search(query))
        has_emp_lookup = any(p.search(query) for p in EMPLOYEE_LOOKUP_PATTERNS)
        has_action_indicator = has_ticket_create or has_ticket_status or has_emp_lookup

        # Policy / Knowledge Inquiry checks
        has_knowledge_indicator = (
            any(p.search(query) for p in KNOWLEDGE_INQUIRY_PATTERNS)
            or analysis.intent == "KNOWLEDGE_INQUIRY"
        )

        # 1. Composite / Hybrid Workflow Check
        has_conditional_intent = any(p.search(query) for p in HYBRID_PATTERNS)
        has_hybrid_conjunction = (
            has_conditional_intent
            or (
                ("and" in q_lower or "then" in q_lower or "if" in q_lower)
                and ("ticket" in q_lower or "emp-" in q_lower or "employee" in q_lower)
            )
        )

        if (has_knowledge_indicator and has_action_indicator) or analysis.intent == "HYBRID":
            if has_hybrid_conjunction:
                return WorkflowType.HYBRID_RAG_TOOL
            # If phrased as a knowledge/policy inquiry without actionable entity IDs, route to RAG
            if q_lower.strip().startswith((
                "what is", "what are", "what does", "how to", "how do i",
                "how can", "can i", "where can", "is it possible",
            )):
                if not TICKET_ID_PATTERN.search(query) and not EMPLOYEE_ID_PATTERN.search(query):
                    return WorkflowType.RAG_ONLY
            return WorkflowType.TOOL_ONLY

        # 2. Pure Action Request
        if has_action_indicator or analysis.intent == "ACTION_REQUEST":
            return WorkflowType.TOOL_ONLY

        # 3. Pure Knowledge Inquiry (or general fallback)
        return WorkflowType.RAG_ONLY

    @staticmethod
    def extract_knowledge_subquery(query: str) -> str:
        """
        Extracts the primary knowledge inquiry from a composite hybrid request
        by stripping operational action clauses, while preserving core domain terms.
        """
        parts = re.split(
            r",?\s+(?:and|then)\s+(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:create|open|file|submit|raise|log|check|look\s*up|find|search)\b",
            query,
            flags=re.IGNORECASE,
        )
        if len(parts) >= 2:
            candidate = parts[0].strip()
            # Verify candidate contains inquiry or policy keywords
            if any(
                w in candidate.lower()
                for w in [
                    "what", "how", "policy", "rules", "allowance", "stipend",
                    "guidelines", "procedure", "vpn", "laptop", "leave",
                    "expense", "password", "security", "refresh", "core hours",
                ]
            ):
                return candidate
        return query

    @staticmethod
    def check_conditional_qualification(query: str) -> Tuple[bool, bool]:
        """
        Evaluates whether a hybrid request is conditional on qualification
        and whether sufficient concrete issue details were provided to evaluate qualification.

        Returns (is_conditional, has_concrete_details).
        """
        CONDITIONAL_PATTERNS = [
            re.compile(r"\bif\s+(?:my\s+)?(?:issue\s+)?qualif(?:ies|y|ication)\b", re.IGNORECASE),
            re.compile(r"\bif\s+(?:i\s+)?eligible\b", re.IGNORECASE),
            re.compile(r"\bif\s+(?:i\s+)?qualify\b", re.IGNORECASE),
            re.compile(r"\bif\s+applicable\b", re.IGNORECASE),
            re.compile(r"\bif\s+appropriate\b", re.IGNORECASE),
            re.compile(r"\bif\s+needed\b", re.IGNORECASE),
        ]
        is_conditional = any(p.search(query) for p in CONDITIONAL_PATTERNS)
        if not is_conditional:
            return False, True

        # Check for concrete issue details beyond the conditional phrase
        cleaned = query
        for p in CONDITIONAL_PATTERNS:
            cleaned = p.sub("", cleaned)
        cleaned = re.sub(
            r"^(?:what\s+(?:does|is|are)|how\s+to|can\s+i|explain).*?(?:and|then)\s+(?:please\s+)?(?:create|open|file|submit|raise)\s+(?:a\s+)?(?:support\s+)?ticket\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" ?:.,;")

        ISSUE_DETAIL_PATTERNS = [
            re.compile(r"\bEMP-[A-Za-z0-9]+\b", re.IGNORECASE),
            re.compile(r"\bTCK-\d{4}-[A-Za-z0-9]+\b", re.IGNORECASE),
            re.compile(
                r"\b(?:because|due\s+to|stating|reporting|failing|fails?|sensor|crowdstrike|bitlocker|filevault|firewall|screen|keyboard|charger|broken|damaged|lost|stolen|inactive|offline|months?\s+old)\b",
                re.IGNORECASE,
            ),
        ]
        has_details = any(p.search(cleaned) for p in ISSUE_DETAIL_PATTERNS) or len(cleaned.split()) >= 4
        return is_conditional, has_details

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
            try:
                tool_res = await self.tool_agent.run(query=query)
            except Exception as exc:
                logger.error("[RootAgent] Failed to run ToolAgent in tool-only workflow: %s", exc)
                tool_res = ToolAgentResult(
                    tool_name="unknown",
                    parameters={"query": query},
                    result_payload={"success": False, "error": str(exc)},
                    success=False,
                    human_readable_summary=f"Unable to execute requested tool action: {str(exc)}",
                )
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
        # Step A: Execute RAG retrieval on focused knowledge subquery
        knowledge_query = self.extract_knowledge_subquery(query)
        rag_res = await self.rag_agent.run(
            query=knowledge_query,
            conversation_history=conversation_history,
            top_k=top_k,
        )
        audit_log["retrieval"] = {
            "total_chunks": len(rag_res.sources),
            "sources": [s.model_dump() for s in rag_res.sources],
            "confidence_score": rag_res.confidence_score,
        }

        # Step B: Evaluate conditional qualification & execute tool action
        is_conditional, has_concrete_details = self.check_conditional_qualification(query)

        if is_conditional and not has_concrete_details:
            logger.info("[RootAgent] Hybrid request is conditional on qualification but lacks concrete issue details.")
            tool_res = ToolAgentResult(
                tool_name="create_support_ticket",
                parameters={"query": query, "qualification_status": "missing_issue_details"},
                result_payload={
                    "success": False,
                    "ticket_created": False,
                    "reason": "Request is conditional ('if my issue qualifies') but does not specify the issue details or device status.",
                    "required_information": [
                        "A description of the specific issue or error encountered (e.g. failing posture assessment, CrowdStrike sensor offline).",
                        "Employee ID (e.g. EMP-1001).",
                        "Device operating system and compliance status.",
                    ],
                },
                success=False,
                human_readable_summary=(
                    "No support ticket was created because your request is conditional ('if my issue qualifies'), "
                    "but no specific issue details were provided to evaluate against the policy. "
                    "To determine qualification and open a support ticket, please provide:\n"
                    "1. A description of the specific issue or error (e.g., failing host posture assessment, sensor inactive).\n"
                    "2. Your employee ID (e.g., EMP-1001).\n"
                    "3. Your device operating system and current status."
                ),
                tool_execution=ToolExecutionResult(
                    tool_name="create_support_ticket",
                    parameters={"query": query},
                    result={
                        "success": False,
                        "ticket_created": False,
                        "reason": "Missing concrete issue description to determine policy qualification.",
                    },
                    success=False,
                    execution_time_ms=0.0,
                ),
            )
        else:
            try:
                tool_res = await self.tool_agent.run(query=query)
            except Exception as exc:
                logger.error("[RootAgent] Failed to run ToolAgent in hybrid workflow: %s", exc)
                tool_res = ToolAgentResult(
                    tool_name="unknown",
                    parameters={"query": query},
                    result_payload={"success": False, "error": str(exc)},
                    success=False,
                    human_readable_summary=f"Unable to execute support tool action: {str(exc)}",
                )

        audit_log["tool_usage"] = {
            "tool_name": tool_res.tool_name,
            "parameters": tool_res.parameters,
            "success": tool_res.success,
            "result_payload": tool_res.result_payload,
        }

        # Step C: Synthesize combined grounded response
        action_header = "### Action Taken" if tool_res.success else "### Action Required to Qualify"
        combined_parts = [
            "### Policy Evaluation",
            rag_res.answer,
            f"\n{action_header}",
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
