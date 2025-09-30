"""Security utilities for API key hashing and verification."""

import hashlib
import secrets
import hmac
from typing import Tuple


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.

    Args:
        api_key: The plaintext API key

    Returns:
        Hexadecimal hash of the API key
    """
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def verify_api_key(plaintext_key: str, hashed_key: str) -> bool:
    """
    Verify a plaintext API key against a hashed key.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        plaintext_key: The plaintext API key to verify
        hashed_key: The stored hashed key to compare against

    Returns:
        True if keys match, False otherwise
    """
    computed_hash = hash_api_key(plaintext_key)
    return hmac.compare_digest(computed_hash, hashed_key)


def generate_api_key(prefix: str = "dem") -> Tuple[str, str]:
    """
    Generate a new API key with prefix and random suffix.

    Format: {prefix}_live_{32_char_random_string}

    Args:
        prefix: 3-letter tenant prefix (e.g., "dem" for demo)

    Returns:
        Tuple of (plaintext_key, hashed_key)
    """
    # Generate 32 characters of URL-safe random data
    random_part = secrets.token_urlsafe(24)  # 24 bytes = ~32 chars base64

    # Format: prefix_live_randomdata
    plaintext_key = f"{prefix}_live_{random_part}"

    # Hash the key for storage
    hashed_key = hash_api_key(plaintext_key)

    return plaintext_key, hashed_key


def generate_tenant_prefix(tenant_name: str) -> str:
    """
    Generate a 3-letter prefix from tenant name.

    Args:
        tenant_name: Full tenant name (e.g., "Acme Corporation")

    Returns:
        3-letter lowercase prefix (e.g., "acm")
    """
    # Remove spaces and special chars, take first 3 letters
    clean_name = ''.join(c for c in tenant_name if c.isalnum())
    return clean_name[:3].lower()