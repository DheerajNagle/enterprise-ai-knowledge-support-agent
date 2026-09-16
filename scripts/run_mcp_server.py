#!/usr/bin/env python
"""
Standalone Entry Point for Enterprise Model Context Protocol (MCP) Server.

Usage:
    # Standard I/O transport (Default, for Claude Desktop, MCP Inspector, Google ADK):
    python scripts/run_mcp_server.py

    # Server-Sent Events (SSE) / HTTP transport:
    python scripts/run_mcp_server.py --transport sse --port 8001

    # Connect with official MCP Inspector:
    npx @modelcontextprotocol/inspector python scripts/run_mcp_server.py
"""

import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.mcp.server import main

if __name__ == "__main__":
    main()
