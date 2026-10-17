"""Shared harness for ScriptPlan audit probes.

Every probe drives ScriptPlan through its own public API or CLI, asserts the
behaviour the EARS spec in ``SPECS/`` requires, and prints PASS/FAIL together
with the evidence it observed -- never a bare exit code.

Target selection (parameterised, no hardcoded paths):

    SCRIPTPLAN_PROBE_PYTHON   interpreter used for CLI sub-process probes
                              (default: the interpreter running the probe)
    SCRIPTPLAN_PROBE_TIMEOUT  seconds allowed per CLI sub-process (default 300)

The package under test is whatever ``import scriptplan`` resolves to, so the
same probe file runs unchanged against a source checkout, an installed wheel,
or a virtualenv built from a release candidate.  Every probe prints the
resolved package path in the run header.
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable

# --------------------------------------------------------------------------
# target resolution
# --------------------------------------------------------------------------

PROBE_PYTHON = os.environ.get("SCRIPTPLAN_PROBE_PYTHON", sys.executable)
PROBE_TIMEOUT = int(os.environ.get("SCRIPTPLAN_PROBE_TIMEOUT", "300"))

RESULTS: list[tuple[str, str, str, list[str]]] = []


def target_info() -> str:
    """Describe the package actually under test."""
    import scriptplan

    return (
        f"scriptplan {getattr(scriptplan, '__version__', '?')} "
        f"at {os.path.dirname(scriptplan.__file__)}\n"
        f"python {sys.version.split()[0]}"
    )


# --------------------------------------------------------------------------
# probe declaration
# --------------------------------------------------------------------------


def probe(claim: str) -> Callable[[Callable[[], tuple[bool, str]]], Callable[[], None]]:
    """Declare a probe.

    The wrapped function returns ``(ok, evidence)``.  ``claim`` states, in the
    positive, the behaviour being falsified -- so a FAIL line reads as the
    claim that does not hold.
    """

    def deco(fn: Callable[[], tuple[bool, str]]) -> Callable[[], None]:
        def wrapper() -> None:
            messages: list[str] = []
            buf = io.StringIO()
            try:
                mh = _message_handler()
                if mh is not None:
                    mh.clear()
                with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(buf):
                    ok, evidence = fn()
                status = "PASS" if ok else "FAIL"
                if mh is not None:
                    messages = [_plain(str(m)) for m in mh.messages]
            except Exception as exc:
                status = "ERROR"
                evidence = f"{type(exc).__name__}: {exc}\n" + "".join(
                    traceback.format_exception_only(type(exc), exc)
                )
            RESULTS.append((claim, status, evidence, messages))

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = claim
        wrapper._is_probe = True  # type: ignore[attr-defined]
        return wrapper

    return deco


def _message_handler() -> Any:
    try:
        from scriptplan.utils.message_handler import get_message_handler_instance

        return get_message_handler_instance()
    except Exception:  # pragma: no cover - defensive
        return None


def _plain(text: str) -> str:
    """Strip ANSI colour so evidence stays readable in logs and CI."""
    out, i = [], 0
    while i < len(text):
        if text[i] == "\x1b":
            while i < len(text) and text[i] not in "mK":
                i += 1
            i += 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


# --------------------------------------------------------------------------
# model helpers
# --------------------------------------------------------------------------

HDR = """project p "P" 2025-01-06 +3m {
  timezone "Etc/UTC"
  now 2025-01-06
}
"""


def parse(tjp: str, schedule: bool = True) -> Any:
    from scriptplan.parser.tjp_parser import ProjectFileParser

    return ProjectFileParser().parse(tjp, schedule=schedule)


def task(project: Any, full_id: str) -> Any:
    for t in project.tasks:
        if t.fullId == full_id or t.id == full_id:
            return t
    raise KeyError(f"no task {full_id!r} (have {[t.fullId for t in project.tasks]})")


def resource(project: Any, rid: str) -> Any:
    for r in project.resources:
        if r.id == rid:
            return r
    raise KeyError(f"no resource {rid!r}")


def window(project: Any, task_id: str, scenario: int = 0) -> tuple[Any, Any]:
    """(start, end) of a task in one scenario."""
    t = task(project, task_id)
    return t.get("start", scenario), t.get("end", scenario)


def booked_slots(project: Any, rid: str, scenario: int = 0) -> list[tuple[int, datetime]]:
    """Slots this resource has booked to some task, as (index, slot start)."""
    board = _board(project, rid, scenario)
    if board is None:
        return []
    return [(i, project.idxToDate(i)) for i in board]


def booked_seconds(project: Any, rid: str, scenario: int = 0) -> dict[int, float]:
    """Seconds booked per slot, summed from what each task was booked for.

    Not slotSecondsUsed: that is the engine's own capacity counter, and the
    defect in issuedb #11 corrupted it in the same step that overbooked the
    slot, so every check that read it stayed green while three tasks ran at
    once on one person.
    """
    rs = resource(project, rid).data[scenario]
    usage = getattr(rs, "slotTaskUsage", {}) or {}
    return {idx: sum(seconds for _, seconds in rows) for idx, rows in usage.items()}


def booked_hours_by_day(project: Any, rid: str, scenario: int = 0) -> dict[Any, float]:
    """Hours booked per UTC calendar day, honouring partial-slot usage."""
    out: dict[Any, float] = defaultdict(float)
    for idx, seconds in booked_seconds(project, rid, scenario).items():
        out[project.idxToDate(idx).date()] += seconds / 3600.0
    return dict(out)


def booked_hours_by_local_day(project: Any, rid: str, tz_name: str, scenario: int = 0) -> dict[Any, float]:
    """Hours booked per calendar day in ``tz_name`` (for limit-period probes)."""
    from datetime import timezone as _tz

    try:
        from zoneinfo import ZoneInfo
    except ImportError:  # pragma: no cover - py<3.9
        raise RuntimeError("zoneinfo required for local-day probes") from None
    zone = ZoneInfo(tz_name)
    out: dict[Any, float] = defaultdict(float)
    for idx, seconds in booked_seconds(project, rid, scenario).items():
        slot = project.idxToDate(idx)
        if slot.tzinfo is None:
            slot = slot.replace(tzinfo=_tz.utc)
        out[slot.astimezone(zone).date()] += seconds / 3600.0
    return dict(out)


def _board(project: Any, rid: str, scenario: int) -> list[int] | None:
    """Indices this resource has booked, whichever backend holds them."""
    res = resource(project, rid)
    rs = res.data[scenario] if res.data else None
    if rs is None:
        return None
    board = getattr(rs, "board", None)
    if board is not None and hasattr(board, "booked_indices"):
        return list(board.booked_indices())
    sb = getattr(rs, "scoreboard", None)
    if sb is None:
        return []
    return [i for i, slot in enumerate(sb) if slot is not None and not isinstance(slot, int)]


def total_booked_hours(project: Any, rid: str, scenario: int = 0) -> float:
    return sum(booked_hours_by_day(project, rid, scenario).values())


# --------------------------------------------------------------------------
# CLI helpers
# --------------------------------------------------------------------------


def run_cli(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    """Run the `plan` CLI as the customer does: a fresh process."""
    env = dict(os.environ)
    import scriptplan

    pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(scriptplan.__file__)))
    env["PYTHONPATH"] = pkg_parent + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [PROBE_PYTHON, "-m", "scriptplan.cli.plan", *args],
        capture_output=True,
        text=True,
        input=stdin,
        env=env,
        timeout=PROBE_TIMEOUT,
    )


def write_tjp(text: str, name: str = "probe.tjp") -> str:
    import tempfile

    directory = tempfile.mkdtemp(prefix="scriptplan_probe_")
    path = os.path.join(directory, name)
    with open(path, "w") as handle:
        handle.write(text)
    return path


# --------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------


def main(module_globals: dict[str, Any]) -> int:
    """Run every probe declared in the calling module; return an exit code."""
    probes = [
        value
        for _, value in sorted(module_globals.items())
        if callable(value) and getattr(value, "_is_probe", False)
    ]
    print(f"# {os.path.basename(sys.argv[0])}")
    print(f"# {target_info()}")
    print(f"# {len(probes)} probe(s)\n")
    for fn in probes:
        fn()

    for claim, status, evidence, messages in RESULTS:
        print(f"[{status}] {claim}")
        for line in str(evidence).strip().splitlines():
            print(f"    {line}")
        if messages:
            print(f"    scheduler messages: {messages}")
    counts = {s: sum(1 for r in RESULTS if r[1] == s) for s in ("PASS", "FAIL", "ERROR")}
    print(f"\nSUMMARY {os.path.basename(sys.argv[0])}: {counts}")
    return 0 if counts["FAIL"] == 0 and counts["ERROR"] == 0 else 1


__all__ = [
    "HDR",
    "booked_hours_by_day",
    "booked_hours_by_local_day",
    "booked_seconds",
    "booked_slots",
    "datetime",
    "main",
    "parse",
    "probe",
    "resource",
    "run_cli",
    "task",
    "timedelta",
    "total_booked_hours",
    "window",
    "write_tjp",
]
