import pandas as pd
import sys

def check_jit(csv_path):
    print(f"--- JUDGING JIT (ALAP + CONTENTION): {csv_path} ---")

    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        print(f"FATAL: Read error {e}")
        sys.exit(1)

    # --- LOGIC TRACE ---
    # Deadline: Fri July 18, 16:00

    # 1. Packaging (8h)
    # Fri July 18: 08:00 - 16:00.
    exp_pack_start = "2025-07-18-08:00"
    exp_pack_end   = "2025-07-18-16:00"

    # 2. Assembly Slots (Reverse from Thu July 17, 16:00)
    # We have two 16h blocks (A and B). Order doesn't matter for correctness,
    # but they must be sequential.

    # Slot 1 (Latest): Thu July 17 + Wed July 16.
    # Start: Wed July 16, 08:00. End: Thu July 17, 16:00.
    slot1_start = "2025-07-16-08:00"
    slot1_end   = "2025-07-17-16:00"

    # Slot 2 (Earliest): Tue July 15 + Mon July 14.
    # Start: Mon July 14, 08:00. End: Tue July 15, 16:00.
    slot2_start = "2025-07-14-08:00"
    slot2_end   = "2025-07-15-16:00"

    errors = 0

    # Check Pack
    row_pack = df[df['id'] == 'delivery.pack']
    if row_pack.empty:
        print("FAIL: Pack task missing.")
        errors += 1
    else:
        s = row_pack.iloc[0]['start'].strip()
        e = row_pack.iloc[0]['end'].strip()
        if s == exp_pack_start and e == exp_pack_end:
            print(f"PASS: Packaging anchored correctly ({s} -> {e})")
        else:
            print(f"FAIL: Packaging ALAP logic.")
            print(f"  Expected: {exp_pack_start} -> {exp_pack_end}")
            print(f"  Got:      {s} -> {e}")
            errors += 1

    # Check Assemblies
    row_a = df[df['id'] == 'delivery.assemble_a']
    row_b = df[df['id'] == 'delivery.assemble_b']

    if row_a.empty or row_b.empty:
        print("FAIL: Assembly tasks missing.")
        sys.exit(1)

    start_a = row_a.iloc[0]['start'].strip()
    end_a   = row_a.iloc[0]['end'].strip()
    start_b = row_b.iloc[0]['start'].strip()
    end_b   = row_b.iloc[0]['end'].strip()

    # Verify Logic
    # One must be in Slot 1, One in Slot 2.
    is_a_slot1 = (start_a == slot1_start and end_a == slot1_end)
    is_a_slot2 = (start_a == slot2_start and end_a == slot2_end)

    is_b_slot1 = (start_b == slot1_start and end_b == slot1_end)
    is_b_slot2 = (start_b == slot2_start and end_b == slot2_end)

    if (is_a_slot1 and is_b_slot2) or (is_a_slot2 and is_b_slot1):
         print(f"PASS: Assemblies sequenced correctly back-to-back.")
         print(f"      Slot 1 (Wed-Thu): Occupied")
         print(f"      Slot 2 (Mon-Tue): Occupied")
    else:
        print("FAIL: Assembly Scheduling Collision or Calendar Error.")
        print(f"  A: {start_a} -> {end_a}")
        print(f"  B: {start_b} -> {end_b}")
        print(f"  Expected Slots: {slot1_start} (Wed) and {slot2_start} (Mon)")

        if start_a == start_b:
             print("  -> ERROR: Tasks are running in parallel (Resource Collision).")
        if "07-12" in start_a or "07-13" in start_a:
             print("  -> ERROR: You scheduled on a Weekend.")
        errors += 1

    if errors == 0:
        print("\nSUCCESS: ALAP Resource Leveling is Perfect.")
    else:
        print("\nFAIL: ALAP Logic Mismatch.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python judge_jit.py <your_output.csv>")
    else:
        check_jit(sys.argv[1])
