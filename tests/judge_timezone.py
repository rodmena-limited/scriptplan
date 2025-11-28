import pandas as pd
import sys

def check_timezone(csv_path):
    print(f"--- JUDGING GLOBAL TIMEZONES: {csv_path} ---")

    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        print(f"FATAL: Read error {e}")
        sys.exit(1)

    # --- GROUND TRUTH (IN UTC) ---

    # 1. Tokyo Task
    # Shift: 09:00-18:00 JST = 00:00-09:00 UTC.
    # Effort: 9h.
    # Fits exactly into one day.
    # Start: 2025-05-01 00:00 UTC.
    # End:   2025-05-01 09:00 UTC.
    expected_jp_end = "2025-05-01-09:00"

    # 2. New York Task
    # Dependency Ready: 09:00 UTC.
    # NY Local Time at 09:00 UTC = 05:00 AM (EDT, UTC-4).
    # NY Shift Starts: 09:00 NY = 13:00 UTC.
    # Waiting Time: 4 Hours (09:00 UTC -> 13:00 UTC).
    # Actual Start: 13:00 UTC.
    # Effort: 4h.
    # 13:00 UTC + 4h = 17:00 UTC.
    expected_ny_start = "2025-05-01-13:00"
    expected_ny_end   = "2025-05-01-17:00"

    errors = 0

    # Check Tokyo
    row_jp = df[df['id'] == 'follow_sun.step1_jp']
    if row_jp.empty:
        print("FAIL: Tokyo task missing.")
        errors += 1
    else:
        got = row_jp.iloc[0]['end'].strip()
        if got == expected_jp_end:
            print(f"PASS: Tokyo finishes correctly at {got} UTC")
        else:
            print(f"FAIL: Tokyo Task.")
            print(f"  Expected End (UTC): {expected_jp_end}")
            print(f"  Got:                {got}")
            errors += 1

    # Check NY
    row_ny = df[df['id'] == 'follow_sun.step2_ny']
    if row_ny.empty:
        print("FAIL: NY task missing.")
        errors += 1
    else:
        start = row_ny.iloc[0]['start'].strip()
        end = row_ny.iloc[0]['end'].strip()

        if start == expected_ny_start and end == expected_ny_end:
            print(f"PASS: Global Handoff successful.")
            print(f"      Tokyo Finished: 09:00 UTC")
            print(f"      NY Started:     13:00 UTC (Gap Correctly Calculated)")
            print(f"      NY Finished:    17:00 UTC")
        else:
            print(f"FAIL: Timezone Handoff Error.")
            print(f"  Expected Start: {expected_ny_start}")
            print(f"  Got Start:      {start}")

            if start == "2025-05-01-09:00":
                print("  -> FATAL: You ignored the timezone offset! NY cannot work at 4 AM.")
            errors += 1

    if errors == 0:
        print("\nSUCCESS: SYSTEM IS GLOBAL-READY.")
    else:
        print("\nFAIL: TIMEZONE HANDLING INCORRECT.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python judge_timezone.py <your_output.csv>")
    else:
        check_timezone(sys.argv[1])
