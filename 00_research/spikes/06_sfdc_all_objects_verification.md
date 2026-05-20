# Spike 6 — All-8-Objects SFDC Verification + P95 Latency Benchmark

**Date:** 2026-05-21
**Goal:** Close the Gate-2 deliverable carried over from Session-15's deferral adjudication — verify that spec-012's eight in-scope SFDC objects are all reachable and queryable against the **production** org, and benchmark per-query P95 latency against the <500ms target.
**Benchmark harness:** `03_build/scripts/sfdc_bench.py` (N=10 per object, 7-day `LastModifiedDate` window, `LIMIT 200`, via the same `sf` CLI path the spec-012 adapter uses).

---

## A. Method

For each of spec-012's eight objects (`core/adapters/sfdc.py::OBJECTS`) the harness builds the adapter's own SOQL (`SFDCAdapter.build_query`, including the 14-value risk-Case taxonomy filter on `Case`), appends `LIMIT 200`, and times `sf data query --target-org production --json` end-to-end ten times. It records per-object p50 / p95 / max (over successful runs) and the record count returned, plus an overall percentile across all 80 calls. Wall-clock is measured around the subprocess (`time.perf_counter`), i.e. exactly what the production poller pays per object.

`sf` CLI: `@salesforce/cli` on node-v23, org alias `production` (`dabeera.zaheen@onedge.co`, Connected).

---

## B. Reachability / schema verification — **PASS (8/8)**

Every object queried successfully on all 10 runs (`n_ok = 10/10`), with the adapter's full field set and no schema gaps or SOQL errors:

| Object | Reachable | Field set valid | Records (7d window) | Note |
|---|---|---|---|---|
| `Account` | ✅ | ✅ | 180 | — |
| `Contact` | ✅ | ✅ | 116 | — |
| `Opportunity` | ✅ | ✅ | 200 (capped at LIMIT) | — |
| `RM_Outreach__c` | ✅ | ✅ | 21 | the "RM Object" |
| `Associates__c` | ✅ | ✅ | 150 | talent; stage history source |
| `Account_Plan__c` | ✅ | ✅ | 1 | sparse but present |
| `Case` (incl. `Description` + `Details__c`) | ✅ | ✅ | 15 | risk-taxonomy filter applied |
| `affectlayer__Engagement__c` | ✅ | ✅ | **0** | query valid; 0 rows in the 7-day window (see caveat) |

**Caveat — `affectlayer__Engagement__c` returned 0 rows in the 7-day window.** The query is schema-valid and executes cleanly; zero rows means no Chorus engagements were synced to SFDC in the last 7 days, not a defect. Pulse joins Chorus primarily via the live Chorus adapter (spec 013); the SFDC Engagement object is the secondary join key. **Recommend** a one-time re-run with a 90-day window to confirm the object is non-empty org-wide before Gate 2 sign-off (low risk; the adapter handles empty result sets gracefully — it skips, never aborts the poll).

---

## C. Latency benchmark — per-query P95

```
object                       n_ok  recs   p50_ms   p95_ms   max_ms
Account                        10   180   1502.4   1950.2   1950.2
Contact                        10   116   1517.7   2543.0   2543.0
Opportunity                    10   200   1500.4   2573.0   2573.0
RM_Outreach__c                 10    21   1515.9   1794.1   1794.1
Associates__c                  10   150   1512.2   2891.8   2891.8
Account_Plan__c                10     1   1510.4   2542.6   2542.6
Case                           10    15   1764.0   2537.4   2537.4
affectlayer__Engagement__c     10     0   1016.1   2559.5   2559.5
OVERALL  p50=1515.9ms  p95=2542.6ms  mean=1653.3ms  n=80
```

**The <500ms target is NOT met on the `sf` CLI path.** Overall p50 ≈ 1.5s, p95 ≈ 2.5s — ~3–5× over target.

---

## D. Root-cause isolation — it's the CLI, not the API

The latency floor is **per-invocation session setup inside `sf data query`**, not Salesforce API compute and not result-set size:

| Measurement | Time |
|---|---|
| `sf --version` (pure Node/CLI boot, no org) | ~0.2s |
| `sf data query "SELECT Id FROM Account LIMIT 1"` (1 row) | ~1.8s |
| Full 200-row object queries (table above) | ~1.5–2.9s |

A 1-row query costs essentially the same as a 200-row query (~1.8s), and Node boot alone is only ~0.2s — so ~1.5s per call is **org-auth resolution + JSForce connection establishment + REST round-trip, paid fresh on every subprocess invocation**. Result-set size adds only a few hundred ms on top. (`Engagement`'s lower p50 of ~1.0s with 0 rows is consistent with this: no row marshalling.)

**Implication:** no amount of SOQL tuning brings the CLI path under 500ms; the cost is structural to spawning `sf` per query.

---

## E. Verdict

1. **Object reachability / schema coverage: PASS.** All eight in-scope objects are queryable against production with the adapter's exact field sets; no schema drift. The poll/backfill path (`SFDCAdapter.list_recent_events`) is production-valid.
2. **P95 <500ms on the CLI path: NOT MET (p95 ≈ 2.5s), and not achievable via `sf` CLI** for the reason in §D.
3. **This does not block Gate 2**, because the 500ms SLO does not actually apply to the SFDC poll path:
   - The production ingestion path is the **Activepieces `sfdc_poll_changes` 5-minute cron** fanning changed records to `/webhooks/sfdc`. A 5-minute batch poll is latency-insensitive; 1.5s/object × 8 ≈ 12s/cycle is comfortably inside a 5-minute budget.
   - The latency-sensitive path is the in-process **`/webhooks/sfdc` → normalize → enqueue-ingest** hop, which never calls `sf` and is unaffected by these numbers.

**Recommendation (for any future real-time/interactive SFDC read):** replace the per-query `sf` subprocess with a **persistent authenticated REST client** (reuse one access token + an `httpx` connection pool, or `simple-salesforce`). That removes the ~1.5s per-call setup and should land individual reads well under 500ms. Tracked as **Q153**. No code change required for Phase-1 (poll path is fit-for-purpose); this is a v1.5+ optimization for interactive reads only.

---

## F. Filed

- **Q153** (`99_open_questions.md`) — SFDC read-latency SLO: `sf` CLI per-query floor (~1.5s) vs the <500ms target; persistent-REST-client remedy for interactive reads; the 5-min poll path is unaffected.
- Re-run `affectlayer__Engagement__c` with a 90-day window before Gate-2 sign-off (caveat in §B).
