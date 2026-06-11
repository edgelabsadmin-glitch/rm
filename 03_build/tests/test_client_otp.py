"""Unit tests for OTP helpers — no DB, no network."""
from __future__ import annotations
import pytest


def test_generate_otp_is_six_digits():
    from core.client.otp import generate_otp
    otp = generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()


def test_generate_otp_zero_padded():
    from core.client.otp import hash_otp, verify_otp_hash
    otp = "000042"
    assert verify_otp_hash(otp, hash_otp(otp))


def test_hash_otp_is_deterministic():
    from core.client.otp import hash_otp
    assert hash_otp("123456") == hash_otp("123456")


def test_verify_otp_hash_wrong_otp():
    from core.client.otp import hash_otp, verify_otp_hash
    h = hash_otp("123456")
    assert not verify_otp_hash("999999", h)


def test_truncate_title_long():
    from core.client.otp import truncate_title
    assert truncate_title("a" * 100) == "a" * 60


def test_truncate_title_strips():
    from core.client.otp import truncate_title
    assert truncate_title("  hello  ") == "hello"
