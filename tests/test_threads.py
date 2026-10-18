"""Projects scheduled in parallel threads do not see each other's errors.

The message handler is one object per process. Before issuedb #28 its error
count, its message list and the flag that says whether errors are collected
were shared too, so one thread leaving ``collecting()`` made another thread's
error raise out of ``Project.schedule()``.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from scriptplan.parser.tjp_parser import ProjectFileParser
from scriptplan.utils.message_handler import TjRuntimeError, get_message_handler_instance

SHOWCASE = Path(__file__).resolve().parent.parent / "examples" / "showcase"

FAILING = """project d "D" 2026-11-02 +6m { timingresolution 30min }
resource r1 "R" { workinghours mon - fri 8:30 - 17:30 }
task a "A" { effort 4h allocate r1 }
task late "Late" { effort 2h allocate r1 depends !a maxend 2026-11-02-10:00 }
"""


def _run(text: str) -> tuple[bool, tuple, tuple]:
    handler = get_message_handler_instance()
    handler.clear()
    project = ProjectFileParser().parse(text, schedule=False)
    ok = project.schedule()
    dates = tuple(sorted((t.fullId, str(t.get("start", 0)), str(t.get("end", 0))) for t in project.tasks))
    return ok, dates, tuple(str(m) for m in handler.messages)


def _in_thread(target) -> threading.Thread:
    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread


def test_leaving_collecting_in_one_thread_does_not_stop_another_collecting() -> None:
    handler = get_message_handler_instance()
    first_inside, second_inside, first_left = threading.Event(), threading.Event(), threading.Event()
    outcome: dict[str, object] = {}

    def first() -> None:
        with handler.collecting():
            first_inside.set()
            second_inside.wait(10)
        first_left.set()

    def second() -> None:
        first_inside.wait(10)
        handler.clear()
        with handler.collecting():
            second_inside.set()
            first_left.wait(10)
            try:
                handler.error("probe", "second thread's error")
                outcome["raised"] = False
            except TjRuntimeError:
                outcome["raised"] = True
        outcome["errors"] = handler.errors

    threads = [_in_thread(first), _in_thread(second)]
    for thread in threads:
        thread.join(20)
    assert outcome == {"raised": False, "errors": 1}


def test_an_error_in_another_thread_does_not_reach_this_one() -> None:
    handler = get_message_handler_instance()
    handler.clear()
    before = (handler.errors, len(handler.messages))

    def other() -> None:
        with handler.collecting():
            handler.error("probe", "other thread's error")

    _in_thread(other).join(20)
    assert (handler.errors, len(handler.messages)) == before
    with pytest.raises(TjRuntimeError):
        handler.error("probe", "this thread does not collect")


def test_parallel_schedules_match_the_same_schedules_run_alone() -> None:
    texts = [(SHOWCASE / name).read_text() for name in ("simple.tjp", "alap_backward.tjp", "thermal.tjp", "quota.tjp")]
    texts.append(FAILING)
    alone = [_run(text) for text in texts]
    assert [ok for ok, _, _ in alone] == [True, True, True, True, False]
    assert any("no later than 2026-11-02 10:00:00" in m for m in alone[-1][2])

    results: dict[tuple[int, int], object] = {}

    def worker(index: int, copy: int) -> None:
        try:
            results[(index, copy)] = _run(texts[index])
        except Exception as exc:  # what a caller of schedule() would see
            results[(index, copy)] = repr(exc)

    threads = [_in_thread(lambda i=i, k=k: worker(i, k)) for k in range(3) for i in range(len(texts))]
    for thread in threads:
        thread.join(300)
    mismatched = sorted(key for key, got in results.items() if got != alone[key[0]])
    assert len(results) == 3 * len(texts)
    assert mismatched == []
