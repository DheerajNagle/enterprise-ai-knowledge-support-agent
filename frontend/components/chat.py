"""
Frontend Chat Component.

Handles the interactive conversation loop, multi-turn history, workflow badge
rendering (RAG, MCP, Direct LLM, RAG + MCP), and integrates citation & tool displays.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
from frontend.services.api_client import EnterpriseAPIClient, map_workflow_label
from frontend.components.rag_display import render_rag_sources
from frontend.components.tool_display import render_tool_executions


def render_workflow_pill(workflow_label: str) -> str:
    """Returns styled HTML badge for the active workflow."""
    css_class = "workflow-direct"
    if workflow_label == "RAG":
        css_class = "workflow-rag"
    elif workflow_label == "MCP":
        css_class = "workflow-mcp"
    elif workflow_label == "RAG + MCP":
        css_class = "workflow-hybrid"

    return f'<span class="workflow-pill {css_class}">Workflow: {workflow_label}</span>'


def render_chat_view(client: EnterpriseAPIClient, user_context: Dict[str, Any]):
    """
    Renders the conversational interface with multi-turn chat history.
    """
    st.markdown("### 💬 Enterprise AI Knowledge & Support Assistant")
    st.caption(
        "Ask corporate policy questions, query support procedures, or trigger enterprise actions. "
        "Every response clearly highlights the reasoning workflow, source citations, and tool actions."
    )

    # Initialize messages list in session state if missing
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I am your Enterprise AI Knowledge and Support Agent. "
                    "I can help you understand company policies (Remote Work, Leave, Code of Conduct), "
                    "check hardware or IT procedures, and create or look up support tickets. How may I assist you?"
                ),
                "workflow": "Direct LLM",
                "retrieved_knowledge": [],
                "tool_results": [],
                "confidence_score": 1.0,
            }
        ]

    # Render historical conversation turns
    for msg in st.session_state["messages"]:
        role = msg["role"]
        with st.chat_message(role):
            if role == "assistant":
                workflow_label = msg.get("workflow", "Direct LLM")
                pill_html = render_workflow_pill(workflow_label)
                
                conf = msg.get("confidence_score")
                conf_html = f'<span class="confidence-pill">Confidence: {conf:.0%}</span>' if conf is not None else ""
                
                st.markdown(f"{pill_html}{conf_html}", unsafe_allow_html=True)
                st.markdown(msg["content"])

                # Render RAG source citations if present
                if msg.get("retrieved_knowledge"):
                    render_rag_sources(msg["retrieved_knowledge"])

                # Render MCP tool executions if present
                if msg.get("tool_results"):
                    render_tool_executions(msg["tool_results"])
            else:
                st.markdown(msg["content"])

    # Chat Input Box
    user_prompt = st.chat_input(
        placeholder="Ask a policy question or request support (e.g. 'What is the remote work eligibility?')..."
    )

    if user_prompt:
        # Append user message immediately
        st.session_state["messages"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Prepare multi-turn history for backend
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state["messages"][:-1]  # Exclude current query
            if m["role"] in ("user", "assistant")
        ]

        # Call API
        with st.chat_message("assistant"):
            with st.spinner("Analyzing knowledge base and operational tools..."):
                response_result = client.send_chat(
                    message=user_prompt,
                    user_id=user_context.get("employee_id"),
                    department=user_context.get("department"),
                    conversation_history=history if history else None,
                )

            if response_result.success and response_result.data:
                data = response_result.data
                response_text = data.get("response", "No response text received.")
                raw_workflow = data.get("workflow")
                workflow_label = map_workflow_label(raw_workflow)
                retrieved_knowledge = data.get("retrieved_knowledge", [])
                tool_results = data.get("tool_results", [])
                conf = data.get("confidence_score", 1.0)

                # Render workflow and confidence badge
                pill_html = render_workflow_pill(workflow_label)
                conf_html = f'<span class="confidence-pill">Confidence: {conf:.0%}</span>'
                st.markdown(f"{pill_html}{conf_html}", unsafe_allow_html=True)

                st.markdown(response_text)

                if retrieved_knowledge:
                    render_rag_sources(retrieved_knowledge)

                if tool_results:
                    render_tool_executions(tool_results)

                # Save to session history
                st.session_state["messages"].append(
                    {
                        "role": "assistant",
                        "content": response_text,
                        "workflow": workflow_label,
                        "retrieved_knowledge": retrieved_knowledge,
                        "tool_results": tool_results,
                        "confidence_score": conf,
                    }
                )
            else:
                error_msg = response_result.error or "Failed to receive response from backend."
                st.error(f"❌ **API Error ({response_result.status_code}):** {error_msg}")
                st.session_state["messages"].append(
                    {
                        "role": "assistant",
                        "content": f"⚠️ *Error contacting backend:* {error_msg}",
                        "workflow": "Direct LLM",
                        "retrieved_knowledge": [],
                        "tool_results": [],
                        "confidence_score": 0.0,
                    }
                )
