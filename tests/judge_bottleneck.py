import pandas as pd
import sys

def check_bottleneck(csv_path):
    print(f"--- JUDGING: {csv_path} ---")

    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        print(f"FATAL: Read error {e}")
        sys.exit(1)

    # --- THE GROUND TRUTH LOGIC ---
    # I am embedding the correct timeline here.
    # Note: If your system matches this, it handles daily limits + holidays correctly.

    # 1. CODING
    # Starts Mon Jun 2, 09:00.
    # Effort 16h. Dev works 8h/day.
    # Mon: 8h. Tue: 8h.
    # Ends: Tuesday, June 3, 17:00.
    truth_code_end = "2025-06-03-17:00"

    # 2. REVIEW
    # Dependent on Coding (Ready Wed Jun 4, 09:00).
    # Resource: QA (Max 4h/day). Effort 12h.
    # Calendar Events: Wed Jun 4 is HOLIDAY.
    # Timeline:
    #   Wed Jun 4: Holiday (0h).
    #   Thu Jun 5: QA works 4h (Limit hit). 8h remain.
    #   Fri Jun 6: QA works 4h (Limit hit). 4h remain.
    #   Sat/Sun: Weekend.
    #   Mon Jun 9: QA works 4h (Limit hit). 0h remain.
    #   Time on Mon Jun 9: 09:00 -> 13:00.
    # Ends: Monday, June 9, 13:00.
    truth_review_end = "2025-06-09-13:00"

    # 3. DEPLOY
    # Dependent on Review (Ready Mon Jun 9, 13:00).
    # Resources: QA + Dev. Effort 4h.
    # Constraint Check:
    #   Dev is free Mon afternoon.
    #   QA has worked 4h on Mon Jun 9 (09:00-13:00).
    #   QA Daily Max is 4h. QA cannot work anymore on Monday.
    # Result: Task must be pushed to Tuesday.
    # Timeline:
    #   Tue Jun 10: Both work 09:00 -> 13:00.
    # Ends: Tuesday, June 10, 13:00.
    truth_deploy_end = "2025-06-10-13:00"

    expected = {
        "release.coding": truth_code_end,
        "release.review": truth_review_end,
        "release.deploy": truth_deploy_end
    }

    # --- COMPARISON ---
    errors = 0
    for task_id, expected_end in expected.items():
        row = df[df['id'] == task_id]
        if row.empty:
            print(f"FAIL: Task {task_id} not found in CSV.")
            errors += 1
            continue

        actual_end = row.iloc[0]['end'].strip()

        if actual_end == expected_end:
            print(f"PASS: {task_id} ends {actual_end}")
        else:
            print(f"FAIL: {task_id}")
            print(f"  Expected: {expected_end}")
            print(f"  Got:      {actual_end}")
            if task_id == "release.deploy":
                print("  (Hint: Did you let the QA Lead work >4h on Monday?)")
            errors += 1

    if errors == 0:
        print("\nSUCCESS: 100% Match.")
    else:
        print(f"\nFAIL: {errors} Errors.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python judge_bottleneck.py <your_output.csv>")
    else:
        check_bottleneck(sys.argv[1])
