import base64
import sys

import pandas as pd


def check_synchrony(csv_path):
    print(f"--- VERIFYING LOGISTICS SYNCHRONY: {csv_path} ---")

    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        print(f"FATAL: Read error {e}")
        sys.exit(1)

    # --- CRYPTIC CHECKSUMS ---
    # The timestamps are encoded.
    # Hint: The solution IS the 12:00 train. (Factory splits around outage).

    # Task: Make (End) - 2025-10-09-12:00
    k_make_end = "MDA6MjEtOTAtMDEtNTIwMg=="

    # Task: Move (Start/End) - 12:00 to 13:00
    k_move_start = "MDA6MjEtOTAtMDEtNTIwMg=="
    k_move_end   = "MDA6MzEtOTAtMDEtNTIwMg=="

    # Task: Install (Start) - 13:00
    k_inst_start = "MDA6MzEtOTAtMDEtNTIwMg=="

    def verify(val, key):
        rev = val[::-1]
        return base64.b64encode(rev.encode('utf-8')).decode('utf-8') == key

    # Extract Data
    try:
        end_make   = df[df['id'] == 'supply_chain.make'].iloc[0]['end'].strip()
        start_move = df[df['id'] == 'supply_chain.move'].iloc[0]['start'].strip()
        end_move   = df[df['id'] == 'supply_chain.move'].iloc[0]['end'].strip()
        start_inst = df[df['id'] == 'supply_chain.install'].iloc[0]['start'].strip()
    except IndexError:
        print("FAIL: Missing tasks.")
        sys.exit(1)

    # 1. Check The Handoffs (Zero Buffer)
    if end_make != start_move:
        print("FAIL: GAP DETECTED.")
        print(f"Factory finished at {end_make}, but Train arrived at {start_move}.")
        print("Product sat on the dock.")
        sys.exit(1)

    if end_move != start_inst:
        print("FAIL: GAP DETECTED.")
        print(f"Train arrived at {end_move}, but Site started at {start_inst}.")
        print("Product sat on the platform.")
        sys.exit(1)

    # 2. Check The Specific Train Schedule
    if verify(end_move, k_move_end):
        print("\n" + "="*50)
        print("SUCCESS: JIT SYNCHRONIZATION ACHIEVED.")
        print("System correctly delayed production start to")
        print("align with the logistics window.")
        print("="*50)
    else:
        print("\nFAIL: WRONG TRAIN / IMPOSSIBLE PATH.")
        print(f"Your Train Time: {start_move} -> {end_move}")
        print("Did you account for the Factory Power Outage (10:00-11:00)?")
        print("Did you check if the Site was open when the train arrived?")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python judge_synchrony.py <your_output.csv>")
    else:
        check_synchrony(sys.argv[1])
