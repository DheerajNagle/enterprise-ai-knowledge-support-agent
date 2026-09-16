"""
Model Context Protocol (MCP) Server.

Built using the official MCP Python SDK v2 (`mcp.server.mcpserver.MCPServer`).
Exposes enterprise policy retrieval, ticket creation, ticket status tracking,
and employee profile lookup tools over standard transports (stdio and SSE/HTTP).
"""

import argparse
import asyncio
import logging
import sys
from mcp.server.mcpserver import MCPServer
from app.mcp.tools import register_all_tools

logger = logging.getLogger("enterprise_agent.mcp")


def create_mcp_server(
    name: str = "enterprise-knowledge-agent",
    version: str = "0.1.0",
) -> MCPServer:
    """
    Factory function to initialize and configure an MCPServer instance.
    Registers all enterprise tools and sets server metadata.
    """
    server = MCPServer(
        name=name,
        version=version,
        instructions=(
            "Enterprise AI Knowledge & Support MCP Server. Provides tools to search "
            "internal policies, manage IT/HR support tickets, and query employee directory."
        ),
    )
    register_all_tools(server)
    return server


# Global default instance
mcp_server = create_mcp_server()


async def run_stdio() -> None:
    """Runs the MCP server over standard input/output (stdio) transport."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,  # IMPORTANT: Keep stdout clean for MCP JSON-RPC protocol
    )
    logger.info("Starting Enterprise MCP Server on stdio transport...")
    await mcp_server.run_stdio_async()


def main() -> None:
    """Entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Enterprise AI Knowledge & Support MCP Server (SDK v2)"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport layer protocol: 'stdio' (default) or 'sse'",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port number when running in SSE/HTTP mode (default: 8001)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address for SSE/HTTP mode (default: 127.0.0.1)",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(run_stdio())
    elif args.transport == "sse":
        logger.info("Starting Enterprise MCP Server on SSE transport at %s:%d...", args.host, args.port)
        asyncio.run(mcp_server.run_sse_async(host=args.host, port=args.port))


if __name__ == "__main__":
    main()
