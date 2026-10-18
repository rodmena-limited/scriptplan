# Examples

Each project here comes with the answer it should produce.

- `showcase/` holds the 24 demonstration projects that `SHOWCASE.md` is built from:
  airport upgrades, a 500-task chain on an irregular shift, time zones, quotas,
  limits, mixed forward and backward plans.
- `edge_cases/` holds one small project for each scheduling pattern that has gone
  wrong in a release, such as several tasks sharing one hour of one person, a
  backward task before a successor that starts mid-hour, or a declared start inside
  a slot.
- `simple.tjp` is a minimal starting point.

## The answers

Next to every project is `<name>.expected.csv`, with the start and end of every task
in the project's own time zone, to the second, and `<name>.expected.md`, which shows
how each date was worked out.

The answers were derived by hand from the project file and the documented semantics,
without running ScriptPlan. Where an hour-level reference scheduler accepts the file,
its result was compared too. Where the two disagree, the reason is recorded: it books
whole slots, so it can end a task later than ScriptPlan, which places work to the
minute.

In three projects the hand derivation and the engine first disagreed, and the notes
record how each was settled. In `thermal` and `quota` the project's own header and its
long-standing test specify the engine's answer. In `jit_supply` the engine moved in
0.10.2 and two independent sources confirm the new date.

## Checking them

```bash
pytest tests/test_examples.py                                  # this checkout
SCRIPTPLAN_EXAMPLES_PYTHON=/path/to/venv/bin/python \
    pytest tests/test_examples.py                              # an installed release
```

Each project runs through the `plan` CLI in a fresh process, and every task is
compared with its answer. These answers are not the golden snapshots in
`tests/golden/`. A snapshot records what the engine produced last time and catches a
change; these files record what it should produce and catch an error.
