"""Signal catalog routing + integrity — the defs handed to the LLM analyst."""

from core.analysis.quant_signals import QUANT_SIGNALS
from core.analysis.signal_catalog import signal_defs_for


def _ids(lines):
    return [ln.split(":", 1)[0].strip() for ln in lines]


def test_account_and_talent_nonempty():
    assert signal_defs_for("account")
    assert signal_defs_for("talent")


def test_unknown_entity_defaults_to_account():
    assert signal_defs_for("widget") == signal_defs_for("account")


def test_every_line_has_id_and_description():
    for et in ("account", "talent"):
        for ln in signal_defs_for(et):
            sid, _, desc = ln.partition(":")
            assert sid.strip() and desc.strip(), f"malformed catalog line: {ln!r}"


def test_no_duplicate_ids_within_entity():
    for et in ("account", "talent"):
        ids = _ids(signal_defs_for(et))
        assert len(ids) == len(set(ids)), f"duplicate signal id in {et} catalog"


def test_talent_only_signals_not_in_account():
    talent_ids = set(_ids(signal_defs_for("talent")))
    account_ids = set(_ids(signal_defs_for("account")))
    assert "ramp_stall_v1" in talent_ids
    assert "talent_silence_concern_v1" in talent_ids
    assert "ramp_stall_v1" not in account_ids


def test_account_signals_include_core_quant():
    account_ids = set(_ids(signal_defs_for("account")))
    for sid in (
        "ebr_overdue_v1",
        "response_time_degradation_v1",
        "coverage_gap_v1",
        "single_threaded_account_v1",
        "inbound_volume_drop_v1",
        "talent_attrition_velocity_v1",
    ):
        assert sid in account_ids


def test_all_quant_signals_routed_somewhere():
    routed = set(_ids(signal_defs_for("account"))) | set(_ids(signal_defs_for("talent")))
    for sid in QUANT_SIGNALS:
        assert sid in routed, f"{sid} has a quant evaluator but no catalog entry"
