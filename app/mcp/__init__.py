"""
Model Context Protocol (MCP) Package.

Built with the official MCP Python SDK v2.
Exposes the enterprise MCP server and tool execution handlers.
"""

from app.mcp.server import create_mcp_server, mcp_server
from app.mcp.client import (
    EnterpriseMCPClient,
    MCPClientError,
    MCPConnectionError,
    MCPToolExecutionError,
)
from app.mcp.tools import (
    register_all_tools,
    execute_search_policy,
    execute_create_support_ticket,
    execute_get_ticket_status,
    execute_get_employee_info,
)

__all__ = [
    "create_mcp_server",
    "mcp_server",
    "EnterpriseMCPClient",
    "MCPClientError",
    "MCPConnectionError",
    "MCPToolExecutionError",
    "register_all_tools",
    "execute_search_policy",
    "execute_create_support_ticket",
    "execute_get_ticket_status",
    "execute_get_employee_info",
]
