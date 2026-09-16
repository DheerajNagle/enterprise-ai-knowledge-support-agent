"""
MCP Policy Tools.

Exposes enterprise knowledge retrieval tools conforming to Model Context Protocol (MCP) v2.
Connects directly to the Qdrant vector store via KnowledgeRetriever.
"""

from typing import Any, Dict, List, Optional
from app.rag.retriever import KnowledgeRetriever, RetrievalResult


def execute_search_policy(
    query: str,
    department: Optional[str] = None,
    top_k: int = 3,
    retriever: Optional[KnowledgeRetriever] = None,
) -> Dict[str, Any]:
    """
    Business logic for searching enterprise policies and documents.
    """
    # 1. Input Validation
    if not query or not query.strip():
        return {
            "success": False,
            "error": "Query parameter cannot be empty.",
            "total_found": 0,
            "results": [],
        }

    clean_query = query.strip()
    clamped_k = max(1, min(int(top_k), 10))

    filter_criteria: Optional[Dict[str, Any]] = None
    if department and department.strip():
        filter_criteria = {"department": department.strip()}

    # 2. Execution via KnowledgeRetriever
    try:
        active_retriever = retriever or KnowledgeRetriever(min_score_threshold=0.20)
        results: List[RetrievalResult] = active_retriever.retrieve(
            query=clean_query,
            top_k=clamped_k,
            filter_criteria=filter_criteria,
            min_score=0.20,
        )

        structured_results = [
            {
                "chunk_id": r.chunk_id,
                "doc_id": r.doc_id,
                "filename": r.filename,
                "section": r.section,
                "page_number": r.page_number,
                "relevance_score": round(r.score, 4),
                "text": r.text,
            }
            for r in results
        ]

        return {
            "success": True,
            "query": clean_query,
            "department_filter": department.strip() if department else None,
            "total_found": len(structured_results),
            "results": structured_results,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Policy search failed: {str(exc)}",
            "total_found": 0,
            "results": [],
        }
