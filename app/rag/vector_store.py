"""
Qdrant Vector Store Integration.

Manages connection to Qdrant (remote HTTP or local embedded storage),
collection creation, idempotent point upsert with metadata payloads,
and vector similarity search using the official Qdrant Python client.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from app.config import get_settings
from app.rag.chunking import DocumentChunk

logger = logging.getLogger("rag.vector_store")


class SearchResult(BaseModel):
    """Represents a retrieved chunk with similarity score."""

    chunk_id: str
    doc_id: str
    text: str
    filename: str
    section: str
    page_number: Optional[int] = None
    score: float
    payload: Dict[str, Any] = Field(default_factory=dict)


class QdrantVectorStoreManager:
    """Manages collection lifecycle and vector operations with Qdrant."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        local_path: Optional[str] = None,
        force_memory: bool = False,
    ):
        settings = get_settings()
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self.vector_size = vector_size or settings.EMBEDDING_DIMENSION
        self.local_path = local_path or "data/qdrant_storage"
        self.force_memory = force_memory

        self.client = self._initialize_client()

    def _initialize_client(self) -> QdrantClient:
        """
        Initializes QdrantClient.
        1. If force_memory is True, initializes in-memory client.
        2. Tries connecting to self.url over HTTP.
        3. If HTTP server is unreachable or offline, falls back seamlessly to local persistent path.
        """
        if self.force_memory:
            logger.info("Initializing in-memory Qdrant client (:memory:).")
            return QdrantClient(":memory:")

        # Attempt remote/local HTTP connection if URL starts with http
        if self.url and (self.url.startswith("http://") or self.url.startswith("https://")):
            try:
                client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key if self.api_key else None,
                    timeout=2.0,
                    check_compatibility=False,
                )
                # Test connectivity
                client.get_collections()
                logger.info(f"Connected to live Qdrant service at {self.url}.")
                return client
            except Exception as e:
                logger.warning(
                    f"Could not connect to Qdrant service at {self.url} ({e}). "
                    f"Falling back to local persistent embedded storage at {self.local_path}."
                )

        # Fallback to local on-disk persistence
        logger.info(f"Using local embedded Qdrant client at {self.local_path}.")
        return QdrantClient(path=self.local_path)

    def ensure_collection(self, vector_size: Optional[int] = None) -> None:
        """
        Creates the Qdrant collection if it does not already exist,
        configuring cosine distance and HNSW index.
        """
        size = vector_size or self.vector_size
        existing = [c.name for c in self.client.get_collections().collections]

        if self.collection_name not in existing:
            logger.info(
                f"Creating Qdrant collection '{self.collection_name}' with vector size {size}."
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=size,
                    distance=models.Distance.COSINE,
                ),
            )
        else:
            logger.debug(f"Collection '{self.collection_name}' already exists.")

    @staticmethod
    def chunk_id_to_uuid(chunk_id: str) -> str:
        """
        Generates a deterministic UUID from chunk_id (UUID v5).
        Ensures idempotency in Qdrant (re-indexing overwrites rather than duplicates).
        """
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

    def upsert_chunks(
        self,
        chunks: List[DocumentChunk],
        vectors: List[List[float]],
    ) -> int:
        """
        Upserts chunks with their embedding vectors and metadata payloads into Qdrant.
        Returns the number of points upserted.
        """
        if len(chunks) != len(vectors):
            raise ValueError(
                f"Mismatch: received {len(chunks)} chunks and {len(vectors)} vectors."
            )

        if not chunks:
            return 0

        # Ensure collection exists
        vector_dim = len(vectors[0])
        self.ensure_collection(vector_size=vector_dim)

        points: List[models.PointStruct] = []
        for chunk, vector in zip(chunks, vectors):
            point_id = self.chunk_id_to_uuid(chunk.chunk_id)
            payload = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "text": chunk.text,
                "filename": chunk.filename,
                "document_type": chunk.document_type,
                "section": chunk.section,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "character_count": chunk.character_count,
                "content_hash": chunk.content_hash,
                **chunk.metadata,
            }

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        # Batch upsert
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

        logger.info(
            f"Successfully upserted {len(points)} vectors into '{self.collection_name}'."
        )
        return len(points)

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Performs cosine similarity search against the collection.
        Returns a list of SearchResult objects sorted by score descending.
        """
        self.ensure_collection(vector_size=len(query_vector))

        qdrant_filter = None
        if filter_criteria:
            conditions = []
            for key, val in filter_criteria.items():
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=val),
                    )
                )
            if conditions:
                qdrant_filter = models.Filter(must=conditions)

        hits = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
            with_payload=True,
        ).points

        results: List[SearchResult] = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                SearchResult(
                    chunk_id=payload.get("chunk_id", str(hit.id)),
                    doc_id=payload.get("doc_id", "unknown"),
                    text=payload.get("text", ""),
                    filename=payload.get("filename", "unknown"),
                    section=payload.get("section", "General"),
                    page_number=payload.get("page_number"),
                    score=float(hit.score),
                    payload=payload,
                )
            )

        return results

    def count_vectors(self) -> int:
        """Returns the total number of points in the collection."""
        try:
            return self.client.count(collection_name=self.collection_name).count
        except Exception:
            return 0

    def close(self) -> None:
        """Closes the underlying client connection cleanly."""
        try:
            self.client.close()
        except Exception:
            pass

    def delete_collection(self) -> bool:
        """Deletes the collection (useful for full re-indexing and testing)."""
        try:
            return self.client.delete_collection(collection_name=self.collection_name)
        except Exception:
            return False
