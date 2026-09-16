"""
Frontend Sidebar Component.

Provides connection status diagnostics, masked API credentials configuration,
employee context settings, and session lifecycle controls.
"""

import streamlit as st
from typing import Optional, Dict, Any
from frontend.services.api_client import EnterpriseAPIClient


def render_sidebar(client: EnterpriseAPIClient) -> Dict[str, Any]:
    """
    Renders the sidebar navigation and configuration controls.
    Returns the active user context (user_id, department).
    """
    with st.sidebar:
        st.markdown("### 🏢 Enterprise Console")
        st.caption("AI Knowledge & Support Platform")

        # ----------------------------------------------------------------------
        # 1. API Connection Status
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 📡 System Connection")
        
        health_result = client.check_health()
        if health_result.success and health_result.data:
            health_data = health_result.data
            overall_status = health_data.get("status", "unknown").lower()
            
            if overall_status == "healthy":
                st.markdown(
                    '<span class="status-dot status-dot-green"></span> **Status:** <span style="color:#10B981;font-weight:600;">ONLINE (Healthy)</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span class="status-dot status-dot-amber"></span> **Status:** <span style="color:#F59E0B;font-weight:600;">DEGRADED</span>',
                    unsafe_allow_html=True,
                )

            with st.expander("Subsystem Diagnostics", expanded=False):
                components = health_data.get("components", {})
                for comp_name, comp_info in components.items():
                    c_status = comp_info.get("status", "unknown") if isinstance(comp_info, dict) else str(comp_info)
                    icon = "🟢" if c_status in ("healthy", "online") else ("🟡" if c_status in ("idle", "degraded", "offline_fallback") else "🔴")
                    st.write(f"{icon} **{comp_name.replace('_', ' ').title()}:** `{c_status}`")
                
                st.caption(f"App Version: `{health_data.get('version', '0.1.0')}`")
                st.caption(f"Environment: `{health_data.get('environment', 'dev')}`")
        else:
            st.markdown(
                '<span class="status-dot status-dot-red"></span> **Status:** <span style="color:#EF4444;font-weight:600;">DISCONNECTED</span>',
                unsafe_allow_html=True,
            )
            st.error(health_result.error or "Cannot reach FastAPI backend.")

        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()

        # ----------------------------------------------------------------------
        # 2. Connection Settings (Masked Credentials)
        # ----------------------------------------------------------------------
        st.markdown("---")
        with st.expander("⚙️ Connection Settings", expanded=False):
            new_url = st.text_input(
                "API Gateway URL",
                value=st.session_state.get("api_base_url", "http://127.0.0.1:8000"),
                help="Backend FastAPI server endpoint",
            )
            new_key = st.text_input(
                "API Authentication Key",
                value=st.session_state.get("api_key", "dev-insecure-api-key-replace-in-prod"),
                type="password",
                help="Secret token for X-API-Key header. Never exposed in UI or logs.",
            )
            if new_url != st.session_state.get("api_base_url") or new_key != st.session_state.get("api_key"):
                st.session_state["api_base_url"] = new_url
                st.session_state["api_key"] = new_key
                st.success("Settings updated! Reconnecting...")
                st.rerun()

        # ----------------------------------------------------------------------
        # 3. Employee Context Configuration
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 👤 Employee Context")
        employee_id = st.text_input(
            "Employee ID",
            value=st.session_state.get("employee_id", "EMP-001"),
            help="Associated employee ID for tickets and audit logs",
        )
        st.session_state["employee_id"] = employee_id

        departments = ["All", "Engineering", "Human Resources", "Finance", "Operations", "Legal", "Product"]
        selected_dept = st.selectbox(
            "Department Scope",
            options=departments,
            index=0,
            help="Filters knowledge retrieval to relevant department policies",
        )
        department_filter = None if selected_dept == "All" else selected_dept

        # ----------------------------------------------------------------------
        # 4. Session Controls
        # ----------------------------------------------------------------------
        st.markdown("---")
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state["messages"] = []
            st.success("Chat history cleared.")
            st.rerun()

        return {
            "employee_id": employee_id,
            "department": department_filter,
            "is_connected": health_result.success,
        }
