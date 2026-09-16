"""
Model Context Protocol (MCP) Client Service.

Built using the official MCP Python SDK v2 (`mcp>=2.2.0`).
Provides an asynchronous service abstraction (`EnterpriseMCPClient`) allowing
the AI agent orchestrator to discover, inspect, and invoke enterprise tools
over standard JSON-RPC 2.0 transports without direct coupling to server internals.
"""

import json
import logging
import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger("enterprise_agent.mcp_client")


# ==============================================================================
# Custom Exceptions
# ==============================================================================

class MCPClientError(Exception):
    """Base exception for all MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Raised when the client fails to connect, times out, or transport drops."""
    pass


class MCPToolExecutionError(MCPClientError):
    """Raised when tool execution fails or an unknown tool is requested."""
    pass


# ==============================================================================
# Enterprise MCP Client Service
# ==============================================================================

class EnterpriseMCPClient:
    """
    High-level asynchronous MCP Client service.
    
    Manages transport lifecycle, tool discovery, schema introspection,
    typed invocation, and error handling for the Enterprise Knowledge & Support Agent.
    """

    def __init__(
        self,
        server_command: Optional[str] = None,
        server_args: Optional[List[str]] = None,
        server_env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        session: Optional[ClientSession] = None,
        server_url: Optional[str] = None,
    ):
        """
        Args:
            server_command: Executable binary for stdio transport (defaults to sys.executable).
            server_args: Arguments for the server command (defaults to ['scripts/run_mcp_server.py']).
            server_env: Optional environment variables dictionary for the server process.
            cwd: Working directory for server process (defaults to repo root).
            session: Optional pre-existing ClientSession (for in-memory stream testing).
            server_url: Optional remote Server-Sent Events (SSE) URL (e.g. 'http://mcp:8001/sse').
        """
        self.server_command = server_command or sys.executable
        self.server_args = server_args or ["scripts/run_mcp_server.py"]
        self.server_env = server_env
        self.cwd = cwd or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.server_url = server_url
        
        self._external_session = session
        self._session: Optional[ClientSession] = session
        self._exit_stack: Optional[AsyncExitStack] = None
        self._tools_cache: Dict[str, Dict[str, Any]] = {}
        self._is_connected: bool = session is not None

    @property
    def is_connected(self) -> bool:
        """Indicates whether the client has an active initialized session."""
        return self._is_connected and self._session is not None

    # --------------------------------------------------------------------------
    # Lifecycle Management
    # --------------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Establishes connection to the MCP server, negotiates capabilities,
        and discovers available tools. Supports both local stdio and remote SSE transports.
        """
        if self.is_connected:
            return

        # If an external session was injected (e.g. in-memory test stream)
        if self._external_session is not None:
            self._session = self._external_session
            await self.discover_tools()
            self._is_connected = True
            return

        # 1. Remote SSE transport
        if self.server_url:
            try:
                from mcp.client.sse import sse_client

                logger.info("Connecting to remote MCP Server via SSE at '%s'...", self.server_url)
                self._exit_stack = AsyncExitStack()

                read_stream, write_stream = await self._exit_stack.enter_async_context(
                    sse_client(self.server_url)
                )
                self._session = await self._exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

                init_res = await self._session.initialize()
                logger.info(
                    "Connected to remote MCP Server: %s (v%s)",
                    init_res.server_info.name,
                    getattr(init_res.server_info, "version", "unknown"),
                )

                await self.discover_tools()
                self._is_connected = True
                return
            except Exception as exc:
                await self.disconnect()
                raise MCPConnectionError(f"Failed to connect to remote MCP server at '{self.server_url}': {str(exc)}") from exc

        # 2. Local Stdio Subprocess transport
        if self.server_command == sys.executable and self.server_args:
            script_path = os.path.join(self.cwd, self.server_args[0])
            if not os.path.exists(script_path):
                raise MCPConnectionError(
                    f"MCP Server script not found at '{script_path}'. Cannot start stdio transport."
                )

        try:
            logger.info("Spawning MCP Server subprocess: %s %s", self.server_command, self.server_args)
            self._exit_stack = AsyncExitStack()

            # Merge environment variables ensuring PYTHONPATH includes repo root
            merged_env = dict(os.environ)
            if self.server_env:
                merged_env.update(self.server_env)
            if "PYTHONPATH" not in merged_env:
                merged_env["PYTHONPATH"] = self.cwd

            params = StdioServerParameters(
                command=self.server_command,
                args=self.server_args,
                env=merged_env,
            )

            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Protocol initialization
            init_res = await self._session.initialize()
            logger.info(
                "Connected to MCP Server: %s (v%s)",
                init_res.server_info.name,
                getattr(init_res.server_info, "version", "unknown"),
            )

            # Pre-fetch and cache tool definitions
            await self.discover_tools()
            self._is_connected = True

        except Exception as exc:
            await self.disconnect()
            raise MCPConnectionError(f"Failed to connect to MCP server: {str(exc)}") from exc

    async def disconnect(self) -> None:
        """Gracefully tears down transport streams and client session."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as exc:
                logger.warning("Error during MCP client disconnect: %s", exc)
            finally:
                self._exit_stack = None

        self._session = None
        self._tools_cache.clear()
        self._is_connected = False
        logger.info("MCP Client disconnected.")

    async def __aenter__(self) -> "EnterpriseMCPClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    async def _ensure_connected(self) -> None:
        """Guarantees connection is active before tool interaction."""
        if not self.is_connected:
            await self.connect()

    # --------------------------------------------------------------------------
    # Tool Discovery & Schema Inspection
    # --------------------------------------------------------------------------

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Discovers all tools advertised by the MCP server and updates local cache.
        Returns a list of tool descriptions with JSON Schema parameters.
        """
        if not self._session:
            raise MCPConnectionError("Cannot discover tools: Client session is not active.")

        try:
            tools_response = await self._session.list_tools()
            self._tools_cache = {
                t.name: {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.input_schema or {},
                }
                for t in tools_response.tools
            }
            logger.debug("Discovered %d tools from MCP server.", len(self._tools_cache))
            return list(self._tools_cache.values())
        except Exception as exc:
            raise MCPToolExecutionError(f"Failed to discover tools from MCP server: {str(exc)}") from exc

    def get_available_tool_names(self) -> List[str]:
        """Returns the list of cached tool names."""
        return list(self._tools_cache.keys())

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Returns the JSON Schema definition for a specific tool."""
        tool = self._tools_cache.get(tool_name)
        return tool["input_schema"] if tool else None

    def to_agent_function_declarations(self) -> List[Dict[str, Any]]:
        """
        Converts discovered MCP tools into standard Google ADK / Gemini
        function declaration format for agent reasoning.
        """
        declarations = []
        for tool in self._tools_cache.values():
            declarations.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            })
        return declarations

    # --------------------------------------------------------------------------
    # Tool Invocation & Structured Parsing
    # --------------------------------------------------------------------------

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invokes an MCP tool by name with specified arguments.
        Parses structured response and handles error states.
        """
        await self._ensure_connected()
        args = arguments or {}

        if tool_name not in self._tools_cache:
            # Refresh cache in case new tools were added dynamically
            await self.discover_tools()
            if tool_name not in self._tools_cache:
                raise MCPToolExecutionError(
                    f"Tool '{tool_name}' is not recognized by the MCP server. "
                    f"Available tools: {list(self._tools_cache.keys())}"
                )

        try:
            call_result = await self._session.call_tool(name=tool_name, arguments=args)
            
            # Extract content from response
            raw_text = ""
            if call_result.content:
                text_parts = [
                    part.text for part in call_result.content if hasattr(part, "text") and part.text
                ]
                raw_text = "\n".join(text_parts).strip()

            # Attempt JSON parsing of structured response
            if raw_text:
                try:
                    parsed_payload = json.loads(raw_text)
                    if isinstance(parsed_payload, dict):
                        return parsed_payload
                    return {"result": parsed_payload, "success": not call_result.is_error}
                except json.JSONDecodeError:
                    pass

            # Fallback for plain text response
            return {
                "success": not call_result.is_error,
                "result": raw_text,
                "is_error": call_result.is_error,
            }

        except Exception as exc:
            logger.error("Error executing MCP tool '%s': %s", tool_name, exc)
            raise MCPToolExecutionError(f"Execution of tool '{tool_name}' failed: {str(exc)}") from exc

    # --------------------------------------------------------------------------
    # High-Level Service Abstractions for Agent Workflows
    # --------------------------------------------------------------------------

    async def search_policy(
        self,
        query: str,
        department: Optional[str] = None,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """Convenience method for searching enterprise policy documents."""
        return await self.call_tool(
            "search_policy",
            {"query": query, "department": department, "top_k": top_k},
        )

    async def create_support_ticket(
        self,
        employee_id: str,
        title: str,
        description: str,
        category: str,
        priority: str = "MEDIUM",
    ) -> Dict[str, Any]:
        """Convenience method for creating a support ticket."""
        return await self.call_tool(
            "create_support_ticket",
            {
                "employee_id": employee_id,
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
            },
        )

    async def get_ticket_status(self, ticket_id: str) -> Dict[str, Any]:
        """Convenience method for tracking support ticket status."""
        return await self.call_tool(
            "get_ticket_status",
            {"ticket_id": ticket_id},
        )

    async def get_employee_info(
        self,
        employee_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convenience method for querying employee directory information."""
        args: Dict[str, Any] = {}
        if employee_id:
            args["employee_id"] = employee_id
        if email:
            args["email"] = email
        return await self.call_tool("get_employee_info", args)
