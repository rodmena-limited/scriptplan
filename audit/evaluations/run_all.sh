#!/usr/bin/env bash
# Run the ScriptPlan audit probe harness.
#
#   ./run_all.sh                      # safe set, against whatever `import scriptplan` resolves to
#   SCRIPTPLAN_PROBE_SLOW=1 ./run_all.sh   # add the performance probes (minutes, still read-only)
#   SCRIPTPLAN_PROBE_PYTHON=/path/to/venv/bin/python ./run_all.sh
#
# Every probe is read-only: it parses and schedules in-process or runs the
# `plan` CLI on a temporary file. Nothing writes to the repository, and there
# is no destructive probe, so the default run is safe against any target.
#
# Exits non-zero if any probe FAILs or ERRORs.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

PY="${SCRIPTPLAN_PROBE_PYTHON:-python3}"
export PYTHONPATH="$here:${PYTHONPATH:-}"

probes=(
  probe_error_propagation.py
  probe_parser_strictness.py
  probe_units.py
  probe_calendar.py
  probe_precision.py
  probe_limits.py
  probe_effort_semantics.py
  probe_slot_sharing.py
  probe_placement.py
  probe_alap.py
  probe_idempotency.py
  probe_priority.py
  probe_reports.py
  probe_showcase_regression.py
)
if [ "${SCRIPTPLAN_PROBE_SLOW:-0}" = "1" ]; then
  probes+=(probe_scale.py)
fi

echo "ScriptPlan audit harness"
echo "interpreter: $PY"
"$PY" -c 'import scriptplan, os; print("package:    " + os.path.dirname(scriptplan.__file__))' || {
  echo "FATAL: cannot import scriptplan with $PY" >&2
  exit 2
}
echo

failed=0
declare -a summary
for probe in "${probes[@]}"; do
  output="$("$PY" "$probe" 2>&1)"
  status=$?
  echo "$output"
  echo
  line="$(printf '%s\n' "$output" | grep -E '^SUMMARY ' | tail -1)"
  if [ $status -ne 0 ]; then
    failed=$((failed + 1))
    summary+=("FAIL  $probe  ${line:-(no summary line; probe crashed)}")
  else
    summary+=("ok    $probe  ${line:-}")
  fi
done

echo "======================================================================"
echo "Probe files:"
for line in "${summary[@]}"; do echo "  $line"; done
echo "======================================================================"
if [ "$failed" -ne 0 ]; then
  echo "RESULT: $failed probe file(s) reported failures"
  exit 1
fi
echo "RESULT: all probe files passed"
