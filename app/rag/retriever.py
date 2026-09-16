"""
Knowledge Retrieval Subsystem for Enterprise RAG.

Executes query embedding, Qdrant vector similarity search, metadata filtering,
and optional reranking to return structured, citation-ready relevance results.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.config import get_settings
from app.rag.embeddings import EmbeddingManager
from app.rag.vector_store import QdrantVectorStoreManager, SearchResult
from app.rag.reranker import BaseReranker, LexicalSemanticReranker

logger = logging.getLogger("rag.retriever")


class RetrievalResult(BaseModel):
    """
    Structured retrieval result returned by the KnowledgeRetriever.
    Contains the full chunk text, document location, and relevance score.
    """

    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Document identifier")
    text: str = Field(..., description="Extracted passage text")
    filename: str = Field(..., description="Source document filename")
    section: str = Field(default="General", description="Section or heading title")
    page_number: Optional[int] = Field(
        default=None, description="Source page number if available"
    )
    score: float = Field(..., description="Similarity or relevance score")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Supplementary metadata payload"
    )


class KnowledgeRetriever:
    """
    Enterprise Knowledge Retriever.
    Orchestrates Query -> Embedding -> Qdrant Vector Search -> Metadata Filtering -> Reranking.
    """

    def __init__(
        self,
        vector_store: Optional[QdrantVectorStoreManager] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        reranker: Optional[BaseReranker] = None,
        min_score_threshold: Optional[float] = None,
        enable_reranking: bool = True,
    ):
        settings = get_settings()
        self.vector_store = vector_store or QdrantVectorStoreManager()
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.min_score_threshold = (
            min_score_threshold
            if min_score_threshold is not None
            else settings.SIMILARITY_THRESHOLD
        )

        # Initialize reranker
        if reranker is not None:
            self.reranker = reranker
        elif enable_reranking:
            self.reranker = LexicalSemanticReranker()
        else:
            self.reranker = None

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieves top-k relevant chunks for a user inquiry.

        Args:
            query: User search question or keyword query.
            top_k: Number of highest-ranked results to return (default: 5).
            filter_criteria: Optional metadata payload filters (e.g. {"filename": "vpn_policy.md"}).
            min_score: Optional minimum similarity threshold.

        Returns:
            List of RetrievalResult objects sorted by relevance score descending.
        """
        query_clean = query.strip()
        if not query_clean:
            return []

        threshold = min_score if min_score is not None else self.min_score_threshold

        # 1. Generate query embedding vector
        query_vector = self.embedding_manager.embed_text(query_clean)

        # 2. Overfetch candidates if reranking is enabled to give reranker a diverse candidate pool
        fetch_limit = max(top_k * 2, 10) if self.reranker else top_k

        # 3. Vector search in Qdrant
        raw_hits: List[SearchResult] = self.vector_store.search(
            query_vector=query_vector,
            limit=fetch_limit,
            score_threshold=threshold,
            filter_criteria=filter_criteria,
        )

        # 4. Map to structured RetrievalResult
        results: List[RetrievalResult] = [
            RetrievalResult(
                chunk_id=hit.chunk_id,
                doc_id=hit.doc_id,
                text=hit.text,
                filename=hit.filename,
                section=hit.section,
                page_number=hit.page_number,
                score=round(hit.score, 4),
                metadata=hit.payload,
            )
            for hit in raw_hits
        ]

        # 5. Apply reranking if configured
        if self.reranker and results:
            results = self.reranker.rerank(
                query=query_clean,
                results=results,
                top_k=top_k,
            )
        else:
            results = results[:top_k]

        return results
