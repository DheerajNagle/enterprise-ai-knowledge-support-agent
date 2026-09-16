"""
Frontend Support Ticket Management Component.

Provides interfaces for:
1. Creating employee support tickets via POST /api/tickets.
2. Looking up ticket status and resolution notes via GET /api/tickets/{ticket_id}.
"""

import streamlit as st
from typing import Any, Dict
from frontend.services.api_client import EnterpriseAPIClient


def render_tickets_view(client: EnterpriseAPIClient, user_context: Dict[str, Any]):
    """Renders the Support Ticket Center."""
    st.markdown("### 🎫 Enterprise Ticket Center")
    st.caption("Submit new support requests or monitor real-time resolution status.")

    tab_create, tab_lookup = st.tabs(["📝 Submit New Ticket", "🔍 Track Ticket Status"])

    # --------------------------------------------------------------------------
    # Tab 1: Create Ticket
    # --------------------------------------------------------------------------
    with tab_create:
        st.markdown("#### Submit a Support Ticket")
        with st.form("create_ticket_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                emp_id = st.text_input(
                    "Employee ID *",
                    value=user_context.get("employee_id", "EMP-001"),
                    help="Valid employee identifier (e.g., EMP-001)",
                )
                category = st.selectbox(
                    "Category *",
                    options=["GENERAL", "HARDWARE", "SOFTWARE", "NETWORK", "ACCESS", "HR", "FACILITIES"],
                    index=0,
                )
            with col2:
                priority = st.selectbox(
                    "Priority *",
                    options=["LOW", "MEDIUM", "HIGH", "URGENT"],
                    index=1,
                )
                title = st.text_input(
                    "Ticket Title *",
                    placeholder="e.g., Need secondary monitor for home office",
                )

            description = st.text_area(
                "Description *",
                placeholder="Provide detailed description of the request or problem...",
                height=120,
            )

            submitted = st.form_submit_button("🚀 Submit Support Ticket", use_container_width=True)

        if submitted:
            if not title or not description:
                st.error("Please provide both a ticket title and a detailed description.")
            else:
                with st.spinner("Submitting ticket to enterprise database..."):
                    result = client.create_ticket(
                        employee_id=emp_id.strip(),
                        title=title.strip(),
                        description=description.strip(),
                        category=category,
                        priority=priority,
                    )

                if result.success and result.data:
                    ticket = result.data
                    t_id = ticket.get("ticket_id", "TCK-UNKNOWN")
                    st.success(f"✅ Ticket created successfully! Assigned Ticket ID: **`{t_id}`**")
                    
                    with st.container():
                        st.markdown(
                            f"""
                            <div class="tool-card">
                                <div class="tool-title">
                                    <span>🎫 Ticket ID: <code>{t_id}</code></span>
                                    <span style="color:#F59E0B;font-weight:600;">STATUS: {ticket.get('status', 'OPEN')}</span>
                                </div>
                                <p><strong>Employee:</strong> {ticket.get('employee_id')} | <strong>Category:</strong> {ticket.get('category')} | <strong>Priority:</strong> {ticket.get('priority')}</p>
                                <p><strong>Title:</strong> {ticket.get('title')}</p>
                                <p><strong>Created:</strong> {ticket.get('created_at')}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.error(f"❌ Failed to create ticket ({result.status_code}): {result.error}")

    # --------------------------------------------------------------------------
    # Tab 2: Ticket Status Lookup
    # --------------------------------------------------------------------------
    with tab_lookup:
        st.markdown("#### Track Support Ticket Status")
        lookup_col1, lookup_col2 = st.columns([3, 1])
        with lookup_col1:
            search_ticket_id = st.text_input(
                "Ticket ID",
                placeholder="e.g., TCK-2026-000001",
                help="Enter unique ticket identifier",
            )
        with lookup_col2:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            search_btn = st.button("🔍 Check Status", use_container_width=True)

        if search_btn or search_ticket_id:
            if not search_ticket_id.strip():
                st.warning("Please enter a valid Ticket ID.")
            else:
                with st.spinner(f"Looking up ticket {search_ticket_id.strip()}..."):
                    lookup_result = client.get_ticket(search_ticket_id.strip())

                if lookup_result.success and lookup_result.data:
                    t = lookup_result.data
                    status_val = t.get("status", "OPEN").upper()
                    
                    status_color = "#10B981" if status_val == "RESOLVED" else ("#38BDF8" if status_val == "IN_PROGRESS" else "#F59E0B")
                    
                    st.markdown(
                        f"""
                        <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 18px; margin-top: 14px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
                                <h4 style="margin:0; color:#F8FAFC;">🎫 Ticket: <code>{t.get('ticket_id')}</code></h4>
                                <span style="background: rgba(255,255,255,0.1); color: {status_color}; padding: 4px 12px; border-radius: 16px; font-weight: 700; font-size: 0.85rem;">
                                    {status_val}
                                </span>
                            </div>
                            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.9rem; color: #CBD5E1; margin-bottom: 12px;">
                                <div><strong>Employee ID:</strong> {t.get('employee_id')}</div>
                                <div><strong>Priority:</strong> {t.get('priority')}</div>
                                <div><strong>Category:</strong> {t.get('category')}</div>
                                <div><strong>Created At:</strong> {t.get('created_at')}</div>
                            </div>
                            <hr style="border-color: rgba(255,255,255,0.08);"/>
                            <h5 style="color:#E2E8F0; margin-top: 10px;">{t.get('title')}</h5>
                            <p style="color:#94A3B8; font-size: 0.9rem;">{t.get('description')}</p>
                            {"<div style='background:rgba(16,185,129,0.1); border-left: 3px solid #10B981; padding: 8px 12px; border-radius: 4px; margin-top: 12px;'><strong>Resolution Notes:</strong> " + str(t.get('resolution_notes')) + "</div>" if t.get('resolution_notes') else ""}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(f"❌ {lookup_result.error or 'Ticket not found.'}")
