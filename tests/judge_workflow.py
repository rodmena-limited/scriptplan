import pandas as pd
import sys

def check_results(csv_path):
    print(f"Checking {csv_path} against Logic Rules...")

    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        print(f"FATAL: Could not read CSV. {e}")
        sys.exit(1)

    # --- EXPECTED VALUES ---

    # 1. PREP TASK
    # Intern (0.5 eff) doing 16h effort = 32h duration.
    # Starts Mon Nov 3, 09:00.
    # Mon (8h), Tue (8h), Wed (8h), Thu (8h).
    # Must end Thursday Nov 6 at 17:00.
    expected_prep_end = "2025-11-06-17:00"

    # 2. DEPLOY TASK
    # Admin (Tue-Sat shift). 16h effort.
    # Ready to start: Thu Nov 6, 17:00.
    # Admin Shift Status on Thu 17:00: Shift ends.
    # Next available slot: Fri Nov 7, 09:00.
    # Work: Fri (8h) + Sat (8h).
    # Must end Saturday Nov 8 at 17:00.
    expected_deploy_end = "2025-11-08-17:00"

    # --- VALIDATION LOOP ---

    errors = 0

    # Check Prep
    row_prep = df[df['id'] == 'migration.prep']
    if row_prep.empty:
        print("FAIL: Missing task 'migration.prep'")
        errors += 1
    else:
        got_end = row_prep.iloc[0]['end'].strip()
        if got_end == expected_prep_end:
            print(f"PASS [Prep]  : Ends {got_end} (Correctly handled 0.5 efficiency)")
        else:
            print(f"FAIL [Prep]  : Expected {expected_prep_end}, Got {got_end}")
            errors += 1

    # Check Deploy
    row_deploy = df[df['id'] == 'migration.deploy']
    if row_deploy.empty:
        print("FAIL: Missing task 'migration.deploy'")
        errors += 1
    else:
        got_end = row_deploy.iloc[0]['end'].strip()
        if got_end == expected_deploy_end:
            print(f"PASS [Deploy]: Ends {got_end} (Correctly handled Tue-Sat shift)")
        else:
            print(f"FAIL [Deploy]: Expected {expected_deploy_end}, Got {got_end}")
            errors += 1

    if errors == 0:
        print("\nSUCCESS: All logic checks passed.")
    else:
        print(f"\nFAILURE: {errors} errors detected.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python judge_workflow.py <output.csv>")
        sys.exit(1)
    check_results(sys.argv[1])
