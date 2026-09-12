#!/usr/bin/env bash
# Everything a change has to pass, in the order that fails fastest.
#
#   ./scripts/ci.sh              # lint, types, tests, probes
#   SKIP_SLOW=0 ./scripts/ci.sh  # also run the performance probes
#
# Used by ci.rodmena.co.uk and runnable by hand. It does not assume a
# virtualenv: set PYTHON to whichever interpreter should be tested.
set -uo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON="${PYTHON:-python3}"
SKIP_SLOW="${SKIP_SLOW:-1}"
export PYTHONPATH="$PWD:${PYTHONPATH:-}"

failures=0
step() {
  local name="$1"; shift
  echo "=== $name"
  if "$@"; then
    echo "--- $name: ok"
  else
    echo "--- $name: FAILED"
    failures=$((failures + 1))
  fi
  echo
}

step "ruff (lint)"        "$PYTHON" -m ruff check scriptplan tests audit
step "ruff (format)"      "$PYTHON" -m ruff format --check scriptplan
step "mypy (types)"       "$PYTHON" -m mypy scriptplan
step "file size cap"      "$PYTHON" scripts/check_file_sizes.py
step "pytest"             "$PYTHON" -m pytest -q tests

echo "=== audit probes"
if SCRIPTPLAN_PROBE_PYTHON="$PYTHON" SCRIPTPLAN_PROBE_SLOW="$([ "$SKIP_SLOW" = "1" ] && echo 0 || echo 1)" \
   audit/evaluations/run_all.sh; then
  echo "--- audit probes: ok"
else
  echo "--- audit probes: FAILED"
  failures=$((failures + 1))
fi

echo
if [ "$failures" -ne 0 ]; then
  echo "RESULT: $failures step(s) failed"
  exit 1
fi
echo "RESULT: all steps passed"
