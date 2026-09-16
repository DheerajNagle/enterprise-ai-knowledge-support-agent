"""
Document Loaders and Text Sanitizers for Enterprise RAG.

Supports Markdown (.md), Plain Text (.txt), and PDF (.pdf) documents,
extracting clean text, structural metadata, and SHA-256 content hashes.
"""

import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field


class LoadedDocument(BaseModel):
    """Represents a raw document or document page loaded from storage."""

    content: str = Field(..., description="Cleaned text content of the document")
    filename: str = Field(..., description="Base filename (e.g. leave_policy.md)")
    file_path: str = Field(..., description="Normalized relative or absolute path")
    document_type: str = Field(..., description="Format: markdown, pdf, or text")
    page_number: Optional[int] = Field(
        default=None, description="Page number if applicable (1-indexed)"
    )
    title: Optional[str] = Field(
        default=None, description="Document title extracted from header or filename"
    )
    content_hash: str = Field(
        ..., description="SHA-256 hash of cleaned text for idempotency tracking"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional arbitrary metadata"
    )


def clean_text(raw_text: str) -> str:
    """
    Cleans and normalizes extracted document text:
    - Normalizes Windows CRLF to standard LF.
    - Strips control and non-printable characters.
    - Collapses multiple redundant blank lines into at most two.
    - Strips leading/trailing whitespace.
    """
    if not raw_text:
        return ""

    # Replace null bytes and non-printable ASCII (except tabs and newlines)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw_text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace runs of more than 2 consecutive newlines with 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple horizontal whitespace to single space
    text = re.sub(r"[^\S\r\n]{2,}", " ", text)

    return text.strip()


def compute_sha256(text: str) -> str:
    """Computes SHA-256 hash of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentLoader:
    """Loads and sanitizes documents across supported enterprise formats."""

    SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf"}

    @classmethod
    def extract_markdown_title(cls, text: str, default_name: str) -> str:
        """Extracts the first top-level # Markdown header as the title."""
        match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
        if match:
            return match.group(1).strip()
        # Fallback to formatting filename
        clean_name = Path(default_name).stem.replace("_", " ").title()
        return clean_name

    @classmethod
    def load_markdown(cls, file_path: Path) -> List[LoadedDocument]:
        """Loads and cleans a Markdown document."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        cleaned = clean_text(raw)
        title = cls.extract_markdown_title(cleaned, file_path.name)
        content_hash = compute_sha256(cleaned)

        return [
            LoadedDocument(
                content=cleaned,
                filename=file_path.name,
                file_path=str(file_path),
                document_type="markdown",
                page_number=1,
                title=title,
                content_hash=content_hash,
                metadata={
                    "file_size_bytes": file_path.stat().st_size,
                    "extension": file_path.suffix.lower(),
                },
            )
        ]

    @classmethod
    def load_text(cls, file_path: Path) -> List[LoadedDocument]:
        """Loads and cleans a plain text document."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        cleaned = clean_text(raw)
        title = file_path.stem.replace("_", " ").title()
        content_hash = compute_sha256(cleaned)

        return [
            LoadedDocument(
                content=cleaned,
                filename=file_path.name,
                file_path=str(file_path),
                document_type="text",
                page_number=1,
                title=title,
                content_hash=content_hash,
                metadata={
                    "file_size_bytes": file_path.stat().st_size,
                    "extension": file_path.suffix.lower(),
                },
            )
        ]

    @classmethod
    def load_pdf(cls, file_path: Path) -> List[LoadedDocument]:
        """
        Loads a PDF document, extracting text on a per-page basis
        to preserve page-level metadata.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError(
                "pypdf is required to process PDF documents. Please install pypdf."
            )

        reader = PdfReader(str(file_path))
        documents: List[LoadedDocument] = []
        doc_title = file_path.stem.replace("_", " ").title()

        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            cleaned = clean_text(page_text)
            if not cleaned:
                continue

            page_num = idx + 1
            documents.append(
                LoadedDocument(
                    content=cleaned,
                    filename=file_path.name,
                    file_path=str(file_path),
                    document_type="pdf",
                    page_number=page_num,
                    title=f"{doc_title} (Page {page_num})",
                    content_hash=compute_sha256(cleaned),
                    metadata={
                        "total_pages": len(reader.pages),
                        "file_size_bytes": file_path.stat().st_size,
                        "extension": ".pdf",
                    },
                )
            )

        # Fallback if all pages were empty
        if not documents:
            documents.append(
                LoadedDocument(
                    content="",
                    filename=file_path.name,
                    file_path=str(file_path),
                    document_type="pdf",
                    page_number=1,
                    title=doc_title,
                    content_hash=compute_sha256(""),
                    metadata={"total_pages": len(reader.pages)},
                )
            )

        return documents

    @classmethod
    def load_file(cls, file_path: Union[str, Path]) -> List[LoadedDocument]:
        """Dispatches loading based on file extension."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {path}")

        ext = path.suffix.lower()
        if ext in {".md", ".markdown"}:
            return cls.load_markdown(path)
        elif ext == ".txt":
            return cls.load_text(path)
        elif ext == ".pdf":
            return cls.load_pdf(path)
        else:
            raise ValueError(
                f"Unsupported document extension '{ext}'. Supported: {cls.SUPPORTED_EXTENSIONS}"
            )

    @classmethod
    def load_directory(
        cls, directory_path: Union[str, Path], recursive: bool = True
    ) -> List[LoadedDocument]:
        """Loads all supported documents from a directory."""
        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")

        pattern = "**/*" if recursive else "*"
        all_docs: List[LoadedDocument] = []

        for item in sorted(dir_path.glob(pattern)):
            if item.is_file() and item.suffix.lower() in cls.SUPPORTED_EXTENSIONS:
                all_docs.extend(cls.load_file(item))

        return all_docs
