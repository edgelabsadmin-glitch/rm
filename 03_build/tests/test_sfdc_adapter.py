"""
SPEC-012 unit tests — SFDC adapter query construction + normalization.

No `sf` CLI / DB: subprocess is mocked. The real-org poll lives behind the
`integration` marker + PULSE_SFDC_LIVE; the stage-history DB test is in
tests/test_sfdc_adapter_db.py.
"""

import json
from datetime import datetime, timezone
UTC = timezone.utc
from types import SimpleNamespace

import pytest

from core.adapters import sfdc
from core.adapters.sfdc import OBJECTS, RISK_CATEGORIES, SFDCAdapter

SINCE = datetime(2026, 5, 1, tzinfo=UTC)


def _raw(object_type: str, record: dict) -> dict:
    return {
        "source": "salesforce",
        "source_event_id": record.get("Id", ""),
        "payload": {"object_type": object_type, "record": record},
    }


def test_all_eight_objects_configured():
    assert set(OBJECTS) == {
        "Account",
        "Contact",
        "Opportunity",
        "RM_Outreach__c",
        "Associates__c",
        "Account_Plan__c",
        "Case",
        "affectlayer__Engagement__c",
    }


def test_build_query_account_has_segment_and_modified_filter():
    q = SFDCAdapter().build_query("Account", SINCE)
    assert "FROM Account" in q
    assert "Segment__c" in q  # tier field (drives policy)
    assert "LastModifiedDate >= 2026-05-01T00:00:00Z" in q


def test_build_query_case_applies_risk_category_filter():
    q = SFDCAdapter().build_query("Case", SINCE)
    assert "Categories__c IN (" in q
    # all 14 taxonomy values present
    for cat in RISK_CATEGORIES:
        assert cat in q
    assert "Description" in q and "Details__c" in q


def test_dedup_key_format():
    raw = _raw("Account", {"Id": "001X", "LastModifiedDate": "2026-05-05T10:00:00.000+0000"})
    assert SFDCAdapter().dedup_key(raw) == "sfdc:Account:001X:2026-05-05T10:00:00.000+0000"


def test_normalize_account_episode():
    raw = _raw(
        "Account",
        {
            "Id": "001X",
            "Name": "Acrisure",
            "Segment__c": "Enterprise",
            "LastModifiedDate": "2026-05-05T10:00:00.000+0000",
        },
    )
    ep = SFDCAdapter().normalize(raw)
    assert ep["content_type"] == "json"
    assert ep["content"]["object_type"] == "Account"
    assert ep["content"]["fields"]["Segment__c"] == "Enterprise"
    assert ep["tags"] == ["sfdc", "account"]
    assert ep["candidate_entities"] == [{"type": "Customer", "sfdc_id": "001X"}]
    assert ep["subject"] == "Account Acrisure"


def test_normalize_case_preserves_full_narrative_and_risk_tag():
    raw = _raw(
        "Case",
        {
            "Id": "500X",
            "CaseNumber": "C-19284",
            "AccountId": "001X",
            "Associate__c": "a0X",
            "Categories__c": "Risk - Talent Competency",
            "Description": "Full description narrative " * 20,
            "Details__c": "Full details narrative " * 20,
            "LastModifiedDate": "2026-05-05T10:00:00.000+0000",
        },
    )
    ep = SFDCAdapter().normalize(raw)
    assert ep["content"]["description_text"].startswith("Full description narrative")
    assert len(ep["content"]["details_text"]) > 100  # not truncated
    assert "risk-tagged" in ep["tags"]
    # Customer + Talent candidate entities
    types = {e["type"] for e in ep["candidate_entities"]}
    assert types == {"Customer", "Talent"}


def test_normalize_associate_emits_talent_entity():
    raw = _raw(
        "Associates__c",
        {
            "Id": "a0X",
            "Name": "Marcus Wells",
            "Account__c": "001X",
            "Stage__c": "Replaced",
            "LastModifiedDate": "2026-05-05T10:00:00.000+0000",
        },
    )
    ep = SFDCAdapter().normalize(raw)
    talent = [e for e in ep["candidate_entities"] if e["type"] == "Talent"]
    assert talent and talent[0]["name"] == "Marcus Wells"


async def test_receive_webhook_valid_and_malformed():
    a = SFDCAdapter()
    events = await a.receive_webhook(
        {"object_type": "Account", "record": {"Id": "001X", "Name": "Acrisure"}}, {}
    )
    assert events[0]["payload"]["object_type"] == "Account"
    with pytest.raises(ValueError, match="malformed"):
        await a.receive_webhook({"nope": 1}, {})


async def test_list_recent_events_builds_events_per_object(monkeypatch):
    # Mock the sf CLI: every object query returns one record.
    def fake_run(cmd, **kw):
        rec = {"Id": "X1", "Name": "Rec", "LastModifiedDate": "2026-05-05T10:00:00.000+0000"}
        return SimpleNamespace(
            returncode=0, stdout=json.dumps({"result": {"records": [rec]}}), stderr=""
        )

    async def fake_stage(**kwargs):
        pass

    monkeypatch.setattr(sfdc.subprocess, "run", fake_run)
    monkeypatch.setattr(sfdc, "record_associate_stage", fake_stage)

    events = await SFDCAdapter().list_recent_events(SINCE)
    assert len(events) == len(OBJECTS)  # one record per object
    assert {e["payload"]["object_type"] for e in events} == set(OBJECTS)
