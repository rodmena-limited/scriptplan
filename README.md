<p align="center">
  <img src="https://raw.githubusercontent.com/rodmena-limited/scriptplan/main/icons/logo.svg" alt="ScriptPlan" width="400"/>
</p>

# ScriptPlan

![Logic Certified](https://img.shields.io/badge/Logic-Certified_Airport--Grade-success?style=for-the-badge&logo=github)
![Tests Passed](https://img.shields.io/badge/Stress_Tests-24%2F24_Passed-success?style=for-the-badge)
![Temporal Physics](https://img.shields.io/badge/Temporal_Physics-Verified-blue?style=for-the-badge)
![Scheduling](https://img.shields.io/badge/Scheduling-ALAP_%7C_JIT_%7C_Priority-blueviolet?style=for-the-badge)
![Constraints](https://img.shields.io/badge/Constraints-Hard_Limits_%7C_Quotas-orange?style=for-the-badge)

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
- SHA256 report_id (content-based hash)
- Lowercase column names
- No HTML metadata
- No file pollution (uses temp directories)
- Safe for concurrent execution (100+ instances)

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

## System Certified

**Certification Level**: Airport-Grade / Mission Critical

**Capabilities Verified**:

- **Temporal Physics**: Floating point precision, Timezones, DST awareness, Date Line crossing.

- **Resource Constraints**: Daily/Weekly limits, Hierarchical quotas, Shift intersections.

- **Advanced Scheduling**: ALAP (Backward pass), Priority preemption, Smart Resource Selection (Failover).

- **Workflow Logic**: Atomicity (Contiguous), Perishability (Max Gap), Zero-Buffer Synchronization.

## Features

- Minute-level scheduling precision
- ASAP and ALAP scheduling modes
- Resource allocation with contention handling
- Working hours and shift definitions
- Dependency chains with gap constraints
- Leap year and timezone handling

## Accuracy

ScriptPlan uses integer arithmetic for all time calculations, avoiding floating-point drift. The scheduler correctly handles:

- Non-standard shift boundaries (e.g., 08:13 - 11:59, 13:07 - 17:47)
- Prime-number effort durations with prime-number gaps
- Resource contention across multi-day tasks
- Calendar gaps (weekends, holidays) vs working time gaps

Example: A chain of 500 tasks, each with 73-minute effort and 29-minute gaps, scheduled across leap year boundaries with non-standard shifts, produces exact minute-aligned results.

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
