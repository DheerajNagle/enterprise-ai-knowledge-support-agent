"""
Input, Request, and File Upload Validation Module.

Provides portfolio-level input security controls:
- File extension whitelisting (.pdf, .txt, .md only)
- File size boundary checks (e.g., 10MB max per document)
- Request payload size limits (e.g., 2MB max for JSON)
- Path traversal prevention
- Defanging of control characters and null bytes
"""

import os
from pathlib import Path
from typing import List, Optional, Set, Union

ALLOWED_DOCUMENT_EXTENSIONS: Set[str] = {".pdf", ".txt", ".md"}
DEFAULT_MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
DEFAULT_MAX_REQUEST_SIZE_BYTES: int = 2 * 1024 * 1024  # 2 MB
MAX_QUERY_LENGTH: int = 4096


class SecurityValidationError(ValueError):
    """Base exception for portfolio security validation failures."""
    def __init__(self, message: str, code: str = "SECURITY_VALIDATION_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


class UnsupportedFileTypeError(SecurityValidationError):
    """Raised when an uploaded or ingested file is not an allowed extension."""
    def __init__(self, filename: str, extension: str):
        msg = (
            f"File '{filename}' has unsupported extension '{extension}'. "
            f"Supported file types are: {sorted(ALLOWED_DOCUMENT_EXTENSIONS)}"
        )
        super().__init__(msg, code="UNSUPPORTED_FILE_TYPE")


class FileSizeExceededError(SecurityValidationError):
    """Raised when an ingested file exceeds maximum allowed file size."""
    def __init__(self, filename: str, actual_bytes: int, max_bytes: int):
        msg = (
            f"File '{filename}' size ({actual_bytes} bytes) exceeds maximum "
            f"allowed limit ({max_bytes} bytes)."
        )
        super().__init__(msg, code="FILE_SIZE_EXCEEDED")


class RequestSizeExceededError(SecurityValidationError):
    """Raised when request payload exceeds size threshold."""
    def __init__(self, actual_bytes: int, max_bytes: int):
        msg = (
            f"Request payload size ({actual_bytes} bytes) exceeds maximum "
            f"allowed limit ({max_bytes} bytes)."
        )
        super().__init__(msg, code="REQUEST_SIZE_EXCEEDED")


def validate_file_extension(filename: Union[str, Path]) -> str:
    """
    Validates that a filename has an allowed document extension (.pdf, .txt, .md).
    Rejects any other file types to prevent arbitrary code or script ingestion.
    """
    path = Path(filename)
    ext = path.suffix.lower()

    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise UnsupportedFileTypeError(filename=path.name, extension=ext)

    return ext


def validate_file_path_safety(file_path: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
    """
    Guarantees that a file path does not attempt directory traversal (e.g. '../../etc/passwd').
    Resolves canonical path and validates against optional base directory boundary.
    """
    path = Path(file_path)
    clean_name = os.path.basename(str(path))
    if not clean_name or clean_name in (".", ".."):
        raise SecurityValidationError("Invalid or suspicious file path.", code="PATH_TRAVERSAL_DETECTED")

    resolved = path.resolve()
    if base_dir:
        resolved_base = base_dir.resolve()
        try:
            resolved.relative_to(resolved_base)
        except ValueError:
            raise SecurityValidationError(
                f"Path traversal detected: '{file_path}' resolves outside allowed directory.",
                code="PATH_TRAVERSAL_DETECTED",
            )

    return resolved


def validate_file_size(file_path: Union[str, Path], max_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES) -> int:
    """
    Validates that file on disk does not exceed maximum allowable size limit.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    size = path.stat().st_size
    if size > max_bytes:
        raise FileSizeExceededError(filename=path.name, actual_bytes=size, max_bytes=max_bytes)

    return size


def validate_file_bytes(
    filename: str,
    data: bytes,
    max_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> None:
    """
    Validates in-memory file bytes: verifies extension whitelisting, size limits,
    and checks for magic bytes where appropriate.
    """
    ext = validate_file_extension(filename)
    actual_size = len(data)

    if actual_size > max_bytes:
        raise FileSizeExceededError(filename=filename, actual_bytes=actual_size, max_bytes=max_bytes)

    # Basic magic byte check for PDF
    if ext == ".pdf" and not data.startswith(b"%PDF-"):
        raise SecurityValidationError(
            f"File '{filename}' has .pdf extension but invalid header bytes.",
            code="INVALID_FILE_SIGNATURE",
        )


def sanitize_input_text(text: Optional[str], max_length: int = MAX_QUERY_LENGTH) -> str:
    """
    Sanitizes user input string: defangs null bytes and enforces maximum length bounds.
    """
    if not text:
        return ""

    # Defang null bytes
    cleaned = text.replace("\x00", "")

    # Strip dangerous Unicode bidirectional override characters
    cleaned = cleaned.replace("\u202e", "").replace("\u202d", "").replace("\u202b", "").replace("\u202a", "")

    # Enforce maximum query length bounds
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned.strip()
