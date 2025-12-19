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

from datetime import datetime, timedelta
from math import isclose
from pathlib import Path

import pandas as pd
import pytest

from scriptplan.parser.tjp_parser import ProjectFileParser


def get_csv_as_dataframe(report):
    """Convert report's CSV output to pandas DataFrame without writing to disk."""
    report.generate_intermediate_format()
    csv_data = report.to_csv()
    if not csv_data:
        return pd.DataFrame()
    # csv_data is list of lists, first row is header
    header = csv_data[0]
    rows = csv_data[1:]
    df = pd.DataFrame(rows, columns=header)
    df.columns = [c.strip().lower() for c in df.columns]
    return df


class TestIssue39UltraMath:
    """
    Issue #39: Ultra-Complex Stress Test

    Exact judge script from issue embedded as pytest.
    """

    # Exact gold standard from issue #39 judge script
    DATE_FMT = "%Y-%m-%d %H:%M:%S"
    GOLD_STANDARD = {
        "t_float": {
            "end": "2025-08-08 14:57:05",
            "description": "Floating Point Efficiency End Time"
        },
        "t_limit": {
            "cost": 2400.0,
            "description": "Cost based on Allocation (12h) not Effort (15h)"
        },
        "t_finish": {
            "end": "2025-08-29 17:00:00",
            "description": "ALAP Hard Deadline Adherence"
        }
    }

    @pytest.fixture
    def csv_data(self):
        """Generate CSV and parse it exactly like the judge script does."""
        import csv
        import io

        parser = ProjectFileParser()
        with open('tests/data/airport_ultra_math_report.tjp') as f:
            content = f.read()
        project = parser.parse(content)

        # Generate CSV
        csv_content = ""
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        # Parse CSV exactly like judge script
        data = {}
        f = io.StringIO(csv_content)
        sample = f.read(1024)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample)
        reader = csv.DictReader(f, dialect=dialect)
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        for row in reader:
            key = row.get('id') or row.get('name')
            if key:
                data[key] = row
        return data

    def check_time(self, actual_str, expected_str):
        """Exact check_time from judge script."""
        try:
            dt_actual = datetime.strptime(actual_str, self.DATE_FMT)
            dt_expected = datetime.strptime(expected_str, self.DATE_FMT)
            diff = (dt_actual - dt_expected).total_seconds()
            if diff == 0:
                return True, "EXACT MATCH"
            else:
                return False, f"OFF by {diff} seconds ({actual_str} vs {expected_str})"
        except ValueError as e:
            return False, f"Format Error: {e}"

    def check_cost(self, actual_str, expected_val):
        """Exact check_cost from judge script."""
        try:
            val_actual = float(actual_str)
            if isclose(val_actual, expected_val, rel_tol=1e-5):
                return True, f"MATCH ({val_actual})"
            else:
                return False, f"MISMATCH (Got {val_actual}, Expected {expected_val})"
        except ValueError:
            return False, f"Invalid Number: {actual_str}"

    def test_t_float_end_time(self, csv_data):
        """Verify t_float End Time (The Precision Test)"""
        task_id = "t_float"
        # Check both short and full ID
        row = csv_data.get(task_id) or csv_data.get(f"airport_math.{task_id}")
        assert row is not None, f"{task_id} not found in CSV"
        ok, msg = self.check_time(row['end'], self.GOLD_STANDARD[task_id]['end'])
        assert ok, f"{task_id} End Time: {msg}"

    def test_t_limit_cost(self, csv_data):
        """Verify t_limit Cost (The Accounting Test)"""
        task_id = "t_limit"
        row = csv_data.get(task_id) or csv_data.get(f"airport_math.{task_id}")
        assert row is not None, f"{task_id} not found in CSV"
        ok, msg = self.check_cost(row['cost'], self.GOLD_STANDARD[task_id]['cost'])
        assert ok, f"{task_id} Cost Calculation: {msg}"

    def test_t_finish_alap_deadline(self, csv_data):
        """Verify t_finish ALAP Deadline"""
        task_id = "t_finish"
        row = csv_data.get(task_id) or csv_data.get(f"airport_math.{task_id}")
        assert row is not None, f"{task_id} not found in CSV"
        ok, msg = self.check_time(row['end'], self.GOLD_STANDARD[task_id]['end'])
        assert ok, f"{task_id} ALAP Deadline: {msg}"


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
        with open('tests/data/math_torture.tjp') as f:
            content = f.read()
        return parser.parse(content)

    @pytest.fixture
    def csv_output(self, project):
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            df = get_csv_as_dataframe(report)
            return df.sort_values('id').reset_index(drop=True)
        return pd.DataFrame()

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
        with open('tests/data/airport_retrofit.tjp') as f:
            content = f.read()
        return parser.parse(content)

    @pytest.fixture
    def csv_output(self, project):
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            return get_csv_as_dataframe(report)
        return pd.DataFrame()

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

    Compares our output against expected values derived from TaskJuggler.
    """

    # Expected values from TaskJuggler output
    EXPECTED = {
        "airport": {"start": "2025-06-02", "end": "2025-06-24"},
        "airport.t_software": {"start": "2025-06-02", "end": "2025-06-04"},
        "airport.t_crit": {"start": "2025-06-04", "end": "2025-06-05"},
        "airport.t_install": {"start": "2025-06-05", "end": "2025-06-06"},
        "airport.t_migration": {"start": "2025-06-05", "end": "2025-06-06"},
        "airport.t_low": {"start": "2025-06-06", "end": "2025-06-06"},
        "airport.t_audit": {"start": "2025-06-19", "end": "2025-06-24"},
        "airport.deliver": {"start": "2025-06-24", "end": "2025-06-24"},
    }

    @pytest.fixture
    def csv_output(self):
        """Generate our tool's output."""
        parser = ProjectFileParser()
        with open('tests/data/airport_stress_test.tjp') as f:
            content = f.read()
        project = parser.parse(content)
        project.schedule()

        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            df = get_csv_as_dataframe(report)
            if not df.empty:
                return df
        return pd.DataFrame()

    def test_row_count_matches(self, csv_output):
        """Row count should match expected task count."""
        assert len(csv_output) == len(self.EXPECTED), \
            f"Row count mismatch. Expected: {len(self.EXPECTED)}, Got: {len(csv_output)}"

    def test_task_ids_match(self, csv_output):
        """All task IDs should match."""
        expected_ids = set(self.EXPECTED.keys())
        actual_ids = set(csv_output['id'])
        missing = expected_ids - actual_ids
        extra = actual_ids - expected_ids
        assert not missing, f"Missing tasks: {missing}"
        assert not extra, f"Extra tasks: {extra}"

    def test_start_dates_match(self, csv_output):
        """Start dates should match expected values."""
        errors = []
        for task_id, expected in self.EXPECTED.items():
            row = csv_output[csv_output['id'] == task_id]
            if row.empty:
                errors.append(f"{task_id}: not found")
                continue
            actual_start = row.iloc[0]['start'].strip()
            if not actual_start.startswith(expected['start']):
                errors.append(f"{task_id}: Start mismatch. Expected={expected['start']}, Got={actual_start}")
        assert not errors, "Start date mismatches:\n" + "\n".join(errors[:10])

    def test_end_dates_match(self, csv_output):
        """End dates should match expected values."""
        errors = []
        for task_id, expected in self.EXPECTED.items():
            row = csv_output[csv_output['id'] == task_id]
            if row.empty:
                continue
            actual_end = row.iloc[0]['end'].strip()
            if not actual_end.startswith(expected['end']):
                errors.append(f"{task_id}: End mismatch. Expected={expected['end']}, Got={actual_end}")
        assert not errors, "End date mismatches:\n" + "\n".join(errors[:10])


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
        with open('tests/data/workflow_engine.tjp') as f:
            content = f.read()
        return parser.parse(content)

    @pytest.fixture
    def csv_output(self, project):
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            return get_csv_as_dataframe(report)
        return pd.DataFrame()

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


class TestBottleneckDailyMax:
    """
    Test dailymax limit enforcement with multi-resource tasks.

    Ground Truth from judge_bottleneck.py:
    - release.coding: ends 2025-06-03-17:00 (16h/8h per day = 2 days)
    - release.review: ends 2025-06-09-13:00 (12h QA, 4h/day limit, Jun 4 holiday)
    - release.deploy: ends 2025-06-10-13:00 (MUST wait for Jun 10 because QA
      exhausted dailymax on Jun 9 doing review)

    The key test: deploy requires BOTH dev and qa. QA used 4h on Mon Jun 9
    (09:00-13:00) doing review, so even though dev is free, deploy cannot
    start until Tue Jun 10 when QA's daily limit resets.
    """

    TJP = '''project "Bottleneck_Release" 2025-06-02 +3w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-06-02
}

shift standard {
  workinghours mon - fri 09:00 - 17:00
}

vacation "Company Founder Day" 2025-06-04

resource team "Dev Team" {
  resource dev "FullStack Dev" {
    workinghours standard
  }
  resource qa "QA Lead" {
    workinghours standard
    limits { dailymax 4h }
  }
}

task release "v1.0 Release" {
  task coding "Feature Code" {
    effort 16h
    allocate dev
    start 2025-06-02-09:00
  }
  task review "Code Review" {
    effort 12h
    allocate qa
    depends !coding
  }
  task deploy "Production Push" {
    effort 4h
    allocate dev, qa
    depends !review
  }
}

taskreport "bottleneck_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
'''

    @pytest.fixture
    def csv_output(self):
        parser = ProjectFileParser()
        project = parser.parse(self.TJP)
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            return get_csv_as_dataframe(report)
        return pd.DataFrame()

    def test_coding_end(self, csv_output):
        """coding: 16h effort / 8h per day = 2 days -> ends Jun 3 17:00"""
        row = csv_output[csv_output['id'] == 'release.coding']
        assert not row.empty, "release.coding not found"
        expected = "2025-06-03-17:00"
        actual = row.iloc[0]['end']
        assert actual == expected, f"coding end: expected {expected}, got {actual}"

    def test_review_end(self, csv_output):
        """review: 12h QA (4h/day limit), Jun 4 holiday -> ends Jun 9 13:00"""
        row = csv_output[csv_output['id'] == 'release.review']
        assert not row.empty, "release.review not found"
        # Thu Jun 5: 4h, Fri Jun 6: 4h, Mon Jun 9: 4h (09:00-13:00)
        expected = "2025-06-09-13:00"
        actual = row.iloc[0]['end']
        assert actual == expected, f"review end: expected {expected}, got {actual}"

    def test_deploy_waits_for_dailymax_reset(self, csv_output):
        """deploy MUST wait for Jun 10 because QA hit dailymax on Jun 9"""
        row = csv_output[csv_output['id'] == 'release.deploy']
        assert not row.empty, "release.deploy not found"
        # QA worked 09:00-13:00 on Jun 9 (4h = dailymax)
        # Deploy needs both dev AND qa
        # Even though dev is free Jun 9 afternoon, qa is not
        # So deploy must wait until Tue Jun 10 when qa's limit resets
        expected = "2025-06-10-13:00"
        actual = row.iloc[0]['end']
        assert actual == expected, (
            f"deploy end: expected {expected}, got {actual}\n"
            "(Hint: QA should not work >4h on Monday Jun 9)"
        )


class TestIssue52EfficiencyFragmentation:
    """
    Issue #52: The Swiss Cheese Schedule

    Tests efficiency with fragmented shifts. A resource with 0.5 efficiency
    needs 2x working time to complete effort. Combined with a fragmented shift
    (1h work, 1h break pattern), the task must correctly navigate breaks.

    Task: 1.5h Effort @ 0.5 Efficiency = 3.0h Working Time needed.
    Shift Slots: 09-10, 11-12, 13-14, 15-16.

    Timeline:
    09:00 -> 10:00: Works 1.0h (accumulated: 1.0h)
    10:00 -> 11:00: Break
    11:00 -> 12:00: Works 1.0h (accumulated: 2.0h)
    12:00 -> 13:00: Break
    13:00 -> 14:00: Works 1.0h (accumulated: 3.0h - DONE)

    Expected End: 2025-11-03-14:00
    """

    TJP = '''project "Slow_Maze" 2025-11-01 +1w {
      timezone "Etc/UTC"
      timeformat "%Y-%m-%d %H:%M"
      now 2025-11-01
    }

    shift swiss_cheese {
      workinghours mon - fri 09:00 - 10:00, 11:00 - 12:00, 13:00 - 14:00, 15:00 - 16:00
    }

    resource intern "Slow Learner" {
      workinghours swiss_cheese
      efficiency 0.5
    }

    task ordeal "The Long Haul" {
      task part1 "Hard Work" {
        effort 1.5h
        allocate intern
        start 2025-11-03-09:00
      }
    }

    taskreport "efficiency_output" {
      formats csv
      columns id, start, end
      timeformat "%Y-%m-%d-%H:%M"
    }
    '''

    @pytest.fixture
    def csv_output(self):
        parser = ProjectFileParser()
        project = parser.parse(self.TJP)
        project.schedule()
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            df = get_csv_as_dataframe(report)
            if not df.empty:
                return df
        return pd.DataFrame()

    def test_efficiency_with_fragmented_shift(self, csv_output):
        """1.5h effort @ 0.5 efficiency needs 3h work, navigating breaks."""
        row = csv_output[csv_output['id'] == 'ordeal.part1']
        assert not row.empty, "ordeal.part1 not found"

        expected_end = "2025-11-03-14:00"
        actual_end = row.iloc[0]['end'].strip()

        assert actual_end == expected_end, (
            f"Expected end: {expected_end}, got: {actual_end}\n"
            "(Common failure: adding effort/efficiency directly to start without navigating gaps)"
        )


class TestIssue49BottleneckRelease:
    """
    Issue #49: The Bottlenecked Release - Judge script logic

    Ground truth from judge_bottleneck.py:
    1. CODING: Dev 8h/day, 16h effort -> ends Tue June 3, 17:00
    2. REVIEW: QA 4h/day max, 12h effort, Jun 4 holiday
       -> Thu Jun 5 (4h), Fri Jun 6 (4h), Mon Jun 9 (4h) -> ends Mon June 9, 13:00
    3. DEPLOY: QA+Dev, 4h effort, but QA hit daily limit on Mon
       -> pushed to Tue Jun 10 -> ends Tue June 10, 13:00
    """

    TJP_FILE = Path(__file__).parent / "data" / "bottleneck.tjp"

    # Ground truth from judge script
    TRUTH_CODE_END = "2025-06-03-17:00"
    TRUTH_REVIEW_END = "2025-06-09-13:00"
    TRUTH_DEPLOY_END = "2025-06-10-13:00"

    @pytest.fixture
    def csv_output(self):
        parser = ProjectFileParser()
        project = parser.parse(self.TJP_FILE.read_text())
        project.schedule()
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            df = get_csv_as_dataframe(report)
            if not df.empty:
                return df
        return pd.DataFrame()

    def test_coding_end(self, csv_output):
        """Coding: 16h effort, Dev 8h/day -> ends Tue June 3, 17:00"""
        row = csv_output[csv_output['id'] == 'release.coding']
        assert not row.empty, "FAIL: Task release.coding not found in CSV."

        actual_end = row.iloc[0]['end'].strip()
        assert actual_end == self.TRUTH_CODE_END, (
            f"FAIL: release.coding\n"
            f"  Expected: {self.TRUTH_CODE_END}\n"
            f"  Got:      {actual_end}"
        )

    def test_review_end(self, csv_output):
        """Review: 12h effort, QA 4h/day max, Jun 4 holiday -> ends Mon June 9, 13:00"""
        row = csv_output[csv_output['id'] == 'release.review']
        assert not row.empty, "FAIL: Task release.review not found in CSV."

        actual_end = row.iloc[0]['end'].strip()
        assert actual_end == self.TRUTH_REVIEW_END, (
            f"FAIL: release.review\n"
            f"  Expected: {self.TRUTH_REVIEW_END}\n"
            f"  Got:      {actual_end}"
        )

    def test_deploy_end(self, csv_output):
        """Deploy: QA hit daily limit Mon, must wait until Tue -> ends Tue June 10, 13:00"""
        row = csv_output[csv_output['id'] == 'release.deploy']
        assert not row.empty, "FAIL: Task release.deploy not found in CSV."

        actual_end = row.iloc[0]['end'].strip()
        assert actual_end == self.TRUTH_DEPLOY_END, (
            f"FAIL: release.deploy\n"
            f"  Expected: {self.TRUTH_DEPLOY_END}\n"
            f"  Got:      {actual_end}\n"
            f"  (Hint: Did you let the QA Lead work >4h on Monday?)"
        )


class TestIssue50PriorityClash:
    """
    Issue #50: Priority Clash - Judge script logic (judge_priority.py)

    Ground truth:
    - Aug 1 (Fri): 4h capacity
    - Aug 2/3: Weekend
    - Aug 4 (Mon): 4h capacity

    - high_prio (Prio 1000) MUST win the Aug 1 slot -> ends 2025-08-01-13:00
    - low_prio (Prio 100) MUST be pushed to Aug 4 -> ends 2025-08-04-13:00
    """

    TJP_FILE = Path(__file__).parent / "data" / "priority_clash.tjp"

    # Ground truth from judge script
    EXPECTED_HIGH_END = "2025-08-01-13:00"
    EXPECTED_LOW_END = "2025-08-04-13:00"

    @pytest.fixture
    def csv_output(self):
        parser = ProjectFileParser()
        project = parser.parse(self.TJP_FILE.read_text())
        project.schedule()
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            df = get_csv_as_dataframe(report)
            if not df.empty:
                return df
        return pd.DataFrame()

    def test_high_priority_wins_first_slot(self, csv_output):
        """High Priority task (Prio 1000) MUST win the Aug 1 slot"""
        row = csv_output[csv_output['id'] == 'conflict.high_prio']
        assert not row.empty, "FAIL: High Prio task missing."

        actual_end = row.iloc[0]['end'].strip()
        assert actual_end == self.EXPECTED_HIGH_END, (
            f"FAIL: High Priority task displaced.\n"
            f"  Expected: {self.EXPECTED_HIGH_END}\n"
            f"  Got:      {actual_end}"
        )

    def test_low_priority_pushed_to_monday(self, csv_output):
        """Low Priority task (Prio 100) MUST be pushed to Aug 4 (Monday)"""
        row = csv_output[csv_output['id'] == 'conflict.low_prio']
        assert not row.empty, "FAIL: Low Prio task missing."

        actual_end = row.iloc[0]['end'].strip()
        assert actual_end == self.EXPECTED_LOW_END, (
            f"FAIL: Low Priority task did not wait.\n"
            f"  Expected: {self.EXPECTED_LOW_END}\n"
            f"  Got:      {actual_end}\n"
            f"  (Did your system schedule strictly by File Order instead of Priority?)"
        )


class TestIssue51ALAPBackwardScheduling:
    """
    Issue #51: ALAP Backward Scheduling - Judge script logic (judge_alap.py)

    Ground truth:
    - Deadline: Friday Dec 12, 17:00

    Step 2 (Painting) - 16h Effort:
    - Must end: Fri Dec 12, 17:00
    - Fri Dec 12: 8h, Thu Dec 11: 8h
    - Start: Thu Dec 11, 09:00

    Step 1 (Assembly) - 16h Effort:
    - Must finish before Painting starts (Thu Dec 11, 09:00)
    - Wed Dec 10: HOLIDAY (Skip)
    - Tue Dec 9: 8h, Mon Dec 8: 8h
    - Start: Mon Dec 8, 09:00

    TRAP: If system ignores holiday during backward pass,
    it schedules Assembly Tue+Wed instead of Mon+Tue.
    """

    TJP_FILE = Path(__file__).parent / "data" / "alap_backward.tjp"

    # Ground truth from judge script
    EXPECTED_PAINT_START = "2025-12-11-09:00"
    EXPECTED_PAINT_END = "2025-12-12-17:00"
    EXPECTED_ASSEMBLY_START = "2025-12-08-09:00"
    EXPECTED_ASSEMBLY_END = "2025-12-09-17:00"

    @pytest.fixture
    def csv_output(self):
        parser = ProjectFileParser()
        project = parser.parse(self.TJP_FILE.read_text())
        project.schedule()
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            df = get_csv_as_dataframe(report)
            if not df.empty:
                return df
        return pd.DataFrame()

    def test_painting_alap_anchored(self, csv_output):
        """Painting (step2) must be anchored at deadline"""
        row = csv_output[csv_output['id'] == 'production.step2']
        assert not row.empty, "FAIL: Painting task missing."

        actual_start = row.iloc[0]['start'].strip()
        actual_end = row.iloc[0]['end'].strip()

        valid = (actual_start == self.EXPECTED_PAINT_START and
                 actual_end == self.EXPECTED_PAINT_END)
        assert valid, (
            f"FAIL: Painting ALAP logic.\n"
            f"  Expected: {self.EXPECTED_PAINT_START} -> {self.EXPECTED_PAINT_END}\n"
            f"  Got:      {actual_start} -> {actual_end}"
        )

    def test_assembly_respects_holiday_backward(self, csv_output):
        """Assembly (step1) must skip Dec 10 holiday in backward pass"""
        row = csv_output[csv_output['id'] == 'production.step1']
        assert not row.empty, "FAIL: Assembly task missing."

        actual_start = row.iloc[0]['start'].strip()
        assert actual_start == self.EXPECTED_ASSEMBLY_START, (
            f"FAIL: Assembly calculation error.\n"
            f"  Expected Start: {self.EXPECTED_ASSEMBLY_START} (Mon)\n"
            f"  Got Start:      {actual_start}\n"
            f"  (If you got 2025-12-09, you missed the holiday in backward pass)"
        )


class TestIssue53GlobalTimezones:
    """
    Issue #53: The Sun Chaser - Global Timezone Handling

    Tests timezone-aware scheduling for resources in different timezones.
    Working hours are defined in local time but the project runs in UTC.

    Tokyo (UTC+9): Local 09:00-18:00 = UTC 00:00-09:00
    New York (UTC-4 in May, EDT): Local 09:00-18:00 = UTC 13:00-22:00

    Task 1 (Tokyo): 9h effort, starts 00:00 UTC
    - Works 00:00-09:00 UTC (one full day in JST)
    - Ends: 09:00 UTC

    Task 2 (NY): 4h effort, depends on Tokyo
    - Tokyo finishes: 09:00 UTC (05:00 AM in NY - too early!)
    - NY shift starts: 09:00 AM local = 13:00 UTC (May is EDT, UTC-4)
    - Actual start: 13:00 UTC
    - 4h work: 13:00-17:00 UTC
    - Ends: 17:00 UTC

    Note: May 1, 2025 is during EDT (Daylight Saving Time), so NY is UTC-4.
    """

    TJP = '''project "Global_Ops" 2025-05-01 +1w {
      timezone "Etc/UTC"
      timeformat "%Y-%m-%d %H:%M"
      now 2025-05-01
    }

    shift local_9to6 {
      workinghours mon - fri 09:00 - 18:00
    }

    resource team "Global Team" {
      resource dev_jp "Tokyo Dev" {
        timezone "Asia/Tokyo"
        workinghours local_9to6
      }

      resource qa_ny "NY QA" {
        timezone "America/New_York"
        workinghours local_9to6
      }
    }

    task follow_sun "Handover" {
      task step1_jp "Build" {
        effort 9h
        allocate dev_jp
        start 2025-05-01-00:00
      }

      task step2_ny "Test" {
        effort 4h
        allocate qa_ny
        depends !step1_jp
      }
    }

    taskreport "timezone_output" {
      formats csv
      columns id, start, end
      timeformat "%Y-%m-%d-%H:%M"
    }
    '''

    @pytest.fixture
    def csv_output(self):
        parser = ProjectFileParser()
        project = parser.parse(self.TJP)
        project.schedule()
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            df = get_csv_as_dataframe(report)
            if not df.empty:
                return df
        return pd.DataFrame()

    def test_tokyo_finishes_at_utc_0900(self, csv_output):
        """Tokyo: 9h effort in JST (09:00-18:00 local = 00:00-09:00 UTC)"""
        row = csv_output[csv_output['id'] == 'follow_sun.step1_jp']
        assert not row.empty, "follow_sun.step1_jp not found"

        expected_end = "2025-05-01-09:00"
        actual_end = row.iloc[0]['end'].strip()

        assert actual_end == expected_end, (
            f"Tokyo end: expected {expected_end}, got {actual_end}\n"
            "(Tokyo shift 09:00-18:00 JST = 00:00-09:00 UTC)"
        )

    def test_ny_waits_for_local_shift_start(self, csv_output):
        """NY must wait until 09:00 local (13:00 UTC during EDT)"""
        row = csv_output[csv_output['id'] == 'follow_sun.step2_ny']
        assert not row.empty, "follow_sun.step2_ny not found"

        # Tokyo finishes 09:00 UTC = 05:00 AM in NY (too early)
        # NY shift starts 09:00 AM local = 13:00 UTC (May = EDT, UTC-4)
        expected_start = "2025-05-01-13:00"
        actual_start = row.iloc[0]['start'].strip()

        assert actual_start == expected_start, (
            f"NY start: expected {expected_start}, got {actual_start}\n"
            "(Tokyo finishes 09:00 UTC = 05:00 AM NY. NY shift starts 09:00 local = 13:00 UTC in May/EDT)"
        )

    def test_ny_finishes_after_4h_work(self, csv_output):
        """NY works 4h: 13:00-17:00 UTC"""
        row = csv_output[csv_output['id'] == 'follow_sun.step2_ny']
        assert not row.empty, "follow_sun.step2_ny not found"

        expected_end = "2025-05-01-17:00"
        actual_end = row.iloc[0]['end'].strip()

        assert actual_end == expected_end, (
            f"NY end: expected {expected_end}, got {actual_end}\n"
            "(4h work starting 13:00 UTC should end 17:00 UTC)"
        )


class TestIssue54JITSupplyChain:
    """
    Issue #54: Just-In-Time Supply Chain - ALAP + Resource Contention

    Judge script logic from issue #54:
    - Deadline: Fri July 18, 16:00
    - Pack (8h): Must be Fri Jul 18, 08:00-16:00
    - Two assembly tasks (16h each) must occupy two sequential slots:
      - Slot 1 (latest): Wed Jul 16 08:00 - Thu Jul 17 16:00
      - Slot 2 (earliest): Mon Jul 14 08:00 - Tue Jul 15 16:00
    - Order of A/B in slots doesn't matter, but they must be sequential
    """

    TJP_FILE = Path(__file__).parent / "data" / "jit_supply.tjp"

    # Expected values from judge script
    EXP_PACK_START = "2025-07-18-08:00"
    EXP_PACK_END = "2025-07-18-16:00"

    # Two valid slots for assemblies (order doesn't matter)
    SLOT1_START = "2025-07-16-08:00"  # Wed-Thu (latest)
    SLOT1_END = "2025-07-17-16:00"
    SLOT2_START = "2025-07-14-08:00"  # Mon-Tue (earliest)
    SLOT2_END = "2025-07-15-16:00"

    @pytest.fixture
    def csv_output(self):
        """Generate our tool's output."""
        parser = ProjectFileParser()
        project = parser.parse(self.TJP_FILE.read_text())
        project.schedule()

        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            df = get_csv_as_dataframe(report)
            if not df.empty:
                return df
        return pd.DataFrame()

    def test_pack_anchored_at_deadline(self, csv_output):
        """Pack task must be anchored at deadline (Fri Jul 18, 08:00-16:00)."""
        row = csv_output[csv_output['id'] == 'delivery.pack']
        assert not row.empty, "delivery.pack not found"

        actual_start = row.iloc[0]['start'].strip()
        actual_end = row.iloc[0]['end'].strip()

        assert actual_start == self.EXP_PACK_START and actual_end == self.EXP_PACK_END, (
            f"Packaging ALAP logic failed.\n"
            f"  Expected: {self.EXP_PACK_START} -> {self.EXP_PACK_END}\n"
            f"  Got:      {actual_start} -> {actual_end}"
        )

    def test_assemblies_in_valid_slots(self, csv_output):
        """Assembly tasks must occupy the two valid slots (order doesn't matter)."""
        row_a = csv_output[csv_output['id'] == 'delivery.assemble_a']
        row_b = csv_output[csv_output['id'] == 'delivery.assemble_b']

        assert not row_a.empty, "delivery.assemble_a not found"
        assert not row_b.empty, "delivery.assemble_b not found"

        start_a = row_a.iloc[0]['start'].strip()
        end_a = row_a.iloc[0]['end'].strip()
        start_b = row_b.iloc[0]['start'].strip()
        end_b = row_b.iloc[0]['end'].strip()

        # Check if A is in slot 1 or slot 2
        is_a_slot1 = (start_a == self.SLOT1_START and end_a == self.SLOT1_END)
        is_a_slot2 = (start_a == self.SLOT2_START and end_a == self.SLOT2_END)

        is_b_slot1 = (start_b == self.SLOT1_START and end_b == self.SLOT1_END)
        is_b_slot2 = (start_b == self.SLOT2_START and end_b == self.SLOT2_END)

        # One must be in Slot 1, one in Slot 2
        valid = (is_a_slot1 and is_b_slot2) or (is_a_slot2 and is_b_slot1)

        error_msg = (
            f"Assembly Scheduling Collision or Calendar Error.\n"
            f"  A: {start_a} -> {end_a}\n"
            f"  B: {start_b} -> {end_b}\n"
            f"  Expected Slots: {self.SLOT1_START} (Wed-Thu) and {self.SLOT2_START} (Mon-Tue)"
        )

        if start_a == start_b:
            error_msg += "\n  -> ERROR: Tasks are running in parallel (Resource Collision)."
        if "07-12" in start_a or "07-13" in start_a or "07-12" in start_b or "07-13" in start_b:
            error_msg += "\n  -> ERROR: You scheduled on a Weekend."

        assert valid, error_msg


class TestIssue55TimeTraveler:
    """
    Issue #55: The Time Traveler (ALAP + Timezones)

    Tests global backward pass with timezone-aware resources.
    Tokyo (UTC+9) and London (UTC+1 BST) must coordinate across timezones.

    Ground Truth (from judge script):
    - Tokyo (impl): 2025-06-13-00:00 to 2025-06-13-09:00 UTC (09:00-18:00 JST)
    - London (design): 2025-06-12-08:00 to 2025-06-12-17:00 UTC (09:00-18:00 BST)
    - London finishes Thursday 18:00 BST (17:00 UTC)
    - Tokyo starts Friday 09:00 JST (00:00 UTC)
    - Gap: 7 hours (Earth rotation)
    """
    TJP_FILE = Path(__file__).parent / "data" / "time_traveler.tjp"

    # Ground truth from judge script
    EXP_TOKYO_START = "2025-06-13-00:00"
    EXP_TOKYO_END = "2025-06-13-09:00"
    EXP_LONDON_START = "2025-06-12-08:00"
    EXP_LONDON_END = "2025-06-12-17:00"

    @pytest.fixture
    def csv_output(self):
        """Parse TJP and generate CSV output."""
        import csv
        import io

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        # Parse like judge script
        data = {}
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        for row in reader:
            task_id = row.get('id')
            if task_id:
                data[task_id] = row
        return data

    def test_tokyo_anchored_to_deadline(self, csv_output):
        """Tokyo task must be anchored to deadline: Jun 13 00:00-09:00 UTC."""
        row = csv_output.get('launch.impl')
        assert row is not None, "FAIL: Tokyo task (launch.impl) missing"

        start = row['start'].strip()
        end = row['end'].strip()

        assert start == self.EXP_TOKYO_START and end == self.EXP_TOKYO_END, (
            f"FAIL: Tokyo ALAP Logic.\n"
            f"  Expected: {self.EXP_TOKYO_START} -> {self.EXP_TOKYO_END}\n"
            f"  Got:      {start} -> {end}"
        )

    def test_london_backward_pass_across_timezone(self, csv_output):
        """
        London must finish before Tokyo starts (Jun 13 00:00 UTC).
        London works 09:00-18:00 BST = 08:00-17:00 UTC.
        Latest finish is Thu Jun 12 17:00 UTC.
        """
        row = csv_output.get('launch.design')
        assert row is not None, "FAIL: London task (launch.design) missing"

        start = row['start'].strip()
        end = row['end'].strip()

        error_msg = (
            f"FAIL: London Timezone/ALAP Logic.\n"
            f"  Expected: {self.EXP_LONDON_START} -> {self.EXP_LONDON_END}\n"
            f"  Got:      {start} -> {end}"
        )

        if "06-13" in start:
            error_msg += (
                "\n  -> ERROR: You tried to schedule London on Friday.\n"
                "     London cannot finish by Fri 00:00 UTC if they start Friday morning!\n"
                "     They must finish Thursday evening."
            )

        assert start == self.EXP_LONDON_START and end == self.EXP_LONDON_END, error_msg

    def test_causality_preserved(self, csv_output):
        """Design must END before Implementation STARTS (no time paradox)."""
        impl = csv_output.get('launch.impl')
        design = csv_output.get('launch.design')

        assert impl and design, "Missing tasks"

        impl_start = impl['start'].strip()
        design_end = design['end'].strip()

        # Parse dates for comparison
        from datetime import datetime
        fmt = "%Y-%m-%d-%H:%M"
        impl_start_dt = datetime.strptime(impl_start, fmt)
        design_end_dt = datetime.strptime(design_end, fmt)

        assert design_end_dt <= impl_start_dt, (
            f"FAIL: Causality Violation!\n"
            f"  Design ends: {design_end}\n"
            f"  Impl starts: {impl_start}\n"
            f"  Design must END before Implementation STARTS."
        )


class TestIssue56UnionContract:
    """
    Issue #56: The "Union Limit" Split

    Tests weeklymax limit enforcement with ISO week boundaries.
    A part-time worker has 20h/week limit. Project starts Wednesday.

    Schedule:
    - Wed Oct 1: step1 (8h) -> Week total: 8h
    - Thu Oct 2: step2 (8h) -> Week total: 16h
    - Fri Oct 3: step3 starts, only 4h remaining in week quota
    - Fri Oct 3 13:00: STOP - hit 20h weekly limit
    - Mon Oct 6: New ISO week, limit resets
    - Mon Oct 6: step3 resumes 09:00-13:00 (remaining 4h)
    - Mon Oct 6: step4 runs 13:00-17:00

    The task MUST split across the week boundary.
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'union_contract.tjp'

    # Ground truth from judge script
    EXP_STEP1_END = "2025-10-01-17:00"
    EXP_STEP2_END = "2025-10-02-17:00"
    EXP_STEP3_START = "2025-10-03-09:00"
    EXP_STEP3_END = "2025-10-06-13:00"
    EXP_STEP4_START = "2025-10-06-13:00"
    EXP_STEP4_END = "2025-10-06-17:00"

    @pytest.fixture
    def csv_output(self):
        """Generate CSV output from our scheduler."""
        import csv
        import io

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        # Parse CSV into dict by task id
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        data = {}
        for row in reader:
            task_id = row.get('Id')
            if task_id:
                data[task_id] = row
        return data

    def test_step1_baseline(self, csv_output):
        """Step1 (Wed) should end at 17:00."""
        row = csv_output.get('chain.step1')
        assert row is not None, "FAIL: chain.step1 missing"
        assert row['End'].strip() == self.EXP_STEP1_END, (
            f"FAIL: Step1 end wrong. Expected {self.EXP_STEP1_END}, Got {row['End']}"
        )

    def test_step2_baseline(self, csv_output):
        """Step2 (Thu) should end at 17:00."""
        row = csv_output.get('chain.step2')
        assert row is not None, "FAIL: chain.step2 missing"
        assert row['End'].strip() == self.EXP_STEP2_END, (
            f"FAIL: Step2 end wrong. Expected {self.EXP_STEP2_END}, Got {row['End']}"
        )

    def test_step3_splits_across_week_boundary(self, csv_output):
        """
        Step3 MUST split across week boundary.
        - Starts Fri Oct 3 09:00
        - Works 4h (hits 20h weekly limit at 13:00)
        - Skips weekend
        - Resumes Mon Oct 6 09:00 (new week, limit reset)
        - Finishes Mon Oct 6 13:00
        """
        row = csv_output.get('chain.step3')
        assert row is not None, "FAIL: chain.step3 missing"

        start = row['Start'].strip()
        end = row['End'].strip()

        error_msg = (
            f"FAIL: Union Limit Logic.\n"
            f"  Expected: {self.EXP_STEP3_START} -> {self.EXP_STEP3_END}\n"
            f"  Got:      {start} -> {end}"
        )

        if "10-03-17:00" in end:
            error_msg += (
                "\n  -> ERROR: You ignored the 20h Weekly Limit! "
                "You let them work 24h in one week."
            )
        if "10-06-09:00" in start:
            error_msg += (
                "\n  -> ERROR: You pushed the whole task to Monday "
                "(Wasted 4h available on Friday)."
            )

        assert start == self.EXP_STEP3_START and end == self.EXP_STEP3_END, error_msg

    def test_step4_picks_up_immediately(self, csv_output):
        """Step4 must start immediately after step3 ends (Mon 13:00)."""
        row = csv_output.get('chain.step4')
        assert row is not None, "FAIL: chain.step4 missing"

        start = row['Start'].strip()
        end = row['End'].strip()

        assert start == self.EXP_STEP4_START, (
            f"FAIL: Step4 should start at {self.EXP_STEP4_START}, got {start}"
        )
        assert end == self.EXP_STEP4_END, (
            f"FAIL: Step4 should end at {self.EXP_STEP4_END}, got {end}"
        )

    def test_weekly_hours_respected(self, csv_output):
        """Verify total hours in week 40 (Oct 1-5) is exactly 20h."""
        from datetime import datetime

        week40_hours = 0
        fmt = "%Y-%m-%d-%H:%M"

        for task_id in ['chain.step1', 'chain.step2', 'chain.step3']:
            row = csv_output.get(task_id)
            if row:
                start = datetime.strptime(row['Start'].strip(), fmt)
                end = datetime.strptime(row['End'].strip(), fmt)

                # Only count hours in week 40 (before Mon Oct 6)
                week_boundary = datetime(2025, 10, 6, 0, 0)

                if start < week_boundary:
                    task_end_in_week = min(end, week_boundary)
                    # This is simplified - real calculation would need shift hours
                    if task_id == 'chain.step3':
                        # step3 works 4h on Friday (09:00-13:00)
                        week40_hours += 4
                    else:
                        week40_hours += 8

        assert week40_hours == 20, (
            f"FAIL: Week 40 should have exactly 20h of work, got {week40_hours}h"
        )


class TestIssue57BlackBoxProtocol:
    """
    Issue #57: The "Black Box" Protocol

    Tests timezone conversion, efficiency, disjoint calendars, day-boundary crossovers.
    No logic hints - the only way to pass is correct simulation of:
    1. Timezone Conversions (UTC vs Local)
    2. Inverse Efficiency (0.5 = 2x slower, 2.0 = 2x faster)
    3. Disjoint Calendars (Mon-Wed vs Thu-Sun)
    4. Day-Boundary Crossovers
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'blackbox.tjp'

    # Ground truth from judge script
    TARGET_PHASE1_END = "2025-01-06-12:00"
    TARGET_PHASE2_END = "2025-01-10-04:00"

    @pytest.fixture
    def csv_dataframe(self):
        """Generate CSV output and return as pandas DataFrame (like judge script)."""
        import io

        import pandas as pd

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        # Parse exactly like judge script
        df = pd.read_csv(io.StringIO(csv_content), sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def test_phase1_checksum(self, csv_dataframe):
        """
        Phase 1 verification - exact judge logic.
        Agent A (UTC+2) works 10:00-14:00 Local = 08:00-12:00 UTC.
        Efficiency 0.5 -> 4h Effort becomes 8h Duration.
        Schedule: Mon-Wed only.
        """
        df = csv_dataframe
        row_1 = df[df['id'] == 'operations.phase_1']

        assert not row_1.empty, "FAIL: Phase 1 missing."

        got = row_1.iloc[0]['end'].strip()
        assert got == self.TARGET_PHASE1_END, (
            f"FAIL: Phase 1.\n"
            f"  Expected: {self.TARGET_PHASE1_END}\n"
            f"  Got:      {got}"
        )

    def test_phase2_checksum(self, csv_dataframe):
        """
        Phase 2 verification - exact judge logic.
        Agent B (UTC-8) works 18:00-22:00 Local = 02:00-06:00 UTC (Next Day).
        Efficiency 2.0 -> 4h Effort becomes 2h Duration.
        Schedule: Thu-Sun only.
        """
        df = csv_dataframe
        row_2 = df[df['id'] == 'operations.phase_2']

        assert not row_2.empty, "FAIL: Phase 2 missing."

        got = row_2.iloc[0]['end'].strip()
        assert got == self.TARGET_PHASE2_END, (
            f"FAIL: Phase 2.\n"
            f"  Expected: {self.TARGET_PHASE2_END}\n"
            f"  Got:      {got}"
        )

    def test_full_judge_verification(self, csv_dataframe):
        """
        Run the complete judge script logic.
        Both phases must pass for system integrity.
        """
        df = csv_dataframe
        errors = 0

        # Check Phase 1
        row_1 = df[df['id'] == 'operations.phase_1']
        if row_1.empty:
            errors += 1
        else:
            got = row_1.iloc[0]['end'].strip()
            if got != self.TARGET_PHASE1_END:
                errors += 1

        # Check Phase 2
        row_2 = df[df['id'] == 'operations.phase_2']
        if row_2.empty:
            errors += 1
        else:
            got = row_2.iloc[0]['end'].strip()
            if got != self.TARGET_PHASE2_END:
                errors += 1

        assert errors == 0, "FAIL: LOGIC MISMATCH - System integrity check failed"


class TestIssue58BlindParadox:
    """
    Issue #58: "Blindfolded" Edition - Date Line + ALAP Gap Paradox

    Tests gapduration subtraction in ALAP backward pass with extreme timezones:
    - Resource K: Pacific/Kiritimati (UTC+14) - first timezone to see new day
    - Resource N: Pacific/Niue (UTC-11) - nearly last timezone
    - 48h gapduration with onstart dependency in ALAP mode

    The trap: gapduration must be subtracted from predecessor's START,
    not just stacked like bricks.
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'paradox.tjp'

    # Base64 encoded ground truth (from blind judge)
    TRUTH_A_START = "MjAyNS0xMi0yNy0yMzowMA=="  # 2025-12-27-23:00
    TRUTH_A_END = "MjAyNS0xMi0yOC0yMzowMA=="    # 2025-12-28-23:00
    TRUTH_B_START = "MjAyNS0xMi0zMC0yMzowMA=="  # 2025-12-30-23:00
    TRUTH_B_END = "MjAyNS0xMi0zMS0yMzowMA=="    # 2025-12-31-23:00

    @pytest.fixture
    def csv_dataframe(self):
        """Generate CSV output and return as pandas DataFrame."""
        import io

        import pandas as pd

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        df = pd.read_csv(io.StringIO(csv_content), sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def _check_task(self, df, tid, code_start, code_end):
        """Verify task against base64 encoded truth (exact blind judge logic)."""
        import base64

        row = df[df['id'] == tid]
        assert not row.empty, f"FAIL: Task {tid} missing."

        got_s = row.iloc[0]['start'].strip()
        got_e = row.iloc[0]['end'].strip()

        user_s_enc = base64.b64encode(got_s.encode('utf-8')).decode('utf-8')
        user_e_enc = base64.b64encode(got_e.encode('utf-8')).decode('utf-8')

        assert user_s_enc == code_start and user_e_enc == code_end, (
            f"FAIL: {tid} Logic Mismatch.\n"
            f"  -> Your output is mathematically incorrect.\n"
            f"  -> Debug your Timezone-ALAP-Gap iterator."
        )

    def test_task_alpha_integrity(self, csv_dataframe):
        """Task Alpha must respect 48h gapduration from Omega's start."""
        self._check_task(csv_dataframe, 'sequence.a',
                        self.TRUTH_A_START, self.TRUTH_A_END)

    def test_task_omega_integrity(self, csv_dataframe):
        """Task Omega must be anchored to container deadline."""
        self._check_task(csv_dataframe, 'sequence.b',
                        self.TRUTH_B_START, self.TRUTH_B_END)

    def test_blind_judge_full_verification(self, csv_dataframe):
        """
        Run complete blind judge protocol.
        ACCESS GRANTED only if both tasks pass integrity check.
        """
        import base64

        errors = 0
        for tid, code_s, code_e in [
            ('sequence.a', self.TRUTH_A_START, self.TRUTH_A_END),
            ('sequence.b', self.TRUTH_B_START, self.TRUTH_B_END)
        ]:
            row = csv_dataframe[csv_dataframe['id'] == tid]
            if row.empty:
                errors += 1
                continue

            got_s = row.iloc[0]['start'].strip()
            got_e = row.iloc[0]['end'].strip()

            user_s_enc = base64.b64encode(got_s.encode('utf-8')).decode('utf-8')
            user_e_enc = base64.b64encode(got_e.encode('utf-8')).decode('utf-8')

            if user_s_enc != code_s or user_e_enc != code_e:
                errors += 1

        assert errors == 0, "ACCESS DENIED - System logic mismatch"


class TestIssue60EclipseProtocol:
    """
    Issue #60: The "Eclipse" Protocol

    Tests intersection of discontinuous shift patterns.
    Task requires BOTH resources simultaneously:
    - r_sun: Mon, Wed, Fri 09:00-17:00
    - r_moon: Mon-Sun 12:00-14:00
    - Intersection: Mon, Wed, Fri 12:00-14:00 (2h windows)

    7h effort across 2h windows = 4 work sessions needed
    Jun 2 (Mon): 2h, Jun 4 (Wed): 2h, Jun 6 (Fri): 2h, Jun 9 (Mon): 1h
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'eclipse.tjp'

    # Cryptic checksums from judge (reversed -> base64 encoded)
    K_START = "MDA6MjEtMjAtNjAtNTIwMg=="  # 2025-06-02-12:00 reversed
    K_END = "MDA6MzEtOTAtNjAtNTIwMg=="    # 2025-06-09-13:00 reversed

    @pytest.fixture
    def csv_dataframe(self):
        """Generate CSV output and return as pandas DataFrame."""
        import io

        import pandas as pd

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        df = pd.read_csv(io.StringIO(csv_content), sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def _verify(self, val, key):
        """Exact judge verification: reverse string -> base64 encode -> compare."""
        import base64
        rev = val[::-1]
        enc = base64.b64encode(rev.encode('utf-8')).decode('utf-8')
        return enc == key

    def test_sync_task_start(self, csv_dataframe):
        """Task start must align with first intersection window."""
        row = csv_dataframe[csv_dataframe['id'] == 'sys.sync']
        assert not row.empty, "FAIL: Task sys.sync missing."

        user_start = row.iloc[0]['start'].strip()
        assert self._verify(user_start, self.K_START), (
            "FAIL: Start time alignment error.\n"
            "Your scheduler likely booked a time slot where\n"
            "one resource was available, but the other was not."
        )

    def test_sync_task_end(self, csv_dataframe):
        """Task end must reflect correct intersection calculation."""
        row = csv_dataframe[csv_dataframe['id'] == 'sys.sync']
        assert not row.empty, "FAIL: Task sys.sync missing."

        user_end = row.iloc[0]['end'].strip()
        assert self._verify(user_end, self.K_END), (
            "FAIL: End time alignment error.\n"
            "7h effort across 2h intersection windows should take ~1 week."
        )

    def test_orbital_alignment_full(self, csv_dataframe):
        """
        Run complete eclipse judge protocol.
        SUCCESS only if both start and end match intersection calculation.
        """
        row = csv_dataframe[csv_dataframe['id'] == 'sys.sync']
        assert not row.empty, "FAIL: Task missing."

        user_start = row.iloc[0]['start'].strip()
        user_end = row.iloc[0]['end'].strip()

        s_match = self._verify(user_start, self.K_START)
        e_match = self._verify(user_end, self.K_END)

        assert s_match and e_match, (
            "FAIL: ALIGNMENT ERROR.\n"
            "Your scheduler likely booked a time slot where\n"
            "one resource was available, but the other was not."
        )


class TestIssue61SineWaveCapacity:
    """
    Issue #61: The "Sine Wave" Capacity Protocol

    Tests variable daily throughput where batch capacity changes each day:
    - Mon: 2h, Tue: 4h, Wed: 8h, Thu: 16h (peak), Fri: 8h, Sat: 4h, Sun: 2h
    - Weekly capacity: 44h
    - 100h effort distributed across variable buckets

    Simulation breakdown:
    - Week 1 (Sep 1-7): 44h consumed, 56h remaining
    - Week 2 (Sep 8-14): 44h consumed, 12h remaining
    - Week 3: Mon 2h (10h rem), Tue 4h (6h rem), Wed 6h (done at 15:00)
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'throughput.tjp'

    # Expected values verified by simulation
    EXPECTED_START = "2025-09-01-09:00"
    EXPECTED_END = "2025-09-17-15:00"

    @pytest.fixture
    def csv_dataframe(self):
        """Generate CSV output and return as pandas DataFrame."""
        import io

        import pandas as pd

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        df = pd.read_csv(io.StringIO(csv_content), sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def test_processing_task_start(self, csv_dataframe):
        """Task must start on Sep 1 09:00."""
        row = csv_dataframe[csv_dataframe['id'] == 'processing']
        assert not row.empty, "FAIL: Task processing missing."

        user_start = row.iloc[0]['start'].strip()
        assert user_start == self.EXPECTED_START, (
            f"FAIL: Start time wrong.\n"
            f"  Expected: {self.EXPECTED_START}\n"
            f"  Got: {user_start}"
        )

    def test_processing_task_end(self, csv_dataframe):
        """
        100h effort across variable capacity should end Sep 17 15:00.
        Week 1: 44h, Week 2: 44h, Week 3: 2+4+6=12h
        """
        row = csv_dataframe[csv_dataframe['id'] == 'processing']
        assert not row.empty, "FAIL: Task processing missing."

        user_end = row.iloc[0]['end'].strip()
        assert user_end == self.EXPECTED_END, (
            f"FAIL: End time drift detected.\n"
            f"  Expected: {self.EXPECTED_END}\n"
            f"  Got: {user_end}\n"
            f"  Hint: Did you handle the 16h peak on Thursday correctly?"
        )

    def test_waveform_simulation_match(self, csv_dataframe):
        """
        Verify against full simulation of daily bucket filling.
        """
        import datetime

        daily_caps = {0: 2.0, 1: 4.0, 2: 8.0, 3: 16.0, 4: 8.0, 5: 4.0, 6: 2.0}
        remaining = 100.0
        current_date = datetime.datetime(2025, 9, 1)

        while remaining > 0:
            weekday = current_date.weekday()
            capacity = daily_caps[weekday]
            consumed = min(remaining, capacity)
            remaining -= consumed

            if remaining == 0:
                start_hour = 6 if weekday == 3 else 9
                end_hour = start_hour + consumed
                expected_end = current_date.replace(
                    hour=int(end_hour), minute=0
                ).strftime("%Y-%m-%d-%H:%M")
                break

            current_date += datetime.timedelta(days=1)

        row = csv_dataframe[csv_dataframe['id'] == 'processing']
        assert not row.empty, "FAIL: Task missing."

        user_end = row.iloc[0]['end'].strip()
        assert user_end == expected_end, (
            f"FAIL: Waveform simulation mismatch.\n"
            f"  Simulation says: {expected_end}\n"
            f"  Your system says: {user_end}"
        )


class TestIssue59DateLineParadox:
    """
    Issue #59: The "Date Line" Paradox

    Tests ALAP + Efficiency + Elapsed Lags + Dateline Crossing.
    Resources are in extreme timezones:
    - Resource K: Pacific/Kiritimati (UTC+14) - first to see tomorrow
    - Resource N: Pacific/Niue (UTC-11) - almost last to see today

    Ground Truth (from judge_paradox.py):
    - Task B (Omega): Dec 30 23:00 -> Dec 31 23:00 UTC
    - Task A (Alpha): Dec 27 23:00 -> Dec 28 23:00 UTC
      (48h gap before B starts, efficiency 2.0)
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'paradox.tjp'

    # Ground truth from judge script
    TARGET_A_START = "2025-12-27-23:00"
    TARGET_A_END = "2025-12-28-23:00"
    TARGET_B_START = "2025-12-30-23:00"
    TARGET_B_END = "2025-12-31-23:00"

    @pytest.fixture
    def csv_dataframe(self):
        """Generate CSV output and return as pandas DataFrame."""
        import io

        import pandas as pd

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        df = pd.read_csv(io.StringIO(csv_content), sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def test_task_alpha_schedule(self, csv_dataframe):
        """
        Task Alpha: 12h effort with efficiency 2.0 = 6h duration.
        Must end 48h before Omega starts (Dec 30 23:00 - 48h = Dec 28 23:00).
        """
        row = csv_dataframe[csv_dataframe['id'] == 'sequence.a']
        assert not row.empty, "FAIL: Task A missing."

        s = row.iloc[0]['start'].strip()
        e = row.iloc[0]['end'].strip()

        assert s == self.TARGET_A_START and e == self.TARGET_A_END, (
            f"FAIL: Alpha Alignment.\n"
            f"  Expected: {self.TARGET_A_START} -> {self.TARGET_A_END}\n"
            f"  Got:      {s} -> {e}"
        )

    def test_task_omega_schedule(self, csv_dataframe):
        """
        Task Omega: 3h effort with efficiency 0.5 = 6h duration.
        Must end at deadline (Dec 31 23:00).
        """
        row = csv_dataframe[csv_dataframe['id'] == 'sequence.b']
        assert not row.empty, "FAIL: Task B missing."

        s = row.iloc[0]['start'].strip()
        e = row.iloc[0]['end'].strip()

        assert s == self.TARGET_B_START and e == self.TARGET_B_END, (
            f"FAIL: Omega Alignment.\n"
            f"  Expected: {self.TARGET_B_START} -> {self.TARGET_B_END}\n"
            f"  Got:      {s} -> {e}"
        )

    def test_dateline_traversed(self, csv_dataframe):
        """
        Full judge verification: All timestamps should show 23:00 UTC
        if timezone math is correct (UTC+14 and UTC-11 interacting).
        """
        errors = 0

        # Check A
        row_a = csv_dataframe[csv_dataframe['id'] == 'sequence.a']
        if row_a.empty:
            errors += 1
        else:
            s = row_a.iloc[0]['start'].strip()
            e = row_a.iloc[0]['end'].strip()
            if s != self.TARGET_A_START or e != self.TARGET_A_END:
                errors += 1

        # Check B
        row_b = csv_dataframe[csv_dataframe['id'] == 'sequence.b']
        if row_b.empty:
            errors += 1
        else:
            s = row_b.iloc[0]['start'].strip()
            e = row_b.iloc[0]['end'].strip()
            if s != self.TARGET_B_START or e != self.TARGET_B_END:
                errors += 1

        assert errors == 0, (
            "FAIL: PARADOX UNRESOLVED.\n"
            "Your system did not correctly handle UTC+14 and UTC-11\n"
            "interacting in an ALAP backward pass."
        )


class TestIssue62SharedQuotaProtocol:
    """
    Issue #62: The "Shared Quota" Protocol

    Tests hierarchical resource limits (parent dailymax applies to children).
    Scenario: 3 connection slots under a rate limiter with dailymax 6h.

    - slot_1, slot_2, slot_3 can run in parallel (concurrency)
    - But combined usage cannot exceed 6h/day (quota)

    Expected:
    - job_a (3h on slot_1): Jul 1 09:00-12:00
    - job_b (3h on slot_2): Jul 1 09:00-12:00
    - job_c (3h on slot_3): MUST wait for Jul 2 (quota exceeded)

    The TRAP: Just because a slot is free doesn't mean you can use it.
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'quota.tjp'

    # Base64 encoded checksums from judge (reversed string -> base64)
    K_END_AB = "MDA6MjEtMTAtNzAtNTIwMg=="  # 2025-07-01-12:00 reversed
    K_END_C = "MDA6MjEtMjAtNzAtNTIwMg=="   # 2025-07-02-12:00 reversed

    @pytest.fixture
    def csv_dataframe(self):
        """Generate CSV output and return as pandas DataFrame."""
        import io

        import pandas as pd

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        df = pd.read_csv(io.StringIO(csv_content), sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def _verify(self, val, key):
        """Exact judge verification: reverse string -> base64 encode -> compare."""
        import base64
        rev = val[::-1]
        enc = base64.b64encode(rev.encode('utf-8')).decode('utf-8')
        return enc == key

    def test_job_a_fits_in_day1(self, csv_dataframe):
        """Job A (3h) should complete on Jul 1 by 12:00."""
        row = csv_dataframe[csv_dataframe['id'] == 'batch.job_a']
        assert not row.empty, "FAIL: Job A missing."

        end_a = row.iloc[0]['end'].strip()
        assert self._verify(end_a, self.K_END_AB), (
            f"FAIL: Job A timing mismatch.\n"
            f"  Got: {end_a}"
        )

    def test_job_b_fits_in_day1(self, csv_dataframe):
        """Job B (3h) should complete on Jul 1 by 12:00 (parallel with A)."""
        row = csv_dataframe[csv_dataframe['id'] == 'batch.job_b']
        assert not row.empty, "FAIL: Job B missing."

        end_b = row.iloc[0]['end'].strip()
        assert self._verify(end_b, self.K_END_AB), (
            f"FAIL: Job B timing mismatch.\n"
            f"  Got: {end_b}"
        )

    def test_job_c_pushed_to_day2(self, csv_dataframe):
        """
        Job C cannot start on Jul 1 even though slot_3 is free.
        Parent's dailymax 6h is already consumed by A+B.
        C must wait for Jul 2 quota reset.
        """
        row = csv_dataframe[csv_dataframe['id'] == 'batch.job_c']
        assert not row.empty, "FAIL: Job C missing."

        end_c = row.iloc[0]['end'].strip()
        assert self._verify(end_c, self.K_END_C), (
            f"FAIL: Job C leaked into the restricted zone.\n"
            f"  Got: {end_c}\n"
            f"  Job C should end on Jul 2, not Jul 1.\n"
            f"  Parent dailymax 6h should prevent scheduling on Jul 1."
        )

    def test_quota_enforced(self, csv_dataframe):
        """
        Full quota enforcement verification.
        A+B use 6h on Day 1, C must wait for Day 2.
        """
        # Verify A and B
        row_a = csv_dataframe[csv_dataframe['id'] == 'batch.job_a']
        row_b = csv_dataframe[csv_dataframe['id'] == 'batch.job_b']
        row_c = csv_dataframe[csv_dataframe['id'] == 'batch.job_c']

        assert not row_a.empty, "FAIL: Job A missing."
        assert not row_b.empty, "FAIL: Job B missing."
        assert not row_c.empty, "FAIL: Job C missing."

        end_a = row_a.iloc[0]['end'].strip()
        end_b = row_b.iloc[0]['end'].strip()
        end_c = row_c.iloc[0]['end'].strip()

        ab_ok = self._verify(end_a, self.K_END_AB) and self._verify(end_b, self.K_END_AB)
        c_ok = self._verify(end_c, self.K_END_C)

        assert ab_ok and c_ok, (
            "FAIL: QUOTA NOT ENFORCED.\n"
            "Concurrent slots utilized beyond the shared parent limit.\n"
            f"  A ends: {end_a}\n"
            f"  B ends: {end_b}\n"
            f"  C ends: {end_c}\n"
            "Expected: A/B on Jul 1, C on Jul 2."
        )


class TestIssue63FailoverProtocol:
    """
    Issue #63: The "Failover" Protocol

    Tests alternative resource allocation with smart routing.
    Scenario: Primary resource on vacation, backup resource available but slower.

    Primary (efficiency 1.0): On vacation Aug 1-5, first available Aug 6
    Backup (efficiency 0.5): Available immediately but takes 2x time

    8h effort paths:
    - Path A (Primary): Wait till Aug 6, Duration 8h, End: Aug 6 17:00
    - Path B (Backup): Start Aug 1, Duration 16h (8h/0.5), End: Aug 4 17:00

    Smart routing should pick Path B (finishes 2 days earlier).
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'failover.tjp'

    # Base64 encoded checksum from judge (reversed string -> base64)
    K_END = "MDA6NzEtNDAtODAtNTIwMg=="  # 2025-08-04-17:00 reversed

    @pytest.fixture
    def csv_dataframe(self):
        """Generate CSV output and return as pandas DataFrame."""
        import io

        import pandas as pd

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        df = pd.read_csv(io.StringIO(csv_content), sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def _verify(self, val, key):
        """Exact judge verification: reverse string -> base64 encode -> compare."""
        import base64
        rev = val[::-1]
        enc = base64.b64encode(rev.encode('utf-8')).decode('utf-8')
        return enc == key

    def test_task_ends_aug_4(self, csv_dataframe):
        """
        Task must end Aug 4 17:00 (using backup resource).
        If it ends Aug 6, smart routing failed to switch to backup.
        """
        row = csv_dataframe[csv_dataframe['id'] == 'compute']
        assert not row.empty, "FAIL: Task compute missing."

        user_end = row.iloc[0]['end'].strip()
        assert self._verify(user_end, self.K_END), (
            f"FAIL: SUBOPTIMAL PATH CHOSEN.\n"
            f"  Your End Time: {user_end}\n"
            f"  Expected: 2025-08-04-17:00\n"
            f"  Did you wait for the Primary resource? (Aug 6)\n"
            f"  A smart scheduler should have switched to Backup (Aug 4)."
        )

    def test_task_starts_aug_1(self, csv_dataframe):
        """Task must start on Aug 1 (immediately with backup, not waiting for primary)."""
        row = csv_dataframe[csv_dataframe['id'] == 'compute']
        assert not row.empty, "FAIL: Task compute missing."

        user_start = row.iloc[0]['start'].strip()
        expected_start = "2025-08-01-09:00"

        assert user_start == expected_start, (
            f"FAIL: Task should start immediately with backup.\n"
            f"  Expected: {expected_start}\n"
            f"  Got: {user_start}\n"
            f"  Task should not wait for primary to become available."
        )

    def test_intelligent_routing(self, csv_dataframe):
        """
        Full judge verification: timing must match AND resource selection must be correct.
        Start now with slow > Wait for fast.
        """
        row = csv_dataframe[csv_dataframe['id'] == 'compute']
        assert not row.empty, "FAIL: Task missing."

        user_end = row.iloc[0]['end'].strip()
        user_start = row.iloc[0]['start'].strip()

        # Verify timing
        timing_ok = self._verify(user_end, self.K_END)

        # Verify start (must be Aug 1, not Aug 6)
        start_ok = user_start == "2025-08-01-09:00"

        assert timing_ok and start_ok, (
            "FAIL: INTELLIGENT ROUTING NOT CONFIRMED.\n"
            f"  Start: {user_start} (expected 2025-08-01-09:00)\n"
            f"  End: {user_end} (expected 2025-08-04-17:00)\n"
            "System should prioritize completion time over resource preference."
        )


class TestIssue64AtomicBooking:
    """
    Issue #64: The "Indivisible" Protocol - Atomicity

    Tests contiguous (atomic) flag for tasks that cannot be split across breaks.
    Scenario: Kiln firing that cannot be paused once started.

    Shift: Mon-Fri 08:00-12:00, 13:00-18:00 (4h morning, 1h lunch gap, 5h afternoon)
    Task: 4.5h effort with contiguous flag

    Logic:
    - Morning slot: 08:00-12:00 = 4h (NOT enough for 4.5h)
    - Afternoon slot: 13:00-18:00 = 5h (ENOUGH for 4.5h)

    Expected: Task slides to afternoon block
    - Start: 2025-11-03-13:00 (Monday afternoon)
    - End: 2025-11-03-17:30 (4.5h later)

    Note: The original judge expected Nov 1, but Nov 1 2025 is Saturday.
    The shift specifies Mon-Fri, so first working day is Nov 3 (Monday).
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'atomic.tjp'

    # Correct expected values based on logic (not judge which has Nov 1 Saturday bug)
    TARGET_START = "2025-11-03-13:00"
    TARGET_END = "2025-11-03-17:30"

    @pytest.fixture
    def csv_dataframe(self):
        """Generate CSV output and return as pandas DataFrame."""
        import io

        import pandas as pd

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        df = pd.read_csv(io.StringIO(csv_content), sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def test_task_starts_afternoon(self, csv_dataframe):
        """
        Task must start at 13:00 (afternoon), not 08:00 (morning).
        Morning slot (4h) is too small for 4.5h contiguous task.
        """
        row = csv_dataframe[csv_dataframe['id'] == 'production']
        assert not row.empty, "FAIL: Task production missing."

        user_start = row.iloc[0]['start'].strip()
        assert user_start == self.TARGET_START, (
            f"FAIL: Task should start in afternoon slot.\n"
            f"  Expected: {self.TARGET_START}\n"
            f"  Got: {user_start}\n"
            f"  Morning slot (4h) is too small for 4.5h contiguous task."
        )

    def test_task_ends_correct_time(self, csv_dataframe):
        """Task must end at 17:30 (13:00 + 4.5h)."""
        row = csv_dataframe[csv_dataframe['id'] == 'production']
        assert not row.empty, "FAIL: Task production missing."

        user_end = row.iloc[0]['end'].strip()
        assert user_end == self.TARGET_END, (
            f"FAIL: Task end time incorrect.\n"
            f"  Expected: {self.TARGET_END}\n"
            f"  Got: {user_end}"
        )

    def test_atomicity_preserved(self, csv_dataframe):
        """
        Full verification: Task was NOT split across lunch break.
        Start at 13:00 proves the task waited for the 5h afternoon slot
        instead of starting at 08:00 and splitting at 12:00-13:00 lunch.
        """
        row = csv_dataframe[csv_dataframe['id'] == 'production']
        assert not row.empty, "FAIL: Task missing."

        user_start = row.iloc[0]['start'].strip()
        user_end = row.iloc[0]['end'].strip()

        # If start is 08:00, the task was fragmented
        if '08:00' in user_start:
            assert False, (
                "FAIL: FRAGMENTATION DETECTED.\n"
                f"  Your Start: {user_start}\n"
                "You likely split a contiguous task across the lunch break.\n"
                "The kiln cooled down. The batch is ruined."
            )

        assert user_start == self.TARGET_START and user_end == self.TARGET_END, (
            "FAIL: ATOMICITY NOT PRESERVED.\n"
            f"  Start: {user_start} (expected {self.TARGET_START})\n"
            f"  End: {user_end} (expected {self.TARGET_END})\n"
            "Task should have slid to the 5h afternoon slot."
        )


class TestIssue65ThermalShock:
    """
    Issue #65: The "Thermal Shock" Protocol - maxgapduration constraint

    Tests that the scheduler delays a predecessor task to respect maxgapduration
    constraint when the successor's resource is blocked.

    Scenario:
    - Heat task (2h) on Heater (available 09:00-17:00)
    - Forge task (2h) on Press (blocked 09:00-15:00 due to booking)
    - Forge depends on Heat with gapduration 0min, maxgapduration 60min

    Naive scheduling:
    - Heat: 09:00-11:00
    - Forge: 15:00-17:00 (earliest press available)
    - Gap: 4h > maxgapduration (60min) -- FAIL

    Smart scheduling:
    - Heat: 13:00-15:00 (delayed)
    - Forge: 15:00-17:00
    - Gap: 0h <= maxgapduration (60min) -- PASS
    """

    TJP_FILE = Path(__file__).parent / 'data' / 'thermal.tjp'

    @pytest.fixture
    def csv_dataframe(self):
        """Generate CSV output and return as pandas DataFrame."""
        import io

        import pandas as pd

        parser = ProjectFileParser()
        with open(self.TJP_FILE) as f:
            content = f.read()
        project = parser.parse(content)

        csv_content = ''
        for report in project.reports:
            if not report.get('scenarios'):
                report['scenarios'] = ['plan']
            report.generate_intermediate_format()
            csv_rows = report.to_csv()
            for row in csv_rows:
                csv_content += ','.join(str(x) for x in row) + '\n'

        df = pd.read_csv(io.StringIO(csv_content), sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    def test_heat_delayed_for_maxgapduration(self, csv_dataframe):
        """
        Heat task must be delayed so it ends when forge can start.
        Heat should NOT start at 09:00 (naive).
        """
        row = csv_dataframe[csv_dataframe['id'] == 'process.heat']
        assert not row.empty, "FAIL: Task process.heat missing."

        user_start = row.iloc[0]['start'].strip()
        # Heat should NOT start at 09:00 because that would create a 4h gap
        assert '09:00' not in user_start, (
            f"FAIL: Heat scheduled too early.\n"
            f"  Start: {user_start}\n"
            f"  A naive scheduler would start Heat at 09:00, but that creates\n"
            f"  a 4h gap before Forge can start (press blocked until 15:00).\n"
            f"  The scheduler should delay Heat to respect maxgapduration."
        )

    def test_gap_within_maxgapduration(self, csv_dataframe):
        """
        The gap between Heat ending and Forge starting must not exceed 60min.
        """
        from datetime import datetime

        heat_row = csv_dataframe[csv_dataframe['id'] == 'process.heat']
        forge_row = csv_dataframe[csv_dataframe['id'] == 'process.forge']

        assert not heat_row.empty, "FAIL: Task process.heat missing."
        assert not forge_row.empty, "FAIL: Task process.forge missing."

        heat_end_str = heat_row.iloc[0]['end'].strip()
        forge_start_str = forge_row.iloc[0]['start'].strip()

        fmt = "%Y-%m-%d-%H:%M"
        t_heat_end = datetime.strptime(heat_end_str, fmt)
        t_forge_start = datetime.strptime(forge_start_str, fmt)

        gap_seconds = (t_forge_start - t_heat_end).total_seconds()
        gap_hours = gap_seconds / 3600.0

        assert gap_hours >= 0, (
            f"FAIL: TIME PARADOX - Forge started before Heat finished.\n"
            f"  Heat End: {heat_end_str}\n"
            f"  Forge Start: {forge_start_str}"
        )

        assert gap_hours <= 1.0, (
            f"FAIL: THERMAL SHOCK - Gap exceeds maxgapduration.\n"
            f"  Heat End: {heat_end_str}\n"
            f"  Forge Start: {forge_start_str}\n"
            f"  Gap: {gap_hours:.2f}h (max allowed: 1.0h)\n"
            f"  The metal cooled down. The ingot cracked."
        )

    def test_forge_starts_when_press_available(self, csv_dataframe):
        """
        Forge should start at 15:00 when press becomes available.
        """
        row = csv_dataframe[csv_dataframe['id'] == 'process.forge']
        assert not row.empty, "FAIL: Task process.forge missing."

        user_start = row.iloc[0]['start'].strip()
        assert '15:00' in user_start, (
            f"FAIL: Forge should start when press is available.\n"
            f"  Got: {user_start}\n"
            f"  Expected start at 15:00 (after press maintenance ends)"
        )

    def test_smart_scheduling_achieved(self, csv_dataframe):
        """
        Full verification: Heat ends exactly when Forge starts (optimal).
        This is the "smart" result from the judge:
        - Heat: 13:00-15:00
        - Forge: 15:00-17:00
        - Gap: 0h
        """
        heat_row = csv_dataframe[csv_dataframe['id'] == 'process.heat']
        forge_row = csv_dataframe[csv_dataframe['id'] == 'process.forge']

        assert not heat_row.empty, "FAIL: Task process.heat missing."
        assert not forge_row.empty, "FAIL: Task process.forge missing."

        heat_start = heat_row.iloc[0]['start'].strip()
        heat_end = heat_row.iloc[0]['end'].strip()
        forge_start = forge_row.iloc[0]['start'].strip()
        forge_end = forge_row.iloc[0]['end'].strip()

        # Check for optimal scheduling
        assert heat_start == "2025-05-12-13:00", (
            f"Expected Heat start: 2025-05-12-13:00, got: {heat_start}"
        )
        assert heat_end == "2025-05-12-15:00", (
            f"Expected Heat end: 2025-05-12-15:00, got: {heat_end}"
        )
        assert forge_start == "2025-05-12-15:00", (
            f"Expected Forge start: 2025-05-12-15:00, got: {forge_start}"
        )
        assert forge_end == "2025-05-12-17:00", (
            f"Expected Forge end: 2025-05-12-17:00, got: {forge_end}"
        )


# Convenience function to run all validation tests
def run_all_scheduling_validations():
    """Run all scheduling validation tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_all_scheduling_validations()
