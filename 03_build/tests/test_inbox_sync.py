"""Ownership check for inbox sync — pure, no network."""

from core.inbox.sync import rm_owns_account


def test_owns_by_salesforce_owner_id():
    meta = {"owner_id": "005AAA", "rm_name": "Akash Tahir"}
    # Robust path: matches on SF owner id regardless of the RM's (longer) Google name.
    assert rm_owns_account(meta, "005AAA", "Akash Tahir Sindhu") is True


def test_owner_id_mismatch_not_owned():
    meta = {"owner_id": "005BBB", "rm_name": "Someone Else"}
    assert rm_owns_account(meta, "005AAA", "Akash Tahir") is False


def test_falls_back_to_name_when_no_sf_id():
    meta = {"owner_id": "005CCC", "rm_name": "Eddy Chen"}
    assert rm_owns_account(meta, None, "eddy chen") is True  # case-insensitive
    assert rm_owns_account(meta, None, "Other RM") is False


def test_sf_id_takes_precedence_over_name():
    # With a mapped sf id, the name is ignored entirely (owner_id is authoritative).
    meta = {"owner_id": "005XXX", "rm_name": "Akash Tahir"}
    assert rm_owns_account(meta, "005YYY", "Akash Tahir") is False
