# churn_signal_sentiment_decline_v1

**Version:** v1
**Category:** churn
**Severity model:** scored (0-1)
**Owning skill(s):** Skill 01 (detect-talent-signal — emits the underlying sentiment vector); Skill 03 (renewal-watcher), Skill 05 (escalation-router) — consume the decline trajectory
**Status:** active

## Plain-English definition

Customer sentiment is trending downward over time. Pulse maintains a multi-axis sentiment vector per Customer (warmth, frustration, urgency, momentum — per Skill 01 spec and Decision log entry 4.4 — *not* a single 1-10 score). When the trajectory of any axis declines meaningfully over a rolling window, this signal fires. The signal is most useful as an early-warning indicator: a customer trending down before they voice a problem is a customer the RM should reach out to *before* the formal complaint.

## Detection mechanism

**Type:** hybrid (rule on aggregated trajectory; LLM only to assist with the underlying per-episode sentiment extraction — already done by Skill 01)

**Rule layer:**
```
For each Customer:
  episodes_60d = retrieve episodes with mentions(Customer) in last 60 days
  sentiment_vectors_60d = [
    episode.sentiment_vector  # written by Skill 01 during ingestion
    for episode in episodes_60d
    if episode.sentiment_vector is not None
  ]

  if len(sentiment_vectors_60d) < 4:
    return None  # insufficient data; do not fire

  # Compute 30-day vs prior-30-day trajectory per axis
  recent = sentiment_vectors_60d where date >= today - 30
  prior  = sentiment_vectors_60d where date BETWEEN today - 60 AND today - 30

  for axis in ['warmth', 'frustration', 'urgency', 'momentum']:
    # warmth and momentum: higher is better; frustration and urgency: higher is worse
    direction = +1 if axis in ['warmth', 'momentum'] else -1
    recent_avg = mean(v[axis] for v in recent)
    prior_avg  = mean(v[axis] for v in prior)
    delta      = (recent_avg - prior_avg) * direction
    # delta < 0 means decline on this axis

    if delta < -0.15:  # threshold: 15% normalized decline
      record axis_decline(axis, magnitude=abs(delta))

  if any axis_decline recorded:
    severity_score = max(magnitude across all axes) / 0.5  # normalize to 0-1
    severity_score = min(severity_score, 1.0)
    fire signal with score
```

**LLM step (already done upstream by Skill 01):** Skill 01's signal-extraction prompt produces the per-episode `sentiment_vector` from the episode's content. This signal does not call the LLM again — it consumes Skill 01's output.

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| Graphiti episodes (any source) | `sentiment_vector` (4 axes, set by Skill 01 during ingestion) | last 60 days |
| `mentions` edges from episodes to Customer | source, date | last 60 days |

## Triggering threshold

- **Fires when** any single axis shows ≥0.15 normalized decline (rolling 30d vs prior 30d).
- **Severity score** = `max(axis decline) / 0.5`, clamped to `[0, 1]`. Severity 0.3 = soft, 0.6 = moderate, 0.85+ = sharp.
- **Minimum data requirement:** ≥4 sentiment-bearing episodes in the 60-day window. Below threshold, the signal does not fire (insufficient evidence).

## Tier-aware variants

| Account tier | Variant |
|---|---|
| **SMB** | Threshold raised to 0.20 normalized decline (SMB has more episode-to-episode sentiment variance per RM observation). |
| **Mid-Market** | Baseline 0.15 threshold. |
| **Enterprise** | Threshold lowered to 0.10 normalized decline AND minimum-data requirement reduced to 3 episodes (small Enterprise customers may have fewer touchpoints but each carries more weight). |

## False-positive failure modes

- **Single bad call.** A bad EBR drops the rolling 30d average; the prior period was fine; the signal fires. This is *probably* worth flagging but is sometimes noise. Mitigation: severity_score scales with magnitude; small declines surface as `low` and the RM can dismiss.
- **Sentiment-extraction noise from Skill 01.** If Skill 01's extractor mislabels a positive call as negative (e.g. fails to recognize sarcasm), the signal inherits the error. Mitigation: golden-trace tests for Skill 01's extractor (per §6 rule 10).
- **Seasonal cycles.** Some customers run cyclically — quarter-end stress shows up as frustration; it's normal. Mitigation: Phase 1 doesn't compensate; v1.5+ may add per-customer baseline learning.

## False-negative failure modes

- **Slow flat decline below threshold.** Sentiment declining 0.05 per month for six months never crosses the 0.15-in-30-days rule. v1.5+ enhancement: longer-window detection.
- **One-axis-positive masking.** If `warmth` improves while `frustration` rises, the max-decline calculation captures the frustration axis correctly — no false negative. (Documented for clarity.)
- **No sentiment data.** If Skill 01 hasn't run on the customer's recent episodes (e.g. raw SFDC updates without LLM-extracted sentiment), this signal cannot fire. Mitigation: Skill 01 runs episode-driven on every ingestion (per its spec) — coverage should be complete in steady state.

## Adjustability

| Parameter | Type | Default | Who can adjust | Effect of increasing |
|---|---|---|---|---|
| `decline_threshold` (Mid baseline) | float | 0.15 | Admin | Fewer fires, higher precision |
| `recent_window_days` | int | 30 | Admin | Smoother trajectory at cost of slower detection |
| `min_episode_count` | int | 4 | Admin | More confidence per fire, fewer fires |
| `severity_normalizer` | float | 0.5 | Admin | Re-scale severity-score distribution |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate (instances/day per RM): _TBD_
- Action-approval rate when this signal contributes: _TBD_
- Outcome-recorded rate: _TBD_
- Apparent false-positive rate: _TBD_
- Last tuned: never

## Examples

### Example 1 — Acrisure
- **Evidence:** 8 sentiment-bearing episodes last 60 days. Frustration axis: prior 30d avg 0.22; recent 30d avg 0.41. Delta on frustration (lower is better) = -0.19. Warmth axis: prior 0.68; recent 0.64. Delta on warmth (higher is better) = -0.04. Max decline = 0.19 on frustration.
- **Severity score:** 0.19 / 0.5 = 0.38 → `medium-low`
- **Action proposed:** Skill 03 (renewal-watcher) draft a check-in; Skill 05 (escalation-router) on standby (not fired yet at this severity).

### Example 2 — Pinnacle (Enterprise)
- **Evidence:** 5 episodes last 60d. Momentum: prior 0.74; recent 0.59. Delta = -0.15 (right at Enterprise lowered threshold of 0.10 — exceeds).
- **Severity:** 0.15 / 0.5 = 0.30 → `low-medium`, Enterprise variant fires.
- **Action proposed:** Skill 03 drafts brief check-in; cc VP-CS per Enterprise tier rule.

### Example 3 — Mendota — does NOT fire
- **Evidence:** Only 3 episodes in last 60d (below `min_episode_count`).
- **Signal does not fire.** No action proposed by this signal (though other signals may).

## Open questions

- **Q128:** Confirmation of Skill 01's sentiment-vector axes. PM_CONTEXT Decision 4.4 named warmth / frustration / urgency / momentum as the proposed quartet (Q51). User to confirm or revise before Phase 4 codification.
- **Q129:** Per-customer baseline learning. Some customers run hot (lots of frustration tone is normal); some run cold (low warmth is the baseline). v1.5+ enhancement: Layer 8 Mechanism 2 (per-RM preference learning) could extend to per-Customer sentiment baselines. Filed.
