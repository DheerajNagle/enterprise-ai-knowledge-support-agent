"""
Frontend RAG Source & Citation Display Component.

Renders retrieved knowledge chunks, document names, sections, relevance scores,
and context text in a clean, executive accordion view.
"""

import streamlit as st
from typing import Any, Dict, List, Optional


def render_rag_sources(retrieved_knowledge: Optional[List[Dict[str, Any]]]):
    """
    Renders RAG citations and retrieved context blocks.
    Strictly displays document, section, and retrieved context/source.
    """
    if not retrieved_knowledge:
        return

    count = len(retrieved_knowledge)
    with st.expander(f"📚 Retrieved Knowledge Sources ({count})", expanded=False):
        for idx, item in enumerate(retrieved_knowledge, 1):
            filename = item.get("filename", "Unknown Document")
            section = item.get("section", "General")
            chunk_text = item.get("chunk_text", "")
            relevance = item.get("relevance_score")
            page_number = item.get("page_number")
            citation = item.get("citation", f"[Source: {filename}]")

            relevance_display = f"{float(relevance):.2f}" if relevance is not None else "N/A"
            page_display = f" | Page: {page_number}" if page_number else ""

            st.markdown(
                f"""
                <div class="citation-card">
                    <div class="citation-title">
                        <span>📄 <strong>Document:</strong> {filename}</span>
                        <span class="confidence-pill">Score: {relevance_display}</span>
                    </div>
                    <div class="citation-meta">
                        <strong>Section:</strong> {section}{page_display} &nbsp;|&nbsp; <em>{citation}</em>
                    </div>
                    <div class="citation-snippet">
                        {chunk_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
