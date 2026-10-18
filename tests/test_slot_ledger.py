"""The slot ledger: where bookings sit inside one slot, and handing time back.

The schedules these mechanics produce are checked end to end, through the CLI,
by audit/evaluations/probe_slot_sharing.py. These tests pin the pieces that a
schedule can only show indirectly: the finishing moment of parallel work, and
that time is never handed back while another booking still sits on it.
"""

from __future__ import annotations

import pytest

from scriptplan.core.slot_ledger import SlotBooking, finish_offset
from scriptplan.parser.tjp_parser import ProjectFileParser

PLAN = """project p "p" 2026-10-19 +1w {
  timingresolution 60min
}
resource r0 "Desk" { workinghours mon - fri 9:00 - 17:00 limits { dailymax 2h } }
task a "A" { start 2026-10-19-09:00 }
task b "B" { start 2026-10-19-09:00 }
"""

# 2026-10-19 09:00, counted in hours from the project start.
NINE = 9


def booking(offset: float, seconds: float, efficiency: float = 1.0) -> SlotBooking:
    return SlotBooking(None, 0, None, True, offset, seconds, efficiency, None)


@pytest.fixture
def desk():
    """An empty desk and two tasks to book on it, outside any scheduling run."""
    project = ProjectFileParser().parse(PLAN)
    tasks = {t.id: t for t in project.tasks}
    rs = next(r for r in project.resources if r.id == "r0").data[0]
    return rs, tasks["a"], tasks["b"]


class TestFinishOffset:
    def test_one_booking_finishes_when_its_work_is_done(self):
        assert finish_offset([booking(0, 3600)], 0.5) == pytest.approx(1800)

    def test_a_booking_that_starts_late_finishes_late(self):
        assert finish_offset([booking(2400, 1200)], 13 / 60) == pytest.approx(2400 + 780)

    def test_a_second_resource_that_is_not_needed_contributes_nothing(self):
        # a works from 0, b only from 40 minutes; half an hour is done by a alone.
        assert finish_offset([booking(0, 3600), booking(2400, 1200)], 0.5) == pytest.approx(1800)

    def test_two_resources_share_the_rest_once_both_are_working(self):
        # 40 minutes by a alone, then 20 minutes of work at two people's rate.
        assert finish_offset([booking(0, 3600), booking(2400, 1200)], 1.0) == pytest.approx(3000)

    def test_efficiency_scales_the_rate(self):
        assert finish_offset([booking(0, 3600, efficiency=0.5)], 0.25) == pytest.approx(1800)

    def test_more_work_than_booked_takes_all_of_it(self):
        assert finish_offset([booking(0, 600)], 1.0) == pytest.approx(600)

    def test_nothing_needed_finishes_where_the_work_would_begin(self):
        assert finish_offset([booking(300, 600)], 0.0) == pytest.approx(300)


class TestReserveAndRelease:
    def test_forward_and_backward_work_take_opposite_ends(self, desk):
        rs, a, b = desk
        [front] = rs.reserve(NINE, a, forward=True)
        rs.release(front, 600)
        [back] = rs.reserve(NINE, b, forward=False)
        assert (front.offset, front.seconds) == (0, 600)
        assert (back.offset, back.seconds) == (0, 3000)
        assert rs.getAvailableSecondsInSlot(NINE) == 0
        assert sum(s for _, s in rs.slotTaskUsage[NINE]) == 3600

    def test_the_next_booking_starts_where_the_last_one_stopped(self, desk):
        rs, a, b = desk
        [first] = rs.reserve(NINE, a)
        rs.release(first, 2400)
        [second] = rs.reserve(NINE, b)
        assert (second.offset, second.seconds) == (2400, 1200)
        assert rs.slotSecondsUsed[NINE] == 3600

    def test_releasing_a_booking_never_touches_its_neighbour(self, desk):
        rs, a, b = desk
        [first] = rs.reserve(NINE, a)
        rs.release(first, 2400)
        rs.reserve(NINE, b)
        rs.release(first, 600)
        # a keeps 0-600; b still holds 2400-3600; 600-2400 is free again.
        spans = [(s, e, t.id) for s, e, t in rs.slotIntervals[NINE]]
        assert spans == [(0, 600, "a"), (2400, 3600, "b")]
        assert sorted((t.id, s) for t, s in rs.slotTaskUsage[NINE]) == [("a", 600), ("b", 1200)]
        assert rs.slotSecondsUsed[NINE] == 1800

    def test_a_booking_released_entirely_leaves_no_trace(self, desk):
        rs, a, _ = desk
        before = rs.scoreboard[NINE]
        [whole] = rs.reserve(NINE, a)
        rs.release(whole, 0)
        assert rs.scoreboard[NINE] == before
        assert NINE not in rs.slotTaskUsage
        assert NINE not in rs.slotIntervals
        assert a not in (rs.property.get("duties", 0) or [])
        assert rs.bookedEffort() == pytest.approx(0.0)

    def test_released_time_goes_back_to_the_daily_limit(self, desk):
        rs, a, _ = desk
        limits = rs.property.get("limits", 0)
        [first] = rs.reserve(NINE, a)
        assert limits.remaining(NINE, rs.property.id) == pytest.approx(3600)
        rs.release(first, 600)
        assert limits.remaining(NINE, rs.property.id) == pytest.approx(6600)
        assert rs.bookedEffort() == pytest.approx(600 / 3600)

    def test_time_skipped_for_a_mid_slot_start_stays_free(self, desk):
        rs, a, b = desk
        [late] = rs.reserve(NINE, a, not_before=3000)
        assert (late.offset, late.seconds) == (3000, 600)
        # The 50 minutes before it are free for anyone else (issuedb #17).
        [early] = rs.reserve(NINE, b)
        assert (early.offset, early.seconds) == (0, 3000)

    def test_backward_work_skips_the_end_of_the_slot_and_leaves_it_free(self, desk):
        rs, a, b = desk
        [before_end] = rs.reserve(NINE, a, forward=False, not_before=1800)
        assert (before_end.offset, before_end.seconds) == (1800, 1800)
        assert [(s, e) for s, e, _ in rs.slotIntervals[NINE]] == [(0, 1800)]
        [after] = rs.reserve(NINE, b, forward=True, not_before=1800)
        assert (after.offset, after.seconds) == (1800, 1800)

    def test_free_time_on_both_sides_is_booked_as_two_stretches(self, desk):
        rs, a, b = desk
        [middle] = rs.reserve(NINE, a, not_before=1200)
        rs.release(middle, 1200)  # a holds 1200-2400
        stretches = rs.reserve(NINE, b)
        assert [(x.offset, x.seconds) for x in stretches] == [(0, 1200), (2400, 1200)]
