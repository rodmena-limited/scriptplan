"""
Issue #39: Ultra-Complex Stress Test Judge

Gold Standard from Issue #39:
- t_float end: 2025-08-08 14:57:05 (floating point precision)
- t_limit cost: 2400.0 (based on allocated time, not effort)
- t_finish end: 2025-08-29 17:00:00 (ALAP adherence)
"""

import csv
import sys
from datetime import datetime
from math import isclose

# --- CONFIGURATION ---
DATE_FMT = "%Y-%m-%d %H:%M:%S"

# --- THE GOLD STANDARD TRUTH ---
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


def parse_csv(filepath):
    """Reads the CSV and maps Task IDs to their data row."""
    data = {}
    try:
        with open(filepath, encoding='utf-8') as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample)

            reader = csv.DictReader(f, dialect=dialect)
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]

            for row in reader:
                key = row.get('id') or row.get('name')
                if key:
                    # Store by short ID (last component after dot)
                    short_key = key.split('.')[-1] if '.' in key else key
                    data[short_key] = row
    except FileNotFoundError:
        print(f"Error: Could not find '{filepath}'")
        sys.exit(1)
    return data


def check_time(task_name, actual_str, expected_str):
    """Strict time comparison to the second."""
    try:
        dt_actual = datetime.strptime(actual_str, DATE_FMT)
        dt_expected = datetime.strptime(expected_str, DATE_FMT)

        diff = (dt_actual - dt_expected).total_seconds()

        if diff == 0:
            return True, "EXACT MATCH"
        else:
            return False, f"OFF by {diff} seconds ({actual_str} vs {expected_str})"
    except ValueError as e:
        return False, f"Format Error: {e}"


def check_cost(task_name, actual_str, expected_val):
    """Float comparison with tolerance."""
    try:
        val_actual = float(actual_str)
        if isclose(val_actual, expected_val, rel_tol=1e-5):
            return True, f"MATCH ({val_actual})"
        else:
            return False, f"MISMATCH (Got {val_actual}, Expected {expected_val})"
    except ValueError:
        return False, f"Invalid Number: {actual_str}"


def run_judge(csv_path):
    print("--- ISSUE #39: ULTRA-COMPLEX STRESS TEST JUDGE ---")
    print(f"Analyzing: {csv_path}\n")

    data = parse_csv(csv_path)
    passed = 0
    total = 3  # 3 checks

    # 1. Verify t_float End Time (The Precision Test)
    task_id = "t_float"
    if task_id in data:
        row = data[task_id]
        ok, msg = check_time(task_id, row['end'], GOLD_STANDARD[task_id]['end'])
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {task_id} End Time")
        print(f"       Details: {msg}")
        if ok:
            passed += 1
    else:
        print(f"[FAIL] {task_id} not found in CSV")

    # 2. Verify t_limit Cost (The Accounting Test)
    task_id = "t_limit"
    if task_id in data:
        row = data[task_id]
        cost_val = row.get('cost', '')
        if cost_val:
            ok, msg = check_cost(task_id, cost_val, GOLD_STANDARD[task_id]['cost'])
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {task_id} Cost Calculation")
            print(f"       Details: {msg}")
            if ok:
                passed += 1
        else:
            print(f"[FAIL] {task_id} Cost: No cost value in CSV")
    else:
        print(f"[FAIL] {task_id} not found in CSV")

    # 3. Verify t_finish (The ALAP Test)
    task_id = "t_finish"
    if task_id in data:
        row = data[task_id]
        ok, msg = check_time(task_id, row['end'], GOLD_STANDARD[task_id]['end'])
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {task_id} ALAP Deadline")
        print(f"       Details: {msg}")
        if ok:
            passed += 1
    else:
        print(f"[FAIL] {task_id} not found in CSV")

    print("-" * 50)
    if passed == total:
        print("RESULT: CERTIFIED (100% COMPLIANCE)")
        print("System is safe for deployment.")
    else:
        print(f"RESULT: FAILED ({passed}/{total})")
        print("DO NOT DEPLOY. FATAL SCHEDULING ERRORS DETECTED.")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python judge_ultra_math.py <output.csv>")
        sys.exit(1)
    run_judge(sys.argv[1])
