"""
Semantic and Markdown-Aware Document Chunker.

Splits loaded documents into semantically coherent passages, preserves
section hierarchy, and assigns deterministic, idempotent chunk identifiers.
"""

import hashlib
import re
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from app.rag.loaders import LoadedDocument


class DocumentChunk(BaseModel):
    """Represents a discrete text chunk indexed in the vector database."""

    chunk_id: str = Field(
        ..., description="Unique, deterministic chunk identifier (e.g. DOC-leave-policy:1:0)"
    )
    doc_id: str = Field(..., description="Document identifier (e.g. DOC-leave-policy)")
    text: str = Field(..., description="Chunk text content")
    filename: str = Field(..., description="Source filename")
    document_type: str = Field(..., description="Format: markdown, pdf, or text")
    section: str = Field(
        default="General", description="Section or header under which this chunk resides"
    )
    page_number: Optional[int] = Field(
        default=None, description="Source page number if available"
    )
    chunk_index: int = Field(..., description="0-indexed chunk position in document")
    character_count: int = Field(..., description="Length of chunk in characters")
    content_hash: str = Field(..., description="SHA-256 hash of chunk text")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Supplementary metadata"
    )


class DocumentChunker:
    """
    Splits documents into overlapping chunks while tracking Markdown sections
    and producing deterministic chunk IDs.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        min_chunk_size: int = 50,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    @staticmethod
    def generate_doc_id(filename: str) -> str:
        """Derives a stable document ID from filename: 'leave_policy.md' -> 'DOC-leave-policy'."""
        clean = re.sub(r"\.[^.]+$", "", filename)
        clean = re.sub(r"[^a-zA-Z0-9]+", "-", clean).strip("-").lower()
        return f"DOC-{clean}"

    def _extract_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Splits text by Markdown headers (##, ###) while preserving the header title.
        Returns a list of dicts with 'section_title' and 'body'.
        """
        lines = text.split("\n")
        sections: List[Dict[str, str]] = []
        current_section = "Overview"
        current_lines: List[str] = []

        header_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

        for line in lines:
            match = header_pattern.match(line)
            if match:
                if current_lines:
                    body = "\n".join(current_lines).strip()
                    if body:
                        sections.append(
                            {"section_title": current_section, "body": body}
                        )
                    current_lines = []
                current_section = match.group(2).strip()
            else:
                current_lines.append(line)

        if current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                sections.append(
                    {"section_title": current_section, "body": body}
                )

        return sections or [{"section_title": "General", "body": text}]

    def _split_text_with_overlap(self, text: str) -> List[str]:
        """
        Splits a text block into chunks of ~chunk_size characters with chunk_overlap,
        breaking on paragraph and sentence boundaries where possible.
        """
        if len(text) <= self.chunk_size:
            return [text] if len(text) >= self.min_chunk_size else []

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            if end >= text_len:
                chunk = text[start:].strip()
                if len(chunk) >= self.min_chunk_size:
                    chunks.append(chunk)
                break

            # Try to break on double newline (paragraph boundary)
            split_at = text.rfind("\n\n", start, end)
            if split_at != -1 and split_at > start + self.chunk_overlap:
                end = split_at + 2
            else:
                # Try to break on single newline
                split_at = text.rfind("\n", start, end)
                if split_at != -1 and split_at > start + self.chunk_overlap:
                    end = split_at + 1
                else:
                    # Try to break on period / sentence boundary
                    split_at = text.rfind(". ", start, end)
                    if split_at != -1 and split_at > start + self.chunk_overlap:
                        end = split_at + 2
                    else:
                        # Try space
                        split_at = text.rfind(" ", start, end)
                        if split_at != -1 and split_at > start + self.chunk_overlap:
                            end = split_at + 1

            chunk = text[start:end].strip()
            if len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)

            # Advance start by chunk length minus overlap
            start = end - self.chunk_overlap
            if start <= 0 or start >= end:
                start = end

        return chunks

    def chunk_document(self, document: LoadedDocument) -> List[DocumentChunk]:
        """Splits a single LoadedDocument into DocumentChunk records."""
        doc_id = self.generate_doc_id(document.filename)
        chunks: List[DocumentChunk] = []
        page_str = str(document.page_number or 1)

        # For Markdown documents, utilize section awareness
        if document.document_type == "markdown":
            sections = self._extract_sections(document.content)
            chunk_idx = 0
            for sec in sections:
                sec_chunks = self._split_text_with_overlap(sec["body"])
                for sc in sec_chunks:
                    chunk_id = f"{doc_id}:p{page_str}:c{chunk_idx}"
                    content_hash = hashlib.sha256(sc.encode("utf-8")).hexdigest()
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            doc_id=doc_id,
                            text=sc,
                            filename=document.filename,
                            document_type=document.document_type,
                            section=sec["section_title"],
                            page_number=document.page_number,
                            chunk_index=chunk_idx,
                            character_count=len(sc),
                            content_hash=content_hash,
                            metadata={
                                **document.metadata,
                                "document_title": document.title,
                            },
                        )
                    )
                    chunk_idx += 1
        else:
            # Plain text / PDF page
            raw_chunks = self._split_text_with_overlap(document.content)
            for idx, rc in enumerate(raw_chunks):
                chunk_id = f"{doc_id}:p{page_str}:c{idx}"
                content_hash = hashlib.sha256(rc.encode("utf-8")).hexdigest()
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        text=rc,
                        filename=document.filename,
                        document_type=document.document_type,
                        section=document.title or "General",
                        page_number=document.page_number,
                        chunk_index=idx,
                        character_count=len(rc),
                        content_hash=content_hash,
                        metadata={
                            **document.metadata,
                            "document_title": document.title,
                        },
                    )
                )

        return chunks

    def chunk_documents(
        self, documents: List[LoadedDocument]
    ) -> List[DocumentChunk]:
        """Processes a list of LoadedDocument objects into chunks."""
        all_chunks: List[DocumentChunk] = []
        for doc in documents:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks
