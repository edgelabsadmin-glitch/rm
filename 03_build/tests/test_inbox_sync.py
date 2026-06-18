"""Ownership filter for inbox sync — pure, no network."""

from core.inbox.sync import owned_account_ids


def _idx():
    return {
        "001": {"rm_name": "Eddy Chen", "name": "Acme", "tier": "Strategic", "risk": "High"},
        "002": {"rm_name": "Other RM", "name": "Beta", "tier": "Core", "risk": "Low"},
    }


def test_owned_account_ids_keeps_only_this_rms_accounts():
    entities = [{"type": "sf_account", "sfdc_id": "001"},
                {"type": "sf_account", "sfdc_id": "002"}]
    assert owned_account_ids(entities, _idx(), "Eddy Chen") == ["001"]


def test_owned_account_ids_case_insensitive():
    entities = [{"type": "sf_account", "sfdc_id": "001"}]
    assert owned_account_ids(entities, _idx(), "eddy chen") == ["001"]


def test_owned_account_ids_unknown_account_excluded():
    entities = [{"type": "sf_account", "sfdc_id": "999"}]
    assert owned_account_ids(entities, _idx(), "Eddy Chen") == []


def test_owned_account_ids_empty():
    assert owned_account_ids([], _idx(), "Eddy Chen") == []
