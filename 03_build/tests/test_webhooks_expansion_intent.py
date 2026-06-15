"""
SPEC-015 — /webhooks/expansion-intent endpoint unit tests (no DB).

The real DB path (mark_processed, run_episode with Postgres) is covered by
the existing test_opportunity_tracker_adapter_db.py integration suite.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

# ── helpers ──────────────────────────────────────────────────────────────────


def _row(tier="hottest", posting_id="post-abc"):
    return {
        "posting_id": posting_id,
        "account_id": "001ACRISURE",
        "account_name": "Acrisure",
        "title": "Remote Billing Coordinator",
        "company": "Acrisure",
        "location": "Remote",
        "source": "linkedin",
        "url": "https://linkedin.com/jobs/x",
        "first_seen_date": "2026-05-18T10:00:00+00:00",
        "match_tier": tier,
        "matched_role": "Billing Coordinator",
        "match_score": 88,
        "reasoning": "Exact match, remote role.",
        "signals": ["remote", "exact match"],
        "work_arrangement": "remote",
    }


def _make_app(token="test-token"):
    import os

    os.environ["PULSE_INTERNAL_API_TOKEN"] = token
    # Use a minimal app with only the webhook router — avoids triggering the
    # full lifespan (DB pool, SF sync) which requires external services in CI.
    from fastapi import FastAPI

    from api.webhooks import router as webhooks_router

    app = FastAPI()
    app.include_router(webhooks_router)
    return app


# ── auth guard ────────────────────────────────────────────────────────────────


def test_missing_token_returns_403():
    client = TestClient(_make_app())
    resp = client.post("/webhooks/expansion-intent", json={"row": _row()})
    assert resp.status_code == 403


def test_wrong_token_returns_403():
    client = TestClient(_make_app("real-token"))
    resp = client.post(
        "/webhooks/expansion-intent",
        json={"row": _row()},
        headers={"x-internal-token": "wrong"},
    )
    assert resp.status_code == 403


# ── normal ingestion ──────────────────────────────────────────────────────────


def test_hottest_row_ingested():
    mock_run = AsyncMock(return_value=True)
    mock_mark = AsyncMock()

    with (
        patch("core.ingest.pipeline.run_episode", mock_run),
        patch(
            "core.adapters.opportunity_tracker.OpportunityTrackerAdapter.mark_processed",
            mock_mark,
        ),
    ):
        client = TestClient(_make_app())
        resp = client.post(
            "/webhooks/expansion-intent",
            json={"row": _row("hottest", "post-hot-01")},
            headers={"x-internal-token": "test-token"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["ingested"] == 1

    # mark_processed called with status='ingested'
    _, _, status = mock_mark.call_args.args
    assert status == "ingested"


def test_duplicate_row_returns_zero_ingested():
    mock_run = AsyncMock(return_value=False)  # duplicate
    mock_mark = AsyncMock()

    with (
        patch("core.ingest.pipeline.run_episode", mock_run),
        patch(
            "core.adapters.opportunity_tracker.OpportunityTrackerAdapter.mark_processed",
            mock_mark,
        ),
    ):
        client = TestClient(_make_app())
        resp = client.post(
            "/webhooks/expansion-intent",
            json={"row": _row("hottest", "post-dup")},
            headers={"x-internal-token": "test-token"},
        )

    assert resp.status_code == 200
    assert resp.json()["ingested"] == 0
    _, _, status = mock_mark.call_args.args
    assert status == "skipped:dup"


# ── off-scope handling ────────────────────────────────────────────────────────


def test_off_scope_row_skipped():
    mock_run = AsyncMock()
    mock_mark = AsyncMock()

    with (
        patch("core.ingest.pipeline.run_episode", mock_run),
        patch(
            "core.adapters.opportunity_tracker.OpportunityTrackerAdapter.mark_processed",
            mock_mark,
        ),
    ):
        client = TestClient(_make_app())
        resp = client.post(
            "/webhooks/expansion-intent",
            json={"row": _row("off-scope", "post-offscope")},
            headers={"x-internal-token": "test-token"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ingested"] == 0
    assert body["skipped"] == 1
    mock_run.assert_not_called()


# ── Graphiti failure resilience ───────────────────────────────────────────────


def test_graphiti_failure_marks_ingested_not_failed():
    """Episode is in DB even if Graphiti raises; EIS row must still be marked
    processed so Activepieces doesn't re-deliver the same row."""
    mock_run = AsyncMock(side_effect=RuntimeError("graphiti down"))
    mock_mark = AsyncMock()

    with (
        patch("core.ingest.pipeline.run_episode", mock_run),
        patch(
            "core.adapters.opportunity_tracker.OpportunityTrackerAdapter.mark_processed",
            mock_mark,
        ),
    ):
        client = TestClient(_make_app())
        resp = client.post(
            "/webhooks/expansion-intent",
            json={"row": _row("hottest", "post-graphiti-fail")},
            headers={"x-internal-token": "test-token"},
        )

    assert resp.status_code == 200
    _, _, status = mock_mark.call_args.args
    assert status == "ingested"


# ── malformed payload ─────────────────────────────────────────────────────────


def test_missing_posting_id_returns_422():
    client = TestClient(_make_app())
    resp = client.post(
        "/webhooks/expansion-intent",
        json={"row": {"no_posting_id": "here"}},
        headers={"x-internal-token": "test-token"},
    )
    assert resp.status_code == 422
