<p align="center">
  <img src="https://raw.githubusercontent.com/rodmena-limited/scriptplan/main/icons/logo.svg" alt="ScriptPlan" width="400"/>
</p>

# ScriptPlan

![Tests](https://img.shields.io/badge/tests-411_passing-success?style=for-the-badge)
![Probes](https://img.shields.io/badge/audit_probes-67_passing-success?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=for-the-badge)
![Licence](https://img.shields.io/badge/licence-Apache--2.0-lightgrey?style=for-the-badge)

A precise project scheduling engine with minute-level accuracy for resource allocation and dependency management. The syntax is compatible with TaskJuggler (.tjp files).

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
- Contention is resolved by priority, then criticalness, then declaration order.
- The declared project period is never rewritten. A task that does not fit is
  reported, with its name and the reason.
- Scheduling the same project twice produces the same dates and the same bookings.
- `maxgapduration`, `maxgaplength`, `maxstart`, `minstart`, `maxend` and `minend`
  are checked once the schedule is complete, and a violation is an error.

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
- `onstart` dependencies are read as "the dependent task must finish before the
  predecessor starts", which is ScriptPlan's own reading rather than
  TaskJuggler's start-to-start one.

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

ScriptPlan references [TaskJuggler](https://taskjuggler.org/) solely for **file format compatibility**. We have not used, modified, or copied any TaskJuggler source code. ScriptPlan is an independent, clean-room implementation.

- The `.tjp` file format is documented publicly and widely used in the project management community
- All scheduling algorithms, parser, and report generation in ScriptPlan are original implementations
- TaskJuggler is mentioned only to indicate that ScriptPlan can read the same project file format

If you're looking for the original TaskJuggler with its full feature set including interactive HTML reports and GUI tools, please visit [taskjuggler.org](https://taskjuggler.org/).

## Why ScriptPlan?

This scheduler is part of Highway Workflow Engine's worker capacity management system. I decided to open-source it for the community to benefit from its precise scheduling capabilities. Thanks to TaskJuggler's established syntax, users can easily adopt ScriptPlan without learning a new format.

Yours,
Farshid.
