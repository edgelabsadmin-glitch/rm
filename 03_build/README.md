# EDGE Pulse — `03_build/`

Phase 4 build artifacts. Every change here traces to a spec in `../02_planning/specs/` via its commit message (`[SPEC-NNN] …`, per PM_CONTEXT §4.13).

## Layout

```
03_build/
  api/        FastAPI service (ADR-001: async-everything; 60s middleware timeout)
    main.py       app factory + /health
    middleware/   auth, request-timeout
    webhooks/      /webhooks/<source> endpoints (per Signal Source Adapters)
    actions/       Action Queue API (spec 031)
    admin/         kill switch, Layer 8 surfaces
  core/       business logic
    llm/          config (model-ID pins, spec 003) + client wrapper
    memory/       PulseKuzuDriver (spec 002), graph, retrievers
    events/       event log schema + emitter (spec 008)
    policy/       tier-aware approval matrix (spec 009) + kill switch (spec 010)
    adapters/     Signal Source Adapters (specs 011-015)
    signals/      Signal Definition Library runtime (spec 017)
    profiles/     Per-Profile Markdown layer (spec 029)
    health/       Dual-Sided account health (spec 030)
    agent/        runner.py — the agent reasoning entry point (ADR-001)
  front/      React + Vite + Tailwind (Tier-0 tokens) — Week 3 onward
  scripts/    one-off scripts (demo priming, synthetic seed, sf describe)
  tests/      unit + integration + golden-trace
```

## Environment

Copy `../.env.example` to `../.env` (project root) and populate. `load_dotenv(override=True)` everywhere (spec 003 / Q116).

## Standing constraints (PM_CONTEXT §6)

- Production-org dev under **read-only** ingestion. SFDC writes only via Action Queue with explicit approval (rule 6).
- `sf` CLI API pinned to **v62.0** (rule 17).
- No black-box detection: every signal-detection mechanism has a `../02_planning/signals/*.md` entry (rule 8).
- Test-account denylist: `Test Account` (`0016S00003UGpijQAD`) excluded from metrics + demo (rule 33).
