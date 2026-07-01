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


def _saver(store):
    async def _f(**kw):
        store.update(kw)

    return _f


async def test_opus_pass_saves_no_sonnet(monkeypatch):
    monkeypatch.setattr(G, "_load_pack", _aret(_pack()))
    calls = []

    async def fake_run(pack, defs, *, model="opus"):
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
    assert r["state"] == "ok" and saved["model_used"] == "opus" and calls == ["opus"]


async def test_opus_fail_then_sonnet(monkeypatch):
    monkeypatch.setattr(G, "_load_pack", _aret(_pack()))
    seq = []

    async def fake_run(pack, defs, *, model="opus"):
        seq.append(model)
        if model == "opus":  # fabricated evidence → gate fails
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
                "opus",
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
            "sonnet",
        )

    monkeypatch.setattr(G, "run_analyst", fake_run)
    saved = {}

    async def fake_save(**kw):
        saved.update(kw)

    monkeypatch.setattr(G, "save_snapshot", fake_save)
    monkeypatch.setattr(G, "submit_action", _anoop)

    await G.analyze_entity("account", "A1")
    assert seq == ["opus", "sonnet"] and saved["model_used"] == "sonnet" and saved["state"] == "ok"


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


# ── run modes: incremental + backfill ────────────────────────────────────────


def _wire_runmode(monkeypatch, *, entities, version, last):
    """Stub the DB seams; record analyze_entity calls. Returns the calls list."""
    monkeypatch.setattr(G, "_active_entities", _aret(entities))

    async def fake_version(et, eid):
        return version.get((et, eid))

    async def fake_last(et, eid):
        return last.get((et, eid))

    monkeypatch.setattr(G, "_data_version", fake_version)
    monkeypatch.setattr(G, "_last_version", fake_last)
    monkeypatch.setattr(G, "_status_set", _anoop)
    calls = []

    async def fake_analyze(et, eid, *, data_version=None):
        calls.append((et, eid, data_version))
        return {"state": "ok"}

    monkeypatch.setattr(G, "analyze_entity", fake_analyze)
    return calls


async def test_incremental_skips_unchanged(monkeypatch):
    calls = _wire_runmode(
        monkeypatch,
        entities=[("account", "A1")],
        version={("account", "A1"): "v1"},
        last={("account", "A1"): "v1"},
    )
    await G.run_incremental()
    assert calls == []


async def test_incremental_analyzes_changed(monkeypatch):
    calls = _wire_runmode(
        monkeypatch,
        entities=[("account", "A1")],
        version={("account", "A1"): "v2"},
        last={("account", "A1"): "v1"},
    )
    await G.run_incremental()
    assert calls == [("account", "A1", "v2")]


async def test_backfill_skips_already_current(monkeypatch):
    calls = _wire_runmode(
        monkeypatch,
        entities=[("account", "A1"), ("talent", "T1")],
        version={("account", "A1"): "v1", ("talent", "T1"): "v9"},
        last={("account", "A1"): "v1", ("talent", "T1"): "v0"},
    )
    await G.run_backfill()
    # A1 already at current version → skipped; T1 changed → analyzed.
    assert calls == [("talent", "T1", "v9")]


async def test_backfill_per_entity_error_isolated(monkeypatch):
    _wire_runmode(
        monkeypatch,
        entities=[("account", "A1"), ("account", "A2")],
        version={("account", "A1"): "v1", ("account", "A2"): "v1"},
        last={},
    )
    done = []

    async def boom(et, eid, *, data_version=None):
        if eid == "A1":
            raise RuntimeError("kaboom")
        done.append(eid)
        return {"state": "ok"}

    monkeypatch.setattr(G, "analyze_entity", boom)
    await G.run_backfill()  # must not raise
    assert done == ["A2"]


# ── pipeline: real quant merge + math override end-to-end (added round 2) ─────


def _packf(facts, *, tier="Core", evidence_ids=None):
    return {
        "entity_type": "account",
        "entity_id": "A1",
        "tier": tier,
        "rm_id": "O",
        "facts": {"tier": tier, **facts},
        "evidence_ids": evidence_ids or {"ev1"},
        "snippets": [],
    }


async def test_quant_merge_adds_signal_llm_omitted(monkeypatch):
    # Facts make ebr_overdue fire (high); the LLM omits it entirely → merged in.
    monkeypatch.setattr(G, "_load_pack", _aret(_packf({"days_since_ebr": 400}, tier="Core")))

    async def fake_run(pack, defs, *, model="sonnet"):
        return ({"signals": [], "narrative": "n"}, model)

    monkeypatch.setattr(G, "run_analyst", fake_run)
    saved = {}
    monkeypatch.setattr(G, "save_snapshot", _saver(saved))
    monkeypatch.setattr(G, "_emit_actions", _anoop)

    r = await G.analyze_entity("account", "A1")
    fired = saved["fired_signals"]
    ids = {s["signal_id"] for s in fired}
    assert "ebr_overdue_v1" in ids
    assert any(s["severity"] == "high" for s in fired if s["signal_id"] == "ebr_overdue_v1")
    assert r["priority"] == "high"  # high on Core


async def test_quant_override_corrects_llm_severity_in_pipeline(monkeypatch):
    # LLM fires ebr_overdue as low; math says high → snapshot reflects high.
    monkeypatch.setattr(G, "_load_pack", _aret(_packf({"days_since_ebr": 400}, tier="Core")))

    async def fake_run(pack, defs, *, model="sonnet"):
        return (
            {
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
            },
            model,
        )

    monkeypatch.setattr(G, "run_analyst", fake_run)
    saved = {}
    monkeypatch.setattr(G, "save_snapshot", _saver(saved))
    monkeypatch.setattr(G, "_emit_actions", _anoop)

    await G.analyze_entity("account", "A1")
    ebr = next(s for s in saved["fired_signals"] if s["signal_id"] == "ebr_overdue_v1")
    assert ebr["severity"] == "high"


async def test_pack_none_returns_none_no_save(monkeypatch):
    monkeypatch.setattr(G, "_load_pack", _aret(None))
    saved = {}
    monkeypatch.setattr(G, "save_snapshot", _saver(saved))
    r = await G.analyze_entity("account", "MISSING")
    assert r is None and saved == {}


async def test_healthy_when_nothing_fires(monkeypatch):
    monkeypatch.setattr(G, "_load_pack", _aret(_packf({"days_since_ebr": 5}, tier="Core")))

    async def fake_run(pack, defs, *, model="sonnet"):
        return ({"signals": [], "narrative": "all good"}, model)

    monkeypatch.setattr(G, "run_analyst", fake_run)
    saved = {}
    monkeypatch.setattr(G, "save_snapshot", _saver(saved))
    monkeypatch.setattr(G, "_emit_actions", _anoop)
    r = await G.analyze_entity("account", "A1")
    assert r["priority"] == "healthy" and saved["state"] == "ok"


async def test_incremental_empty_scope(monkeypatch):
    _wire_runmode(monkeypatch, entities=[], version={}, last={})
    result = await G.run_incremental()
    assert result == {"scanned": 0, "analyzed": 0}


async def test_incremental_reports_counts(monkeypatch):
    calls = _wire_runmode(
        monkeypatch,
        entities=[("account", "A1"), ("account", "A2"), ("talent", "T1")],
        version={("account", "A1"): "v2", ("account", "A2"): "v1", ("talent", "T1"): "v2"},
        last={("account", "A1"): "v1", ("account", "A2"): "v1", ("talent", "T1"): "v1"},
    )
    result = await G.run_incremental()
    # A2 unchanged → skipped; A1 + T1 changed → analyzed
    assert result == {"scanned": 3, "analyzed": 2}
    assert ("account", "A2", "v1") not in calls


async def test_backfill_reports_counts(monkeypatch):
    _wire_runmode(
        monkeypatch,
        entities=[("account", "A1"), ("talent", "T1")],
        version={("account", "A1"): "v2", ("talent", "T1"): "v2"},
        last={},
    )
    result = await G.run_backfill()
    assert result["total"] == 2 and result["analyzed"] == 2 and result["errors"] == 0
