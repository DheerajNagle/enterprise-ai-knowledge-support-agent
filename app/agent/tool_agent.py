"""
Google ADK MCP Tool Specialized Agent.

Implements the enterprise action agent using Google Agent Development Kit (ADK).
Specialized in executing transactional actions via the Model Context Protocol (MCP) client:
support ticket creation, ticket lifecycle inspection, and employee directory queries.
"""

import logging
import re
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from google.adk import Agent
from app.config import get_settings
from app.agent.prompts import TOOL_USAGE_INSTRUCTION
from app.agent.schemas import LLMExplanation, ToolExecutionResult
from app.agent.llm_service import LLMService
from app.mcp import EnterpriseMCPClient

logger = logging.getLogger("enterprise_agent.tool_agent")

TOOL_AGENT_INSTRUCTION = f"""{TOOL_USAGE_INSTRUCTION}

You are the Specialized MCP Tool Agent in the Enterprise AI hierarchy.
Your responsibility is to execute transactional database actions via Model Context Protocol:
1. create_support_ticket: Creates a formal IT/HR/Hardware support ticket in SQLite.
2. get_ticket_status: Inspects ticket lifecycle, priority, and resolution notes.
3. get_employee_info: Looks up employee corporate profiles.

Always validate parameters before execution.
Never invent employee IDs or ticket IDs.
Report exact execution outcomes and generated identifiers.
"""


class ToolAgentResult(BaseModel):
    """Structured response emitted by MCPToolAgent."""

    tool_name: str = Field(..., description="Name of the MCP tool invoked")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters passed to the tool")
    result_payload: Dict[str, Any] = Field(default_factory=dict, description="Structured tool output payload")
    success: bool = Field(..., description="True if tool executed successfully")
    human_readable_summary: str = Field(..., description="Conversational explanation of the result")
    tool_execution: Optional[ToolExecutionResult] = Field(
        default=None, description="Detailed tool execution metrics"
    )
    llm_explanation: Optional[LLMExplanation] = Field(
        default=None, description="LLM explanation of the tool action"
    )


class MCPToolAgent:
    """
    Specialized Action Agent built on Google ADK.
    Interfaces directly with the EnterpriseMCPClient to perform live tool execution
    and LLMService for conversational operational confirmations.
    """

    def __init__(
        self,
        mcp_client: Optional[EnterpriseMCPClient] = None,
        llm_service: Optional[LLMService] = None,
        model_name: Optional[str] = None,
    ):
        settings = get_settings()
        self.mcp_client = mcp_client or EnterpriseMCPClient()
        self.model_name = model_name or settings.gemini_model
        self.llm_service = llm_service or LLMService(model_name=self.model_name)

        # Underlying official Google ADK Agent definition
        self.adk_agent = Agent(
            name="mcp_tool_agent",
            model=self.model_name,
            description="Specialized agent for managing support tickets and querying employee directory via MCP.",
            instruction=TOOL_AGENT_INSTRUCTION,
        )

    # --------------------------------------------------------------------------
    # Natural Language Parameter Extraction Helpers
    # --------------------------------------------------------------------------

    @staticmethod
    def extract_ticket_id(text: str) -> Optional[str]:
        """Extracts ticket ID matching format TCK-YYYY-XXXX."""
        match = re.search(r"\b(TCK-\d{4}-[A-Za-z0-9]+)\b", text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    @staticmethod
    def extract_employee_id(text: str) -> Optional[str]:
        """Extracts employee ID matching format EMP-XXXX."""
        match = re.search(r"\b(EMP-[A-Za-z0-9]+)\b", text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    # --------------------------------------------------------------------------
    # Execution Dispatcher
    # --------------------------------------------------------------------------

    async def run(
        self,
        query: str,
        explicit_tool: Optional[str] = None,
        explicit_params: Optional[Dict[str, Any]] = None,
    ) -> ToolAgentResult:
        """
        Interprets the requested action and executes the appropriate tool via MCP client.
        """
        logger.info("[MCPToolAgent] Processing tool action for query: '%s'", query)
        q_lower = query.lower()
        start_time = time.perf_counter()

        # Connect MCP client if not connected
        try:
            if not self.mcp_client.is_connected:
                await self.mcp_client.connect()
        except Exception as exc:
            logger.warning("[MCPToolAgent] Failed to connect MCP client: %s", exc)

        # 1. Action: Get Ticket Status
        if explicit_tool == "get_ticket_status" or "status" in q_lower or "ticket" in q_lower and ("check" in q_lower or "track" in q_lower):
            ticket_id = (
                explicit_params.get("ticket_id") if explicit_params
                else self.extract_ticket_id(query)
            )
            if not ticket_id:
                exec_time = round((time.perf_counter() - start_time) * 1000, 2)
                tool_res = ToolExecutionResult(
                    tool_name="get_ticket_status",
                    parameters={"query": query},
                    result={"success": False, "error": "No valid Ticket ID found in request."},
                    success=False,
                    execution_time_ms=exec_time,
                )
                return ToolAgentResult(
                    tool_name="get_ticket_status",
                    parameters={"query": query},
                    result_payload={"success": False, "error": "No valid Ticket ID found in request."},
                    success=False,
                    human_readable_summary="Please provide a valid ticket ID (e.g. TCK-2024-0101) to check status.",
                    tool_execution=tool_res,
                )

            try:
                res = await self.mcp_client.get_ticket_status(ticket_id=ticket_id)
            except Exception as exc:
                logger.error("[MCPToolAgent] Error executing get_ticket_status: %s", exc)
                res = {"success": False, "error": f"Failed to retrieve ticket status: {str(exc)}"}
            exec_time = round((time.perf_counter() - start_time) * 1000, 2)
            tool_res = ToolExecutionResult(
                tool_name="get_ticket_status",
                parameters={"ticket_id": ticket_id},
                result=res,
                success=res.get("success", False),
                execution_time_ms=exec_time,
            )

            llm_explanation = await self.llm_service.generate_tool_explanation(
                query=query, tool_result=tool_res
            )

            return ToolAgentResult(
                tool_name="get_ticket_status",
                parameters={"ticket_id": ticket_id},
                result_payload=res,
                success=res.get("success", False),
                human_readable_summary=llm_explanation.text,
                tool_execution=tool_res,
                llm_explanation=llm_explanation,
            )

        # 2. Action: Create Support Ticket
        if explicit_tool == "create_support_ticket" or any(w in q_lower for w in ["create", "open", "file", "submit", "broken", "issue"]):
            params = explicit_params or {}
            emp_id = params.get("employee_id") or self.extract_employee_id(query) or "EMP-1001"
            title = params.get("title")
            desc = params.get("description") or query

            # Infer category
            category = params.get("category")
            if not category:
                if any(w in q_lower for w in ["vpn", "wifi", "network", "firewall"]):
                    category = "IT"
                elif any(w in q_lower for w in ["laptop", "macbook", "hardware", "monitor", "screen"]):
                    category = "HARDWARE"
                elif any(w in q_lower for w in ["pto", "leave", "vacation", "benefits"]):
                    category = "HR"
                elif any(w in q_lower for w in ["expense", "receipt", "mileage"]):
                    category = "FINANCE"
                else:
                    category = "GENERAL"

            # Infer priority
            priority = params.get("priority") or ("HIGH" if any(w in q_lower for w in ["urgent", "down", "critical", "broken"]) else "MEDIUM")

            if not title:
                # Use clean summary from query
                clean_q = re.sub(r"^(please\s+)?(create|open|file|submit)\s+(a\s+)?(support\s+)?ticket\s+(about|for|because)?\s*", "", query, flags=re.IGNORECASE).strip()
                title = clean_q[:60].capitalize() if clean_q else "General Support Request"

            try:
                res = await self.mcp_client.create_support_ticket(
                    employee_id=emp_id,
                    title=title,
                    description=desc,
                    category=category,
                    priority=priority,
                )
            except Exception as exc:
                logger.error("[MCPToolAgent] Error executing create_support_ticket: %s", exc)
                res = {"success": False, "error": f"Failed to create support ticket: {str(exc)}"}
            exec_time = round((time.perf_counter() - start_time) * 1000, 2)
            tool_res = ToolExecutionResult(
                tool_name="create_support_ticket",
                parameters={"employee_id": emp_id, "title": title, "category": category, "priority": priority},
                result=res,
                success=res.get("success", False),
                execution_time_ms=exec_time,
            )

            llm_explanation = await self.llm_service.generate_tool_explanation(
                query=query, tool_result=tool_res
            )

            # Ensure ticket ID appears in summary text
            tck = res.get("ticket", {}) if res.get("success") else {}
            summary_text = llm_explanation.text
            if tck.get("ticket_id") and tck["ticket_id"] not in summary_text:
                summary_text = f"Support ticket **{tck['ticket_id']}** created. {summary_text}"

            return ToolAgentResult(
                tool_name="create_support_ticket",
                parameters={"employee_id": emp_id, "title": title, "category": category, "priority": priority},
                result_payload=res,
                success=res.get("success", False),
                human_readable_summary=summary_text,
                tool_execution=tool_res,
                llm_explanation=llm_explanation,
            )

        # 3. Action: Get Employee Info
        if explicit_tool == "get_employee_info" or "employee" in q_lower or "directory" in q_lower:
            emp_id = self.extract_employee_id(query)
            try:
                res = await self.mcp_client.get_employee_info(employee_id=emp_id)
            except Exception as exc:
                logger.error("[MCPToolAgent] Error executing get_employee_info: %s", exc)
                res = {"success": False, "error": f"Failed to retrieve employee info: {str(exc)}"}
            exec_time = round((time.perf_counter() - start_time) * 1000, 2)
            tool_res = ToolExecutionResult(
                tool_name="get_employee_info",
                parameters={"employee_id": emp_id},
                result=res,
                success=res.get("success", False),
                execution_time_ms=exec_time,
            )

            llm_explanation = await self.llm_service.generate_tool_explanation(
                query=query, tool_result=tool_res
            )

            return ToolAgentResult(
                tool_name="get_employee_info",
                parameters={"employee_id": emp_id},
                result_payload=res,
                success=res.get("success", False),
                human_readable_summary=llm_explanation.text,
                tool_execution=tool_res,
                llm_explanation=llm_explanation,
            )

        # Fallback default
        exec_time = round((time.perf_counter() - start_time) * 1000, 2)
        tool_res = ToolExecutionResult(
            tool_name="unknown",
            parameters={"query": query},
            result={"success": False, "error": "Unable to determine requested tool action."},
            success=False,
            execution_time_ms=exec_time,
        )
        return ToolAgentResult(
            tool_name="unknown",
            parameters={"query": query},
            result_payload={"success": False, "error": "Unable to determine requested tool action."},
            success=False,
            human_readable_summary="I was unable to determine what action to take. Please specify whether you want to create a ticket, check a ticket status, or look up an employee.",
            tool_execution=tool_res,
        )
