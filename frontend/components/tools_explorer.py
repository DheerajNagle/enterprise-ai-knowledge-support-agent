"""
Frontend MCP Tools Explorer Component.

Inspects registered Model Context Protocol tools, parameter schemas, and
provides a direct invocation sandbox for administrators and testing.
"""

import json
import streamlit as st
from frontend.services.api_client import EnterpriseAPIClient


def render_tools_explorer_view(client: EnterpriseAPIClient):
    """Renders the MCP Tools and System Diagnostics Explorer."""
    st.markdown("### 🛠️ MCP Tools & Subsystem Registry")
    st.caption("Inspect registered Model Context Protocol operational tools, JSON schemas, and test tool invocations.")

    tools_result = client.list_tools()
    if not tools_result.success or not tools_result.data:
        st.warning(f"Could not retrieve tools catalog: {tools_result.error}")
        return

    tools = tools_result.data.get("tools", [])
    count = tools_result.data.get("count", len(tools))
    st.markdown(f"**Registered Tools Catalog ({count} Available)**")

    if not tools:
        st.info("No MCP tools are currently registered in the catalog.")
        return

    tool_names = [t.get("name") for t in tools]
    selected_tool_name = st.selectbox("Select Tool to Inspect or Test", options=tool_names)

    selected_tool = next((t for t in tools if t.get("name") == selected_tool_name), None)
    if selected_tool:
        st.markdown(f"#### Tool: `/{selected_tool.get('name')}`")
        st.markdown(f"*{selected_tool.get('description', 'No description provided.')}*")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Parameter Schema")
            schema = selected_tool.get("input_schema", {})
            st.json(schema)

        with col2:
            st.markdown("##### Test Invocation Sandbox")
            # Generate default json template from properties
            props = schema.get("properties", {})
            default_args = {k: "sample_value" if v.get("type") == "string" else 1 for k, v in props.items()}
            
            args_input = st.text_area(
                "Arguments (JSON)",
                value=json.dumps(default_args, indent=2),
                height=180,
            )

            if st.button(f"⚡ Execute {selected_tool_name}", use_container_width=True):
                try:
                    parsed_args = json.loads(args_input) if args_input.strip() else {}
                    with st.spinner(f"Executing {selected_tool_name} via MCP..."):
                        exec_res = client.execute_tool(selected_tool_name, parsed_args)

                    if exec_res.success and exec_res.data:
                        out = exec_res.data
                        st.success(f"Execution completed in {out.get('execution_time_seconds', 0.0):.3f}s")
                        st.markdown("**Result Payload:**")
                        st.json(out.get("result"))
                    else:
                        st.error(f"❌ Execution failed ({exec_res.status_code}): {exec_res.error}")
                except json.JSONDecodeError as err:
                    st.error(f"Invalid JSON in arguments: {err}")
