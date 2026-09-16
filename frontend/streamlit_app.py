"""
Enterprise AI Knowledge & Support Agent — Streamlit Web Console.

Executive frontend delivering conversational policy guidance, source citations,
MCP tool execution tracing, ticket creation & lookup, and document ingestion.
"""

import os
import streamlit as st

# Set page configuration before rendering any UI elements
st.set_page_config(
    page_title="Enterprise AI Knowledge & Support Agent",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

from frontend.services.api_client import EnterpriseAPIClient
from frontend.components.styles import apply_custom_styles
from frontend.components.sidebar import render_sidebar
from frontend.components.chat import render_chat_view
from frontend.components.tickets import render_tickets_view
from frontend.components.documents import render_documents_view
from frontend.components.tools_explorer import render_tools_explorer_view


def main():
    """Main application lifecycle and view router."""
    # 1. Apply customized CSS design tokens
    apply_custom_styles()

    # 2. Initialize connection credentials in session state
    if "api_base_url" not in st.session_state:
        st.session_state["api_base_url"] = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    if "api_key" not in st.session_state:
        st.session_state["api_key"] = os.getenv("API_KEY", "dev-insecure-api-key-replace-in-prod")

    # 3. Instantiate frontend API client (never runs agent/db logic in Streamlit)
    client = EnterpriseAPIClient(
        base_url=st.session_state["api_base_url"],
        api_key=st.session_state["api_key"],
    )

    # 4. Render sidebar navigation & connection telemetry
    user_context = render_sidebar(client)

    # 5. Render Executive Header
    st.markdown(
        """
        <div class="enterprise-header">
            <h1>🏢 Enterprise AI Knowledge & Support Agent</h1>
            <p>Google ADK Multi-Tier Orchestrator &nbsp;|&nbsp; FastMCP Operational Tools &nbsp;|&nbsp; Hybrid Qdrant Vector Retrieval</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 6. Primary navigation tabs
    tab_chat, tab_tickets, tab_documents, tab_tools = st.tabs(
        [
            "💬 Knowledge & Support Chat",
            "🎫 Support Ticket Center",
            "📄 Document Ingestion",
            "🛠️ MCP Tools & Diagnostics",
        ]
    )

    with tab_chat:
        render_chat_view(client, user_context)

    with tab_tickets:
        render_tickets_view(client, user_context)

    with tab_documents:
        render_documents_view(client)

    with tab_tools:
        render_tools_explorer_view(client)


if __name__ == "__main__":
    main()
