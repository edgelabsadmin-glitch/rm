"""OTP generation and hashing helpers — pure functions, no I/O."""
from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_otp() -> str:
    """Return a 6-digit zero-padded OTP string."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    """Return SHA-256 hex digest of the OTP."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp_hash(otp: str, otp_hash: str) -> bool:
    """Constant-time comparison of OTP against its stored hash."""
    expected = hash_otp(otp)
    return hmac.compare_digest(expected, otp_hash)


def truncate_title(text: str) -> str:
    """Trim whitespace and cap at 60 chars for conversation auto-titles."""
    return text.strip()[:60]
