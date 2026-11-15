<p align="center">
  <img src="https://raw.githubusercontent.com/rodmena-limited/scriptplan/main/icons/logo.svg" alt="ScriptPlan" width="400"/>
</p>

# ScriptPlan

![Tests](https://img.shields.io/badge/tests-581_passing-success?style=for-the-badge)
![Probes](https://img.shields.io/badge/audit_probes-145_passing-success?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=for-the-badge)
![Licence](https://img.shields.io/badge/licence-Apache--2.0-lightgrey?style=for-the-badge)

ScriptPlan is a project scheduler. It reads a project written in the .tjp format, works
out when each task runs and who does it, and prints the result as JSON or CSV. Times are
kept to the minute.

## Installation

```bash
pip install scriptplan
```

It needs Python 3.9 or later.

## Command line

`plan report` reads a project file and writes the report to standard output.

```bash
plan report project.tjp               # JSON
plan report --csv project.tjp         # CSV
plan report - < project.tjp           # read the project from standard input
cat project.tjp | plan report         # the same, from a pipe
plan report project.tjp > plan.json   # keep the result

# one id per project in a directory
for f in projects/*.tjp; do
  plan report "$f" | jq -r '.report_id'
done
```

The JSON looks like this:

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

The columns come from the `taskreport` in the project file. A file with no report gets
the id, start and end of each task.

Progress messages, warnings and errors go to standard error. The report on standard
output can be piped into `jq` or saved to a file as it is, and its column names are
lowercase in the JSON. A project that cannot be scheduled exits with a non-zero status
and says why.

`report_id` is a SHA-256 of the rendered result. The same schedule gives the same id,
and a different schedule gives a different one.

`plan report` writes nothing to the working directory. Several runs can work at once
because each uses a temporary directory of its own.

## Python API

```python
from scriptplan.core.timezones import from_utc
from scriptplan.parser.tjp_parser import ProjectFileParser

parser = ProjectFileParser()
project = parser.parse(open('project.tjp').read())
zone = project['timezone']

# Access scheduled tasks
for task in project.tasks:
    if task.leaf():
        start = from_utc(task.get('start', 0), zone)
        end = from_utc(task.get('end', 0), zone)
        print(f"{task.id}: {start} -> {end}")
```

`task.get('start', 0)` and `task.get('end', 0)` return naive datetimes in UTC,
whatever the project's timezone. A task that starts at 00:00 in London in June
reads 23:00 the day before. `from_utc` gives the time in the project's zone, which
is what the reports print.

Projects can be parsed and scheduled in parallel threads. Messages and the error
count belong to the thread that produced them. Read
`get_message_handler_instance().messages` in the thread that called `schedule()`.

## What it does

Each statement in this section is checked by a probe in `audit/evaluations/`. A probe
runs ScriptPlan through its API or command line and compares what comes back with the
expected result. The probes run with the test suite, and you can run them against an
installed release:

```bash
audit/evaluations/run_all.sh
```

### Time

- Dates in the file are in the project's timezone. Scheduling is done in UTC and the
  reports convert back.
- A project's working week is Monday to Friday, 09:00 to 17:00, in the project's
  timezone. `length`, `gaplength` and a resource that states no hours use it.
- A `workinghours` line replaces the hours of the days it names. The other days stay as
  they were, and `workinghours fri off` closes a day. A shift starts from the project's
  week. A resource starts from its parent resource's week, or from the project's when it
  has no parent.
- `workinghours <shift id>` puts a resource on a shift. Its week becomes the shift's, and
  the shift's `leaves` apply to it.
- A resource's hours are read in its own `timezone` when it has one and in the project's
  when it does not. They stay at the same local time when the clocks change, in spring
  and in autumn.
- An interval that ends at or before its start runs past midnight. `fri 22:00 - 06:00` is
  Friday evening and Saturday morning, and both halves belong to Friday's line.
- A global `leaves` or `vacation` closes the calendar for everyone, for whole days or for
  part of one, whatever kind of leave it is.
- ScriptPlan picks the slot size from the times the project uses. `start 09:30` is kept
  exactly, and a shift of `08:13 - 11:59, 13:07 - 17:47` gives its true 8h26m a day.
  `timingresolution` sets the slot size outright, and a slot then counts as worked when
  it starts in working time.

### Units

- `duration` and `gapduration` are calendar time. `effort`, `length` and `gaplength` are
  working time, in which a day is `dailyworkinghours` long and a year has
  `yearlyworkingdays` days. `m` is months and `min` is minutes.

### Resources

- `effort` is person-time. Two resources working the same hour deliver two hours of it.
- A task makes progress only while a `mandatory` resource is available. `persistent`
  keeps the resource that was chosen first, and `alternative` names one to fall back on.
- Allocating a resource that has members allocates each member.
- A task with a `duration`, or with a stated `start` and `end`, books the resources it
  allocates for the hours they are on shift and free. Its dates stay as stated when they
  are not free.
- `dailymax`, `weeklymax`, `monthlymax` and `maximum` stop bookings at the cap, and
  booking resumes in the next period. Periods are counted in the resource's own calendar
  and a week runs Monday to Sunday. A cap smaller than one slot is kept exactly.
- `dailymin`, `weeklymin`, `monthlymin` and `minimum` are targets, which placing tasks
  cannot guarantee. A period in which the resource or task was booked for less draws a
  warning once the schedule is complete.

### Scheduling

- A task is scheduled as soon as possible unless `scheduling alap` on the task, on a
  container or on the project says as late as possible. One chain can mix the two.
- A task scheduled as late as possible ends by the earliest of its own `end`, the start
  of each task that follows it (less any gap that task asks for) and the project end.
  With none of these but a follower scheduled as soon as possible that states no start,
  it is scheduled as soon as possible as well, and a warning says so.
- `depends X { onstart }` lets a task start once X has started. It needs a task scheduled
  as soon as possible, and the file is refused when the task is scheduled as late as
  possible. `precedes X` is how such a task says it must finish before X starts.
- When tasks compete for a resource, the higher `priority` is placed first, then the
  higher criticalness, then the task declared first. A task's criticalness is its effort
  times how much is asked of the resources it may use, plus that of the heaviest chain
  of tasks waiting for it. At equal priority this places the larger effort first.
- Tasks are placed one at a time in that order. A task ranked higher takes a resource's
  daily or weekly allowance first, and a lower-ranked task that started earlier can
  finish later. Raising its priority keeps it going.
- The declared project period is never rewritten. A task that does not fit is reported
  with its name and the reason, and a date stated outside the period is an error.
- Scheduling the same project twice gives the same dates and the same bookings.
- A stated `start` or `end` that the schedule cannot keep is an error. So is a task that
  would start before something it depends on finishes.
- `length` and `gaplength` count the project's working time. A resource on longer hours
  does not shorten the gap.
- `maxgapduration`, `maxstart`, `minstart`, `maxend` and `minend` are checked once the
  schedule is complete, and a violation is an error. `maxgaplength` is not part of the
  syntax and is refused when the file is read.

### Errors and warnings

- A dependency cycle is rejected before scheduling, and the message names the cycle.
- An attribute or reference the parser cannot place is an error. Each directive the
  grammar accepts has a probe showing that it changes a schedule, is refused or draws a
  warning. The few that do none of these are listed, each with the reason, in
  `audit/evaluations/probe_directive_effect.py`.
- Warnings are printed to standard error by `plan report` and by `scriptplan`.

## Differences from other schedulers of this format

A file written for another scheduler may behave differently in these places.

- **Direction.** A task's direction comes from `scheduling`. A `depends` written after
  `scheduling alap` does not turn the task back to as soon as possible.
- **Placement order.** Where two tasks lead into the same task, ScriptPlan counts that
  task towards the criticalness of both. Another scheduler of this format counts it
  towards the one declared first. The two can then place tasks of equal priority in a
  different order. Of 150 random projects with contended resources, 132 came out the
  same in both. Give a task a `priority` to fix its place.
- **Start of a `length` task.** A `length` task with no start of its own is reported as
  starting at the first working moment it can. Other schedulers report the moment it was
  released, which may be midnight. The end is the same.
- **Task references.** A reference is looked up from the referring task's scope, one
  level up for each `!`. When the `!`s stop at a task, the reference must name one of its
  children, and `!x` with no sibling `x` is refused. When there are no `!`s, or they
  reach the top level and no top-level task matches, the reference binds to the only
  task in the project with that id. `depends !!pack` inside `delivery` finds
  `delivery.pack` this way. When two tasks could be meant, the file is refused and both
  are named.
- **Additions.** `scheduling` in the project block, `workinghours <shift id>` on a
  resource, `timezone` on a resource and intervals that run past midnight are
  ScriptPlan's own.

## Known limits

- `include`, `supplement`, `leaveallowance` and `statussheet` are not implemented.
- Output formats are JSON and CSV. `ical`, `tjp`, `niku` and MS Project XML are refused
  when the file is read.
- Accounts are parsed and not yet modelled. `chargeset` and `charge` record an amount
  without posting it anywhere.
- The value a task or resource gives to a custom attribute declared with `extend` is
  read and not kept.
- `limits` inside an `allocate` option block is refused. Put the limits on the task, and
  add `{ resources <id> }` to hold them to one resource.
- `onend` on `precedes` is refused.
- Memory grows with the number of resources times the project's length divided by the
  slot size, because a resource holds one entry per slot for the whole project. Times
  off the hour make the slots smaller.

## Example project

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
    precedes !!pack
  }

  task assemble_a "Engine Assembly" {
    effort 16h
    allocate machine
  }
}

task connection_setup "Logic" {
  task set_deps "Apply" {
    depends !!delivery.assemble_a, !!delivery.assemble_b
    precedes !!delivery.pack
  }
}

taskreport output "output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

The project is scheduled backward from the delivery deadline. Packaging ends at 16:00
on 18 July. Both assemblies have to finish before packaging starts. With one machine
they run one after the other, on the four working days before it.

```
delivery.pack:       2025-07-18-08:00 -> 2025-07-18-16:00
delivery.assemble_a: 2025-07-14-08:00 -> 2025-07-15-16:00
delivery.assemble_b: 2025-07-16-08:00 -> 2025-07-17-16:00
```

## License

Apache-2.0

## Acknowledgments

ScriptPlan reads the .tjp project file format. Its parser, its scheduling algorithms and
its reports were written for it, and it contains no code from any other scheduler.

## Why ScriptPlan?

This scheduler is part of Highway Workflow Engine's worker capacity management system. I decided to open-source it for the community to benefit from its precise scheduling capabilities. Because it reads the established .tjp syntax, users can adopt ScriptPlan without learning a new format.

Yours,
Farshid.
