import pandas as pd
import sys
from datetime import datetime

def measure_temperature(csv_path):
    print(f"--- MEASURING INGOT TEMPERATURE: {csv_path} ---")

    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        print(f"FATAL: Read error {e}")
        sys.exit(1)

    # 1. Extract Timestamps
    row_heat = df[df['id'] == 'process.heat']
    row_forge = df[df['id'] == 'process.forge']

    if row_heat.empty or row_forge.empty:
        print("FAIL: Tasks missing.")
        sys.exit(1)

    heat_end_str = row_heat.iloc[0]['end'].strip()
    forge_start_str = row_forge.iloc[0]['start'].strip()

    fmt = "%Y-%m-%d-%H:%M"
    t_heat_end = datetime.strptime(heat_end_str, fmt)
    t_forge_start = datetime.strptime(forge_start_str, fmt)

    # 2. Calculate Gap
    gap_seconds = (t_forge_start - t_heat_end).total_seconds()
    gap_hours = gap_seconds / 3600.0

    print(f"Heat Ends:   {heat_end_str}")
    print(f"Forge Start: {forge_start_str}")
    print(f"Gap:         {gap_hours:.2f} hours")

    # 3. Verify Constraint
    if gap_hours < 0:
        print("\nFAIL: TIME PARADOX. Forge started before Heat finished.")
        sys.exit(1)

    if gap_hours <= 1.0:
        print("\n" + "="*50)
        print("SUCCESS: THERMAL INTEGRITY MAINTAINED.")
        print("The system intelligently delayed the first task")
        print("to synchronize with the downstream bottleneck.")
        print("="*50)
    else:
        print("\nFAIL: THERMAL SHOCK.")
        print("The metal cooled down. The ingot cracked.")
        print(f"Allowed Gap: 1.0h. Actual Gap: {gap_hours:.2f}h.")
        print("Hint: Your scheduler ran 'Heat' too early.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python judge_thermal.py <your_output.csv>")
    else:
        measure_temperature(sys.argv[1])
