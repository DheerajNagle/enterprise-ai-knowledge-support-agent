"""
Sanitization, Secret Redaction, and Prompt Injection Defense Module.

Provides portfolio-level controls:
- Secret and PII redaction filter for logging (never logs API keys, tokens, passwords)
- Multi-signal prompt injection detection and risk assessment
- Retrieved-document instruction isolation and passive XML tagging
"""

import logging
import re
from typing import Any, Dict, List, NamedTuple, Optional, Set

# Regex patterns matching sensitive credentials, tokens, and secrets in text/logs
SENSITIVE_PATTERNS = [
    # API Keys / generic key pairs
    re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{8,})['\"]?"),
    # Bearer / JWT tokens
    re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{15,})"),
    re.compile(r"(?i)(authorization\s*[:=]\s*['\"]?(?:bearer\s+)?[a-zA-Z0-9_\-\.]{15,}['\"]?)"),
    # Passwords & Secrets
    re.compile(r"(?i)(password|passwd|secret|client[_-]?secret)\s*[:=]\s*['\"]?([^'\"\s,;]+)['\"]?"),
    # Private keys
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
]

# Patterns for prompt injection detection
PROMPT_INJECTION_PATTERNS = [
    (re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions", re.IGNORECASE), "DIRECTIVE_OVERRIDE"),
    (re.compile(r"disregard\s+(all\s+)?(prior|system|earlier)\s+(instructions|directives)", re.IGNORECASE), "DIRECTIVE_OVERRIDE"),
    (re.compile(r"(reveal|show|print|output|leak)\s+(your\s+)?(system\s+prompt|instructions|initial\s+prompt)", re.IGNORECASE), "SYSTEM_PROMPT_LEAK"),
    (re.compile(r"(simulate|act\s+as|roleplay\s+as)\s+(dan|jailbreak|developer\s+mode|unrestricted|god\s+mode)", re.IGNORECASE), "JAILBREAK_ROLEPLAY"),
    (re.compile(r"<\s*/?\s*(system|system_directives|instruction|retrieved_context)\s*>", re.IGNORECASE), "DELIMITER_TAMPERING"),
    (re.compile(r"bypass\s+(safety|security|content)\s+filters", re.IGNORECASE), "SAFETY_BYPASS"),
    (re.compile(r"you\s+are\s+now\s+in\s+(developer|maintenance|debug)\s+mode", re.IGNORECASE), "MODE_SWITCH"),
    (re.compile(r"from\s+now\s+on\s+you\s+(will|must)\s+ignore", re.IGNORECASE), "DIRECTIVE_OVERRIDE"),
]


class InjectionDetectionResult(NamedTuple):
    """Result of prompt injection analysis."""
    is_injection: bool
    risk_score: float
    matched_patterns: List[str]


def sanitize_log_message(message: str) -> str:
    """
    Sanitizes a string to prevent sensitive secrets from leaking into logs.
    Replaces API keys, passwords, bearer tokens, and private keys with [REDACTED].
    """
    if not isinstance(message, str):
        message = str(message)

    redacted = message
    for pattern in SENSITIVE_PATTERNS:
        if "PRIVATE KEY" in pattern.pattern:
            redacted = pattern.sub("[REDACTED_PRIVATE_KEY]", redacted)
        elif "bearer" in pattern.pattern.lower():
            redacted = pattern.sub(r"\1[REDACTED_TOKEN]", redacted)
        else:
            redacted = pattern.sub(r"\1: [REDACTED]", redacted)

    return redacted


class RedactingLogFilter(logging.Filter):
    """
    Logging filter that sanitizes log records before emission.
    Ensures credentials, passwords, and tokens are NEVER persisted in log outputs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_log_message(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize_log_message(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_log_message(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def detect_prompt_injection(query: str) -> InjectionDetectionResult:
    """
    Detects adversarial prompt injection attempts in input text using
    multi-signal heuristic signature analysis.
    """
    if not query or not query.strip():
        return InjectionDetectionResult(is_injection=False, risk_score=0.0, matched_patterns=[])

    matched = []
    for pattern, label in PROMPT_INJECTION_PATTERNS:
        if pattern.search(query):
            matched.append(label)

    is_injection = len(matched) > 0
    # Risk score: 0.0 to 1.0 based on matched categories
    score = min(1.0, len(matched) * 0.45)

    return InjectionDetectionResult(
        is_injection=is_injection,
        risk_score=round(score, 2),
        matched_patterns=matched,
    )


def isolate_document_content(
    text: str,
    doc_id: str,
    filename: Optional[str] = None,
    section: Optional[str] = None,
) -> str:
    """
    Isolates retrieved document text to defend against indirect prompt injection.
    Defangs structural tags and wraps content inside explicit passive XML boundaries
    so the downstream LLM treats it strictly as passive data rather than instructions.
    """
    if not text:
        return ""

    # 1. Defang structural delimiter tags
    sanitized = re.sub(r"<\s*/?\s*(system|instruction|system_directives)\s*>", "[sanitized_tag]", text, flags=re.IGNORECASE)
    sanitized = re.sub(r"<\s*/?\s*untrusted_document_content[^>]*>", "[sanitized_tag: untrusted]", sanitized, flags=re.IGNORECASE)

    # 2. Defang high-risk instruction override triggers inside retrieved text
    for pattern, _ in PROMPT_INJECTION_PATTERNS:
        sanitized = pattern.sub("[sanitized_untrusted_directive]", sanitized)

    # 3. Encapsulate inside unambiguous passive isolation boundary
    file_attr = f' filename="{filename}"' if filename else ""
    sec_attr = f' section="{section}"' if section else ""

    isolated = (
        f'<untrusted_document_content id="{doc_id}"{file_attr}{sec_attr} role="inert_data">\n'
        f"{sanitized.strip()}\n"
        f"</untrusted_document_content>"
    )
    return isolated
