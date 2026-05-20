"""
One-off: all-8-objects SFDC poll verification + per-query P95 latency benchmark
(Gate-2 deliverable, Session-15 deferral). Runs each in-scope object's SOQL via
the `sf` CLI against the production org N times and reports latency percentiles +
record counts. Not part of the test suite. Usage: python scripts/sfdc_bench.py [N]
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta

from core.adapters.sfdc import OBJECTS, SFDCAdapter

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
TARGET_ORG = "production"
SINCE = datetime.now(UTC) - timedelta(days=7)


def run_query(query: str) -> tuple[float, int, bool]:
    """Return (elapsed_seconds, record_count, ok)."""
    cmd = ["sf", "data", "query", "--target-org", TARGET_ORG, "--query", query, "--json"]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    elapsed = time.perf_counter() - t0
    if p.returncode != 0:
        return elapsed, 0, False
    try:
        recs = json.loads(p.stdout)["result"].get("records", [])
    except (json.JSONDecodeError, KeyError):
        return elapsed, 0, False
    return elapsed, len(recs), True


def pctl(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round(q * (len(xs) - 1)))))
    return xs[k]


def main() -> None:
    adapter = SFDCAdapter(target_org=TARGET_ORG)
    print(f"# SFDC all-8-objects benchmark — N={N} per object, since={SINCE.isoformat()}\n")
    print(f"{'object':<28} {'n_ok':>4} {'recs':>5} {'p50_ms':>8} {'p95_ms':>8} {'max_ms':>8}")
    print("-" * 70)
    overall: list[float] = []
    for obj in OBJECTS:
        query = adapter.build_query(obj, SINCE) + " LIMIT 200"
        samples: list[float] = []
        recs = 0
        ok_n = 0
        for _ in range(N):
            elapsed, n, ok = run_query(query)
            if ok:
                samples.append(elapsed * 1000.0)
                recs = n
                ok_n += 1
            overall.append(elapsed * 1000.0)
        p50 = pctl(samples, 0.50)
        p95 = pctl(samples, 0.95)
        mx = max(samples) if samples else 0.0
        print(f"{obj:<28} {ok_n:>4} {recs:>5} {p50:>8.1f} {p95:>8.1f} {mx:>8.1f}")
    print("-" * 70)
    print(
        f"OVERALL p50={pctl(overall, 0.50):.1f}ms  "
        f"p95={pctl(overall, 0.95):.1f}ms  "
        f"mean={statistics.mean(overall):.1f}ms  n={len(overall)}"
    )


if __name__ == "__main__":
    main()
