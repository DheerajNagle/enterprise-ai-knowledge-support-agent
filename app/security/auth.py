"""
Authentication & Secret Protection Module.

Provides portfolio-level authentication security:
- Constant-time API key verification resisting timing attacks (secrets.compare_digest)
- Bearer token parsing and header normalization
- Secret masking and credential protection utilities
"""

import secrets
from typing import Optional


class APIKeyAuthenticator:
    """
    Portfolio-level API key authenticator enforcing constant-time token verification.
    """

    @staticmethod
    def verify(provided_key: Optional[str], expected_key: str) -> bool:
        """
        Validates the provided API key against the expected secret using
        constant-time byte comparison to eliminate timing side-channel attacks.
        """
        if not provided_key or not expected_key:
            return False

        provided_clean = provided_key.strip()
        expected_clean = expected_key.strip()

        if not provided_clean or not expected_clean:
            return False

        return secrets.compare_digest(provided_clean, expected_clean)

    @staticmethod
    def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
        """Extracts token from 'Authorization: Bearer <token>' header."""
        if not authorization_header:
            return None
        parts = authorization_header.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return None


def mask_secret(secret: Optional[str], unmasked_prefix: int = 4, unmasked_suffix: int = 4) -> str:
    """
    Masks a sensitive string or credential for safe logging and display.
    Guarantees secrets are never printed in plaintext.
    """
    if not secret:
        return "[EMPTY]"

    s = secret.strip()
    length = len(s)

    if length <= (unmasked_prefix + unmasked_suffix + 2):
        return "***"

    prefix = s[:unmasked_prefix]
    suffix = s[-unmasked_suffix:]
    return f"{prefix}...{suffix}"
