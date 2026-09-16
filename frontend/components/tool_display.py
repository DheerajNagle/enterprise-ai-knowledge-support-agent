"""
Frontend Tool Execution Display Component.

Renders Model Context Protocol (MCP) tool invocations, displaying:
- Tool Name
- Action (arguments / parameters)
- Result (return payload & status)
"""

import json
import streamlit as st
from typing import Any, Dict, List, Optional


def render_tool_executions(tool_results: Optional[List[Dict[str, Any]]]):
    """
    Renders MCP tool execution cards showing tool name, action parameters, and output.
    """
    if not tool_results:
        return

    count = len(tool_results)
    with st.expander(f"🛠️ MCP Tool Actions Executed ({count})", expanded=False):
        for idx, tool in enumerate(tool_results, 1):
            tool_name = tool.get("tool_name", "unknown_tool")
            parameters = tool.get("parameters", {})
            result = tool.get("result", "")
            success = tool.get("success", True)

            status_color = "#10B981" if success else "#EF4444"
            status_text = "SUCCESS" if success else "FAILED"

            st.markdown(
                f"""
                <div class="tool-card">
                    <div class="tool-title">
                        <span>🔧 <strong>Tool Name:</strong> <code>{tool_name}</code></span>
                        <span style="color: {status_color}; font-size: 0.78rem; font-weight: 600;">{status_text}</span>
                    </div>
                    <div class="tool-action">
                        <strong>Action (Input Parameters):</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Display parameters as formatted JSON
            if parameters:
                st.json(parameters, expanded=False)
            else:
                st.caption("No input parameters supplied.")

            st.markdown("<strong>Execution Result:</strong>", unsafe_allow_html=True)
            if isinstance(result, (dict, list)):
                st.json(result, expanded=True)
            else:
                st.code(str(result), language="text")
