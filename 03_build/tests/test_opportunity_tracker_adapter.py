"""
SPEC-015 unit tests — opportunity-tracker adapter normalization (no DB).

The poll / off-scope-skip / mark_processed / idempotency behavior is in
tests/test_opportunity_tracker_adapter_db.py (marker `db`).
"""

from core.adapters.opportunity_tracker import OpportunityTrackerAdapter


def _row(posting_id="abc123", tier="hottest", **extra):
    row = {
        "posting_id": posting_id,
        "account_id": "001ACRISURE",
        "account_name": "Acrisure",
        "title": "Remote Medical Coder II",
        "company": "Acrisure",
        "location": "Remote",
        "source": "linkedin",
        "url": "https://linkedin.com/jobs/x",
        "first_seen_date": "2026-05-18T10:00:00+00:00",
        "match_tier": tier,
        "matched_role": "medical-coder-ii",
        "match_score": 92,
        "reasoning": "Remote-compatible coding role at an existing client.",
        "signals": ["remote", "coding"],
        "work_arrangement": "remote",
    }
    row.update(extra)
    return row


def _raw(row):
    return {
        "source": "opportunity-tracker",
        "source_event_id": row["posting_id"],
        "payload": {"row": row},
    }


def test_dedup_key_uses_posting_hash():
    a = OpportunityTrackerAdapter()
    assert a.dedup_key(_raw(_row("deadbeef"))) == "oppt:posting:deadbeef"


def test_normalize_maps_spike4_envelope():
    ep = OpportunityTrackerAdapter().normalize(_raw(_row(tier="hottest")))
    assert ep["content_type"] == "json"
    assert ep["content"]["match"]["tier"] == "hottest"
    assert ep["content"]["match"]["work_arrangement"] == "remote"
    assert ep["content"]["posting"]["source"] == "linkedin"
    assert ep["candidate_entities"] == [{"type": "Customer", "sfdc_id": "001ACRISURE"}]
    assert ep["tags"] == ["expansion-intent", "hottest", "linkedin"]
    assert ep["description"] == "opportunity-tracker hottest match: medical-coder-ii"


def test_tags_carry_tier_and_board():
    ep = OpportunityTrackerAdapter().normalize(_raw(_row(tier="warm", source="indeed")))
    assert ep["tags"] == ["expansion-intent", "warm", "indeed"]
