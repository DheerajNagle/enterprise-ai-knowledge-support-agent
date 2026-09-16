"""
Agent Service Layer.

Provides clean architectural separation between the API presentation layer and
the internal agent orchestration (RootAgent, RAGAgent, MCPToolAgent, LLMService).
Manages lifecycle of the MCP client connection, handles chat dispatching, and provides
direct tool invocation utilities.
"""

import logging
import time
from typing import Any, Dict, List, Optional
from app.config import get_settings
from app.agent.root_agent import RootAgent, AgentResponse
from app.agent.schemas import ConversationTurn
from app.mcp.client import EnterpriseMCPClient
from app.mcp.tools.policy_tools import execute_search_policy
from app.mcp.tools.ticket_tools import (
    execute_create_support_ticket,
    execute_get_ticket_status,
)
from app.mcp.tools.employee_tools import execute_get_employee_info

logger = logging.getLogger("enterprise_agent.service")

KNOWN_TOOLS = {
    "search_policy": execute_search_policy,
    "create_support_ticket": execute_create_support_ticket,
    "get_ticket_status": execute_get_ticket_status,
    "get_employee_info": execute_get_employee_info,
}


class AgentService:
    """
    Enterprise Agent Service managing RootAgent orchestration and MCP lifecycle.
    Keeps API controllers free of agent-specific orchestration logic.
    """

    def __init__(
        self,
        mcp_client: Optional[EnterpriseMCPClient] = None,
        root_agent: Optional[RootAgent] = None,
    ):
        self.settings = get_settings()
        self._mcp_client = mcp_client
        self._root_agent = root_agent
        self._initialized = False

    @property
    def mcp_client(self) -> Optional[EnterpriseMCPClient]:
        return self._mcp_client

    @property
    def is_mcp_connected(self) -> bool:
        return bool(self._mcp_client and self._mcp_client.is_connected)

    @property
    def root_agent(self) -> RootAgent:
        if self._root_agent is None:
            self._root_agent = RootAgent(
                mcp_client=self._mcp_client,
                model_name=self.settings.GEMINI_MODEL,
            )
        return self._root_agent

    async def start(self) -> None:
        """Initializes service resources if an explicit MCP client is configured."""
        if not self._initialized:
            logger.info("[AgentService] Starting Agent Service...")
            if self._mcp_client and not self._mcp_client.is_connected:
                try:
                    await self._mcp_client.connect()
                    logger.info("[AgentService] Connected to MCP server.")
                except Exception as exc:
                    logger.warning("[AgentService] MCP Client connection warning: %s", exc)
            self._initialized = True

    async def stop(self) -> None:
        """Gracefully tears down service resources."""
        if self._mcp_client and self._mcp_client.is_connected:
            logger.info("[AgentService] Disconnecting MCP Client...")
            try:
                await self._mcp_client.disconnect()
            except Exception as exc:
                logger.warning("[AgentService] Error during MCP Client disconnect: %s", exc)
        self._initialized = False
        logger.info("[AgentService] Agent Service stopped.")

    async def run_chat(
        self,
        message: str,
        conversation_history: Optional[List[ConversationTurn]] = None,
        user_id: Optional[str] = None,
        department: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> AgentResponse:
        """
        Executes an end-to-end chat turn through the RootAgent orchestrator.
        """
        logger.info(
            "[AgentService] Processing chat request from user_id='%s', dept='%s': '%s'",
            user_id,
            department,
            message[:80],
        )

        response = await self.root_agent.run(
            query=message,
            conversation_history=conversation_history,
        )
        return response

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Discovers and returns all available MCP tools with their JSON schemas.
        """
        if self._mcp_client and self._mcp_client.is_connected:
            try:
                tools = await self._mcp_client.discover_tools()
                return tools
            except Exception as exc:
                logger.warning("[AgentService] Failed to discover live MCP tools: %s", exc)

        # Standard canonical catalog of enterprise tools
        return [
            {
                "name": "search_policy",
                "description": "Searches the enterprise vector database for corporate policy documents.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "department": {"type": "string", "description": "Department filter"},
                        "top_k": {"type": "integer", "description": "Number of results", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "create_support_ticket",
                "description": "Creates a new support ticket in the enterprise SQLite database.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "employee_id": {"type": "string", "description": "Valid employee ID"},
                        "title": {"type": "string", "description": "Ticket summary"},
                        "description": {"type": "string", "description": "Detailed explanation"},
                        "category": {"type": "string", "description": "Ticket category", "default": "General"},
                        "priority": {"type": "string", "description": "Priority level", "default": "MEDIUM"},
                    },
                    "required": ["employee_id", "title", "description"],
                },
            },
            {
                "name": "get_ticket_status",
                "description": "Retrieves the current status and resolution details of a support ticket.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string", "description": "Ticket identifier (TCK-XXXX)"},
                    },
                    "required": ["ticket_id"],
                },
            },
            {
                "name": "get_employee_info",
                "description": "Retrieves employee profile information by employee_id or email.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "employee_id": {"type": "string", "description": "Employee ID"},
                        "email": {"type": "string", "description": "Corporate email address"},
                    },
                },
            },
        ]

    async def execute_tool(
        self, tool_name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a named tool directly or via MCP protocol, measuring execution duration.
        """
        start_time = time.time()
        logger.info("[AgentService] Executing tool '%s' with arguments: %s", tool_name, arguments)
        args = arguments or {}

        if tool_name not in KNOWN_TOOLS:
            return {
                "tool_name": tool_name,
                "success": False,
                "result": f"Tool '{tool_name}' is not recognized.",
                "execution_time_seconds": 0.0,
            }

        # Route through live MCP protocol if connected
        if self._mcp_client and self._mcp_client.is_connected:
            try:
                res = await self._mcp_client.call_tool(tool_name, args)
                elapsed = time.time() - start_time
                return {
                    "tool_name": tool_name,
                    "success": True,
                    "result": res,
                    "execution_time_seconds": round(elapsed, 4),
                }
            except Exception as exc:
                logger.warning("[AgentService] MCP protocol execution failed: %s. Using local fallback.", exc)

        # Direct execution fallback
        try:
            handler = KNOWN_TOOLS[tool_name]
            result = handler(**args)
            elapsed = time.time() - start_time
            return {
                "tool_name": tool_name,
                "success": True,
                "result": result,
                "execution_time_seconds": round(elapsed, 4),
            }
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("[AgentService] Direct tool execution failed: %s", exc)
            return {
                "tool_name": tool_name,
                "success": False,
                "result": str(exc),
                "execution_time_seconds": round(elapsed, 4),
            }


_agent_service_instance: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """Singleton accessor for the AgentService instance."""
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
    return _agent_service_instance
