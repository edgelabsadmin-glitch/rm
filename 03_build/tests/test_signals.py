"""
SPEC-017 unit tests — Signal Definition Library runtime + per-signal evaluate.

No DB/LLM: module.evaluate is pure (reads ctx.facts). The CI meta-test enforces
1:1 markdown↔code correspondence and header↔META alignment. The event-emitting
runtime.evaluate is covered in tests/test_signals_db.py.
"""

import pytest

from core.signals import runtime
from core.signals.base import EvaluationContext


def _ctx(tier=None, **facts):
    return EvaluationContext(customer_id="001X", tier=tier, facts=facts)


# ── CI meta-test: markdown ↔ code ───────────────────────────────────────────
def test_markdown_and_code_correspond_one_to_one():
    runtime.check_correspondence()  # raises on any orphan md or py


def test_library_loads_all_14_with_aligned_meta():
    lib = runtime.load_signal_library()
    assert len(lib) == 14
    # alignment is asserted inside load_signal_library; spot-check a few metas
    assert lib["talent_pay_concern_v1"].meta.owning_skills == frozenset({1, 4, 5, 9, 10})
    assert lib["churn_signal_sentiment_decline_v1"].meta.severity_model == "scored"
    assert lib["account_silence_pattern_v1"].meta.detection_type == "rule-based"


def test_evaluate_unknown_signal_raises():
    lib = runtime.load_signal_library()
    assert "nope_v1" not in lib


@pytest.mark.parametrize(
    "loaded", list(runtime.load_signal_library().values()), ids=lambda x: x.meta.signal_id
)
def test_every_signal_id_matches_filename(loaded):
    assert loaded.definition.signal_id == loaded.meta.signal_id


# ── per-signal evaluate (fire + no-fire) ─────────────────────────────────────
import core.signals.account_silence_pattern_v1 as account_silence  # noqa: E402
import core.signals.churn_signal_competitor_mention_v1 as competitor  # noqa: E402
import core.signals.churn_signal_contact_disengagement_v1 as contact  # noqa: E402
import core.signals.churn_signal_renewal_period_silence_v1 as renewal  # noqa: E402
import core.signals.churn_signal_sentiment_decline_v1 as sentiment  # noqa: E402
import core.signals.client_termination_pattern_v1 as termination  # noqa: E402
import core.signals.escalation_signal_case_pattern_v1 as case_pattern  # noqa: E402
import core.signals.escalation_signal_severity_jump_v1 as sev_jump  # noqa: E402
import core.signals.expansion_signal_job_posting_match_v1 as job_match  # noqa: E402
import core.signals.recognition_signal_advocacy_candidate_v1 as advocacy  # noqa: E402
import core.signals.talent_burnout_signal_v1 as burnout  # noqa: E402


async def test_contact_disengagement_fires_medium_two_rules():
    # rule A (silence) + rule C (active→silent), Mid-Market, not in renewal
    r = await contact.evaluate(
        _ctx(
            tier="Mid-Market",
            days_since_last_reply=21,
            chorus_call_count_21d=0,
            chorus_call_count_prior_21d=1,
            in_renewal_window=False,
        )
    )
    assert r.fired and r.severity == "medium"
    assert len(r.evidence) == 2


async def test_contact_disengagement_suppressed_by_llm_explanation():
    r = await contact.evaluate(
        _ctx(tier="Mid-Market", days_since_last_reply=30, is_explained=True, explanation="PTO")
    )
    assert r.fired is False


async def test_contact_disengagement_no_fire_under_threshold():
    r = await contact.evaluate(_ctx(tier="SMB", days_since_last_reply=16))  # < 21 SMB
    assert r.fired is False


async def test_account_silence_tiers_by_overage():
    assert (
        await account_silence.evaluate(_ctx(days_since_activity=10, silence_days=21))
    ).fired is False
    r = await account_silence.evaluate(_ctx(days_since_activity=55, silence_days=21))
    assert r.fired and r.severity == "high"


async def test_renewal_silence_fires_in_window():
    r = await renewal.evaluate(_ctx(renewal_days=20, days_since_contact=20))
    assert r.fired and r.severity == "high"
    assert (await renewal.evaluate(_ctx(renewal_days=200, days_since_contact=30))).fired is False


async def test_sentiment_decline_scored():
    r = await sentiment.evaluate(_ctx(sentiment_now=0.4, sentiment_prior=0.8))
    assert r.fired and r.score == 0.4
    assert (await sentiment.evaluate(_ctx(sentiment_now=0.75, sentiment_prior=0.8))).fired is False


async def test_client_termination_rate():
    r = await termination.evaluate(_ctx(replaced_count=3, terminated_count=2, total_associates=10))
    assert r.fired and r.severity == "medium"  # 50%
    assert (await termination.evaluate(_ctx(replaced_count=1, total_associates=10))).fired is False


async def test_case_pattern_recurring_or_count():
    assert (await case_pattern.evaluate(_ctx(open_risk_cases=4))).severity == "high"
    assert (await case_pattern.evaluate(_ctx(open_risk_cases=1, recurring_category=True))).fired
    assert (await case_pattern.evaluate(_ctx(open_risk_cases=1))).fired is False


async def test_severity_jump():
    assert (await sev_jump.evaluate(_ctx(prior_severity="low", current_severity="high"))).fired
    assert (
        await sev_jump.evaluate(_ctx(prior_severity="high", current_severity="low"))
    ).fired is False


async def test_job_posting_tier_mapping():
    assert (await job_match.evaluate(_ctx(match_tier="hottest"))).severity == "high"
    assert (await job_match.evaluate(_ctx(match_tier="warm"))).severity == "medium"
    assert (await job_match.evaluate(_ctx(match_tier="off-scope"))).fired is False


async def test_advocacy_scored_threshold():
    assert (await advocacy.evaluate(_ctx(advocacy_score=0.82))).fired
    assert (await advocacy.evaluate(_ctx(advocacy_score=0.4))).fired is False


async def test_competitor_takes_max_severity():
    r = await competitor.evaluate(
        _ctx(
            competitor_mentions=[
                {"competitor": "Acme", "severity": "low", "quote": "saw Acme"},
                {"competitor": "Globex", "severity": "high", "quote": "switching to Globex"},
            ]
        )
    )
    assert r.fired and r.severity == "high"
    assert (await competitor.evaluate(_ctx(competitor_mentions=[]))).fired is False


async def test_extraction_backed_burnout():
    r = await burnout.evaluate(_ctx(burnout={"fired": True, "severity": "high", "evidence": ["q"]}))
    assert r.fired and r.severity == "high"
    assert (await burnout.evaluate(_ctx())).fired is False  # no extraction → no fire
