"""
Unit and Integration Tests for RAG Ingestion Pipeline.

Tests document loading (Markdown, Text, PDF), chunking, metadata retention,
embedding vector mathematics, and Qdrant vector upsert/search.
"""

import math
from pathlib import Path
import pytest
from app.rag.loaders import DocumentLoader, LoadedDocument, clean_text
from app.rag.chunking import DocumentChunker, DocumentChunk
from app.rag.embeddings import EmbeddingManager, LocalSemanticVectorizer
from app.rag.vector_store import QdrantVectorStoreManager
from app.rag.ingestion import DocumentIngestionPipeline


@pytest.fixture
def sample_markdown_file(tmp_path):
    """Creates a temporary sample markdown document with sections."""
    doc_path = tmp_path / "sample_policy.md"
    content = """# Global Security Protocol

## 1. Access Control
All employees must utilize hardware security keys for corporate authentication.
MFA is strictly enforced across all internal and external portals.

## 2. Incident Escalation
Report critical incidents to the SOC hotline within 15 minutes.
Do not attempt unauthorized network forensics on compromised hosts.
"""
    doc_path.write_text(content, encoding="utf-8")
    return doc_path


@pytest.fixture
def sample_text_file(tmp_path):
    """Creates a temporary sample plain text document."""
    doc_path = tmp_path / "system_notes.txt"
    doc_path.write_text("Standard operating procedures for deployment.\nEnsure backups are validated.", encoding="utf-8")
    return doc_path


# ==============================================================================
# 1. Document Loading Tests
# ==============================================================================


def test_clean_text():
    """Verify text cleaning normalizes whitespace and CRLF."""
    raw = "Line 1\r\n\r\n\r\n\r\nLine 2   with spaces\x00and nulls\n"
    cleaned = clean_text(raw)
    assert "\r" not in cleaned
    assert "\x00" not in cleaned
    assert "Line 1\n\nLine 2 with spacesand nulls" == cleaned


def test_load_markdown(sample_markdown_file):
    """Verify loading Markdown preserves title, metadata, and hash."""
    docs = DocumentLoader.load_file(sample_markdown_file)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.document_type == "markdown"
    assert doc.title == "Global Security Protocol"
    assert doc.filename == "sample_policy.md"
    assert len(doc.content_hash) == 64
    assert "Access Control" in doc.content


def test_load_text(sample_text_file):
    """Verify loading plain text document."""
    docs = DocumentLoader.load_file(sample_text_file)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.document_type == "text"
    assert doc.filename == "system_notes.txt"
    assert "backups are validated" in doc.content


def test_load_nonexistent_file():
    """Verify loading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        DocumentLoader.load_file("data/documents/non_existent.md")


def test_load_unsupported_extension(tmp_path):
    """Verify unsupported file extensions raise ValueError."""
    bad_file = tmp_path / "archive.zip"
    bad_file.write_bytes(b"PK000")
    with pytest.raises(ValueError) as exc:
        DocumentLoader.load_file(bad_file)
    assert "Unsupported document extension" in str(exc.value)


# ==============================================================================
# 2. Chunking & Metadata Preservation Tests
# ==============================================================================


def test_chunking_with_section_tracking(sample_markdown_file):
    """Verify section titles, chunk IDs, and metadata are retained."""
    docs = DocumentLoader.load_file(sample_markdown_file)
    chunker = DocumentChunker(chunk_size=200, chunk_overlap=30)
    chunks = chunker.chunk_documents(docs)

    assert len(chunks) >= 2
    sections = {c.section for c in chunks}
    assert "1. Access Control" in sections
    assert "2. Incident Escalation" in sections

    for c in chunks:
        assert c.chunk_id.startswith("DOC-sample-policy:")
        assert c.filename == "sample_policy.md"
        assert c.document_type == "markdown"
        assert len(c.content_hash) == 64
        assert c.character_count > 0


def test_chunking_idempotency(sample_markdown_file):
    """Verify chunking the exact same document produces identical chunk IDs."""
    docs1 = DocumentLoader.load_file(sample_markdown_file)
    docs2 = DocumentLoader.load_file(sample_markdown_file)

    chunker = DocumentChunker()
    chunks1 = chunker.chunk_documents(docs1)
    chunks2 = chunker.chunk_documents(docs2)

    assert [c.chunk_id for c in chunks1] == [c.chunk_id for c in chunks2]
    assert [c.content_hash for c in chunks1] == [c.content_hash for c in chunks2]


# ==============================================================================
# 3. Embedding Generation Tests
# ==============================================================================


def test_embedding_dimensions_and_normalization():
    """Verify embedding vector length and L2 unit norm."""
    mgr = EmbeddingManager(dimension=768)
    text = "Enterprise single sign-on authentication via Okta and FIDO2 Yubikey."
    vec = mgr.embed_text(text)

    assert len(vec) == 768
    # L2 norm must be approximately 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(norm, 0.001) == 1.0


def test_embedding_semantic_sensitivity():
    """Verify that different texts produce different vectors and similar texts have positive alignment."""
    mgr = EmbeddingManager(dimension=768)
    vec_vpn1 = mgr.embed_text("How do I fix GlobalProtect VPN gateway 502 error?")
    vec_vpn2 = mgr.embed_text("GlobalProtect VPN 502 connection issue troubleshooting")
    vec_leave = mgr.embed_text("Bereavement leave and parental vacation policy details")

    # Cosine similarity (dot product of unit vectors)
    sim_vpn = sum(a * b for a, b in zip(vec_vpn1, vec_vpn2))
    sim_diff = sum(a * b for a, b in zip(vec_vpn1, vec_leave))

    # Similar queries must have significantly higher similarity than unrelated topics
    assert sim_vpn > sim_diff
    assert sim_vpn > 0.0


# ==============================================================================
# 4. Qdrant Insertion and Retrieval Tests
# ==============================================================================


def test_qdrant_in_memory_insertion_and_search():
    """Verify collection creation, point upsert, and vector search with in-memory Qdrant."""
    qdrant_mgr = QdrantVectorStoreManager(
        collection_name="test_collection",
        vector_size=768,
        force_memory=True,
    )
    embedding_mgr = EmbeddingManager(dimension=768)

    sample_chunks = [
        DocumentChunk(
            chunk_id="DOC-test:p1:c0",
            doc_id="DOC-test",
            text="Employees must enroll in Okta Verify MFA using biometric challenge.",
            filename="auth_policy.md",
            document_type="markdown",
            section="MFA Requirements",
            page_number=1,
            chunk_index=0,
            character_count=67,
            content_hash="abc123hash",
            metadata={"department": "Security"},
        ),
        DocumentChunk(
            chunk_id="DOC-test:p1:c1",
            doc_id="DOC-test",
            text="Per diem meal allowance for international business travel is $100 per day.",
            filename="expense_policy.md",
            document_type="markdown",
            section="Travel Expenses",
            page_number=1,
            chunk_index=1,
            character_count=74,
            content_hash="def456hash",
            metadata={"department": "Finance"},
        ),
    ]

    vectors = embedding_mgr.embed_batch([c.text for c in sample_chunks])
    upserted = qdrant_mgr.upsert_chunks(sample_chunks, vectors)
    assert upserted == 2
    assert qdrant_mgr.count_vectors() == 2

    # Idempotent upsert: upserting same chunks again must not increase count
    qdrant_mgr.upsert_chunks(sample_chunks, vectors)
    assert qdrant_mgr.count_vectors() == 2

    # Query matching first chunk
    query_vec = embedding_mgr.embed_text("How to setup Okta MFA?")
    results = qdrant_mgr.search(query_vector=query_vec, limit=1)

    assert len(results) == 1
    assert results[0].chunk_id == "DOC-test:p1:c0"
    assert results[0].filename == "auth_policy.md"
    assert results[0].section == "MFA Requirements"
    assert "Okta Verify MFA" in results[0].text
    assert results[0].score > 0.0


def test_pipeline_ingest_directory():
    """Verify end-to-end ingestion pipeline ingesting data/documents into an in-memory store."""
    qdrant_mgr = QdrantVectorStoreManager(
        collection_name="test_enterprise_kb",
        vector_size=768,
        force_memory=True,
    )
    embedding_mgr = EmbeddingManager(dimension=768)
    pipeline = DocumentIngestionPipeline(
        vector_store=qdrant_mgr,
        embedding_manager=embedding_mgr,
    )

    report = pipeline.ingest_directory("data/documents")
    assert report.status == "success"
    assert report.files_processed == 8
    assert report.chunks_created > 50
    assert report.vectors_upserted == report.chunks_created
    assert qdrant_mgr.count_vectors() == report.chunks_created
