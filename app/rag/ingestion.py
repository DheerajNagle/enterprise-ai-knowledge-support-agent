"""
Document Ingestion Pipeline.

End-to-end orchestration:
Documents -> Loading -> Sanitizing -> Chunking -> Metadata -> Embeddings -> Qdrant.
Idempotent and repeatable.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field
from app.rag.loaders import DocumentLoader, LoadedDocument
from app.rag.chunking import DocumentChunker, DocumentChunk
from app.rag.embeddings import EmbeddingManager
from app.rag.vector_store import QdrantVectorStoreManager

logger = logging.getLogger("rag.ingestion")


class IngestionReport(BaseModel):
    """Execution metrics and summary for document ingestion."""

    status: str
    files_processed: int
    documents_loaded: int
    chunks_created: int
    vectors_upserted: int
    total_vectors_in_collection: int
    elapsed_seconds: float
    details: List[Dict[str, Any]] = Field(default_factory=list)


class DocumentIngestionPipeline:
    """Orchestrates the complete document ingestion pipeline into Qdrant."""

    def __init__(
        self,
        vector_store: Optional[QdrantVectorStoreManager] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        chunker: Optional[DocumentChunker] = None,
    ):
        self.vector_store = vector_store or QdrantVectorStoreManager()
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.chunker = chunker or DocumentChunker()

    def ingest_files(
        self, file_paths: List[Union[str, Path]]
    ) -> IngestionReport:
        """Ingests a specified list of file paths into Qdrant."""
        start_time = time.time()
        all_chunks: List[DocumentChunk] = []
        details: List[Dict[str, Any]] = []

        for p in file_paths:
            path = Path(p)
            try:
                docs = DocumentLoader.load_file(path)
                chunks = self.chunker.chunk_documents(docs)
                all_chunks.extend(chunks)
                details.append(
                    {
                        "file": path.name,
                        "status": "success",
                        "pages": len(docs),
                        "chunks": len(chunks),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to load/chunk {path.name}: {e}")
                details.append(
                    {
                        "file": path.name,
                        "status": "error",
                        "error": str(e),
                    }
                )

        if not all_chunks:
            return IngestionReport(
                status="empty",
                files_processed=len(file_paths),
                documents_loaded=0,
                chunks_created=0,
                vectors_upserted=0,
                total_vectors_in_collection=self.vector_store.count_vectors(),
                elapsed_seconds=time.time() - start_time,
                details=details,
            )

        # Generate embeddings in batch
        texts = [chunk.text for chunk in all_chunks]
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        vectors = self.embedding_manager.embed_batch(texts)

        # Upsert into Qdrant
        upserted_count = self.vector_store.upsert_chunks(
            chunks=all_chunks,
            vectors=vectors,
        )

        total_in_collection = self.vector_store.count_vectors()
        elapsed = round(time.time() - start_time, 3)

        return IngestionReport(
            status="success",
            files_processed=len(file_paths),
            documents_loaded=len(file_paths),
            chunks_created=len(all_chunks),
            vectors_upserted=upserted_count,
            total_vectors_in_collection=total_in_collection,
            elapsed_seconds=elapsed,
            details=details,
        )

    def ingest_directory(
        self, directory_path: Union[str, Path] = "data/documents"
    ) -> IngestionReport:
        """Discovers and ingests all supported documents in a directory."""
        dir_path = Path(directory_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"Documents directory not found: {dir_path}")

        supported_files: List[Path] = []
        for item in sorted(dir_path.glob("**/*")):
            if item.is_file() and item.suffix.lower() in DocumentLoader.SUPPORTED_EXTENSIONS:
                supported_files.append(item)

        logger.info(f"Found {len(supported_files)} supported documents in {dir_path}.")
        return self.ingest_files(supported_files)
