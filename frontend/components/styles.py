"""
Frontend UI Design System & CSS Styles.

Provides executive styling tokens, responsive badges, glassmorphic cards,
and modern typography to deliver a clean, professional enterprise experience.
"""

import streamlit as st


def apply_custom_styles():
    """Injects custom CSS stylesheets into the Streamlit app."""
    st.markdown(
        """
        <style>
        /* Modern Font and Base Polish */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* Top Header Banner */
        .enterprise-header {
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 24px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        .enterprise-header h1 {
            color: #F8FAFC !important;
            font-size: 1.6rem !important;
            font-weight: 700 !important;
            margin: 0 0 6px 0 !important;
            letter-spacing: -0.02em;
        }
        .enterprise-header p {
            color: #94A3B8 !important;
            font-size: 0.95rem !important;
            margin: 0 !important;
        }

        /* Workflow Status Badges */
        .workflow-pill {
            display: inline-flex;
            align-items: center;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-right: 8px;
        }
        .workflow-rag {
            background-color: rgba(79, 70, 229, 0.15);
            color: #6366F1;
            border: 1px solid rgba(99, 102, 241, 0.35);
        }
        .workflow-mcp {
            background-color: rgba(217, 119, 6, 0.15);
            color: #F59E0B;
            border: 1px solid rgba(245, 158, 11, 0.35);
        }
        .workflow-hybrid {
            background: linear-gradient(135deg, rgba(124, 58, 237, 0.18) 0%, rgba(79, 70, 229, 0.18) 100%);
            color: #A855F7;
            border: 1px solid rgba(168, 85, 247, 0.4);
        }
        .workflow-direct {
            background-color: rgba(2, 132, 199, 0.15);
            color: #38BDF8;
            border: 1px solid rgba(56, 189, 248, 0.35);
        }

        /* Metric Pill */
        .confidence-pill {
            display: inline-flex;
            align-items: center;
            font-size: 0.76rem;
            font-weight: 500;
            padding: 2px 8px;
            border-radius: 6px;
            background-color: rgba(16, 185, 129, 0.12);
            color: #10B981;
            border: 1px solid rgba(16, 185, 129, 0.25);
            margin-left: 6px;
        }

        /* Citation & Source Card */
        .citation-card {
            background: rgba(30, 41, 59, 0.5);
            border-left: 3px solid #6366F1;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 0 8px 8px 0;
            padding: 10px 14px;
            margin: 8px 0;
            font-size: 0.88rem;
        }
        .citation-title {
            font-weight: 600;
            color: #E2E8F0;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .citation-meta {
            color: #94A3B8;
            font-size: 0.78rem;
            margin-bottom: 6px;
        }
        .citation-snippet {
            color: #CBD5E1;
            background: rgba(15, 23, 42, 0.6);
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 0.82rem;
            line-height: 1.45;
            font-family: monospace;
        }

        /* Tool Execution Card */
        .tool-card {
            background: rgba(30, 41, 59, 0.5);
            border-left: 3px solid #F59E0B;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 0 8px 8px 0;
            padding: 10px 14px;
            margin: 8px 0;
            font-size: 0.88rem;
        }
        .tool-title {
            font-weight: 600;
            color: #FDE68A;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .tool-action {
            color: #94A3B8;
            font-size: 0.78rem;
            margin-bottom: 6px;
        }

        /* Status Dot */
        .status-dot {
            height: 8px;
            width: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        .status-dot-green {
            background-color: #10B981;
            box-shadow: 0 0 6px #10B981;
        }
        .status-dot-amber {
            background-color: #F59E0B;
            box-shadow: 0 0 6px #F59E0B;
        }
        .status-dot-red {
            background-color: #EF4444;
            box-shadow: 0 0 6px #EF4444;
        }

        /* Subtle borders and clean container spacing */
        div[data-testid="stExpander"] {
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
            margin-top: 6px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
