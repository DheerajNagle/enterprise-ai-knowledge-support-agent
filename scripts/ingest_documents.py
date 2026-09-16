"""
CLI Script to Ingest Enterprise Documents into Qdrant Vector Store.

Reads all policies and documentation from data/documents/,
generates embeddings, and stores them in the configured Qdrant collection.
Performs verification queries to ensure vectors exist and are searchable.
"""

import sys
from pathlib import Path

# Set UTF-8 encoding for Windows terminal output
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.config import get_settings
from app.rag.ingestion import DocumentIngestionPipeline
from app.rag.embeddings import EmbeddingManager
from app.rag.vector_store import QdrantVectorStoreManager


def main():
    settings = get_settings()
    print("=" * 70)
    print("  Enterprise AI Knowledge & Support Agent - Document Ingestion")
    print("=" * 70)
    print(f"Target Directory: data/documents")
    print(f"Qdrant URL:       {settings.QDRANT_URL}")
    print(f"Collection:       {settings.QDRANT_COLLECTION_NAME}")
    print(f"Embedding Model:  {settings.EMBEDDING_MODEL} (Dim: {settings.EMBEDDING_DIMENSION})")
    print(f"Gemini Active:    {settings.is_gemini_configured()}")
    print("-" * 70)

    # Initialize components
    vector_store = QdrantVectorStoreManager()
    embedding_mgr = EmbeddingManager()
    pipeline = DocumentIngestionPipeline(
        vector_store=vector_store,
        embedding_manager=embedding_mgr,
    )

    # Ingest documents
    print("\n[1/3] Starting Document Ingestion Pipeline...")
    report = pipeline.ingest_directory("data/documents")

    print(f"[+] Status:                       {report.status.upper()}")
    print(f"[+] Files Processed:              {report.files_processed}")
    print(f"[+] Chunks Created:               {report.chunks_created}")
    print(f"[+] Vectors Upserted:             {report.vectors_upserted}")
    print(f"[+] Total Vectors in Collection:  {report.total_vectors_in_collection}")
    print(f"[+] Elapsed Time:                 {report.elapsed_seconds}s")

    if report.total_vectors_in_collection == 0:
        print("\n[ERROR] Collection is empty! Ingestion failed.")
        sys.exit(1)

    # Verification: Query the vector store
    print("\n[2/3] Verifying Vector Store with Sample Semantic Queries...")
    test_queries = [
        "How do I fix VPN error 502?",
        "What is the maximum PTO rollover cap into the next year?",
        "What is the daily meal expense allowance for domestic travel?",
        "What are the laptop hardware refresh tiers?",
    ]

    all_passed = True
    for query in test_queries:
        query_vec = embedding_mgr.embed_text(query)
        hits = vector_store.search(query_vector=query_vec, limit=2)
        if not hits:
            print(f"  [-] Query failed (0 hits): '{query}'")
            all_passed = False
        else:
            top_hit = hits[0]
            print(f"  [+] Query: '{query}'")
            print(f"      -> Matched Doc:  {top_hit.filename} (Section: {top_hit.section})")
            print(f"      -> Score:        {top_hit.score:.4f}")
            print(f"      -> Snippet:      {top_hit.text[:120]}...")

    print("\n[3/3] Final Verification Check...")
    success = all_passed and report.total_vectors_in_collection > 0
    if success:
        print("[SUCCESS] All enterprise documents ingested and verified in Qdrant!")
        print("=" * 70)
    else:
        print("[ERROR] Vector verification checks did not succeed.")

    vector_store.close()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
