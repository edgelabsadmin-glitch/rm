# Design 02 — Signal Source Adapter

**Phase:** 2 (Design)
**Tier:** 1 — first-week lock
**Status:** Draft, Phase 2

---

## Purpose

Define the plug-in interface for ingesting signals from any external source into Pulse's memory layer. Phase 1 ships exactly three adapters — **Chorus**, **Salesforce**, **Calendar** — implemented against this interface. Future phases add Zoom, Slack, Jira, email, news RSS, and others against the *same* interface without rework. The interface is the architectural commitment (PM_CONTEXT §6 rule 20 + memory pattern `signal_source_adapter_pattern_is_load_bearing_when_scoping_for_a_demo`).

---

## Inputs

- **External signal events** in whatever shape the source provides:
  - Chorus webhook for `engagement.complete` + Chorus v3 API for transcript fetch
  - Salesforce CDC (Change Data Capture) or polled SOQL for object updates
  - Calendar webhooks (Google Calendar push notifications or MS Graph subscriptions) for upcoming meetings
- **Adapter configuration** (per-source `.env` keys + per-source rate/retry settings)
- **Idempotency hint** from the source (event-id, conversation-id, message-id) — used to suppress duplicate ingestion

## Outputs

- **Normalized `Episode` envelopes** written to the Temporal Context Graph (Design 01) and to the Postgres `episodes` audit table (Design 04).
- **Ingestion events** logged to the event log: `signal-received`, `signal-normalized`, `episode-ingested`, `episode-deduped`, `ingestion-failed`.
- **One `Episode` per atomic source event**, with provenance back to the source (URL, event-id, source-system, source-timestamp).

---

## Behavior

### The adapter contract

Every adapter implements a single Python class with five methods. **Phase 1 implementations live in `03_build/adapters/`; the interface lives in `03_build/core/adapter.py`.**

```python
# Pseudocode contract — Phase 4 implementation
class SignalSourceAdapter(ABC):
    SOURCE_NAME: str           # e.g. "chorus", "salesforce", "calendar"
    SUPPORTS_WEBHOOKS: bool    # webhook-driven vs. poll-driven
    SUPPORTS_BACKFILL: bool    # can re-ingest historical events

    @abstractmethod
    async def list_recent_events(self, since: datetime) -> list[RawEvent]:
        """Poll path: return raw events since `since`. Used by both poll-only
        adapters and for webhook-receiver backfill on missed deliveries."""

    @abstractmethod
    async def receive_webhook(self, payload: dict, headers: dict) -> list[RawEvent]:
        """Webhook path: validate signature, parse payload, return zero or
        more RawEvents. Raise on malformed/forged payloads."""

    @abstractmethod
    async def fetch_full(self, event: RawEvent) -> RawEvent:
        """Hydrate a thin event (e.g., a webhook notification) into a full
        event (e.g., the transcript text). Idempotent."""

    @abstractmethod
    def normalize(self, raw: RawEvent) -> Episode:
        """Convert source-shape into the canonical Episode envelope. Pure
        function: no I/O, no side effects. Must be deterministic for the
        same input."""

    @abstractmethod
    def dedup_key(self, raw: RawEvent) -> str:
        """Return a stable key for this event. Two events with the same key
        are the same event (idempotency layer in Postgres prevents
        re-ingestion). Format: f"{SOURCE_NAME}:{stable-source-id}"."""
```

### The `Episode` envelope (the canonical normalized shape)

```python
Episode = TypedDict({
    # Identity
    "episode_id": UUID,             # Pulse-assigned, stable
    "dedup_key": str,               # from adapter; uniqueness enforced in Postgres

    # Provenance
    "source": str,                  # "chorus" | "salesforce" | "calendar" | future
    "source_event_id": str,         # the source system's id
    "source_url": str | None,       # link back if applicable
    "source_timestamp": datetime,   # when the event happened in the world

    # Content
    "content_type": Literal["text", "json", "structured"],
    "content": str | dict,          # text body OR structured payload
    "subject": str,                 # short title for the agent ("Acrisure EBR 2026-05-05")
    "description": str,             # 1-line description ("Quarterly business review")

    # Routing hints (pre-computed by adapter to save the LLM work)
    "candidate_entities": list[EntityRef],  # e.g. [{"type": "Customer", "sfdc_id": "001..."}]
    "tags": list[str],              # source-known tags ("ebr", "risk-tagged", "expansion")

    # Pulse-internal
    "ingested_at": datetime,        # when Pulse received it
    "processing_state": Literal["received", "normalized", "ingested", "failed"],
})
```

**Design principles for the envelope:**
1. **Source-side enrichment is encouraged.** If the source already knows the SFDC Account.Id (Chorus does, via `affectlayer__Engagement__c`), the adapter pre-fills `candidate_entities`. The agent shouldn't re-derive what the source already knows.
2. **Content stays in source shape** (text-as-text, JSON-as-JSON). Graphiti's extractor handles both natively; flattening loses signal.
3. **`dedup_key` is the contract for idempotency.** Same key = same event = skip. No `ON CONFLICT DO UPDATE` for episodes — episodes are immutable by intent.
4. **No PHI redaction step in Phase 1** (per PM_CONTEXT Decision 17, Session 5). If PHI ever enters scope, redaction becomes a step in `normalize()` and is adapter-specific.

### The ingestion pipeline (where the adapter sits)

```
   ┌────────────────────┐
   │   Source           │ (Chorus / SFDC / Calendar / future)
   └─────────┬──────────┘
             │  webhook OR poll
             ▼
   ┌────────────────────┐
   │  Receiver (workflow│  - validates signatures
   │  engine: Activep.  │  - rate-limits per source
   │  or self-host n8n) │  - dispatches to the right adapter by URL/topic
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │  Adapter           │  .receive_webhook() OR .list_recent_events()
   │  (per-source code) │  → list[RawEvent]
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │  Dedup gate        │  Postgres `episodes` table; UNIQUE(dedup_key)
   │  (idempotency)     │  Skips already-seen events.
   └─────────┬──────────┘
             │  new events only
             ▼
   ┌────────────────────┐
   │  Hydrator          │  adapter.fetch_full()   (e.g. fetch transcript)
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │  Normalizer        │  adapter.normalize() → Episode envelope
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │  Memory ingest     │  Graphiti.add_episode() (Design 01)
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │  Event log         │  Design 04 — emits ingestion event
   └────────────────────┘
```

**Notes on the diagram:**
- The workflow engine (Activepieces or self-hosted n8n — see Design 11) sits between the source and the adapter code. Its only job is signature validation, rate limiting, and routing. **The adapter does the source-specific logic in code, not in workflow nodes.** This is the separation PM_CONTEXT Decision 9 + memory pattern `workflow_engine_and_agent_framework_are_different_layers_dont_collapse_them` enforces.
- Failures at any stage are caught and re-emitted as `ingestion-failed` events with the source event-id preserved, so retries are explicit (no silent retry-loops).
- Retries: exponential backoff with a 3-attempt cap, then dead-letter. Phase 1 dead-letter destination is a Postgres `episodes_failed` table; a human reviews weekly.

### Error & retry semantics

| Failure mode | Behavior |
|---|---|
| Webhook signature invalid | Reject 401, log to event log as `signal-rejected`, no retry |
| Source API rate-limited (429) | Exponential backoff: 1s → 4s → 16s → dead-letter |
| Source API transient 5xx | Same backoff as 429 |
| Source returns 404 (event gone) | Log `signal-lost`, no retry, surface in admin dashboard |
| `normalize()` raises | Move event to `episodes_failed`, alert |
| `fetch_full()` returns empty/short body (e.g., empty transcript) | Ingest with `tags += ["thin-content"]`, let agent layer downweight |
| Memory ingest fails (Kuzu unreachable) | Hold in `episodes` table with `processing_state = "normalized"`, retry on a 5-min cron |

### Idempotency contract

The Postgres `episodes` table has `UNIQUE(dedup_key)`. The dedup gate is a single insert-or-skip. **The adapter is required to return a stable, deterministic `dedup_key`** even when the same source event arrives twice (webhook + poll-backfill, or webhook retried after timeout). Examples:

- **Chorus:** `dedup_key = f"chorus:conv:{conversation_id}"`
- **Salesforce:** `dedup_key = f"sfdc:{object_api_name}:{record_id}:{last_modified_iso}"` (object-name + id + LastModifiedDate; same record updated twice = two episodes)
- **Calendar:** `dedup_key = f"calendar:{event_id}:{etag}"`

### Phase 1 adapter inventory

| Adapter | SOURCE_NAME | Webhooks | Backfill | Phase 1 owner code path |
|---|---|---|---|---|
| **Chorus** | `chorus` | Yes (Chorus v3 engagement webhooks) | Yes (via `list_recent_events`) | Lift `rm-intelligence-agent/src/chorus_pull.py`; port to adapter shape |
| **Salesforce** | `salesforce` | CDC via Streaming API; polled SOQL fallback | Yes | Lift `rm-intelligence-agent/src/sfdc_pull.py`; constrain to READ ONLY per §6 rule 6 |
| **Calendar** | `calendar` | Google Calendar push notifications (Phase 1 default; MS Graph if EDGE uses Outlook) | No (Phase 1) | Net-new; small surface |

**Calendar adapter scope (Phase 1 minimum, per §13.3 Workflow 2):**
- Detect customer meeting on calendar **24h ahead** of start time.
- Resolve attendee emails to SFDC Account.Id via the existing `salesforce_client` Account lookup.
- Emit one `calendar.upcoming-customer-meeting` Episode per qualifying event.
- Out of Phase 1 scope: meeting-conflict detection, automatic calendar holds (that's an Action Queue dispatch, not an ingestion event), past-meeting reconciliation against Chorus.

### Future adapters (v1.5+) and their no-rework contract

Each future adapter is one Python class implementing the interface. The workflow engine config gains one route; the adapter inventory gains one row. No core code changes.

| v1.5+ Adapter | Mechanism | Trigger |
|---|---|---|
| **Zoom** | Webhooks: `recording.transcript_completed`, `meeting.summary_completed`; poll fallback via Zoom API. | After Phase 1 demo lands. See Spike 2 (`02_zoom_feasibility.md`) for plan-tier prerequisites. |
| **Slack** | Slack Events API webhook subscriptions on configured RM channels. | After Phase 1 demo lands. Per `feedback_dont_flood_slack` memory: Slack is OUT for v1 *as a Pulse output surface*; Slack-as-Pulse-input is a future-phase candidate. |
| **Jira / Email** | Jira webhooks + IMAP poll. Volume-driven decision. | After Phase 1; depends on EDGE's internal issue volume. |
| **News RSS / Google News** | Polled per-account feeds (PM_CONTEXT `project_outside_signals_open_question` already names this as committed for v1 via opportunity-tracker; consider promoting to a first-class adapter in Phase 2). | Phase 2 — promote `opportunity-tracker`-style job-posting signals into the adapter framework. |

---

## EDGE Coverage references

- **§13.2 Workflow 1** row "Meeting ends → webhook fires → workflow activates" — directly implemented by the Chorus adapter's webhook path through the workflow engine receiver.
- **§13.2 Workflow 1** row "Workflow captures meeting transcript" — Chorus adapter's `fetch_full()` step.
- **§13.3 Workflow 2** row "Detect customer meeting on calendar 24h ahead" — Calendar adapter's job.
- **§13.3 Workflow 2** row "Pull all talent profiles from Salesforce" — Salesforce adapter's `list_recent_events()` against `Associates__c`.
- **§13.6 #9** "Signal Source Adapter pattern — pluggable from day one, even though Phase 1 ships only two sources" — this artifact *is* the receipt for that claim. Phase 1 actually ships **three** adapters (Chorus + SFDC + Calendar); §13.6 #9 should be updated.

---

## Open questions

- **Q31** — Workflow engine receiver: do Activepieces and self-hosted n8n both support signature verification + idempotency-key forwarding to the adapter code path? Resolves in Design 11 (tech stack decisions).
- **Q32** — Salesforce CDC vs. polled SOQL for change detection. CDC is realtime but requires Streaming API + permission set. Polled SOQL with `LastModifiedDate > X` is simple and proven (rm-intelligence-agent uses it). PM recommendation: polled SOQL in Phase 1 (every 5 min), CDC in Phase 2.
- **Q33** — Calendar: Google Calendar vs. MS Outlook. Which does EDGE use for RM scheduling? Affects the Phase 1 Calendar adapter's underlying API choice.
- **Q34** — Dead-letter review cadence. PM proposes weekly; user to confirm.
- **Q35** — Backfill bounds. If a new adapter ships and there are 6 months of historical events to backfill, do we ingest all of them or only the last N days? PM proposes: configurable per adapter; default 30 days for Phase 1.

---

## What this is NOT

- **Not a generic ETL framework.** Adapters are simple plug-ins, not a Spark / Airflow analog. No transformations beyond `normalize()`.
- **Not the place agent reasoning runs.** Adapters extract structured shape; the agent reasons later, on demand, via Design 03/05.
- **Not where PHI redaction lives.** Session 5 removed PHI redaction from Phase 1 scope (no PHI in RM calls). If PHI ever enters scope, redaction becomes a per-adapter `normalize()` step — *not* a central middleware (different sources have different PHI surfaces).
- **Not a Zoom adapter.** Zoom is v1.5+. Phase 1 ships three adapters: Chorus, Salesforce, Calendar.
- **Not a Slack-output adapter.** Slack-as-output is OUT for v1 per `feedback_dont_flood_slack` memory. Slack-as-input is v1.5+.
- **Not a database write surface.** Writes back to Salesforce go through the Action Queue (Design 03) with explicit per-write human approval (§6 rule 6). Adapters are read-only by contract.
