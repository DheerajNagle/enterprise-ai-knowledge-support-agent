"""
Retrieval-Augmented Generation (RAG) Subsystem.

Provides document loading, text cleaning, semantic chunking,
embedding generation, and vector indexing into Qdrant.
"""

from app.rag.loaders import DocumentLoader, LoadedDocument
from app.rag.chunking import DocumentChunker, DocumentChunk
from app.rag.embeddings import EmbeddingManager
from app.rag.vector_store import QdrantVectorStoreManager
from app.rag.ingestion import DocumentIngestionPipeline
from app.rag.retriever import KnowledgeRetriever, RetrievalResult
from app.rag.reranker import BaseReranker, LexicalSemanticReranker, NoOpReranker

__all__ = [
    "DocumentLoader",
    "LoadedDocument",
    "DocumentChunker",
    "DocumentChunk",
    "EmbeddingManager",
    "QdrantVectorStoreManager",
    "DocumentIngestionPipeline",
    "KnowledgeRetriever",
    "RetrievalResult",
    "BaseReranker",
    "LexicalSemanticReranker",
    "NoOpReranker",
]
