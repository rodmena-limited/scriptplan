#!/usr/bin/env python3
"""Falsifies: "ScriptPlan schedules realistic projects in reasonable time".

Claims under test (SPECS/005-ws3-scheduler-core-engine-package.md):
  - 500 chained tasks at 1h resolution schedule in <= 3s
  - 100 tasks / 10 resources / 1 year at 1min schedule in <= 10s, <= 200MB RSS

These take minutes rather than seconds, so run_all.sh only includes them when
SCRIPTPLAN_PROBE_SLOW=1 is set.  They are read-only and safe against any
target; the opt-in exists to keep the default run quick.
"""

from __future__ import annotations

import os
import resource as rusage
import time

from harness import main, parse, probe, window

BUDGET_CHAIN_SECONDS = float(os.environ.get("SCRIPTPLAN_BUDGET_CHAIN", "3"))
BUDGET_MINUTE_SECONDS = float(os.environ.get("SCRIPTPLAN_BUDGET_MINUTE", "10"))
BUDGET_MINUTE_RSS_MB = float(os.environ.get("SCRIPTPLAN_BUDGET_RSS_MB", "200"))


def _rss_mb() -> float:
    return rusage.getrusage(rusage.RUSAGE_SELF).ru_maxrss / 1024.0


@probe(f"500 chained tasks schedule at 1h resolution within {BUDGET_CHAIN_SECONDS:g}s")
def probe_long_chain_is_fast() -> tuple[bool, str]:
    tasks = "\n".join(
        'task t%d "T%d" { effort 4h allocate r %s }' % (i, i, ("depends !t%d" % (i - 1)) if i else "")
        for i in range(500)
    )
    started = time.time()
    project = parse("""project p "P" 2025-01-06 +3y { timezone "Etc/UTC" now 2025-01-06 }
resource r "R" { workinghours mon-fri 9:00-17:00 }
""" + tasks)
    elapsed = time.time() - started
    last = window(project, "t499")
    return elapsed <= BUDGET_CHAIN_SECONDS, (
        f"{elapsed:.1f}s for 500 chained tasks (budget {BUDGET_CHAIN_SECONDS:g}s); last task {last}"
    )


@probe(
    f"100 tasks over 10 resources for a year at 1min schedule within "
    f"{BUDGET_MINUTE_SECONDS:g}s and {BUDGET_MINUTE_RSS_MB:g}MB"
)
def probe_minute_resolution_year_is_bounded() -> tuple[bool, str]:
    resources = "\n".join('resource r%d "R%d" { workinghours mon-fri 9:00-17:00 }' % (i, i) for i in range(10))
    tasks = "\n".join(
        'task t%d "T%d" { effort 8h allocate r%d %s }'
        % (i, i, i % 10, ("depends !t%d" % (i - 10)) if i >= 10 else "")
        for i in range(100)
    )
    started = time.time()
    project = parse("""project p "P" 2025-01-06 +1y {
  timezone "Etc/UTC"
  now 2025-01-06
  timingresolution 1min
}
""" + resources + "\n" + tasks)
    elapsed = time.time() - started
    rss = _rss_mb()
    last = window(project, "t99")
    ok = elapsed <= BUDGET_MINUTE_SECONDS and rss <= BUDGET_MINUTE_RSS_MB
    return ok, (
        f"{elapsed:.1f}s (budget {BUDGET_MINUTE_SECONDS:g}s), peak RSS {rss:.0f}MB "
        f"(budget {BUDGET_MINUTE_RSS_MB:g}MB); last task {last}"
    )


if __name__ == "__main__":
    raise SystemExit(main(globals()))
