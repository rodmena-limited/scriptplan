import pandas as pd
import sys
from datetime import datetime, timedelta

# --- CONFIGURATION ---

# 1. Calendars
HOLIDAYS = [datetime(2025, 9, 5).date()]
ARCH_VACATION = [datetime(2025, 9, 11).date(), datetime(2025, 9, 12).date()]

def is_holiday(dt):
    return dt.date() in HOLIDAYS

def is_weekend(dt):
    return dt.weekday() >= 5 # 5=Sat, 6=Sun

# 2. Logic Engines for Specific Resources

def add_working_hours_standard(start_dt, hours_needed, exclude_dates=[]):
    """
    Standard Shift: 09:00 - 17:00 (8h). Mon-Fri.
    """
    cursor = start_dt
    remaining = hours_needed

    # Align to start of shift if before
    if cursor.hour < 9:
        cursor = cursor.replace(hour=9, minute=0)
    elif cursor.hour >= 17:
        cursor = cursor + timedelta(days=1)
        cursor = cursor.replace(hour=9, minute=0)

    while remaining > 0:
        # Check if today is workable
        if is_weekend(cursor) or is_holiday(cursor) or (cursor.date() in exclude_dates):
            # Skip to next day 09:00
            cursor = cursor + timedelta(days=1)
            cursor = cursor.replace(hour=9, minute=0)
            continue

        # We are in a valid day. We are currently at 'cursor'.
        # Work ends at 17:00 today.
        end_of_shift = cursor.replace(hour=17, minute=0)

        # Calculate capacity left today
        capacity = (end_of_shift - cursor).total_seconds() / 3600.0

        if capacity <= 0:
            # Shift done, move to next day
            cursor = cursor + timedelta(days=1)
            cursor = cursor.replace(hour=9, minute=0)
            continue

        if capacity >= remaining:
            cursor += timedelta(hours=remaining)
            remaining = 0
        else:
            remaining -= capacity
            # Move to next day start
            cursor = cursor + timedelta(days=1)
            cursor = cursor.replace(hour=9, minute=0)

    return cursor

def add_working_hours_night(start_dt, hours_needed):
    """
    Night Shift: 22:00 - 06:00 (8h). Mon-Fri.
    Shift starts Mon 22:00, ends Tue 06:00.
    """
    cursor = start_dt
    remaining = hours_needed

    # Logic: If we are between 06:00 and 22:00, jump to 22:00.
    # If we are in a shift, consume it.

    while remaining > 0:
        # 1. Normalize cursor to a valid start block or current position
        if 6 <= cursor.hour < 22:
            cursor = cursor.replace(hour=22, minute=0)

        # Check if valid night (Mon-Fri start)
        # However, a shift starting Fri 22:00 ends Sat 06:00. That is valid.
        # A shift starting Sat 22:00 is invalid.
        # We need to check the "start of the shift" day.

        current_shift_start_day = cursor
        if cursor.hour < 6:
            # We are in the AM part of the shift, the shift started yesterday
            current_shift_start_day = cursor - timedelta(days=1)

        if current_shift_start_day.weekday() >= 5 or is_holiday(current_shift_start_day):
            # Non-working night. Advance to next potential start (22:00)
            # If we are at 04:00 Sat, we need to get to Mon 22:00 or Sun 22:00?
            # Standard TJP "Mon - Fri" usually means shifts starting on these days.
            cursor = cursor.replace(hour=22, minute=0) + timedelta(days=1)
            continue

        # Valid shift.
        # Determine end of this specific shift block (06:00 next day)
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
            # Jump to next shift start (22:00 today or tomorrow depending on logic)
            # Easiest: Set to end_of_shift (which is 06:00), loop will handle jump to 22:00
            cursor = end_of_shift

    return cursor

# --- 3. GROUND TRUTH CALCULATION ---

def calculate_ground_truth():
    print("Computing Expected Mathematical Schedule...")

    # TASK 1: Design
    # Starts Sep 1, 09:00. 40h effort. Std Shift. Sep 5 is Holiday.
    # Mon(8) + Tue(8) + Wed(8) + Thu(8) + Fri(Holiday) + Mon(8)
    # Should end Sep 8 at 17:00.
    t1_start = datetime(2025, 9, 1, 9, 0)
    t1_end = add_working_hours_standard(t1_start, 40)

    # TASK 2: Demo
    # Depends on T1 End (Sep 8, 17:00).
    # Night Shift (Start 22:00). 16h effort.
    # Sep 8 is Monday.
    # Shift 1: Sep 8 22:00 -> Sep 9 06:00 (8h)
    # Shift 2: Sep 9 22:00 -> Sep 10 06:00 (8h)
    # Should end Sep 10 at 06:00.
    t2_start = t1_end # Logical dependency
    t2_end = add_working_hours_night(t2_start, 16)

    # TASK 3: Wiring
    # Depends on T2 Start (Start-Start) + 24h gap.
    # T2 actual start: Sep 8, 22:00 (First night shift).
    # Gap: 24h elapsed.
    # Ready to Start: Sep 9, 22:00.
    # Resource: Junior (0.8 eff). Effort 32h.
    # Real Hours needed = 32 / 0.8 = 40h.
    # Shift: Standard (09:00-17:00).
    # Ready Sep 9 (Tue) 22:00. Next work slot: Sep 10 (Wed) 09:00.
    # Wed(8) + Thu(8) + Fri(8) + Sat/Sun(Skip) + Mon(8) + Tue(8).
    # Note: Arch vacation (Sep 11-12) does NOT affect Electrician.
    # Holiday Sep 5 is passed.
    # Work Days: Sep 10, 11, 12, 15, 16.
    # Should end Sep 16 at 17:00.

    # Note on T2 Start: T2 *could* start at 17:00 logically, but physically starts at 22:00.
    # TJP "depends !demo { onstart }" usually links to the scheduled start.
    # If the tool aligns start to shift, it is Sep 8 22:00.
    t3_ready = datetime(2025, 9, 8, 22, 0) + timedelta(hours=24) # Sep 9, 22:00
    t3_end = add_working_hours_standard(t3_ready, 40) # 40h adjusted effort

    # The tool might report start time as the first working minute (Sep 10 09:00)
    # or the ready time (Sep 9 22:00). We usually compare End times for correctness.
    t3_start_work = datetime(2025, 9, 10, 9, 0)

    return [
        {"id": "bhs.design", "end": t1_end},
        {"id": "bhs.demo",   "end": t2_end},
        {"id": "bhs.wiring", "end": t3_end},
    ]

# --- 4. COMPARISON ---

def judge(csv_path):
    truth = calculate_ground_truth()

    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    print("\n--- RESULTS ---")
    failures = 0

    fmt = "%Y-%m-%d-%H:%M"

    for item in truth:
        row = df[df['id'] == item['id']]
        if row.empty:
            print(f"MISSING: {item['id']}")
            failures += 1
            continue

        csv_end_str = row.iloc[0]['end'].strip()
        expected_str = item['end'].strftime(fmt)

        if csv_end_str != expected_str:
            print(f"FAIL {item['id']}: Expected End {expected_str}, Got {csv_end_str}")
            failures += 1
        else:
            print(f"PASS {item['id']}: Ends {expected_str}")

    if failures == 0:
        print("\nSUCCESS: System logic matches valid scenarios.")
    else:
        print(f"\nFAILURE: {failures} mismatches found.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python judge_complex.py <output.csv>")
    else:
        judge(sys.argv[1])
