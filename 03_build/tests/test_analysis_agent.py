"""Orchestrator pipeline + Sonnet→Opus fallback (collaborators mocked)."""

from core.analysis import agent as G


def _pack(tier="Core"):
    return {
        "entity_type": "account",
        "entity_id": "A1",
        "tier": tier,
        "rm_id": "O",
        "facts": {"tier": tier, "days_since_ebr": None},
        "evidence_ids": {"ev1"},
        "snippets": [],
    }


def _aret(value):
    async def _f(*a, **k):
        return value

    return _f


async def _anoop(*a, **k):
    return None


async def test_sonnet_pass_saves_no_opus(monkeypatch):
    monkeypatch.setattr(G, "_load_pack", _aret(_pack()))
    calls = []

    async def fake_run(pack, defs, *, model="sonnet"):
        calls.append(model)
        return (
            {
                "signals": [
                    {
                        "signal_id": "a",
                        "fired": False,
                        "severity": None,
                        "confidence": 0.9,
                        "evidence": [],
                    }
                ],
                "narrative": "ok",
            },
            model,
        )

    monkeypatch.setattr(G, "run_analyst", fake_run)
    saved = {}

    async def fake_save(**kw):
        saved.update(kw)

    monkeypatch.setattr(G, "save_snapshot", fake_save)
    monkeypatch.setattr(G, "submit_action", _anoop)

    r = await G.analyze_entity("account", "A1")
    assert r["state"] == "ok" and saved["model_used"] == "sonnet" and calls == ["sonnet"]


async def test_sonnet_fail_then_opus(monkeypatch):
    monkeypatch.setattr(G, "_load_pack", _aret(_pack()))
    seq = []

    async def fake_run(pack, defs, *, model="sonnet"):
        seq.append(model)
        if model == "sonnet":  # fabricated evidence → gate fails
            return (
                {
                    "signals": [
                        {
                            "signal_id": "a",
                            "fired": True,
                            "severity": "high",
                            "confidence": 0.9,
                            "evidence": ["ev_FAKE"],
                        }
                    ],
                    "narrative": "x",
                },
                "sonnet",
            )
        return (
            {
                "signals": [
                    {
                        "signal_id": "a",
                        "fired": False,
                        "severity": None,
                        "confidence": 0.9,
                        "evidence": [],
                    }
                ],
                "narrative": "ok",
            },
            "opus",
        )

    monkeypatch.setattr(G, "run_analyst", fake_run)
    saved = {}

    async def fake_save(**kw):
        saved.update(kw)

    monkeypatch.setattr(G, "save_snapshot", fake_save)
    monkeypatch.setattr(G, "submit_action", _anoop)

    await G.analyze_entity("account", "A1")
    assert seq == ["sonnet", "opus"] and saved["model_used"] == "opus" and saved["state"] == "ok"


async def test_both_fail_marks_needs_review(monkeypatch):
    monkeypatch.setattr(G, "_load_pack", _aret(_pack()))

    async def fake_run(pack, defs, *, model="sonnet"):
        return (
            {
                "signals": [
                    {
                        "signal_id": "a",
                        "fired": True,
                        "severity": "high",
                        "confidence": 0.9,
                        "evidence": ["ev_FAKE"],
                    }
                ],
                "narrative": "x",
            },
            model,
        )

    monkeypatch.setattr(G, "run_analyst", fake_run)
    saved = {}

    async def fake_save(**kw):
        saved.update(kw)

    monkeypatch.setattr(G, "save_snapshot", fake_save)
    monkeypatch.setattr(G, "submit_action", _anoop)

    r = await G.analyze_entity("account", "A1")
    assert r["state"] == "needs_review" and saved["state"] == "needs_review"


async def test_high_signal_emits_action(monkeypatch):
    # Imports core.agent.context (needs py3.11+); runs on CI.
    monkeypatch.setattr(G, "_load_pack", _aret(_pack("Strategic")))

    async def fake_run(pack, defs, *, model="sonnet"):
        return (
            {
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
            },
            model,
        )

    monkeypatch.setattr(G, "run_analyst", fake_run)
    monkeypatch.setattr(G, "save_snapshot", _anoop)
    submitted = []

    async def fake_submit(ctx, action):
        submitted.append(action)

    monkeypatch.setattr(G, "submit_action", fake_submit)

    r = await G.analyze_entity("account", "A1")
    assert r["priority"] == "critical" and len(submitted) == 1
