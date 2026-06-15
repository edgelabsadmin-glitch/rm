"""Send OTP emails via AWS SES."""

from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger(__name__)

_SENDER = os.environ.get("AWS_SES_SENDER", "pulse@onedge.co")
_REGION = os.environ.get("AWS_SES_REGION", "us-east-1")


def _send_otp_sync(to_email: str, otp: str) -> None:
    """Blocking SES send — call via asyncio.to_thread."""
    import boto3  # imported lazily so tests don't need AWS credentials

    client = boto3.client("ses", region_name=_REGION)
    client.send_email(
        Source=_SENDER,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": "Your EDGE login code"},
            "Body": {
                "Text": {
                    "Data": (
                        f"Your one-time login code is: {otp}\n\n"
                        "This code expires in 10 minutes.\n\n"
                        "If you did not request this, ignore this email."
                    )
                }
            },
        },
    )
    log.info("OTP email sent to %s", to_email)


async def send_otp_email(to_email: str, otp: str) -> None:
    """Send OTP to client email address (non-blocking).
    When FRONTEND_URL is localhost (dev), logs OTP to console instead of calling SES."""
    frontend = os.environ.get("FRONTEND_URL", "")
    if "localhost" in frontend:
        log.warning("DEV MODE — OTP for %s: %s", to_email, otp)
        return
    await asyncio.to_thread(_send_otp_sync, to_email, otp)
