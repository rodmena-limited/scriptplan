#!/usr/bin/env python3
"""
The Infallible Judge - Validator for math_torture test.

This script implements a discrete minute-by-minute simulation of the calendar
and shift logic to verify scheduling accuracy down to the minute.
"""

import datetime
import sys
from datetime import timedelta

import pandas as pd

# --- CONFIGURATION ---
START_DATE = datetime.datetime(2024, 2, 28, 8, 13)  # Start of first shift
ITERATIONS = 500
TASK_EFFORT_MIN = 73
GAP_MIN = 29

# Shift Definition: [Start, End) intervals
# Work intervals are: 08:13 - 11:59 and 13:07 - 17:47
SHIFTS = [
    (datetime.time(8, 13), datetime.time(11, 59)),
    (datetime.time(13, 7), datetime.time(17, 47))
]


def is_working_time(dt):
    """Check if a datetime falls within working hours."""
    t = dt.time()
    for s_start, s_end in SHIFTS:
        if s_start <= t < s_end:
            return True
    return False


def get_next_working_minute(dt):
    """
    If dt is working time, return dt.
    If not, fast forward to the start of the next valid shift interval.
    """
    if is_working_time(dt):
        return dt

    curr = dt
    while not is_working_time(curr):
        curr += timedelta(minutes=1)
        curr = curr.replace(second=0, microsecond=0)
    return curr


def add_working_minutes(start_dt, minutes_effort):
    """
    Adds 'minutes_effort' to start_dt, skipping non-working time.
    """
    cursor = start_dt
    remaining = minutes_effort

    cursor = get_next_working_minute(cursor)

    while remaining > 0:
        if is_working_time(cursor):
            remaining -= 1

        cursor += timedelta(minutes=1)

        if remaining > 0:
            cursor = get_next_working_minute(cursor)

    return cursor


def generate_ground_truth():
    """Generates the mathematically perfect schedule."""
    schedule = []

    current_start = START_DATE

    for i in range(1, ITERATIONS + 1):
        task_id = f"chain.t_{i:03d}"

        actual_end = add_working_minutes(current_start, TASK_EFFORT_MIN)

        schedule.append({
            "id": task_id,
            "start": current_start,
            "end": actual_end
        })

        next_ready_time = actual_end + timedelta(minutes=GAP_MIN)
        current_start = get_next_working_minute(next_ready_time)

    return pd.DataFrame(schedule)


def validate_submission(csv_path):
    print("--- GENERATING GROUND TRUTH ---")
    df_truth = generate_ground_truth()

    fmt = "%Y-%m-%d-%H:%M"
    df_truth['start_str'] = df_truth['start'].dt.strftime(fmt)
    df_truth['end_str'] = df_truth['end'].dt.strftime(fmt)

    print(f"Calculated {len(df_truth)} tasks. Last task ends: {df_truth.iloc[-1]['end_str']}")

    print(f"\n--- LOADING SUBMISSION: {csv_path} ---")
    try:
        df_sub = pd.read_csv(csv_path, sep=None, engine='python')
        df_sub.columns = [c.strip().lower() for c in df_sub.columns]
        df_sub = df_sub.sort_values('id').reset_index(drop=True)
    except Exception as e:
        print(f"FATAL: Read error - {e}")
        sys.exit(1)

    # Validate Row Count
    if len(df_sub) != ITERATIONS:
        print(f"FAIL: Expected {ITERATIONS} rows, got {len(df_sub)}")
        sys.exit(1)

    # Validate Precision
    errors = 0
    for idx, row in df_truth.iterrows():
        sub_row = df_sub.iloc[idx]

        if sub_row['id'] != row['id']:
            print(f"Row Mismatch at index {idx}: Expected {row['id']}, got {sub_row['id']}")
            sys.exit(1)

        if sub_row['start'] != row['start_str']:
            print(f"FAIL [Task {row['id']}]: Start Mismatch.")
            print(f"  Expected: {row['start_str']}")
            print(f"  Got:      {sub_row['start']}")
            errors += 1

        if sub_row['end'] != row['end_str']:
            print(f"FAIL [Task {row['id']}]: End Mismatch.")
            print(f"  Expected: {row['end_str']}")
            print(f"  Got:      {sub_row['end']}")
            errors += 1

        if errors >= 5:
            print("...Too many errors. Aborting.")
            break

    if errors == 0:
        print("\n" + "="*50)
        print("PASS: SYSTEM IS MATHEMATICALLY PERFECT.")
        print(f"Verified {ITERATIONS} chained tasks across Leap Year/Shift boundaries.")
        print("="*50)
    else:
        print("\n" + "!"*50)
        print(f"FAIL: Found {errors} discrepancies.")
        print("!"*50)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python judge_of_time.py <your_output.csv>")
    else:
        validate_submission(sys.argv[1])
