<p align="center">
  <img src="https://raw.githubusercontent.com/rodmena-limited/scriptplan/main/icons/logo.svg" alt="ScriptPlan" width="400"/>
</p>

# ScriptPlan

![Tests](https://img.shields.io/badge/tests-496_passing-success?style=for-the-badge)
![Probes](https://img.shields.io/badge/audit_probes-85_passing-success?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=for-the-badge)
![Licence](https://img.shields.io/badge/licence-Apache--2.0-lightgrey?style=for-the-badge)

A precise project scheduling engine with minute-level accuracy for resource allocation and dependency management. It reads projects written in the .tjp format.

## Installation

```bash
pip install scriptplan
```

## Quick Start

### Report Generation (Unix-style)

```bash
# Generate JSON report to stdout
plan report project.tjp

# Generate CSV report
plan report --csv project.tjp

# Save to file
plan report project.tjp > output.json
plan report --csv project.tjp > output.csv

# Read from stdin
cat project.tjp | plan report
plan report - < project.tjp

# Pipe to other tools
plan report project.tjp | jq '.data[0]'
plan report --csv project.tjp | csvkit

# Process multiple files
for f in projects/*.tjp; do
  plan report "$f" | jq -r '.report_id'
done
```

**Output Format** (JSON):
```json
{
  "data": [
    {
      "id": "project.task1",
      "start": "2024-01-01-09:00",
      "end": "2024-01-05-17:00"
    }
  ],
  "columns": ["id", "start", "end"],
  "report_id": "ea3f901dd6426dfa58288d945819c75485fd9ff1875db59def350f219e2d62ca"
}
```

**Features**:
- Output to stdout (Unix philosophy)
- Messages to stderr
- SHA256 `report_id` over the rendered result, so it changes when the schedule does
- Lowercase column names
- No HTML metadata
- No file pollution (uses temp directories)
- Separate processes do not collide: temporary files and directories are unique per run

### Python API

```python
from scriptplan.parser.tjp_parser import ProjectFileParser

parser = ProjectFileParser()
project = parser.parse(open('project.tjp').read())

# Access scheduled tasks
for task in project.tasks:
    if task.leaf():
        start = task.get('start', 0)
        end = task.get('end', 0)
        print(f"{task.id}: {start} -> {end}")
```

Projects can be parsed and scheduled in parallel threads. Messages and the error
count belong to the thread that produced them, so read
`get_message_handler_instance().messages` in the thread that called `schedule()`.

## What is verified

Each behaviour below has a probe in `audit/evaluations/` that drives ScriptPlan
through its own API or CLI and asserts the result. They run as part of the test
suite, and can be run on their own against an installed release:

```bash
audit/evaluations/run_all.sh
```

**Time**

- Dates are read in the project's timezone and scheduled in UTC; reports convert back.
- Resource shifts follow their own timezone across daylight-saving changes in both directions.
- A working-hours interval that crosses midnight applies to the following day.
- Slot size is derived from the times a project uses, so `start 09:30` is honoured
  exactly and a shift of `08:13 - 11:59, 13:07 - 17:47` yields its true 8h26m a day.
  `timingresolution` overrides this.

**Units**

- Calendar time (`duration`, `gapduration`) and working time (`effort`, `length`,
  `gaplength`) are distinguished, with working time derived from
  `dailyworkinghours` and `yearlyworkingdays`. `m` means months; `min` means minutes.

**Resources**

- `effort` is person-time: two resources available in a slot contribute two
  slots of it. `mandatory` requires a resource for the task to progress at all;
  `persistent` keeps the one first chosen; `alternative` falls back.
- `dailymax`, `weeklymax`, `monthlymax`, `maximum` and their `min` counterparts
  block at the cap **and** release in the next period. Periods are counted in the
  resource's own calendar, and a cap smaller than one slot is honoured exactly.

**Scheduling**

- ASAP and ALAP, including chains that mix the two.
- A task scheduled as late as possible ends by the earliest of its own `end`, the
  start of each successor (less any gap that successor asks for) and the project
  end. With none of these but a successor scheduled as soon as possible that
  states no start, it is scheduled as soon as possible instead, with a warning.
- Contention is resolved by priority, then criticalness, then declaration order.
- The declared project period is never rewritten. A task that does not fit is
  reported, with its name and the reason. A date stated outside the period is an
  error.
- Scheduling the same project twice produces the same dates and the same bookings.
- A stated `start` or `end` that the schedule cannot keep, and a task that would
  start before something it depends on finishes, are errors.
- `length` and `gaplength` count the project's working time, not a resource's:
  a resource on longer hours does not shorten the gap.
- `maxgapduration`, `maxstart`, `minstart`, `maxend` and `minend` are checked
  once the schedule is complete, and a violation is an error. (`maxgaplength` is
  not part of the syntax and is refused when parsed.)

**Honesty**

- A project that cannot be scheduled exits non-zero and says why. A dependency
  cycle is rejected before scheduling, naming the cycle.
- An attribute or reference the parser cannot place is an error, never a silent
  drop.
- `report_id` is a SHA-256 of the rendered result, so it differs when the
  schedule differs.

## Known limits

- `include`, `supplement`, `leaveallowance` and `statussheet` are not implemented.
- Output formats are JSON and CSV. `ical`, `tjp`, `niku` and MS Project XML are
  rejected at parse time rather than silently producing nothing.
- Accounts are parsed but not yet modelled, so `chargeset` and `charge` record an
  amount without posting it anywhere.
- A task reference is first looked up from the referring task's scope, one level
  up for each `!`. When that finds nothing but exactly one task in the project has
  that id, the reference binds to it, so `depends !!pack` inside `delivery` finds
  `delivery.pack`. When two tasks could be meant, the file is refused and both are
  named.
- `onstart` on a dependency means start-to-start for a task scheduled as soon as
  possible: it may start once the predecessor starts. For a task scheduled as
  late as possible it means the task must finish before the predecessor starts,
  which is ScriptPlan's own reading.

## Example Project

```
project "Manufacturing" 2025-07-01 +1m {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  scheduling alap
}

shift factory_hours "Factory Hours" {
  workinghours mon - fri 08:00 - 16:00
}

resource machine "Press" {
  workinghours factory_hours
}

task delivery "Product Launch" {
  end 2025-07-18-16:00

  task pack "Packaging" {
    effort 8h
    allocate machine
  }

  task assemble_b "Body Assembly" {
    effort 16h
    allocate machine
    depends !!pack { onstart }
  }

  task assemble_a "Engine Assembly" {
    effort 16h
    allocate machine
  }
}

task connection_setup "Logic" {
  task set_deps "Apply" {
    depends !delivery.assemble_a, !delivery.assemble_b
    precedes !delivery.pack
  }
}

taskreport output "output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

This project schedules backward from the delivery deadline (ALAP mode). The scheduler:

1. Anchors packaging to end at 16:00 on July 18
2. Schedules both assembly tasks to complete before packaging starts
3. Resolves resource contention (single machine) by sequencing assemblies back-to-back
4. Respects weekend boundaries (Mon-Fri working hours)

Result:
```
delivery.pack:       2025-07-18-08:00 -> 2025-07-18-16:00
delivery.assemble_a: 2025-07-14-08:00 -> 2025-07-15-16:00
delivery.assemble_b: 2025-07-16-08:00 -> 2025-07-17-16:00
```

## License

Apache-2.0

## Acknowledgments

ScriptPlan reads the .tjp project file format. It contains no code from any other
scheduler: the parser, the scheduling algorithms and the reports are its own.

## Why ScriptPlan?

This scheduler is part of Highway Workflow Engine's worker capacity management system. I decided to open-source it for the community to benefit from its precise scheduling capabilities. Because it reads the established .tjp syntax, users can adopt ScriptPlan without learning a new format.

Yours,
Farshid.
