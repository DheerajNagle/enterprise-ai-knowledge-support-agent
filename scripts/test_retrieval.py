"""
CLI Script to Test Knowledge Retrieval against Qdrant Vector Store.

Usage:
  python scripts/test_retrieval.py
  python scripts/test_retrieval.py "What is the remote work policy?"
  python scripts/test_retrieval.py "What is the daily meal allowance?" --top-k 3
"""

import argparse
import sys
from pathlib import Path

# Safe encoding for Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.config import get_settings
from app.rag.retriever import KnowledgeRetriever
from app.rag.vector_store import QdrantVectorStoreManager
from app.rag.embeddings import EmbeddingManager


def main():
    parser = argparse.ArgumentParser(description="Test Knowledge Retrieval from Qdrant")
    parser.add_argument(
        "query",
        nargs="?",
        default="What is the remote work policy?",
        help="Query to test (default: 'What is the remote work policy?')",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve (default: 5)",
    )
    parser.add_argument(
        "--filter-file",
        type=str,
        default=None,
        help="Optional filename to filter on (e.g. remote_work_policy.md)",
    )
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Disable lexical-semantic reranking",
    )

    args = parser.parse_args()

    settings = get_settings()
    print("=" * 75)
    print("  Enterprise AI Knowledge & Support Agent - Retrieval Test")
    print("=" * 75)
    print(f"Query:        '{args.query}'")
    print(f"Top-K:        {args.top_k}")
    print(f"Reranking:    {not args.no_rerank}")
    print(f"Collection:   {settings.QDRANT_COLLECTION_NAME}")
    if args.filter_file:
        print(f"File Filter:  {args.filter_file}")
    print("-" * 75)

    # Initialize retriever
    vector_store = QdrantVectorStoreManager()
    embedding_mgr = EmbeddingManager()
    retriever = KnowledgeRetriever(
        vector_store=vector_store,
        embedding_manager=embedding_mgr,
        min_score_threshold=0.0,  # return top matches for inspection
        enable_reranking=not args.no_rerank,
    )

    filter_criteria = {"filename": args.filter_file} if args.filter_file else None

    # Execute retrieval
    results = retriever.retrieve(
        query=args.query,
        top_k=args.top_k,
        filter_criteria=filter_criteria,
    )

    if not results:
        print("\n[-] No relevant chunks retrieved for this query.")
        vector_store.close()
        sys.exit(0)

    print(f"\n[+] Retrieved {len(results)} relevant chunks:\n")
    for i, res in enumerate(results, start=1):
        print(f"--- Result #{i} ---")
        print(f"Document:       {res.filename}")
        print(f"Section:        {res.section}")
        print(f"Chunk ID:       {res.chunk_id}")
        if res.page_number:
            print(f"Page:           {res.page_number}")
        print(f"Score:          {res.score:.4f}")
        print(f"Retrieved Text:\n{res.text.strip()}\n")

    print("=" * 75)
    vector_store.close()


if __name__ == "__main__":
    main()
