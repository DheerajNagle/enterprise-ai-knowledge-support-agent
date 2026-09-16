"""
Portfolio-Level Application Security Package.

Consolidates and exports:
- Constant-time API Key Authentication and Bearer token parsing
- File upload extension whitelisting (.pdf, .txt, .md only) and file size bounds
- Request payload size protection and input sanitization
- Sensitive data & secret log redaction filter
- Multi-signal prompt injection detection
- Untrusted retrieved-document instruction isolation
"""

from app.security.auth import (
    APIKeyAuthenticator,
    mask_secret,
)
from app.security.validation import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_MAX_REQUEST_SIZE_BYTES,
    SecurityValidationError,
    UnsupportedFileTypeError,
    FileSizeExceededError,
    RequestSizeExceededError,
    validate_file_extension,
    validate_file_path_safety,
    validate_file_size,
    validate_file_bytes,
    sanitize_input_text,
)
from app.security.sanitization import (
    RedactingLogFilter,
    sanitize_log_message,
    detect_prompt_injection,
    isolate_document_content,
    InjectionDetectionResult,
)

__all__ = [
    # Auth
    "APIKeyAuthenticator",
    "mask_secret",
    # Validation
    "ALLOWED_DOCUMENT_EXTENSIONS",
    "DEFAULT_MAX_FILE_SIZE_BYTES",
    "DEFAULT_MAX_REQUEST_SIZE_BYTES",
    "SecurityValidationError",
    "UnsupportedFileTypeError",
    "FileSizeExceededError",
    "RequestSizeExceededError",
    "validate_file_extension",
    "validate_file_path_safety",
    "validate_file_size",
    "validate_file_bytes",
    "sanitize_input_text",
    # Sanitization
    "RedactingLogFilter",
    "sanitize_log_message",
    "detect_prompt_injection",
    "isolate_document_content",
    "InjectionDetectionResult",
]
