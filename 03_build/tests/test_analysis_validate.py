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
