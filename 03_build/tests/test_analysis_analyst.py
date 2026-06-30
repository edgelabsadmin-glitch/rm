"""LLM analyst — prompt construction + model routing (Anthropic mocked)."""

from core.analysis import analyst as A


def test_build_prompt_includes_facts_and_signal_defs():
    p = A.build_analyst_prompt({"tier": "Core", "facts": {"x": 1}}, ["sig_a: fires when X"])
    assert "sig_a" in p and "tier" in p.lower()


def test_prompt_forbids_invention():
    p = A.build_analyst_prompt({"tier": "Core", "facts": {"x": 1}}, ["a: x"])
    assert "do not" in p.lower() or "only" in p.lower()


async def test_run_analyst_returns_parsed(monkeypatch):
    captured = {}

    def fake_call(model_id, prompt):
        captured["model_id"] = model_id
        return {
            "signals": [
                {"signal_id": "a", "fired": False, "severity": None, "confidence": 0.9, "evidence": []}
            ],
            "narrative": "ok",
        }

    monkeypatch.setattr(A, "_call_tool", fake_call)
    out, model = await A.run_analyst({"tier": "Core", "facts": {"x": 1}}, ["a: x"])
    assert model == "sonnet" and out["narrative"] == "ok"


async def test_run_analyst_opus_routing(monkeypatch):
    captured = {}

    def fake_call(model_id, prompt):
        captured["model_id"] = model_id
        return {"signals": [], "narrative": "n"}

    monkeypatch.setattr(A, "_call_tool", fake_call)
    out, model = await A.run_analyst({"facts": {}}, ["a: x"], model="opus")
    assert model == "opus" and "opus" in captured["model_id"]
