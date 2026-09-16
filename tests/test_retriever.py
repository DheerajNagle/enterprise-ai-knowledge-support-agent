"""
Unit and Integration Tests for Knowledge Retriever and Reranker.

Tests relevant document retrieval, irrelevant query handling, metadata preservation,
top-k constraints, metadata filtering, and reranker functionality.
"""

import pytest
from app.rag.loaders import LoadedDocument
from app.rag.chunking import DocumentChunk, DocumentChunker
from app.rag.embeddings import EmbeddingManager
from app.rag.vector_store import QdrantVectorStoreManager
from app.rag.retriever import KnowledgeRetriever, RetrievalResult
from app.rag.reranker import LexicalSemanticReranker, NoOpReranker


@pytest.fixture
def in_memory_retriever():
    """Initializes an in-memory vector store with seeded test chunks."""
    vector_store = QdrantVectorStoreManager(
        collection_name="test_retriever_collection",
        vector_size=768,
        force_memory=True,
    )
    embedding_mgr = EmbeddingManager(dimension=768)

    test_chunks = [
        DocumentChunk(
            chunk_id="DOC-remote:p1:c0",
            doc_id="DOC-remote",
            text="Employees on hybrid model must be in the corporate office on Tuesdays and Thursdays.",
            filename="remote_work_policy.md",
            document_type="markdown",
            section="2.1 Hybrid Model",
            page_number=1,
            chunk_index=0,
            character_count=85,
            content_hash="hash0",
            metadata={"department": "Operations"},
        ),
        DocumentChunk(
            chunk_id="DOC-remote:p1:c1",
            doc_id="DOC-remote",
            text="One-time ergonomic home office stipend allows up to $750 reimbursement for desks and chairs.",
            filename="remote_work_policy.md",
            document_type="markdown",
            section="3.1 Ergonomic Stipend",
            page_number=1,
            chunk_index=1,
            character_count=93,
            content_hash="hash1",
            metadata={"department": "Operations"},
        ),
        DocumentChunk(
            chunk_id="DOC-vpn:p1:c0",
            doc_id="DOC-vpn",
            text="GlobalProtect VPN connection error 502 indicates DNS or captive portal timeout.",
            filename="vpn_policy.md",
            document_type="markdown",
            section="7. Troubleshooting",
            page_number=1,
            chunk_index=0,
            character_count=79,
            content_hash="hash2",
            metadata={"department": "Security"},
        ),
        DocumentChunk(
            chunk_id="DOC-laptop:p1:c0",
            doc_id="DOC-laptop",
            text="Laptops are provisioned on a strict 36-month refresh cycle from original deployment.",
            filename="laptop_policy.md",
            document_type="markdown",
            section="3. Refresh Lifecycle",
            page_number=1,
            chunk_index=0,
            character_count=84,
            content_hash="hash3",
            metadata={"department": "IT Hardware"},
        ),
        DocumentChunk(
            chunk_id="DOC-leave:p1:c0",
            doc_id="DOC-leave",
            text="Full-time employees receive 24 days annual vacation with a maximum 5-day rollover into Q1.",
            filename="leave_policy.md",
            document_type="markdown",
            section="2.1 Annual Vacation",
            page_number=1,
            chunk_index=0,
            character_count=90,
            content_hash="hash4",
            metadata={"department": "HR"},
        ),
    ]

    vectors = embedding_mgr.embed_batch([c.text for c in test_chunks])
    vector_store.upsert_chunks(test_chunks, vectors)

    retriever = KnowledgeRetriever(
        vector_store=vector_store,
        embedding_manager=embedding_mgr,
        min_score_threshold=0.0,
        enable_reranking=True,
    )
    return retriever


# ==============================================================================
# 1. Relevant Document Retrieval Tests
# ==============================================================================


def test_relevant_document_retrieval(in_memory_retriever):
    """Verify that a specific topic query retrieves the relevant document and section."""
    results = in_memory_retriever.retrieve(
        query="What is the remote work policy anchor days?",
        top_k=3,
    )
    assert len(results) > 0
    top_hit = results[0]
    assert top_hit.filename == "remote_work_policy.md"
    assert "hybrid model" in top_hit.text.lower()
    assert top_hit.section == "2.1 Hybrid Model"


def test_laptop_refresh_retrieval(in_memory_retriever):
    """Verify hardware refresh query retrieves laptop policy."""
    results = in_memory_retriever.retrieve(
        query="When is laptop refresh eligible after deployment?",
        top_k=2,
    )
    assert len(results) > 0
    top_hit = results[0]
    assert top_hit.filename == "laptop_policy.md"
    assert "36-month" in top_hit.text


# ==============================================================================
# 2. Metadata Preservation Tests
# ==============================================================================


def test_metadata_preservation(in_memory_retriever):
    """Verify that chunk metadata (filename, section, page, chunk_id, score) is fully preserved."""
    results = in_memory_retriever.retrieve(
        query="GlobalProtect VPN connection error 502",
        top_k=1,
    )
    assert len(results) == 1
    res = results[0]

    assert res.chunk_id == "DOC-vpn:p1:c0"
    assert res.doc_id == "DOC-vpn"
    assert res.filename == "vpn_policy.md"
    assert res.section == "7. Troubleshooting"
    assert res.page_number == 1
    assert res.score > 0.0
    assert "GlobalProtect" in res.text
    assert res.metadata.get("department") == "Security"


# ==============================================================================
# 3. Top-K Behavior Tests
# ==============================================================================


def test_top_k_limiting(in_memory_retriever):
    """Verify that top_k strictly limits the number of returned chunks."""
    results_k1 = in_memory_retriever.retrieve("policy", top_k=1)
    assert len(results_k1) == 1

    results_k3 = in_memory_retriever.retrieve("policy", top_k=3)
    assert len(results_k3) == 3

    results_k10 = in_memory_retriever.retrieve("policy", top_k=10)
    # Total seeded chunks is 5
    assert len(results_k10) == 5


# ==============================================================================
# 4. Irrelevant Query Handling Tests
# ==============================================================================


def test_empty_query_handling(in_memory_retriever):
    """Verify empty or whitespace-only queries return an empty result set."""
    assert in_memory_retriever.retrieve("") == []
    assert in_memory_retriever.retrieve("   ") == []


def test_irrelevant_query_with_threshold(in_memory_retriever):
    """Verify that irrelevant queries do not pass a high similarity threshold."""
    # A query completely unrelated to enterprise IT/HR policies with a high threshold
    results = in_memory_retriever.retrieve(
        query="astrophysics galactic black hole event horizon gamma radiation",
        top_k=5,
        min_score=0.85,
    )
    assert len(results) == 0


# ==============================================================================
# 5. Metadata Filtering Tests
# ==============================================================================


def test_metadata_filtering(in_memory_retriever):
    """Verify that filtering by filename restricts results exclusively to that file."""
    results = in_memory_retriever.retrieve(
        query="policy rules and requirements",
        top_k=5,
        filter_criteria={"filename": "vpn_policy.md"},
    )
    assert len(results) > 0
    assert all(r.filename == "vpn_policy.md" for r in results)


# ==============================================================================
# 6. Reranker Functionality Tests
# ==============================================================================


def test_reranker_rescoring():
    """Verify that LexicalSemanticReranker boosts exact query phrase matches."""
    reranker = LexicalSemanticReranker()
    query = "ergonomic home office stipend"

    candidate_relevant = RetrievalResult(
        chunk_id="DOC-1",
        doc_id="DOC-1",
        text="One-time ergonomic home office stipend allows $750 for desks.",
        filename="remote_work.md",
        section="3.1 Ergonomic Stipend",
        score=0.30,
    )
    candidate_general = RetrievalResult(
        chunk_id="DOC-2",
        doc_id="DOC-2",
        text="General office facilities and cafeteria lunch schedule.",
        filename="office.md",
        section="Cafeteria",
        score=0.35,  # Higher initial vector score
    )

    reranked = reranker.rerank(query, [candidate_general, candidate_relevant], top_k=2)

    # candidate_relevant should be boosted to rank #1 due to exact keyword and section match
    assert reranked[0].chunk_id == "DOC-1"
    assert reranked[0].score > reranked[1].score


def test_noop_reranker():
    """Verify NoOpReranker preserves candidate order."""
    noop = NoOpReranker()
    r1 = RetrievalResult(chunk_id="1", doc_id="1", text="a", filename="f1", section="s", score=0.9)
    r2 = RetrievalResult(chunk_id="2", doc_id="2", text="b", filename="f2", section="s", score=0.8)

    output = noop.rerank("test", [r1, r2], top_k=1)
    assert len(output) == 1
    assert output[0].chunk_id == "1"
