#!/usr/bin/env python3
"""Render every fixture in tests/data and snapshot the result.

This is the regression gate for the 24 example projects that SHOWCASE.md is
generated from: it records what each one schedules to, so a change that moves
a date has to say so out loud.

    python fixture_snapshot.py write  <dir>   # record a baseline
    python fixture_snapshot.py check  <dir>   # compare against one

Each fixture is rendered through the library the way a caller would: parse,
schedule, then emit id/start/end for every task in declaration order. Failures
are recorded too, so "this fixture stopped scheduling" is a visible diff rather
than a missing file.
"""

from __future__ import annotations

import contextlib
import difflib
import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.normpath(os.path.join(HERE, "..", "..", "tests", "data"))


def render(path: str) -> str:
    """Render one fixture to a stable text form."""
    from scriptplan.parser.tjp_parser import ProjectFileParser
    from scriptplan.utils.message_handler import get_message_handler_instance

    handler = get_message_handler_instance()
    handler.clear()
    lines: list[str] = []
    noise = io.StringIO()
    try:
        with open(path) as handle:
            text = handle.read()
        with contextlib.redirect_stderr(noise), contextlib.redirect_stdout(noise):
            project = ParsedProject(ProjectFileParser().parse(text))
    except Exception as exc:
        first = traceback.format_exception_only(type(exc), exc)[-1].strip()
        return f"! {type(exc).__name__}: {first[:200]}\n"

    # Times are recorded as a reader sees them, in the project's own timezone,
    # not in the UTC the scheduler works in. The snapshot is a record of
    # customer-visible behaviour, so it should not move when the internal
    # representation does.
    lines.append(
        f"project timezone={project.timezone} start={project.start} end={project.end}"
    )
    for task_id, start, end, scheduled in project.rows():
        lines.append(f"{task_id}\t{start}\t{end}\t{scheduled}")
    for message in sorted({_plain(str(m)) for m in handler.messages}):
        lines.append(f"# {message}")
    return "\n".join(lines) + "\n"


def _plain(text: str) -> str:
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


class ParsedProject:
    """A project, read in the timezone its file was written in."""

    def __init__(self, project) -> None:
        self._project = project
        try:
            from scriptplan.core.timezones import from_utc

            self._local = lambda moment: from_utc(moment, project["timezone"])
        except ImportError:
            self._local = lambda moment: moment

    @property
    def timezone(self):
        return self._project["timezone"]

    @property
    def start(self):
        return self._local(self._project["start"])

    @property
    def end(self):
        return self._local(self._project["end"])

    def rows(self):
        for task in self._project.tasks:
            yield (
                task.fullId,
                self._local(task.get("start", 0)),
                self._local(task.get("end", 0)),
                bool(task.get("scheduled", 0)),
            )


def fixtures() -> list[str]:
    return sorted(f for f in os.listdir(FIXTURES) if f.endswith(".tjp"))


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"write", "check"}:
        print(__doc__)
        return 2
    mode, directory = argv[1], argv[2]
    os.makedirs(directory, exist_ok=True)

    failures = 0
    for name in fixtures():
        rendered = render(os.path.join(FIXTURES, name))
        target = os.path.join(directory, name + ".txt")
        if mode == "write":
            with open(target, "w") as handle:
                handle.write(rendered)
            print(f"wrote {name}")
            continue
        if not os.path.exists(target):
            print(f"MISSING baseline for {name}")
            failures += 1
            continue
        with open(target) as handle:
            expected = handle.read()
        if expected == rendered:
            print(f"same  {name}")
        else:
            failures += 1
            print(f"DIFF  {name}")
            diff = difflib.unified_diff(
                expected.splitlines(), rendered.splitlines(),
                fromfile=f"baseline/{name}", tofile=f"current/{name}", lineterm="", n=1,
            )
            for line in list(diff)[:40]:
                print("    " + line)
    print(f"\n{len(fixtures())} fixtures, {failures} differing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
