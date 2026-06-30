"""Anti-hallucination validation gate — pure."""

from core.analysis.quant_signals import QuantResult
from core.analysis.validate import validate_matrix


def _pack():
    return {"evidence_ids": {"ev1", "ev2"}}


def test_fabricated_evidence_rejected():
    out = {
        "signals": [
            {
                "signal_id": "churn_x",
                "fired": True,
                "severity": "high",
                "confidence": 0.9,
                "evidence": ["ev_FAKE"],
            }
        ],
        "narrative": "n",
    }
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant={})
    assert not ok and any("fabricated" in r for r in reasons)


def test_grounded_evidence_passes():
    out = {
        "signals": [
            {
                "signal_id": "churn_x",
                "fired": True,
                "severity": "high",
                "confidence": 0.9,
                "evidence": ["ev1"],
            }
        ],
        "narrative": "n",
    }
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant={})
    assert ok


def test_low_confidence_demoted():
    out = {
        "signals": [
            {
                "signal_id": "churn_x",
                "fired": True,
                "severity": "high",
                "confidence": 0.2,
                "evidence": ["ev1"],
            }
        ],
        "narrative": "n",
    }
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant={})
    assert ok and cleaned["signals"][0]["fired"] is False


def test_math_override_demotes_false_positive():
    out = {
        "signals": [
            {
                "signal_id": "ebr_overdue_v1",
                "fired": True,
                "severity": "high",
                "confidence": 0.9,
                "evidence": ["ev1"],
            }
        ],
        "narrative": "n",
    }
    quant = {"ebr_overdue_v1": QuantResult("ebr_overdue_v1", False)}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant=quant)
    sig = next(s for s in cleaned["signals"] if s["signal_id"] == "ebr_overdue_v1")
    assert sig["fired"] is False and any("override" in r for r in reasons)


def test_math_override_corrects_severity():
    out = {
        "signals": [
            {
                "signal_id": "ebr_overdue_v1",
                "fired": True,
                "severity": "low",
                "confidence": 0.9,
                "evidence": ["ev1"],
            }
        ],
        "narrative": "n",
    }
    quant = {"ebr_overdue_v1": QuantResult("ebr_overdue_v1", True, "high")}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant=quant)
    sig = next(s for s in cleaned["signals"] if s["signal_id"] == "ebr_overdue_v1")
    assert sig["fired"] is True and sig["severity"] == "high"


def test_malformed_rejected():
    ok, cleaned, reasons = validate_matrix({"bad": 1}, _pack(), quant={})
    assert not ok


# ── deeper anti-hallucination coverage (added round 2) ───────────────────────


def _sig(**kw):
    base = {
        "signal_id": "churn_x",
        "fired": True,
        "severity": "high",
        "confidence": 0.9,
        "evidence": ["ev1"],
    }
    base.update(kw)
    return base


def test_out_not_dict_rejected():
    ok, _, reasons = validate_matrix(["nope"], _pack(), quant={})
    assert not ok and "malformed" in reasons[0]


def test_signals_not_a_list_rejected():
    ok, _, reasons = validate_matrix({"signals": "x", "narrative": "n"}, _pack(), quant={})
    assert not ok


def test_signal_entry_missing_signal_id_rejected():
    out = {"signals": [{"fired": True, "evidence": ["ev1"]}], "narrative": "n"}
    ok, _, reasons = validate_matrix(out, _pack(), quant={})
    assert not ok and "malformed" in reasons[0]


def test_confidence_exactly_at_floor_kept():
    out = {"signals": [_sig(confidence=0.4)], "narrative": "n"}
    ok, cleaned, _ = validate_matrix(out, _pack(), quant={})
    assert ok and cleaned["signals"][0]["fired"] is True


def test_missing_confidence_treated_as_zero_demotes():
    s = _sig()
    del s["confidence"]
    out = {"signals": [s], "narrative": "n"}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant={})
    assert ok and cleaned["signals"][0]["fired"] is False
    assert any("confidence" in r for r in reasons)


def test_invalid_severity_normalized_to_none():
    out = {"signals": [_sig(severity="critical")], "narrative": "n"}
    ok, cleaned, _ = validate_matrix(out, _pack(), quant={})
    # fired stays (has evidence + confidence) but severity is scrubbed
    assert ok and cleaned["signals"][0]["fired"] is True
    assert cleaned["signals"][0]["severity"] is None


def test_non_string_evidence_filtered_then_demoted():
    out = {"signals": [_sig(evidence=[123, None, {"x": 1}])], "narrative": "n"}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant={})
    # all evidence non-string → filtered to empty → no-evidence demotion
    assert ok and cleaned["signals"][0]["fired"] is False
    assert any("no evidence" in r for r in reasons)


def test_not_fired_signal_skips_evidence_check():
    # a not-fired signal with bogus evidence must NOT reject the whole matrix
    out = {
        "signals": [{"signal_id": "x", "fired": False, "evidence": ["ev_FAKE"], "confidence": 0.1}],
        "narrative": "n",
    }
    ok, cleaned, _ = validate_matrix(out, _pack(), quant={})
    assert ok and cleaned["signals"][0]["fired"] is False


def test_quant_overrides_llm_miss_to_fired():
    # LLM did not fire, but the math says fired-high → override fires it
    out = {
        "signals": [
            {"signal_id": "ebr_overdue_v1", "fired": False, "evidence": [], "confidence": 0.9}
        ],
        "narrative": "n",
    }
    quant = {"ebr_overdue_v1": QuantResult("ebr_overdue_v1", True, "high")}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant=quant)
    sig = cleaned["signals"][0]
    assert ok and sig["fired"] is True and sig["severity"] == "high"
    assert any("override" in r for r in reasons)


def test_quant_fires_even_when_llm_evidence_demoted():
    # LLM fired with NO evidence (demoted), but the deterministic math fires → authoritative
    out = {
        "signals": [
            {
                "signal_id": "ebr_overdue_v1",
                "fired": True,
                "severity": "low",
                "evidence": [],
                "confidence": 0.9,
            }
        ],
        "narrative": "n",
    }
    quant = {"ebr_overdue_v1": QuantResult("ebr_overdue_v1", True, "high")}
    ok, cleaned, _ = validate_matrix(out, _pack(), quant=quant)
    sig = cleaned["signals"][0]
    assert sig["fired"] is True and sig["severity"] == "high"


def test_quant_agreement_no_override_reason():
    out = {
        "signals": [
            {
                "signal_id": "ebr_overdue_v1",
                "fired": True,
                "severity": "high",
                "evidence": ["ev1"],
                "confidence": 0.9,
            }
        ],
        "narrative": "n",
    }
    quant = {"ebr_overdue_v1": QuantResult("ebr_overdue_v1", True, "high")}
    ok, _, reasons = validate_matrix(out, _pack(), quant=quant)
    assert ok and not any("override" in r for r in reasons)


def test_mixed_signals_one_fired_one_not():
    out = {
        "signals": [
            {
                "signal_id": "a",
                "fired": True,
                "severity": "high",
                "evidence": ["ev1"],
                "confidence": 0.9,
            },
            {"signal_id": "b", "fired": False, "evidence": [], "confidence": 0.0},
        ],
        "narrative": "n",
    }
    ok, cleaned, _ = validate_matrix(out, _pack(), quant={})
    fired = [s for s in cleaned["signals"] if s["fired"]]
    assert ok and len(cleaned["signals"]) == 2 and len(fired) == 1


def test_empty_signals_list_is_valid():
    ok, cleaned, _ = validate_matrix({"signals": [], "narrative": "n"}, _pack(), quant={})
    assert ok and cleaned["signals"] == []
