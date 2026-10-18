"""Golden regression gate for the example projects in examples/showcase.

Every fixture is scheduled and its result compared against a recorded
snapshot. This is what stops a change from quietly moving a date in one of
the 24 example projects that SHOWCASE.md is generated from.

When a change is *meant* to move a date, regenerate the snapshot with

    python audit/evaluations/fixture_snapshot.py write tests/golden/fixtures

and say in the commit message which fixture moved and why. A snapshot updated
without that explanation is indistinguishable from a regression.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO_ROOT / "tests" / "golden" / "fixtures"
sys.path.insert(0, str(REPO_ROOT / "audit" / "evaluations"))

from fixture_snapshot import FIXTURES, render  # noqa: E402


def fixture_names() -> list[str]:
    return sorted(p.name for p in Path(FIXTURES).glob("*.tjp"))


@pytest.mark.parametrize("name", fixture_names())
def test_fixture_schedule_matches_golden(name: str) -> None:
    golden = GOLDEN_DIR / f"{name}.txt"
    assert golden.exists(), (
        f"No golden snapshot for {name}. Record one with:\n"
        f"  python audit/evaluations/fixture_snapshot.py write tests/golden/fixtures"
    )
    expected = golden.read_text()
    actual = render(str(Path(FIXTURES) / name))
    if expected != actual:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=f"golden/{name}",
                tofile=f"current/{name}",
                lineterm="",
                n=2,
            )
        )
        pytest.fail(f"{name} scheduled differently than the recorded golden:\n{diff}")


def test_every_fixture_has_a_golden() -> None:
    recorded = {p.name[: -len(".txt")] for p in GOLDEN_DIR.glob("*.tjp.txt")}
    present = set(fixture_names())
    assert recorded == present, (
        f"golden snapshots out of step with examples/showcase: "
        f"missing={sorted(present - recorded)} stale={sorted(recorded - present)}"
    )
