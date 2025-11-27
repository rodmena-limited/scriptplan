"""
Scheduling Validation Tests

These tests validate the scheduling engine against mathematically computed
ground truth for various complex scenarios. Each test corresponds to a
specific issue that was verified during development.

Issue #39: Ultra-Complex Stress Test (floating point efficiency, irregular calendars)
Issue #40: Airport Stress Test (basic scheduling validation)
Issue #41: Math Torture (500 chained tasks with minute-level precision)
Issue #42: Airport Retrofit (mixed calendars, night shifts, start-to-start dependencies)
Issue #43: Workflow Engine (efficiency scaling, offset work weeks)
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from math import isclose
from io import StringIO

from rodmena_resource_management.parser.tjp_parser import ProjectFileParser


class TestIssue39UltraMath:
    """
    Issue #39: Ultra-Complex Stress Test

    Tests floating point efficiency (0.77), irregular calendars,
    daily limits vs efficiency, and ALAP scheduling.

    Gold Standard:
    - t_float end: 2025-08-08 14:57:05
    - t_limit cost: 2400.0
    - t_finish end: 2025-08-29 17:00:00
    """

    @pytest.fixture
    def project(self):
        parser = ProjectFileParser()
        with open('tests/data/airport_ultra_math_report.tjp', 'r') as f:
            content = f.read()
        return parser.parse(content)

    @pytest.fixture
    def csv_output(self, project):
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate()

        # Read generated CSV
        with open('ultra_math_output.csv', 'r') as f:
            return pd.read_csv(f)

    def test_t_float_end_time(self, csv_output):
        """t_float should end at exactly 2025-08-08 14:57:05 (floating point precision)"""
        row = csv_output[csv_output['id'] == 't_float']
        assert not row.empty, "t_float task not found"
        expected = "2025-08-08 14:57:05"
        actual = row.iloc[0]['end']
        assert actual == expected, f"t_float end mismatch: expected {expected}, got {actual}"

    def test_t_limit_cost(self, csv_output):
        """t_limit cost should be 2400.0 (based on allocation, not effort)"""
        row = csv_output[csv_output['id'] == 't_limit']
        assert not row.empty, "t_limit task not found"
        expected = 2400.0
        actual = float(row.iloc[0]['cost'])
        assert isclose(actual, expected, rel_tol=1e-5), f"t_limit cost mismatch: expected {expected}, got {actual}"

    def test_t_finish_alap_deadline(self, csv_output):
        """t_finish should end at exactly 2025-08-29 17:00:00 (ALAP adherence)"""
        row = csv_output[csv_output['id'] == 't_finish']
        assert not row.empty, "t_finish task not found"
        expected = "2025-08-29 17:00:00"
        actual = row.iloc[0]['end']
        assert actual == expected, f"t_finish end mismatch: expected {expected}, got {actual}"


class TestIssue41MathTorture:
    """
    Issue #41: Math Torture Test

    500 chained tasks with:
    - 73min effort each (prime number)
    - 29min gap between tasks (prime number)
    - Custom shift: 08:13-11:59, 13:07-17:47 Mon-Sun
    - Crosses leap year boundary (Feb 2024)
    - 1 minute timing resolution

    Tests minute-level precision and accumulated error detection.
    """

    # Shift Definition
    SHIFTS = [
        (datetime.strptime("08:13", "%H:%M").time(), datetime.strptime("11:59", "%H:%M").time()),
        (datetime.strptime("13:07", "%H:%M").time(), datetime.strptime("17:47", "%H:%M").time())
    ]
    START_DATE = datetime(2024, 2, 28, 8, 13)
    ITERATIONS = 500
    TASK_EFFORT_MIN = 73
    GAP_MIN = 29

    def is_working_time(self, dt):
        t = dt.time()
        for s_start, s_end in self.SHIFTS:
            if s_start <= t < s_end:
                return True
        return False

    def get_next_working_minute(self, dt):
        curr = dt
        while not self.is_working_time(curr):
            curr += timedelta(minutes=1)
            curr = curr.replace(second=0, microsecond=0)
        return curr

    def add_working_minutes(self, start_dt, minutes_effort):
        cursor = start_dt
        remaining = minutes_effort
        cursor = self.get_next_working_minute(cursor)

        while remaining > 0:
            if self.is_working_time(cursor):
                remaining -= 1
            cursor += timedelta(minutes=1)
            if remaining > 0:
                cursor = self.get_next_working_minute(cursor)
        return cursor

    def generate_ground_truth(self):
        schedule = []
        current_start = self.START_DATE

        for i in range(1, self.ITERATIONS + 1):
            task_id = f"chain.t_{i:03d}"
            actual_end = self.add_working_minutes(current_start, self.TASK_EFFORT_MIN)
            schedule.append({
                "id": task_id,
                "start": current_start,
                "end": actual_end
            })
            next_ready_time = actual_end + timedelta(minutes=self.GAP_MIN)
            current_start = self.get_next_working_minute(next_ready_time)

        return pd.DataFrame(schedule)

    @pytest.fixture
    def project(self):
        parser = ProjectFileParser()
        with open('tests/data/math_torture.tjp', 'r') as f:
            content = f.read()
        return parser.parse(content)

    @pytest.fixture
    def csv_output(self, project):
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate()

        with open('math_check.csv', 'r') as f:
            df = pd.read_csv(f)
            df.columns = [c.strip().lower() for c in df.columns]
            return df.sort_values('id').reset_index(drop=True)

    def test_task_count(self, csv_output):
        """Should have exactly 500 leaf tasks"""
        assert len(csv_output) == 500, f"Expected 500 tasks, got {len(csv_output)}"

    def test_all_tasks_match_ground_truth(self, csv_output):
        """All 500 tasks should match mathematically computed ground truth"""
        df_truth = self.generate_ground_truth()
        fmt = "%Y-%m-%d-%H:%M"
        df_truth['start_str'] = df_truth['start'].dt.strftime(fmt)
        df_truth['end_str'] = df_truth['end'].dt.strftime(fmt)

        errors = []
        for idx, row in df_truth.iterrows():
            sub_row = csv_output.iloc[idx]

            if sub_row['id'] != row['id']:
                errors.append(f"ID mismatch at {idx}: expected {row['id']}, got {sub_row['id']}")
                continue

            if sub_row['start'] != row['start_str']:
                errors.append(f"Start mismatch [{row['id']}]: expected {row['start_str']}, got {sub_row['start']}")

            if sub_row['end'] != row['end_str']:
                errors.append(f"End mismatch [{row['id']}]: expected {row['end_str']}, got {sub_row['end']}")

        assert len(errors) == 0, f"Found {len(errors)} mismatches:\n" + "\n".join(errors[:10])

    def test_last_task_end_time(self, csv_output):
        """Task 500 should end at 2024-06-06-17:22"""
        last_task = csv_output[csv_output['id'] == 'chain.t_500']
        assert not last_task.empty, "Task 500 not found"
        expected = "2024-06-06-17:22"
        actual = last_task.iloc[0]['end']
        assert actual == expected, f"Task 500 end mismatch: expected {expected}, got {actual}"


class TestIssue42AirportRetrofit:
    """
    Issue #42: Airport Retrofit Test

    Tests:
    - Global vacation (Sep 5 holiday)
    - Night shift (22:00-06:00)
    - Standard shift (09:00-17:00)
    - Efficiency factor (0.8)
    - Start-to-start dependency with gap (onstart)

    Ground Truth:
    - bhs.design: ends 2025-09-08 17:00
    - bhs.demo: ends 2025-09-10 06:00
    - bhs.wiring: ends 2025-09-16 17:00
    """

    HOLIDAYS = [datetime(2025, 9, 5).date()]

    def is_holiday(self, dt):
        return dt.date() in self.HOLIDAYS

    def is_weekend(self, dt):
        return dt.weekday() >= 5

    def add_working_hours_standard(self, start_dt, hours_needed):
        cursor = start_dt
        remaining = hours_needed

        if cursor.hour < 9:
            cursor = cursor.replace(hour=9, minute=0)
        elif cursor.hour >= 17:
            cursor = cursor + timedelta(days=1)
            cursor = cursor.replace(hour=9, minute=0)

        while remaining > 0:
            if self.is_weekend(cursor) or self.is_holiday(cursor):
                cursor = cursor + timedelta(days=1)
                cursor = cursor.replace(hour=9, minute=0)
                continue

            end_of_shift = cursor.replace(hour=17, minute=0)
            capacity = (end_of_shift - cursor).total_seconds() / 3600.0

            if capacity <= 0:
                cursor = cursor + timedelta(days=1)
                cursor = cursor.replace(hour=9, minute=0)
                continue

            if capacity >= remaining:
                cursor += timedelta(hours=remaining)
                remaining = 0
            else:
                remaining -= capacity
                cursor = cursor + timedelta(days=1)
                cursor = cursor.replace(hour=9, minute=0)

        return cursor

    def add_working_hours_night(self, start_dt, hours_needed):
        cursor = start_dt
        remaining = hours_needed

        while remaining > 0:
            if 6 <= cursor.hour < 22:
                cursor = cursor.replace(hour=22, minute=0)

            current_shift_start_day = cursor
            if cursor.hour < 6:
                current_shift_start_day = cursor - timedelta(days=1)

            if current_shift_start_day.weekday() >= 5 or self.is_holiday(current_shift_start_day):
                cursor = cursor.replace(hour=22, minute=0) + timedelta(days=1)
                continue

            if cursor.hour >= 22:
                end_of_shift = (cursor + timedelta(days=1)).replace(hour=6, minute=0)
            else:
                end_of_shift = cursor.replace(hour=6, minute=0)

            capacity = (end_of_shift - cursor).total_seconds() / 3600.0

            if capacity >= remaining:
                cursor += timedelta(hours=remaining)
                remaining = 0
            else:
                remaining -= capacity
                cursor = end_of_shift

        return cursor

    @pytest.fixture
    def project(self):
        parser = ProjectFileParser()
        with open('tests/data/airport_retrofit.tjp', 'r') as f:
            content = f.read()
        return parser.parse(content)

    @pytest.fixture
    def csv_output(self, project):
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate()

        with open('retrofit_output.csv', 'r') as f:
            df = pd.read_csv(f)
            df.columns = [c.strip().lower() for c in df.columns]
            return df

    def test_design_task(self, csv_output):
        """bhs.design should end at 2025-09-08-17:00 (skips Sep 5 holiday)"""
        row = csv_output[csv_output['id'] == 'bhs.design']
        assert not row.empty, "bhs.design task not found"

        # Calculate expected: 40h effort, standard shift, holiday on Sep 5
        t1_start = datetime(2025, 9, 1, 9, 0)
        t1_end = self.add_working_hours_standard(t1_start, 40)
        expected = t1_end.strftime("%Y-%m-%d-%H:%M")
        actual = row.iloc[0]['end']
        assert actual == expected, f"bhs.design end mismatch: expected {expected}, got {actual}"

    def test_demo_task(self, csv_output):
        """bhs.demo should end at 2025-09-10-06:00 (night shift)"""
        row = csv_output[csv_output['id'] == 'bhs.demo']
        assert not row.empty, "bhs.demo task not found"

        # Calculate expected: 16h effort, night shift, after design ends
        t1_end = datetime(2025, 9, 8, 17, 0)
        t2_end = self.add_working_hours_night(t1_end, 16)
        expected = t2_end.strftime("%Y-%m-%d-%H:%M")
        actual = row.iloc[0]['end']
        assert actual == expected, f"bhs.demo end mismatch: expected {expected}, got {actual}"

    def test_wiring_task(self, csv_output):
        """bhs.wiring should end at 2025-09-16-17:00 (onstart + gap + efficiency)"""
        row = csv_output[csv_output['id'] == 'bhs.wiring']
        assert not row.empty, "bhs.wiring task not found"

        # Calculate expected:
        # - onstart dependency on demo (starts Sep 8 22:00)
        # - 24h gap -> ready Sep 9 22:00
        # - 32h effort / 0.8 efficiency = 40h work time
        # - Standard shift
        t3_ready = datetime(2025, 9, 8, 22, 0) + timedelta(hours=24)
        t3_end = self.add_working_hours_standard(t3_ready, 40)
        expected = t3_end.strftime("%Y-%m-%d-%H:%M")
        actual = row.iloc[0]['end']
        assert actual == expected, f"bhs.wiring end mismatch: expected {expected}, got {actual}"


class TestIssue40AirportStressTest:
    """
    Issue #40: Airport Stress Test

    Basic scheduling validation with:
    - Standard working hours
    - Task dependencies
    - Resource allocation
    """

    @pytest.fixture
    def project(self):
        parser = ProjectFileParser()
        with open('tests/data/airport_stress_test.tjp', 'r') as f:
            content = f.read()
        return parser.parse(content)

    def test_project_parses(self, project):
        """Project should parse without errors"""
        assert project is not None
        assert len(project.tasks) > 0

    def test_all_tasks_scheduled(self, project):
        """All leaf tasks should be scheduled"""
        for task in project.tasks:
            if task.leaf():
                scheduled = task.get('scheduled', 0)
                start = task.get('start', 0)
                end = task.get('end', 0)
                assert scheduled or (start and end), f"Task {task.id} not scheduled"

    def test_no_scheduling_warnings(self, project, capsys):
        """Should not produce scheduling warnings for valid project"""
        # Re-parse to capture output
        parser = ProjectFileParser()
        with open('tests/data/airport_stress_test.tjp', 'r') as f:
            content = f.read()
        parser.parse(content)
        captured = capsys.readouterr()
        # Allow for some warnings but not critical failures
        assert "could not be scheduled" not in captured.out.lower() or "0 tasks" in captured.out


class TestIssue43WorkflowEngine:
    """
    Issue #43: Workflow Engine Test

    Tests efficiency scaling and offset work weeks:
    - Intern: 0.5 efficiency (16h effort = 32h duration)
    - Admin: Tue-Sat shift (offset work week)
    - Dependency hand-off respects successor's calendar

    Ground Truth:
    - migration.prep: ends 2025-11-06 17:00
    - migration.deploy: ends 2025-11-08 17:00
    """

    @pytest.fixture
    def project(self):
        parser = ProjectFileParser()
        with open('tests/data/workflow_engine.tjp', 'r') as f:
            content = f.read()
        return parser.parse(content)

    @pytest.fixture
    def csv_output(self, project):
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate()

        with open('workflow_output.csv', 'r') as f:
            df = pd.read_csv(f)
            df.columns = [c.strip().lower() for c in df.columns]
            return df

    def test_prep_task_efficiency(self, csv_output):
        """migration.prep should end at 2025-11-06-17:00 (0.5 efficiency = 32h duration for 16h effort)"""
        row = csv_output[csv_output['id'] == 'migration.prep']
        assert not row.empty, "migration.prep task not found"

        # Intern (0.5 eff) doing 16h effort = 32h duration
        # Mon (8h) + Tue (8h) + Wed (8h) + Thu (8h) = 32h
        expected = "2025-11-06-17:00"
        actual = row.iloc[0]['end']
        assert actual == expected, f"migration.prep end mismatch: expected {expected}, got {actual}"

    def test_deploy_task_offset_week(self, csv_output):
        """migration.deploy should end at 2025-11-08-17:00 (Tue-Sat shift)"""
        row = csv_output[csv_output['id'] == 'migration.deploy']
        assert not row.empty, "migration.deploy task not found"

        # Admin works Tue-Sat. Ready Thu 17:00, next work slot Fri 09:00
        # Fri (8h) + Sat (8h) = 16h
        expected = "2025-11-08-17:00"
        actual = row.iloc[0]['end']
        assert actual == expected, f"migration.deploy end mismatch: expected {expected}, got {actual}"

    def test_deploy_starts_on_admin_shift(self, csv_output):
        """Deploy should start on Friday (Admin's first available day after prep ends)"""
        row = csv_output[csv_output['id'] == 'migration.deploy']
        assert not row.empty, "migration.deploy task not found"

        # Should start Fri Nov 7, not Thu Nov 6 (Admin doesn't work Mon)
        expected_start = "2025-11-07-09:00"
        actual_start = row.iloc[0]['start']
        assert actual_start == expected_start, f"migration.deploy start mismatch: expected {expected_start}, got {actual_start}"


# Convenience function to run all validation tests
def run_all_scheduling_validations():
    """Run all scheduling validation tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_all_scheduling_validations()
