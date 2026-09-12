#!/usr/bin/env python3
"""Falsifies: "a project ScriptPlan cannot schedule is reported as a failure".

Claims under test (SPECS/002-ws0-honesty-and-safety-fail-closed.md):
  - If any task cannot be scheduled, Project.schedule() returns False and
    records an error naming the task and the reason.
  - A dependency cycle is an error, raised before scheduling starts.
  - Library code never calls sys.exit().
  - `plan report` exits non-zero when scheduling failed.
  - report_id is a hash of the rendered result, not of the input file.
"""

from __future__ import annotations

import json
import subprocess
import sys

from harness import HDR, main, parse, probe, run_cli, window, write_tjp

CYCLE = (
    HDR
    + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { depends !b effort 8h allocate r }
task b "B" { depends !a effort 8h allocate r }
"""
)

NO_ALLOCATION = (
    HDR
    + """
task a "A" { start 2025-01-06 effort 8h }
task b "B" { depends !a effort 1h }
"""
)

OUTSIDE_WINDOW = (
    HDR
    + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-06-01 effort 2d allocate r }
"""
)


@probe("A dependency cycle is rejected with an error naming the cycle")
def probe_cycle_is_an_error() -> tuple[bool, str]:
    from scriptplan.core.exceptions import CircularDependencyError

    try:
        parse(CYCLE)
    except CircularDependencyError as exc:
        return True, f"raised CircularDependencyError: {exc}"
    except Exception as exc:
        return False, f"raised {type(exc).__name__} instead of CircularDependencyError: {exc}"
    return False, "parse() and schedule() returned normally on a two-task dependency cycle"


@probe("Project.schedule() returns False when a task cannot be scheduled")
def probe_schedule_returns_false_on_unallocated_effort() -> tuple[bool, str]:
    project = parse(NO_ALLOCATION, schedule=False)
    result = project.schedule()
    a, b = window(project, "a"), window(project, "b")
    return result is False, f"schedule() returned {result!r}; a={a} b={b} (effort task with no allocation)"


@probe("Project.schedule() returns False when a task falls outside the project window")
def probe_schedule_returns_false_outside_window() -> tuple[bool, str]:
    project = parse(OUTSIDE_WINDOW, schedule=False)
    result = project.schedule()
    return result is False, f"schedule() returned {result!r}; a={window(project, 'a')}"


@probe("Scheduling failure records an error that names the failing task")
def probe_failure_names_the_task() -> tuple[bool, str]:
    from scriptplan.utils.message_handler import get_message_handler_instance

    handler = get_message_handler_instance()
    handler.clear()
    project = parse(NO_ALLOCATION, schedule=False)
    project.schedule()
    texts = [str(m) for m in handler.messages]
    named = any(getattr(m, "task_id", None) == "a" or ".a" in str(m) or "'a'" in str(m) for m in handler.messages)
    return named, f"messages={texts}"


@probe("Library code never calls sys.exit()")
def probe_library_never_exits() -> tuple[bool, str]:
    code = (
        "from scriptplan.utils.message_handler import get_message_handler_instance\n"
        "h = get_message_handler_instance()\n"
        "try:\n"
        "    h.error('probe', 'boom')\n"
        "    print('RETURNED')\n"
        "except SystemExit as exc:\n"
        "    print('SYSTEMEXIT', exc.code)\n"
        "except Exception as exc:\n"
        "    print('RAISED', type(exc).__name__)\n"
    )
    import os

    import scriptplan

    env = dict(os.environ)
    env["PYTHONPATH"] = (
        os.path.dirname(os.path.dirname(os.path.abspath(scriptplan.__file__)))
        + os.pathsep
        + env.get("PYTHONPATH", "")
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)
    out = done.stdout.strip()
    return "SYSTEMEXIT" not in out, f"error() produced: {out!r}"


@probe("`plan report` exits non-zero on a project it cannot schedule")
def probe_cli_exits_non_zero_on_cycle() -> tuple[bool, str]:
    path = write_tjp(CYCLE + '\ntaskreport t "t" { formats csv columns id, start, end }\n')
    done = run_cli(["report", path])
    return done.returncode != 0, (
        f"exit={done.returncode}\nstdout={done.stdout[:300]!r}\nstderr={done.stderr[-300:]!r}"
    )


@probe("`plan report` explains the failure on stderr")
def probe_cli_explains_failure() -> tuple[bool, str]:
    path = write_tjp(CYCLE + '\ntaskreport t "t" { formats csv columns id, start, end }\n')
    done = run_cli(["report", path])
    text = (done.stderr or "").lower()
    explained = any(word in text for word in ("circular", "cycle", "depend"))
    return explained, f"stderr={done.stderr[-400:]!r}"


@probe("report_id is a hash of the rendered result, not of the input file")
def probe_report_id_covers_the_result() -> tuple[bool, str]:
    import hashlib

    good = (
        HDR
        + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-01-06 effort 8h allocate r }
"""
    )
    path = write_tjp(good)
    done = run_cli(["report", path])
    if done.returncode != 0:
        return False, f"CLI failed: exit={done.returncode} stderr={done.stderr[-200:]!r}"
    payload = json.loads(done.stdout)
    with open(path, "rb") as handle:
        input_hash = hashlib.sha256(handle.read()).hexdigest()
    reported = payload.get("report_id")
    body = {k: v for k, v in payload.items() if k != "report_id"}
    expected = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    ok = reported == expected and reported != input_hash
    return ok, (
        f"report_id={reported}\n  sha256(result)={expected}\n  sha256(input file)={input_hash}"
    )


@probe("`plan report` renders the report the input file defines")
def probe_cli_honours_declared_report() -> tuple[bool, str]:
    text = (
        HDR
        + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-01-06 effort 8h allocate r }
taskreport mine "mine" { formats json columns id, name, start, end }
"""
    )
    path = write_tjp(text)
    done = run_cli(["report", path])
    if done.returncode != 0:
        return False, f"CLI failed: exit={done.returncode} stderr={done.stderr[-200:]!r}"
    columns = json.loads(done.stdout).get("columns", [])
    return columns == ["id", "name", "start", "end"], f"served columns={columns} (file asked for id, name, start, end)"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
