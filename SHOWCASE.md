# ScriptPlan Report Generation - Certification Exam

**Generated**: 28 November 2025, London, UK
**Tool**: plan (ScriptPlan CLI)
**Purpose**: Audit certification of report generation correctness

This document contains all test project files (.tjp) and their corresponding
generated reports (JSON format) for verification and certification.

---

## Table of Contents

1. [airport_retrofit.tjp](#test-1-airport_retrofit.tjp)
2. [airport_stress_test.tjp](#test-2-airport_stress_test.tjp)
3. [airport_ultra_math_report.tjp](#test-3-airport_ultra_math_report.tjp)
4. [airport_ultra_math.tjp](#test-4-airport_ultra_math.tjp)
5. [alap_backward.tjp](#test-5-alap_backward.tjp)
6. [atomic.tjp](#test-6-atomic.tjp)
7. [blackbox.tjp](#test-7-blackbox.tjp)
8. [bottleneck.tjp](#test-8-bottleneck.tjp)
9. [eclipse.tjp](#test-9-eclipse.tjp)
10. [failover.tjp](#test-10-failover.tjp)
11. [jit_supply.tjp](#test-11-jit_supply.tjp)
12. [math_torture.tjp](#test-12-math_torture.tjp)
13. [paradox.tjp](#test-13-paradox.tjp)
14. [priority_clash.tjp](#test-14-priority_clash.tjp)
15. [quota.tjp](#test-15-quota.tjp)
16. [simple.tjp](#test-16-simple.tjp)
17. [synchrony.tjp](#test-17-synchrony.tjp)
18. [thermal.tjp](#test-18-thermal.tjp)
19. [throughput.tjp](#test-19-throughput.tjp)
20. [time_traveler.tjp](#test-20-time_traveler.tjp)
21. [timezone_stress.tjp](#test-21-timezone_stress.tjp)
22. [tutorial.tjp](#test-22-tutorial.tjp)
23. [union_contract.tjp](#test-23-union_contract.tjp)
24. [workflow_engine.tjp](#test-24-workflow_engine.tjp)

---


## Test 1: airport_retrofit.tjp

**File**: `tests/data/airport_retrofit.tjp`
**Size**: 1668 bytes
**Lines**: 80 lines

### Input File Content

```tjp
project "Airport_BHS_Upgrade" 2025-09-01 +2m {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  numberformat "-" "" "," "." 1
  currencyformat "(" ")" "," "." 0
  now 2025-09-01
}

# --- 1. CALENDARS & SHIFTS ---

# National Holiday (Friday)
vacation "Public Holiday" 2025-09-05

# Standard Office: Mon-Fri, 09:00-17:00 (8h)
shift standard_shift {
  workinghours mon - fri 09:00 - 17:00
}

# Night Construction: Mon-Fri, 22:00-06:00 (8h)
# Note: In TJP, 22:00-06:00 usually implies the shift crosses midnight.
shift night_shift {
  workinghours mon - fri 22:00 - 06:00
}

# --- 2. RESOURCES ---

resource team "Project Team" {

  # Architect: Standard hours, takes vacation the second week
  resource arch "Senior Architect" {
    workinghours standard_shift
    vacation 2025-09-11 - 2025-09-12
  }

  # Construction Crew: Night shift only
  resource crew "Night Crew" {
    workinghours night_shift
  }

  # Electrician: Standard hours, but Junior (0.8 efficiency)
  resource sparky "Junior Electrician" {
    workinghours standard_shift
    efficiency 0.8
  }
}

# --- 3. TASKS ---

task bhs "Baggage Handling System" {

  # TASK 1: Design Phase
  task design "Blueprint Design" {
    effort 40h
    allocate arch
    start 2025-09-01-09:00
  }

  # TASK 2: Demolition
  task demo "Old System Demo" {
    effort 16h
    allocate crew
    depends !design
  }

  # TASK 3: Electrical Rewiring
  task wiring "Electrical Rewiring" {
    effort 32h
    allocate sparky
    depends !demo { gapduration 24h onstart }
  }
}

# --- 4. REPORT ---

taskreport "retrofit_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
  leaftasksonly true
}
```

### Generated Report (JSON)

**Report ID**: `2c70d0b525be1903a66fb54cbfea11b570c700ccbe4ecc8ebd65873db916bbc2`
**Columns**: 3
**Rows**: 4
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "bhs",
      "start": "2025-09-01-09:00",
      "end": "2025-09-16-17:00"
    },
    {
      "id": "bhs.design",
      "start": "2025-09-01-09:00",
      "end": "2025-09-08-17:00"
    },
    {
      "id": "bhs.demo",
      "start": "2025-09-08-22:00",
      "end": "2025-09-10-06:00"
    },
    {
      "id": "bhs.wiring",
      "start": "2025-09-10-09:00",
      "end": "2025-09-16-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "2c70d0b525be1903a66fb54cbfea11b570c700ccbe4ecc8ebd65873db916bbc2"
}
```

---

## Test 2: airport_stress_test.tjp

**File**: `tests/data/airport_stress_test.tjp`
**Size**: 2387 bytes
**Lines**: 110 lines

### Input File Content

```tjp
/*
 * AIRPORT BAGGAGE SYSTEM UPGRADE - STRESS TEST
 * Challenge: Mixed calendars, efficiency factors, resource constraints,
 * and strict dependency chains.
 */

project acso "AirportStressTest" 2025-06-01 +2m {
  timezone "UTC"
  timeformat "%Y-%m-%d"
  currency "USD"
  dailyworkinghours 8
  yearlyworkingdays 260
}

# ---------------------------------------------------------------------------
# 1. RESOURCES WITH ATTRIBUTES
# ---------------------------------------------------------------------------

resource dev "IT Team" {
  efficiency 0.8
  rate 100.0

  resource d1 "Senior Dev" {
    leaves annual 2025-06-05 - 2025-06-06
  }

  resource d2 "Night Ops" {
    limits { dailymax 8h }
  }
}

resource elec "Electricians" {
  efficiency 1.0
  rate 80.0

  resource e1 "Master Electrician" {
    efficiency 1.2
  }

  resource e2 "Apprentice" {
    efficiency 0.5
  }
}

# ---------------------------------------------------------------------------
# 2. TASKS - THE GAUNTLET
# ---------------------------------------------------------------------------

task airport "Terminal 5 Upgrade" {

  # SCENARIO A: Efficiency & Leave Calculation
  task t_software "Control Software" {
    effort 2d
    allocate d1
    start 2025-06-02
  }

  # SCENARIO B: Dependency & Lag
  task t_install "Hardware Install" {
    depends !t_software { gapduration 4h }
    effort 1d
    allocate e1
  }

  # SCENARIO C: Resource contention & Priority
  task t_crit "Critical Power Patch" {
    priority 1000
    effort 1d
    allocate e1
    depends !t_software
  }

  task t_low "Labeling Cables" {
    priority 100
    effort 4h
    allocate e1
    depends !t_software
  }

  # SCENARIO D: Night Shift Logic
  task t_migration "Database Migration" {
    depends !t_crit
    effort 6h
    allocate d2
  }

  # SCENARIO E: ALAP (As Late As Possible)
  task t_audit "Safety Audit" {
    scheduling alap
    effort 2d
    allocate e2
    end 2025-06-25
  }

  # SCENARIO F: Milestone & Hierarchy
  task deliver "Go Live" {
    depends !t_migration, !t_audit, !t_low
  }
}

# ---------------------------------------------------------------------------
# 3. REPORT DEFINITION (CSV OUTPUT)
# ---------------------------------------------------------------------------

taskreport status_csv "status" {
  formats csv
  columns id, name, start, end, effort, duration
  timeformat "%Y-%m-%d"
  loadunit days
}
```

### Generated Report (JSON)

**Report ID**: `8afa42ebffd65bfbe4b745aff5276c3eee502b19faff96159a80521d08dc4432`
**Columns**: 3
**Rows**: 8
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "airport",
      "start": "2025-06-02-09:00",
      "end": "2025-06-24-17:00"
    },
    {
      "id": "airport.t_software",
      "start": "2025-06-02-09:00",
      "end": "2025-06-04-13:00"
    },
    {
      "id": "airport.t_install",
      "start": "2025-06-05-11:00",
      "end": "2025-06-06-10:20"
    },
    {
      "id": "airport.t_crit",
      "start": "2025-06-04-13:00",
      "end": "2025-06-05-11:40"
    },
    {
      "id": "airport.t_low",
      "start": "2025-06-06-10:00",
      "end": "2025-06-06-13:40"
    },
    {
      "id": "airport.t_migration",
      "start": "2025-06-05-11:40",
      "end": "2025-06-06-11:10"
    },
    {
      "id": "airport.t_audit",
      "start": "2025-06-19-09:00",
      "end": "2025-06-24-17:00"
    },
    {
      "id": "airport.deliver",
      "start": "2025-06-24-17:00",
      "end": "2025-06-24-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "8afa42ebffd65bfbe4b745aff5276c3eee502b19faff96159a80521d08dc4432"
}
```

---

## Test 3: airport_ultra_math_report.tjp

**File**: `tests/data/airport_ultra_math_report.tjp`
**Size**: 4896 bytes
**Lines**: 152 lines

### Input File Content

```tjp
/* * GLOBAL AIRPORT SYNCHRONIZATION - ULTRA COMPLEX
 * Challenge: Floating point efficiency, irregular calendars,
 * daily limits vs. limits, and priority-based preemption.
 */

project "AirportUltraMath" 2025-08-01 +3m {
  timezone "UTC"
  timeformat "%Y-%m-%d %H:%M:%S"
  currency "EUR"
  timingresolution 15min

  # Standard: 8h days. But we will override this per resource.
  dailyworkinghours 8
  yearlyworkingdays 260
}

# ---------------------------------------------------------------------------
# ACCOUNTS (must be defined before resources that use them)
# ---------------------------------------------------------------------------
account cost "Labor Cost" {
  aggregate resources
}
account rev "Revenue" {}
balance cost rev

# ---------------------------------------------------------------------------
# 1. THE "SWISS CHEESE" CALENDAR
# ---------------------------------------------------------------------------
# This calendar has odd gaps. If your system assumes hourly blocks, it fails.
resource irregular_shift "Irregular Shift" {
  workinghours mon, wed, fri 08:15 - 11:45, 13:15 - 16:30
  workinghours tue, thu      09:00 - 10:30, 14:45 - 16:00
}

# ---------------------------------------------------------------------------
# 2. RESOURCES (The Math Hazards)
# ---------------------------------------------------------------------------

resource r_math "The Math Hazard" {
  # Efficiency 0.77 forces nasty floating point expansion.
  # 1 hour effort = 1.2987... hours duration.
  efficiency 0.77
  rate 150.0
  chargeset cost

  # Uses the swiss cheese calendar
  workinghours mon, wed, fri 08:15 - 11:45, 13:15 - 16:30
  workinghours tue, thu      09:00 - 10:30, 14:45 - 16:00

  # Leave specifically during a critical Tuesday slot
  vacation 2025-08-05-09:30 - 2025-08-05-10:00
}

resource r_limit "The Bottleneck" {
  efficiency 1.25
  rate 200.0
  chargeset cost
  workinghours mon - fri 08:00 - 18:00

  # LIMIT TEST: Max 3.5 hours per day.
  # With eff 1.25, they do 4.375h of work in 3.5h calendar time.
  # Your system must stop scheduling them after 3.5h clock time.
  limits { dailymax 3.5h }
}

# ---------------------------------------------------------------------------
# 3. THE TASKS
# ---------------------------------------------------------------------------

task airport_math "Complex Calculations" {

  # SCENARIO A: The Floating Point Expansion
  # ----------------------------------------
  # Effort: 17.5 hours.
  # Resource: r_math (Eff 0.77).
  # Calendar: Irregular.
  # Leave: 30 mins in the middle of slot.
  #
  # Start: Monday Aug 4, 2025.
  # Logic Check:
  # Work Required = 17.5 / 0.77 = 22.7272... hours.
  # Mon Available: (11:45-08:15) + (16:30-13:15) = 3.5 + 3.25 = 6.75h
  # Tue Available: (10:30-09:00) + (16:00-14:45) = 1.5 + 1.25 = 2.75h
  # ... MINUS the leave (30m) on Tuesday = 2.25h net.
  # Your system must navigate these fractions exactly.
  task t_float "Floating Point Expansion" {
    priority 100
    effort 17.5h
    allocate r_math
    start 2025-08-04-08:15
  }

  # SCENARIO B: The Interruption (Preemption)
  # ----------------------------------------
  # A high priority task aimed at the EXACT time r_math is working on t_float.
  # Wed Aug 6 is a work day.
  # t_float should still be running.
  # This task MUST pause t_float, run for 45 mins, then t_float resumes.
  task t_interrupt "Emergency Patch" {
    priority 1000
    effort 45min
    allocate r_math
    start 2025-08-06-14:00
  }

  # SCENARIO C: Limits vs Efficiency
  # ----------------------------------------
  # Task requires 15 hours of EFFORT.
  # Resource r_limit has eff 1.25.
  # Actual work time needed = 15 / 1.25 = 12 hours.
  # Constraint: dailymax 3.5h.
  #
  # Schedule should allow 3.5h/day for 3 days (3.5 * 3 = 10.5h).
  # Day 4: Remaining 1.5h.
  # Cost: 12h * 200 rate = 2400 (NOT based on effort 15h, but allocated time).
  task t_limit "Bottleneck Squeeze" {
    effort 15h
    allocate r_limit
    depends !t_float
  }

  # SCENARIO D: ALAP + Start-Start Lead
  # ----------------------------------------
  # t_finish must end on Friday, Aug 29 at 17:00.
  # t_pre must start 3 days BEFORE t_finish starts.
  task t_finish "Hard Deadline" {
    scheduling alap
    effort 1d
    allocate r_limit
    end 2025-08-29-17:00
  }

  # NOTE: Negative gapduration is not supported by TJ. Removing this test case.
  # task t_pre "Lead Time Dependency" {
  #   scheduling alap
  #   effort 4h
  #   allocate r_math
  #   # Start-Start dependency with a 3 day LEAD (negative gap)
  #   depends !t_finish { gapduration -3d }
  # }
}

# ---------------------------------------------------------------------------
# 4. REPORT
# ---------------------------------------------------------------------------

taskreport "math_dump" {
  formats csv
  columns id, name, start, end, duration, effort, cost
  hidetask ~isleaf()
  loadunit hours
}
```

### Generated Report (JSON)

**Report ID**: `28a626ddcc83d7f2a82df1d97088fe59dd6c79a6c24f3b8f8b3a6484fb8dba4c`
**Columns**: 3
**Rows**: 5
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "airport_math",
      "start": "2025-08-04-08:15",
      "end": "2025-08-29-17:00"
    },
    {
      "id": "airport_math.t_float",
      "start": "2025-08-04-08:15",
      "end": "2025-08-08-14:57"
    },
    {
      "id": "airport_math.t_interrupt",
      "start": "2025-08-06-14:00",
      "end": "2025-08-06-14:58"
    },
    {
      "id": "airport_math.t_limit",
      "start": "2025-08-08-14:57",
      "end": "2025-08-13-09:57"
    },
    {
      "id": "airport_math.t_finish",
      "start": "2025-08-28-15:06",
      "end": "2025-08-29-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "28a626ddcc83d7f2a82df1d97088fe59dd6c79a6c24f3b8f8b3a6484fb8dba4c"
}
```

---

## Test 4: airport_ultra_math.tjp

**File**: `tests/data/airport_ultra_math.tjp`
**Size**: 5067 bytes
**Lines**: 160 lines

### Input File Content

```tjp
/* * GLOBAL AIRPORT SYNCHRONIZATION - ULTRA COMPLEX
 * Challenge: Floating point efficiency, irregular calendars,
 * daily limits vs. limits, and priority-based preemption.
 */

project "AirportUltraMath" 2025-08-01 +3m {
  timezone "UTC"
  timeformat "%Y-%m-%d %H:%M:%S"
  currency "EUR"
  timingresolution 15min

  # Standard: 8h days. But we will override this per resource.
  dailyworkinghours 8
  yearlyworkingdays 260
}

# ---------------------------------------------------------------------------
# ACCOUNTS (must be defined before resources that use them)
# ---------------------------------------------------------------------------
account cost "Labor Cost" {
  aggregate resources
}
account rev "Revenue" {}
balance cost rev

# ---------------------------------------------------------------------------
# 1. THE "SWISS CHEESE" CALENDAR
# ---------------------------------------------------------------------------
# This calendar has odd gaps. If your system assumes hourly blocks, it fails.
resource irregular_shift "Irregular Shift" {
  workinghours mon, wed, fri 08:15 - 11:45, 13:15 - 16:30
  workinghours tue, thu      09:00 - 10:30, 14:45 - 16:00
}

# ---------------------------------------------------------------------------
# 2. RESOURCES (The Math Hazards)
# ---------------------------------------------------------------------------

resource r_math "The Math Hazard" {
  # Efficiency 0.77 forces nasty floating point expansion.
  # 1 hour effort = 1.2987... hours duration.
  efficiency 0.77
  rate 150.0
  chargeset cost

  # Uses the swiss cheese calendar
  workinghours mon, wed, fri 08:15 - 11:45, 13:15 - 16:30
  workinghours tue, thu      09:00 - 10:30, 14:45 - 16:00

  # Leave specifically during a critical Tuesday slot (30 mins)
  vacation 2025-08-05-09:30 - 2025-08-05-10:00
}

resource r_limit "The Bottleneck" {
  efficiency 1.25
  rate 200.0
  chargeset cost
  workinghours mon - fri 08:00 - 18:00

  # LIMIT TEST: Max 3.5 hours per day.
  # With eff 1.25, they do 4.375h of work in 3.5h calendar time.
  # Your system must stop scheduling them after 3.5h clock time.
  limits { dailymax 3.5h }
}

# ---------------------------------------------------------------------------
# 3. THE TASKS
# ---------------------------------------------------------------------------

task airport_math "Complex Calculations" {

  # SCENARIO A: The Floating Point Expansion
  # ----------------------------------------
  # Effort: 17.5 hours.
  # Resource: r_math (Eff 0.77).
  # Calendar: Irregular.
  # Leave: 30 mins in the middle of slot.
  #
  # Start: Monday Aug 4, 2025.
  # Logic Check:
  # Work Required = 17.5 / 0.77 = 22.7272... hours.
  # Mon Available: (11:45-08:15) + (16:30-13:15) = 3.5 + 3.25 = 6.75h
  # Tue Available: (10:30-09:00) + (16:00-14:45) = 1.5 + 1.25 = 2.75h
  # ... MINUS the leave (30m) on Tuesday = 2.25h net.
  # Your system must navigate these fractions exactly.
  task t_float "Floating Point Expansion" {
    priority 100
    effort 17.5h
    allocate r_math
    start 2025-08-04-08:15
  }

  # SCENARIO B: The Interruption (Preemption)
  # ----------------------------------------
  # A high priority task aimed at the EXACT time r_math is working on t_float.
  # Wed Aug 6 is a work day.
  # t_float should still be running.
  # This task MUST pause t_float, run for 45 mins, then t_float resumes.
  task t_interrupt "Emergency Patch" {
    priority 1000
    effort 45min
    allocate r_math
    start 2025-08-06-14:00
  }

  # SCENARIO C: Limits vs Efficiency
  # ----------------------------------------
  # Task requires 15 hours of EFFORT.
  # Resource r_limit has eff 1.25.
  # Actual work time needed = 15 / 1.25 = 12 hours.
  # Constraint: dailymax 3.5h.
  #
  # Schedule should allow 3.5h/day for 3 days (3.5 * 3 = 10.5h).
  # Day 4: Remaining 1.5h.
  # Cost: 12h * 200 rate = 2400 (NOT based on effort 15h, but allocated time).
  task t_limit "Bottleneck Squeeze" {
    effort 15h
    allocate r_limit
    depends !t_float
  }

  # SCENARIO D: ALAP + Start-Start Lead
  # ----------------------------------------
  # t_finish must end on Friday, Aug 29 at 17:00.
  # t_pre must start 3 days BEFORE t_finish starts.
  task t_finish "Hard Deadline" {
    scheduling alap
    effort 1d
    allocate r_limit
    end 2025-08-29-17:00
  }

  # NOTE: Negative gapduration is not supported by TJ. Removing this test case.
  # task t_pre "Lead Time Dependency" {
  #   scheduling alap
  #   effort 4h
  #   allocate r_math
  #   # Start-Start dependency with a 3 day LEAD (negative gap)
  #   depends !t_finish { gapduration -3d }
  # }
}

# ---------------------------------------------------------------------------
# 4. REPORT (commented out for now - formats not supported in parser)
# ---------------------------------------------------------------------------

# taskreport "math_dump" {
#   formats csv
#   columns id,
#           name,
#           start,
#           end,
#           duration,
#           effort,
#           cost,
#           complete,
#           note
#
#   hideresource 0
# }
```

### Generated Report (JSON)

**Report ID**: `5fc1e9e0f41f85ecc893b7e92ba647da812e4abe31c154fe3d220e9313e8a068`
**Columns**: 3
**Rows**: 5
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "airport_math",
      "start": "2025-08-04-08:15",
      "end": "2025-08-29-17:00"
    },
    {
      "id": "airport_math.t_float",
      "start": "2025-08-04-08:15",
      "end": "2025-08-08-14:57"
    },
    {
      "id": "airport_math.t_interrupt",
      "start": "2025-08-06-14:00",
      "end": "2025-08-06-14:58"
    },
    {
      "id": "airport_math.t_limit",
      "start": "2025-08-08-14:57",
      "end": "2025-08-13-09:57"
    },
    {
      "id": "airport_math.t_finish",
      "start": "2025-08-28-15:06",
      "end": "2025-08-29-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "5fc1e9e0f41f85ecc893b7e92ba647da812e4abe31c154fe3d220e9313e8a068"
}
```

---

## Test 5: alap_backward.tjp

**File**: `tests/data/alap_backward.tjp`
**Size**: 772 bytes
**Lines**: 44 lines

### Input File Content

```tjp
/*
 * Issue #51: ALAP Backward Scheduling
 * Tests backward calculation with holiday handling
 */

project alap "ALAP_Production" 2025-12-01 +3w {
  timezone "UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-12-01
}

shift standard "Standard" {
  workinghours mon - fri 09:00 - 17:00
}

vacation "Holiday" 2025-12-10

resource team "Team" {
  resource worker "Worker" {
    workinghours mon - fri 09:00 - 17:00
  }
}

task production "Product" {
  task step1 "Assembly" {
    effort 16h
    allocate worker
    scheduling alap
    precedes !step2
  }

  task step2 "Painting" {
    effort 16h
    allocate worker
    scheduling alap
    end 2025-12-12-17:00
  }
}

taskreport alap_output "alap_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `5a8e1a53c5e69dc3dfbd08ed3208fea9620d55f54aed4b5e07caeeaf0595d68f`
**Columns**: 3
**Rows**: 3
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "production",
      "start": "2025-12-08-09:00",
      "end": "2025-12-12-17:00"
    },
    {
      "id": "production.step1",
      "start": "2025-12-08-09:00",
      "end": "2025-12-09-17:00"
    },
    {
      "id": "production.step2",
      "start": "2025-12-11-09:00",
      "end": "2025-12-12-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "5a8e1a53c5e69dc3dfbd08ed3208fea9620d55f54aed4b5e07caeeaf0595d68f"
}
```

---

## Test 6: atomic.tjp

**File**: `tests/data/atomic.tjp`
**Size**: 608 bytes
**Lines**: 31 lines

### Input File Content

```tjp
/*
 * Issue #64: The "Indivisible" Protocol - Atomicity
 * Tests contiguous flag (atomic booking)
 * Task cannot be split across shift breaks
 */

project "Atomic_Booking" 2025-11-01 +1w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-11-01
}

shift broken_day "Broken Day" {
  workinghours mon - fri 08:00 - 12:00, 13:00 - 18:00
}

resource kiln "Ceramic Oven" {
  workinghours broken_day
}

task production "Firing Phase" {
  effort 4.5h
  flags contiguous
  allocate kiln
}

taskreport atomic_output "atomic_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `0899b7c2e9c7a5522ca65265d346b80c97d7b5bc54004a6641ee07d28100df18`
**Columns**: 3
**Rows**: 1
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "production",
      "start": "2025-11-03-13:00",
      "end": "2025-11-03-17:30"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "0899b7c2e9c7a5522ca65265d346b80c97d7b5bc54004a6641ee07d28100df18"
}
```

---

## Test 7: blackbox.tjp

**File**: `tests/data/blackbox.tjp`
**Size**: 921 bytes
**Lines**: 51 lines

### Input File Content

```tjp
/*
 * Issue #57: The "Black Box" Protocol
 * Tests timezone conversion, efficiency, disjoint calendars, day-boundary crossovers
 */

project "Black_Box_Protocol" 2025-01-01 +1m {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-01-01
}

shift alpha_shift {
  workinghours mon - wed 10:00 - 14:00
}

shift beta_shift {
  workinghours thu - sun 18:00 - 22:00
}

resource agent_a "Alpha" {
  timezone "Europe/Athens"
  workinghours alpha_shift
  efficiency 0.5
}

resource agent_b "Beta" {
  timezone "America/Los_Angeles"
  workinghours beta_shift
  efficiency 2.0
}

task operations "Covert Ops" {

  task phase_1 "Infiltration" {
    effort 4h
    allocate agent_a
    start 2025-01-01-00:00
  }

  task phase_2 "Extraction" {
    effort 4h
    allocate agent_b
    depends !phase_1
  }
}

taskreport blackbox_output "blackbox_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `a9f35fa0b20771c0493e475ffde0f33e32be551dd3e98545d56c032a63d50094`
**Columns**: 3
**Rows**: 3
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "operations",
      "start": "2025-01-01-08:00",
      "end": "2025-01-10-04:00"
    },
    {
      "id": "operations.phase_1",
      "start": "2025-01-01-08:00",
      "end": "2025-01-06-12:00"
    },
    {
      "id": "operations.phase_2",
      "start": "2025-01-10-02:00",
      "end": "2025-01-10-04:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "a9f35fa0b20771c0493e475ffde0f33e32be551dd3e98545d56c032a63d50094"
}
```

---

## Test 8: bottleneck.tjp

**File**: `tests/data/bottleneck.tjp`
**Size**: 963 bytes
**Lines**: 53 lines

### Input File Content

```tjp
/*
 * Issue #49: The Bottlenecked Release
 * Tests daily limits + holiday interaction
 */

project bottleneck "Bottleneck_Release" 2025-06-02 +3w {
  timezone "UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-06-02
}

shift standard "Standard" {
  workinghours mon - fri 09:00 - 17:00
}

vacation "Company Founder Day" 2025-06-04

resource team "Dev Team" {
  resource dev "FullStack Dev" {
    workinghours mon - fri 09:00 - 17:00
  }

  resource qa "QA Lead" {
    workinghours mon - fri 09:00 - 17:00
    limits { dailymax 4h }
  }
}

task release "v1.0 Release" {
  task coding "Feature Code" {
    effort 16h
    allocate dev
    start 2025-06-02-09:00
  }

  task review "Code Review" {
    effort 12h
    allocate qa
    depends !coding
  }

  task deploy "Deploy to Prod" {
    effort 4h
    allocate dev, qa
    depends !review
  }
}

taskreport bottleneck_output "bottleneck_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `0cedc57de126d2eafea63bff38583cc5c23b572cf4336be5684d1146111cf2a2`
**Columns**: 3
**Rows**: 4
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "release",
      "start": "2025-06-02-09:00",
      "end": "2025-06-10-13:00"
    },
    {
      "id": "release.coding",
      "start": "2025-06-02-09:00",
      "end": "2025-06-03-17:00"
    },
    {
      "id": "release.review",
      "start": "2025-06-05-09:00",
      "end": "2025-06-09-13:00"
    },
    {
      "id": "release.deploy",
      "start": "2025-06-10-09:00",
      "end": "2025-06-10-13:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "0cedc57de126d2eafea63bff38583cc5c23b572cf4336be5684d1146111cf2a2"
}
```

---

## Test 9: eclipse.tjp

**File**: `tests/data/eclipse.tjp`
**Size**: 722 bytes
**Lines**: 41 lines

### Input File Content

```tjp
/*
 * Issue #60: The "Eclipse" Protocol
 * Tests intersection of discontinuous shift patterns
 * Task requires BOTH resources simultaneously
 */

project "Eclipse_Protocol" 2025-06-01 +1m {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-06-01
}

shift s_odd "Odd" {
  workinghours mon, wed, fri 09:00 - 17:00
}

shift s_mid "Mid" {
  workinghours mon - sun 12:00 - 14:00
}

resource r_sun "Sun" {
  workinghours s_odd
}

resource r_moon "Moon" {
  workinghours s_mid
}

task sys "Alignment" {
  task sync "Syzygy" {
    effort 7h
    allocate r_sun, r_moon
    start 2025-06-01-00:00
  }
}

taskreport eclipse_output "eclipse_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `931dd3cb6cc845adc52f413c786ad27a97c8de8b7c08afb9f8a6e4ee6676251a`
**Columns**: 3
**Rows**: 2
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "sys",
      "start": "2025-06-02-12:00",
      "end": "2025-06-09-13:00"
    },
    {
      "id": "sys.sync",
      "start": "2025-06-02-12:00",
      "end": "2025-06-09-13:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "931dd3cb6cc845adc52f413c786ad27a97c8de8b7c08afb9f8a6e4ee6676251a"
}
```

---

## Test 10: failover.tjp

**File**: `tests/data/failover.tjp`
**Size**: 771 bytes
**Lines**: 37 lines

### Input File Content

```tjp
/*
 * Issue #63: The "Failover" Protocol
 * Tests alternative resource allocation (smart routing)
 * Primary is on vacation, system should use slower backup to finish earlier
 */

project "Failover_Test" 2025-08-01 +2w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-08-01
}

shift standard "Standard" {
  workinghours mon - fri 09:00 - 17:00
}

resource primary "Cluster A (GPU)" {
  workinghours standard
  efficiency 1.0
  vacation 2025-08-01 - 2025-08-05
}

resource backup "Cluster B (CPU)" {
  workinghours standard
  efficiency 0.5
}

task compute "Rendering" {
  effort 8h
  allocate primary { alternative backup }
}

taskreport failover_output "failover_output" {
  formats csv
  columns id, start, end, resources
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `6e9dfa106f9adae577a766c9c5efb0f5a9d9d6702324fdff8b3e2b02fe178d61`
**Columns**: 3
**Rows**: 1
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "compute",
      "start": "2025-08-01-09:00",
      "end": "2025-08-04-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "6e9dfa106f9adae577a766c9c5efb0f5a9d9d6702324fdff8b3e2b02fe178d61"
}
```

---

## Test 11: jit_supply.tjp

**File**: `tests/data/jit_supply.tjp`
**Size**: 1082 bytes
**Lines**: 58 lines

### Input File Content

```tjp
/*
 * Issue #54: Just-In-Time Supply Chain
 * Tests ALAP + Resource Contention + Weekend handling
 *
 * Original specification requires:
 * - Project-level scheduling alap
 * - End date on parent task
 * - Complex dependencies with onstart
 */

project "Just_In_Time" 2025-07-01 +1m {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-07-01

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

taskreport jit_output "jit_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `35c932f5f3b994dd9d25aab329d9bf32b3df388de21f6b56a3867507959ed1db`
**Columns**: 3
**Rows**: 6
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "delivery",
      "start": "2025-07-14-08:00",
      "end": "2025-07-18-16:00"
    },
    {
      "id": "delivery.pack",
      "start": "2025-07-18-08:00",
      "end": "2025-07-18-16:00"
    },
    {
      "id": "delivery.assemble_b",
      "start": "2025-07-16-08:00",
      "end": "2025-07-17-16:00"
    },
    {
      "id": "delivery.assemble_a",
      "start": "2025-07-14-08:00",
      "end": "2025-07-15-16:00"
    },
    {
      "id": "connection_setup",
      "start": "2025-07-31-16:00",
      "end": "2025-07-31-16:00"
    },
    {
      "id": "connection_setup.set_deps",
      "start": "2025-07-31-16:00",
      "end": "2025-07-31-16:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "35c932f5f3b994dd9d25aab329d9bf32b3df388de21f6b56a3867507959ed1db"
}
```

---

## Test 12: math_torture.tjp

**File**: `tests/data/math_torture.tjp`
**Size**: 55876 bytes
**Lines**: 3025 lines

### Input File Content

```tjp
project "Math_Torture" 2024-02-28-00:00 +3m {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  numberformat "-" "" "," "." 2
  currencyformat "(" ")" "," "." 2
  timingresolution 1min
}

shift prime_shift {
  workinghours mon - sun 08:13 - 11:59, 13:07 - 17:47
}

resource cruncher "Number Cruncher" {
  workinghours prime_shift
}

task chain "Chain Reaction" {

  task t_001 "Link 1" {
    effort 73min
    allocate cruncher
    start 2024-02-28-08:13
  }

  task t_002 "Link 2" {
    effort 73min
    allocate cruncher
    depends !t_001 { gapduration 29min }
  }

  task t_003 "Link 3" {
    effort 73min
    allocate cruncher
    depends !t_002 { gapduration 29min }
  }

  task t_004 "Link 4" {
    effort 73min
    allocate cruncher
    depends !t_003 { gapduration 29min }
  }

  task t_005 "Link 5" {
    effort 73min
    allocate cruncher
    depends !t_004 { gapduration 29min }
  }

  task t_006 "Link 6" {
    effort 73min
    allocate cruncher
    depends !t_005 { gapduration 29min }
  }

  task t_007 "Link 7" {
    effort 73min
    allocate cruncher
    depends !t_006 { gapduration 29min }
  }

  task t_008 "Link 8" {
    effort 73min
    allocate cruncher
    depends !t_007 { gapduration 29min }
  }

  task t_009 "Link 9" {
    effort 73min
    allocate cruncher
    depends !t_008 { gapduration 29min }
  }

  task t_010 "Link 10" {
    effort 73min
    allocate cruncher
    depends !t_009 { gapduration 29min }
  }

  task t_011 "Link 11" {
    effort 73min
    allocate cruncher
    depends !t_010 { gapduration 29min }
  }

  task t_012 "Link 12" {
    effort 73min
    allocate cruncher
    depends !t_011 { gapduration 29min }
  }

  task t_013 "Link 13" {
    effort 73min
    allocate cruncher
    depends !t_012 { gapduration 29min }
  }

  task t_014 "Link 14" {
    effort 73min
    allocate cruncher
    depends !t_013 { gapduration 29min }
  }

  task t_015 "Link 15" {
    effort 73min
    allocate cruncher
    depends !t_014 { gapduration 29min }
  }

  task t_016 "Link 16" {
    effort 73min
    allocate cruncher
    depends !t_015 { gapduration 29min }
  }

  task t_017 "Link 17" {
    effort 73min
    allocate cruncher
    depends !t_016 { gapduration 29min }
  }

  task t_018 "Link 18" {
    effort 73min
    allocate cruncher
    depends !t_017 { gapduration 29min }
  }

  task t_019 "Link 19" {
    effort 73min
    allocate cruncher
    depends !t_018 { gapduration 29min }
  }

  task t_020 "Link 20" {
    effort 73min
    allocate cruncher
    depends !t_019 { gapduration 29min }
  }

  task t_021 "Link 21" {
    effort 73min
    allocate cruncher
    depends !t_020 { gapduration 29min }
  }

  task t_022 "Link 22" {
    effort 73min
    allocate cruncher
    depends !t_021 { gapduration 29min }
  }

  task t_023 "Link 23" {
    effort 73min
    allocate cruncher
    depends !t_022 { gapduration 29min }
  }

  task t_024 "Link 24" {
    effort 73min
    allocate cruncher
    depends !t_023 { gapduration 29min }
  }

  task t_025 "Link 25" {
    effort 73min
    allocate cruncher
    depends !t_024 { gapduration 29min }
  }

  task t_026 "Link 26" {
    effort 73min
    allocate cruncher
    depends !t_025 { gapduration 29min }
  }

  task t_027 "Link 27" {
    effort 73min
    allocate cruncher
    depends !t_026 { gapduration 29min }
  }

  task t_028 "Link 28" {
    effort 73min
    allocate cruncher
    depends !t_027 { gapduration 29min }
  }

  task t_029 "Link 29" {
    effort 73min
    allocate cruncher
    depends !t_028 { gapduration 29min }
  }

  task t_030 "Link 30" {
    effort 73min
    allocate cruncher
    depends !t_029 { gapduration 29min }
  }

  task t_031 "Link 31" {
    effort 73min
    allocate cruncher
    depends !t_030 { gapduration 29min }
  }

  task t_032 "Link 32" {
    effort 73min
    allocate cruncher
    depends !t_031 { gapduration 29min }
  }

  task t_033 "Link 33" {
    effort 73min
    allocate cruncher
    depends !t_032 { gapduration 29min }
  }

  task t_034 "Link 34" {
    effort 73min
    allocate cruncher
    depends !t_033 { gapduration 29min }
  }

  task t_035 "Link 35" {
    effort 73min
    allocate cruncher
    depends !t_034 { gapduration 29min }
  }

  task t_036 "Link 36" {
    effort 73min
    allocate cruncher
    depends !t_035 { gapduration 29min }
  }

  task t_037 "Link 37" {
    effort 73min
    allocate cruncher
    depends !t_036 { gapduration 29min }
  }

  task t_038 "Link 38" {
    effort 73min
    allocate cruncher
    depends !t_037 { gapduration 29min }
  }

  task t_039 "Link 39" {
    effort 73min
    allocate cruncher
    depends !t_038 { gapduration 29min }
  }

  task t_040 "Link 40" {
    effort 73min
    allocate cruncher
    depends !t_039 { gapduration 29min }
  }

  task t_041 "Link 41" {
    effort 73min
    allocate cruncher
    depends !t_040 { gapduration 29min }
  }

  task t_042 "Link 42" {
    effort 73min
    allocate cruncher
    depends !t_041 { gapduration 29min }
  }

  task t_043 "Link 43" {
    effort 73min
    allocate cruncher
    depends !t_042 { gapduration 29min }
  }

  task t_044 "Link 44" {
    effort 73min
    allocate cruncher
    depends !t_043 { gapduration 29min }
  }

  task t_045 "Link 45" {
    effort 73min
    allocate cruncher
    depends !t_044 { gapduration 29min }
  }

  task t_046 "Link 46" {
    effort 73min
    allocate cruncher
    depends !t_045 { gapduration 29min }
  }

  task t_047 "Link 47" {
    effort 73min
    allocate cruncher
    depends !t_046 { gapduration 29min }
  }

  task t_048 "Link 48" {
    effort 73min
    allocate cruncher
    depends !t_047 { gapduration 29min }
  }

  task t_049 "Link 49" {
    effort 73min
    allocate cruncher
    depends !t_048 { gapduration 29min }
  }

  task t_050 "Link 50" {
    effort 73min
    allocate cruncher
    depends !t_049 { gapduration 29min }
  }

  task t_051 "Link 51" {
    effort 73min
    allocate cruncher
    depends !t_050 { gapduration 29min }
  }

  task t_052 "Link 52" {
    effort 73min
    allocate cruncher
    depends !t_051 { gapduration 29min }
  }

  task t_053 "Link 53" {
    effort 73min
    allocate cruncher
    depends !t_052 { gapduration 29min }
  }

  task t_054 "Link 54" {
    effort 73min
    allocate cruncher
    depends !t_053 { gapduration 29min }
  }

  task t_055 "Link 55" {
    effort 73min
    allocate cruncher
    depends !t_054 { gapduration 29min }
  }

  task t_056 "Link 56" {
    effort 73min
    allocate cruncher
    depends !t_055 { gapduration 29min }
  }

  task t_057 "Link 57" {
    effort 73min
    allocate cruncher
    depends !t_056 { gapduration 29min }
  }

  task t_058 "Link 58" {
    effort 73min
    allocate cruncher
    depends !t_057 { gapduration 29min }
  }

  task t_059 "Link 59" {
    effort 73min
    allocate cruncher
    depends !t_058 { gapduration 29min }
  }

  task t_060 "Link 60" {
    effort 73min
    allocate cruncher
    depends !t_059 { gapduration 29min }
  }

  task t_061 "Link 61" {
    effort 73min
    allocate cruncher
    depends !t_060 { gapduration 29min }
  }

  task t_062 "Link 62" {
    effort 73min
    allocate cruncher
    depends !t_061 { gapduration 29min }
  }

  task t_063 "Link 63" {
    effort 73min
    allocate cruncher
    depends !t_062 { gapduration 29min }
  }

  task t_064 "Link 64" {
    effort 73min
    allocate cruncher
    depends !t_063 { gapduration 29min }
  }

  task t_065 "Link 65" {
    effort 73min
    allocate cruncher
    depends !t_064 { gapduration 29min }
  }

  task t_066 "Link 66" {
    effort 73min
    allocate cruncher
    depends !t_065 { gapduration 29min }
  }

  task t_067 "Link 67" {
    effort 73min
    allocate cruncher
    depends !t_066 { gapduration 29min }
  }

  task t_068 "Link 68" {
    effort 73min
    allocate cruncher
    depends !t_067 { gapduration 29min }
  }

  task t_069 "Link 69" {
    effort 73min
    allocate cruncher
    depends !t_068 { gapduration 29min }
  }

  task t_070 "Link 70" {
    effort 73min
    allocate cruncher
    depends !t_069 { gapduration 29min }
  }

  task t_071 "Link 71" {
    effort 73min
    allocate cruncher
    depends !t_070 { gapduration 29min }
  }

  task t_072 "Link 72" {
    effort 73min
    allocate cruncher
    depends !t_071 { gapduration 29min }
  }

  task t_073 "Link 73" {
    effort 73min
    allocate cruncher
    depends !t_072 { gapduration 29min }
  }

  task t_074 "Link 74" {
    effort 73min
    allocate cruncher
    depends !t_073 { gapduration 29min }
  }

  task t_075 "Link 75" {
    effort 73min
    allocate cruncher
    depends !t_074 { gapduration 29min }
  }

  task t_076 "Link 76" {
    effort 73min
    allocate cruncher
    depends !t_075 { gapduration 29min }
  }

  task t_077 "Link 77" {
    effort 73min
    allocate cruncher
    depends !t_076 { gapduration 29min }
  }

  task t_078 "Link 78" {
    effort 73min
    allocate cruncher
    depends !t_077 { gapduration 29min }
  }

  task t_079 "Link 79" {
    effort 73min
    allocate cruncher
    depends !t_078 { gapduration 29min }
  }

  task t_080 "Link 80" {
    effort 73min
    allocate cruncher
    depends !t_079 { gapduration 29min }
  }

  task t_081 "Link 81" {
    effort 73min
    allocate cruncher
    depends !t_080 { gapduration 29min }
  }

  task t_082 "Link 82" {
    effort 73min
    allocate cruncher
    depends !t_081 { gapduration 29min }
  }

  task t_083 "Link 83" {
    effort 73min
    allocate cruncher
    depends !t_082 { gapduration 29min }
  }

  task t_084 "Link 84" {
    effort 73min
    allocate cruncher
    depends !t_083 { gapduration 29min }
  }

  task t_085 "Link 85" {
    effort 73min
    allocate cruncher
    depends !t_084 { gapduration 29min }
  }

  task t_086 "Link 86" {
    effort 73min
    allocate cruncher
    depends !t_085 { gapduration 29min }
  }

  task t_087 "Link 87" {
    effort 73min
    allocate cruncher
    depends !t_086 { gapduration 29min }
  }

  task t_088 "Link 88" {
    effort 73min
    allocate cruncher
    depends !t_087 { gapduration 29min }
  }

  task t_089 "Link 89" {
    effort 73min
    allocate cruncher
    depends !t_088 { gapduration 29min }
  }

  task t_090 "Link 90" {
    effort 73min
    allocate cruncher
    depends !t_089 { gapduration 29min }
  }

  task t_091 "Link 91" {
    effort 73min
    allocate cruncher
    depends !t_090 { gapduration 29min }
  }

  task t_092 "Link 92" {
    effort 73min
    allocate cruncher
    depends !t_091 { gapduration 29min }
  }

  task t_093 "Link 93" {
    effort 73min
    allocate cruncher
    depends !t_092 { gapduration 29min }
  }

  task t_094 "Link 94" {
    effort 73min
    allocate cruncher
    depends !t_093 { gapduration 29min }
  }

  task t_095 "Link 95" {
    effort 73min
    allocate cruncher
    depends !t_094 { gapduration 29min }
  }

  task t_096 "Link 96" {
    effort 73min
    allocate cruncher
    depends !t_095 { gapduration 29min }
  }

  task t_097 "Link 97" {
    effort 73min
    allocate cruncher
    depends !t_096 { gapduration 29min }
  }

  task t_098 "Link 98" {
    effort 73min
    allocate cruncher
    depends !t_097 { gapduration 29min }
  }

  task t_099 "Link 99" {
    effort 73min
    allocate cruncher
    depends !t_098 { gapduration 29min }
  }

  task t_100 "Link 100" {
    effort 73min
    allocate cruncher
    depends !t_099 { gapduration 29min }
  }

  task t_101 "Link 101" {
    effort 73min
    allocate cruncher
    depends !t_100 { gapduration 29min }
  }

  task t_102 "Link 102" {
    effort 73min
    allocate cruncher
    depends !t_101 { gapduration 29min }
  }

  task t_103 "Link 103" {
    effort 73min
    allocate cruncher
    depends !t_102 { gapduration 29min }
  }

  task t_104 "Link 104" {
    effort 73min
    allocate cruncher
    depends !t_103 { gapduration 29min }
  }

  task t_105 "Link 105" {
    effort 73min
    allocate cruncher
    depends !t_104 { gapduration 29min }
  }

  task t_106 "Link 106" {
    effort 73min
    allocate cruncher
    depends !t_105 { gapduration 29min }
  }

  task t_107 "Link 107" {
    effort 73min
    allocate cruncher
    depends !t_106 { gapduration 29min }
  }

  task t_108 "Link 108" {
    effort 73min
    allocate cruncher
    depends !t_107 { gapduration 29min }
  }

  task t_109 "Link 109" {
    effort 73min
    allocate cruncher
    depends !t_108 { gapduration 29min }
  }

  task t_110 "Link 110" {
    effort 73min
    allocate cruncher
    depends !t_109 { gapduration 29min }
  }

  task t_111 "Link 111" {
    effort 73min
    allocate cruncher
    depends !t_110 { gapduration 29min }
  }

  task t_112 "Link 112" {
    effort 73min
    allocate cruncher
    depends !t_111 { gapduration 29min }
  }

  task t_113 "Link 113" {
    effort 73min
    allocate cruncher
    depends !t_112 { gapduration 29min }
  }

  task t_114 "Link 114" {
    effort 73min
    allocate cruncher
    depends !t_113 { gapduration 29min }
  }

  task t_115 "Link 115" {
    effort 73min
    allocate cruncher
    depends !t_114 { gapduration 29min }
  }

  task t_116 "Link 116" {
    effort 73min
    allocate cruncher
    depends !t_115 { gapduration 29min }
  }

  task t_117 "Link 117" {
    effort 73min
    allocate cruncher
    depends !t_116 { gapduration 29min }
  }

  task t_118 "Link 118" {
    effort 73min
    allocate cruncher
    depends !t_117 { gapduration 29min }
  }

  task t_119 "Link 119" {
    effort 73min
    allocate cruncher
    depends !t_118 { gapduration 29min }
  }

  task t_120 "Link 120" {
    effort 73min
    allocate cruncher
    depends !t_119 { gapduration 29min }
  }

  task t_121 "Link 121" {
    effort 73min
    allocate cruncher
    depends !t_120 { gapduration 29min }
  }

  task t_122 "Link 122" {
    effort 73min
    allocate cruncher
    depends !t_121 { gapduration 29min }
  }

  task t_123 "Link 123" {
    effort 73min
    allocate cruncher
    depends !t_122 { gapduration 29min }
  }

  task t_124 "Link 124" {
    effort 73min
    allocate cruncher
    depends !t_123 { gapduration 29min }
  }

  task t_125 "Link 125" {
    effort 73min
    allocate cruncher
    depends !t_124 { gapduration 29min }
  }

  task t_126 "Link 126" {
    effort 73min
    allocate cruncher
    depends !t_125 { gapduration 29min }
  }

  task t_127 "Link 127" {
    effort 73min
    allocate cruncher
    depends !t_126 { gapduration 29min }
  }

  task t_128 "Link 128" {
    effort 73min
    allocate cruncher
    depends !t_127 { gapduration 29min }
  }

  task t_129 "Link 129" {
    effort 73min
    allocate cruncher
    depends !t_128 { gapduration 29min }
  }

  task t_130 "Link 130" {
    effort 73min
    allocate cruncher
    depends !t_129 { gapduration 29min }
  }

  task t_131 "Link 131" {
    effort 73min
    allocate cruncher
    depends !t_130 { gapduration 29min }
  }

  task t_132 "Link 132" {
    effort 73min
    allocate cruncher
    depends !t_131 { gapduration 29min }
  }

  task t_133 "Link 133" {
    effort 73min
    allocate cruncher
    depends !t_132 { gapduration 29min }
  }

  task t_134 "Link 134" {
    effort 73min
    allocate cruncher
    depends !t_133 { gapduration 29min }
  }

  task t_135 "Link 135" {
    effort 73min
    allocate cruncher
    depends !t_134 { gapduration 29min }
  }

  task t_136 "Link 136" {
    effort 73min
    allocate cruncher
    depends !t_135 { gapduration 29min }
  }

  task t_137 "Link 137" {
    effort 73min
    allocate cruncher
    depends !t_136 { gapduration 29min }
  }

  task t_138 "Link 138" {
    effort 73min
    allocate cruncher
    depends !t_137 { gapduration 29min }
  }

  task t_139 "Link 139" {
    effort 73min
    allocate cruncher
    depends !t_138 { gapduration 29min }
  }

  task t_140 "Link 140" {
    effort 73min
    allocate cruncher
    depends !t_139 { gapduration 29min }
  }

  task t_141 "Link 141" {
    effort 73min
    allocate cruncher
    depends !t_140 { gapduration 29min }
  }

  task t_142 "Link 142" {
    effort 73min
    allocate cruncher
    depends !t_141 { gapduration 29min }
  }

  task t_143 "Link 143" {
    effort 73min
    allocate cruncher
    depends !t_142 { gapduration 29min }
  }

  task t_144 "Link 144" {
    effort 73min
    allocate cruncher
    depends !t_143 { gapduration 29min }
  }

  task t_145 "Link 145" {
    effort 73min
    allocate cruncher
    depends !t_144 { gapduration 29min }
  }

  task t_146 "Link 146" {
    effort 73min
    allocate cruncher
    depends !t_145 { gapduration 29min }
  }

  task t_147 "Link 147" {
    effort 73min
    allocate cruncher
    depends !t_146 { gapduration 29min }
  }

  task t_148 "Link 148" {
    effort 73min
    allocate cruncher
    depends !t_147 { gapduration 29min }
  }

  task t_149 "Link 149" {
    effort 73min
    allocate cruncher
    depends !t_148 { gapduration 29min }
  }

  task t_150 "Link 150" {
    effort 73min
    allocate cruncher
    depends !t_149 { gapduration 29min }
  }

  task t_151 "Link 151" {
    effort 73min
    allocate cruncher
    depends !t_150 { gapduration 29min }
  }

  task t_152 "Link 152" {
    effort 73min
    allocate cruncher
    depends !t_151 { gapduration 29min }
  }

  task t_153 "Link 153" {
    effort 73min
    allocate cruncher
    depends !t_152 { gapduration 29min }
  }

  task t_154 "Link 154" {
    effort 73min
    allocate cruncher
    depends !t_153 { gapduration 29min }
  }

  task t_155 "Link 155" {
    effort 73min
    allocate cruncher
    depends !t_154 { gapduration 29min }
  }

  task t_156 "Link 156" {
    effort 73min
    allocate cruncher
    depends !t_155 { gapduration 29min }
  }

  task t_157 "Link 157" {
    effort 73min
    allocate cruncher
    depends !t_156 { gapduration 29min }
  }

  task t_158 "Link 158" {
    effort 73min
    allocate cruncher
    depends !t_157 { gapduration 29min }
  }

  task t_159 "Link 159" {
    effort 73min
    allocate cruncher
    depends !t_158 { gapduration 29min }
  }

  task t_160 "Link 160" {
    effort 73min
    allocate cruncher
    depends !t_159 { gapduration 29min }
  }

  task t_161 "Link 161" {
    effort 73min
    allocate cruncher
    depends !t_160 { gapduration 29min }
  }

  task t_162 "Link 162" {
    effort 73min
    allocate cruncher
    depends !t_161 { gapduration 29min }
  }

  task t_163 "Link 163" {
    effort 73min
    allocate cruncher
    depends !t_162 { gapduration 29min }
  }

  task t_164 "Link 164" {
    effort 73min
    allocate cruncher
    depends !t_163 { gapduration 29min }
  }

  task t_165 "Link 165" {
    effort 73min
    allocate cruncher
    depends !t_164 { gapduration 29min }
  }

  task t_166 "Link 166" {
    effort 73min
    allocate cruncher
    depends !t_165 { gapduration 29min }
  }

  task t_167 "Link 167" {
    effort 73min
    allocate cruncher
    depends !t_166 { gapduration 29min }
  }

  task t_168 "Link 168" {
    effort 73min
    allocate cruncher
    depends !t_167 { gapduration 29min }
  }

  task t_169 "Link 169" {
    effort 73min
    allocate cruncher
    depends !t_168 { gapduration 29min }
  }

  task t_170 "Link 170" {
    effort 73min
    allocate cruncher
    depends !t_169 { gapduration 29min }
  }

  task t_171 "Link 171" {
    effort 73min
    allocate cruncher
    depends !t_170 { gapduration 29min }
  }

  task t_172 "Link 172" {
    effort 73min
    allocate cruncher
    depends !t_171 { gapduration 29min }
  }

  task t_173 "Link 173" {
    effort 73min
    allocate cruncher
    depends !t_172 { gapduration 29min }
  }

  task t_174 "Link 174" {
    effort 73min
    allocate cruncher
    depends !t_173 { gapduration 29min }
  }

  task t_175 "Link 175" {
    effort 73min
    allocate cruncher
    depends !t_174 { gapduration 29min }
  }

  task t_176 "Link 176" {
    effort 73min
    allocate cruncher
    depends !t_175 { gapduration 29min }
  }

  task t_177 "Link 177" {
    effort 73min
    allocate cruncher
    depends !t_176 { gapduration 29min }
  }

  task t_178 "Link 178" {
    effort 73min
    allocate cruncher
    depends !t_177 { gapduration 29min }
  }

  task t_179 "Link 179" {
    effort 73min
    allocate cruncher
    depends !t_178 { gapduration 29min }
  }

  task t_180 "Link 180" {
    effort 73min
    allocate cruncher
    depends !t_179 { gapduration 29min }
  }

  task t_181 "Link 181" {
    effort 73min
    allocate cruncher
    depends !t_180 { gapduration 29min }
  }

  task t_182 "Link 182" {
    effort 73min
    allocate cruncher
    depends !t_181 { gapduration 29min }
  }

  task t_183 "Link 183" {
    effort 73min
    allocate cruncher
    depends !t_182 { gapduration 29min }
  }

  task t_184 "Link 184" {
    effort 73min
    allocate cruncher
    depends !t_183 { gapduration 29min }
  }

  task t_185 "Link 185" {
    effort 73min
    allocate cruncher
    depends !t_184 { gapduration 29min }
  }

  task t_186 "Link 186" {
    effort 73min
    allocate cruncher
    depends !t_185 { gapduration 29min }
  }

  task t_187 "Link 187" {
    effort 73min
    allocate cruncher
    depends !t_186 { gapduration 29min }
  }

  task t_188 "Link 188" {
    effort 73min
    allocate cruncher
    depends !t_187 { gapduration 29min }
  }

  task t_189 "Link 189" {
    effort 73min
    allocate cruncher
    depends !t_188 { gapduration 29min }
  }

  task t_190 "Link 190" {
    effort 73min
    allocate cruncher
    depends !t_189 { gapduration 29min }
  }

  task t_191 "Link 191" {
    effort 73min
    allocate cruncher
    depends !t_190 { gapduration 29min }
  }

  task t_192 "Link 192" {
    effort 73min
    allocate cruncher
    depends !t_191 { gapduration 29min }
  }

  task t_193 "Link 193" {
    effort 73min
    allocate cruncher
    depends !t_192 { gapduration 29min }
  }

  task t_194 "Link 194" {
    effort 73min
    allocate cruncher
    depends !t_193 { gapduration 29min }
  }

  task t_195 "Link 195" {
    effort 73min
    allocate cruncher
    depends !t_194 { gapduration 29min }
  }

  task t_196 "Link 196" {
    effort 73min
    allocate cruncher
    depends !t_195 { gapduration 29min }
  }

  task t_197 "Link 197" {
    effort 73min
    allocate cruncher
    depends !t_196 { gapduration 29min }
  }

  task t_198 "Link 198" {
    effort 73min
    allocate cruncher
    depends !t_197 { gapduration 29min }
  }

  task t_199 "Link 199" {
    effort 73min
    allocate cruncher
    depends !t_198 { gapduration 29min }
  }

  task t_200 "Link 200" {
    effort 73min
    allocate cruncher
    depends !t_199 { gapduration 29min }
  }

  task t_201 "Link 201" {
    effort 73min
    allocate cruncher
    depends !t_200 { gapduration 29min }
  }

  task t_202 "Link 202" {
    effort 73min
    allocate cruncher
    depends !t_201 { gapduration 29min }
  }

  task t_203 "Link 203" {
    effort 73min
    allocate cruncher
    depends !t_202 { gapduration 29min }
  }

  task t_204 "Link 204" {
    effort 73min
    allocate cruncher
    depends !t_203 { gapduration 29min }
  }

  task t_205 "Link 205" {
    effort 73min
    allocate cruncher
    depends !t_204 { gapduration 29min }
  }

  task t_206 "Link 206" {
    effort 73min
    allocate cruncher
    depends !t_205 { gapduration 29min }
  }

  task t_207 "Link 207" {
    effort 73min
    allocate cruncher
    depends !t_206 { gapduration 29min }
  }

  task t_208 "Link 208" {
    effort 73min
    allocate cruncher
    depends !t_207 { gapduration 29min }
  }

  task t_209 "Link 209" {
    effort 73min
    allocate cruncher
    depends !t_208 { gapduration 29min }
  }

  task t_210 "Link 210" {
    effort 73min
    allocate cruncher
    depends !t_209 { gapduration 29min }
  }

  task t_211 "Link 211" {
    effort 73min
    allocate cruncher
    depends !t_210 { gapduration 29min }
  }

  task t_212 "Link 212" {
    effort 73min
    allocate cruncher
    depends !t_211 { gapduration 29min }
  }

  task t_213 "Link 213" {
    effort 73min
    allocate cruncher
    depends !t_212 { gapduration 29min }
  }

  task t_214 "Link 214" {
    effort 73min
    allocate cruncher
    depends !t_213 { gapduration 29min }
  }

  task t_215 "Link 215" {
    effort 73min
    allocate cruncher
    depends !t_214 { gapduration 29min }
  }

  task t_216 "Link 216" {
    effort 73min
    allocate cruncher
    depends !t_215 { gapduration 29min }
  }

  task t_217 "Link 217" {
    effort 73min
    allocate cruncher
    depends !t_216 { gapduration 29min }
  }

  task t_218 "Link 218" {
    effort 73min
    allocate cruncher
    depends !t_217 { gapduration 29min }
  }

  task t_219 "Link 219" {
    effort 73min
    allocate cruncher
    depends !t_218 { gapduration 29min }
  }

  task t_220 "Link 220" {
    effort 73min
    allocate cruncher
    depends !t_219 { gapduration 29min }
  }

  task t_221 "Link 221" {
    effort 73min
    allocate cruncher
    depends !t_220 { gapduration 29min }
  }

  task t_222 "Link 222" {
    effort 73min
    allocate cruncher
    depends !t_221 { gapduration 29min }
  }

  task t_223 "Link 223" {
    effort 73min
    allocate cruncher
    depends !t_222 { gapduration 29min }
  }

  task t_224 "Link 224" {
    effort 73min
    allocate cruncher
    depends !t_223 { gapduration 29min }
  }

  task t_225 "Link 225" {
    effort 73min
    allocate cruncher
    depends !t_224 { gapduration 29min }
  }

  task t_226 "Link 226" {
    effort 73min
    allocate cruncher
    depends !t_225 { gapduration 29min }
  }

  task t_227 "Link 227" {
    effort 73min
    allocate cruncher
    depends !t_226 { gapduration 29min }
  }

  task t_228 "Link 228" {
    effort 73min
    allocate cruncher
    depends !t_227 { gapduration 29min }
  }

  task t_229 "Link 229" {
    effort 73min
    allocate cruncher
    depends !t_228 { gapduration 29min }
  }

  task t_230 "Link 230" {
    effort 73min
    allocate cruncher
    depends !t_229 { gapduration 29min }
  }

  task t_231 "Link 231" {
    effort 73min
    allocate cruncher
    depends !t_230 { gapduration 29min }
  }

  task t_232 "Link 232" {
    effort 73min
    allocate cruncher
    depends !t_231 { gapduration 29min }
  }

  task t_233 "Link 233" {
    effort 73min
    allocate cruncher
    depends !t_232 { gapduration 29min }
  }

  task t_234 "Link 234" {
    effort 73min
    allocate cruncher
    depends !t_233 { gapduration 29min }
  }

  task t_235 "Link 235" {
    effort 73min
    allocate cruncher
    depends !t_234 { gapduration 29min }
  }

  task t_236 "Link 236" {
    effort 73min
    allocate cruncher
    depends !t_235 { gapduration 29min }
  }

  task t_237 "Link 237" {
    effort 73min
    allocate cruncher
    depends !t_236 { gapduration 29min }
  }

  task t_238 "Link 238" {
    effort 73min
    allocate cruncher
    depends !t_237 { gapduration 29min }
  }

  task t_239 "Link 239" {
    effort 73min
    allocate cruncher
    depends !t_238 { gapduration 29min }
  }

  task t_240 "Link 240" {
    effort 73min
    allocate cruncher
    depends !t_239 { gapduration 29min }
  }

  task t_241 "Link 241" {
    effort 73min
    allocate cruncher
    depends !t_240 { gapduration 29min }
  }

  task t_242 "Link 242" {
    effort 73min
    allocate cruncher
    depends !t_241 { gapduration 29min }
  }

  task t_243 "Link 243" {
    effort 73min
    allocate cruncher
    depends !t_242 { gapduration 29min }
  }

  task t_244 "Link 244" {
    effort 73min
    allocate cruncher
    depends !t_243 { gapduration 29min }
  }

  task t_245 "Link 245" {
    effort 73min
    allocate cruncher
    depends !t_244 { gapduration 29min }
  }

  task t_246 "Link 246" {
    effort 73min
    allocate cruncher
    depends !t_245 { gapduration 29min }
  }

  task t_247 "Link 247" {
    effort 73min
    allocate cruncher
    depends !t_246 { gapduration 29min }
  }

  task t_248 "Link 248" {
    effort 73min
    allocate cruncher
    depends !t_247 { gapduration 29min }
  }

  task t_249 "Link 249" {
    effort 73min
    allocate cruncher
    depends !t_248 { gapduration 29min }
  }

  task t_250 "Link 250" {
    effort 73min
    allocate cruncher
    depends !t_249 { gapduration 29min }
  }

  task t_251 "Link 251" {
    effort 73min
    allocate cruncher
    depends !t_250 { gapduration 29min }
  }

  task t_252 "Link 252" {
    effort 73min
    allocate cruncher
    depends !t_251 { gapduration 29min }
  }

  task t_253 "Link 253" {
    effort 73min
    allocate cruncher
    depends !t_252 { gapduration 29min }
  }

  task t_254 "Link 254" {
    effort 73min
    allocate cruncher
    depends !t_253 { gapduration 29min }
  }

  task t_255 "Link 255" {
    effort 73min
    allocate cruncher
    depends !t_254 { gapduration 29min }
  }

  task t_256 "Link 256" {
    effort 73min
    allocate cruncher
    depends !t_255 { gapduration 29min }
  }

  task t_257 "Link 257" {
    effort 73min
    allocate cruncher
    depends !t_256 { gapduration 29min }
  }

  task t_258 "Link 258" {
    effort 73min
    allocate cruncher
    depends !t_257 { gapduration 29min }
  }

  task t_259 "Link 259" {
    effort 73min
    allocate cruncher
    depends !t_258 { gapduration 29min }
  }

  task t_260 "Link 260" {
    effort 73min
    allocate cruncher
    depends !t_259 { gapduration 29min }
  }

  task t_261 "Link 261" {
    effort 73min
    allocate cruncher
    depends !t_260 { gapduration 29min }
  }

  task t_262 "Link 262" {
    effort 73min
    allocate cruncher
    depends !t_261 { gapduration 29min }
  }

  task t_263 "Link 263" {
    effort 73min
    allocate cruncher
    depends !t_262 { gapduration 29min }
  }

  task t_264 "Link 264" {
    effort 73min
    allocate cruncher
    depends !t_263 { gapduration 29min }
  }

  task t_265 "Link 265" {
    effort 73min
    allocate cruncher
    depends !t_264 { gapduration 29min }
  }

  task t_266 "Link 266" {
    effort 73min
    allocate cruncher
    depends !t_265 { gapduration 29min }
  }

  task t_267 "Link 267" {
    effort 73min
    allocate cruncher
    depends !t_266 { gapduration 29min }
  }

  task t_268 "Link 268" {
    effort 73min
    allocate cruncher
    depends !t_267 { gapduration 29min }
  }

  task t_269 "Link 269" {
    effort 73min
    allocate cruncher
    depends !t_268 { gapduration 29min }
  }

  task t_270 "Link 270" {
    effort 73min
    allocate cruncher
    depends !t_269 { gapduration 29min }
  }

  task t_271 "Link 271" {
    effort 73min
    allocate cruncher
    depends !t_270 { gapduration 29min }
  }

  task t_272 "Link 272" {
    effort 73min
    allocate cruncher
    depends !t_271 { gapduration 29min }
  }

  task t_273 "Link 273" {
    effort 73min
    allocate cruncher
    depends !t_272 { gapduration 29min }
  }

  task t_274 "Link 274" {
    effort 73min
    allocate cruncher
    depends !t_273 { gapduration 29min }
  }

  task t_275 "Link 275" {
    effort 73min
    allocate cruncher
    depends !t_274 { gapduration 29min }
  }

  task t_276 "Link 276" {
    effort 73min
    allocate cruncher
    depends !t_275 { gapduration 29min }
  }

  task t_277 "Link 277" {
    effort 73min
    allocate cruncher
    depends !t_276 { gapduration 29min }
  }

  task t_278 "Link 278" {
    effort 73min
    allocate cruncher
    depends !t_277 { gapduration 29min }
  }

  task t_279 "Link 279" {
    effort 73min
    allocate cruncher
    depends !t_278 { gapduration 29min }
  }

  task t_280 "Link 280" {
    effort 73min
    allocate cruncher
    depends !t_279 { gapduration 29min }
  }

  task t_281 "Link 281" {
    effort 73min
    allocate cruncher
    depends !t_280 { gapduration 29min }
  }

  task t_282 "Link 282" {
    effort 73min
    allocate cruncher
    depends !t_281 { gapduration 29min }
  }

  task t_283 "Link 283" {
    effort 73min
    allocate cruncher
    depends !t_282 { gapduration 29min }
  }

  task t_284 "Link 284" {
    effort 73min
    allocate cruncher
    depends !t_283 { gapduration 29min }
  }

  task t_285 "Link 285" {
    effort 73min
    allocate cruncher
    depends !t_284 { gapduration 29min }
  }

  task t_286 "Link 286" {
    effort 73min
    allocate cruncher
    depends !t_285 { gapduration 29min }
  }

  task t_287 "Link 287" {
    effort 73min
    allocate cruncher
    depends !t_286 { gapduration 29min }
  }

  task t_288 "Link 288" {
    effort 73min
    allocate cruncher
    depends !t_287 { gapduration 29min }
  }

  task t_289 "Link 289" {
    effort 73min
    allocate cruncher
    depends !t_288 { gapduration 29min }
  }

  task t_290 "Link 290" {
    effort 73min
    allocate cruncher
    depends !t_289 { gapduration 29min }
  }

  task t_291 "Link 291" {
    effort 73min
    allocate cruncher
    depends !t_290 { gapduration 29min }
  }

  task t_292 "Link 292" {
    effort 73min
    allocate cruncher
    depends !t_291 { gapduration 29min }
  }

  task t_293 "Link 293" {
    effort 73min
    allocate cruncher
    depends !t_292 { gapduration 29min }
  }

  task t_294 "Link 294" {
    effort 73min
    allocate cruncher
    depends !t_293 { gapduration 29min }
  }

  task t_295 "Link 295" {
    effort 73min
    allocate cruncher
    depends !t_294 { gapduration 29min }
  }

  task t_296 "Link 296" {
    effort 73min
    allocate cruncher
    depends !t_295 { gapduration 29min }
  }

  task t_297 "Link 297" {
    effort 73min
    allocate cruncher
    depends !t_296 { gapduration 29min }
  }

  task t_298 "Link 298" {
    effort 73min
    allocate cruncher
    depends !t_297 { gapduration 29min }
  }

  task t_299 "Link 299" {
    effort 73min
    allocate cruncher
    depends !t_298 { gapduration 29min }
  }

  task t_300 "Link 300" {
    effort 73min
    allocate cruncher
    depends !t_299 { gapduration 29min }
  }

  task t_301 "Link 301" {
    effort 73min
    allocate cruncher
    depends !t_300 { gapduration 29min }
  }

  task t_302 "Link 302" {
    effort 73min
    allocate cruncher
    depends !t_301 { gapduration 29min }
  }

  task t_303 "Link 303" {
    effort 73min
    allocate cruncher
    depends !t_302 { gapduration 29min }
  }

  task t_304 "Link 304" {
    effort 73min
    allocate cruncher
    depends !t_303 { gapduration 29min }
  }

  task t_305 "Link 305" {
    effort 73min
    allocate cruncher
    depends !t_304 { gapduration 29min }
  }

  task t_306 "Link 306" {
    effort 73min
    allocate cruncher
    depends !t_305 { gapduration 29min }
  }

  task t_307 "Link 307" {
    effort 73min
    allocate cruncher
    depends !t_306 { gapduration 29min }
  }

  task t_308 "Link 308" {
    effort 73min
    allocate cruncher
    depends !t_307 { gapduration 29min }
  }

  task t_309 "Link 309" {
    effort 73min
    allocate cruncher
    depends !t_308 { gapduration 29min }
  }

  task t_310 "Link 310" {
    effort 73min
    allocate cruncher
    depends !t_309 { gapduration 29min }
  }

  task t_311 "Link 311" {
    effort 73min
    allocate cruncher
    depends !t_310 { gapduration 29min }
  }

  task t_312 "Link 312" {
    effort 73min
    allocate cruncher
    depends !t_311 { gapduration 29min }
  }

  task t_313 "Link 313" {
    effort 73min
    allocate cruncher
    depends !t_312 { gapduration 29min }
  }

  task t_314 "Link 314" {
    effort 73min
    allocate cruncher
    depends !t_313 { gapduration 29min }
  }

  task t_315 "Link 315" {
    effort 73min
    allocate cruncher
    depends !t_314 { gapduration 29min }
  }

  task t_316 "Link 316" {
    effort 73min
    allocate cruncher
    depends !t_315 { gapduration 29min }
  }

  task t_317 "Link 317" {
    effort 73min
    allocate cruncher
    depends !t_316 { gapduration 29min }
  }

  task t_318 "Link 318" {
    effort 73min
    allocate cruncher
    depends !t_317 { gapduration 29min }
  }

  task t_319 "Link 319" {
    effort 73min
    allocate cruncher
    depends !t_318 { gapduration 29min }
  }

  task t_320 "Link 320" {
    effort 73min
    allocate cruncher
    depends !t_319 { gapduration 29min }
  }

  task t_321 "Link 321" {
    effort 73min
    allocate cruncher
    depends !t_320 { gapduration 29min }
  }

  task t_322 "Link 322" {
    effort 73min
    allocate cruncher
    depends !t_321 { gapduration 29min }
  }

  task t_323 "Link 323" {
    effort 73min
    allocate cruncher
    depends !t_322 { gapduration 29min }
  }

  task t_324 "Link 324" {
    effort 73min
    allocate cruncher
    depends !t_323 { gapduration 29min }
  }

  task t_325 "Link 325" {
    effort 73min
    allocate cruncher
    depends !t_324 { gapduration 29min }
  }

  task t_326 "Link 326" {
    effort 73min
    allocate cruncher
    depends !t_325 { gapduration 29min }
  }

  task t_327 "Link 327" {
    effort 73min
    allocate cruncher
    depends !t_326 { gapduration 29min }
  }

  task t_328 "Link 328" {
    effort 73min
    allocate cruncher
    depends !t_327 { gapduration 29min }
  }

  task t_329 "Link 329" {
    effort 73min
    allocate cruncher
    depends !t_328 { gapduration 29min }
  }

  task t_330 "Link 330" {
    effort 73min
    allocate cruncher
    depends !t_329 { gapduration 29min }
  }

  task t_331 "Link 331" {
    effort 73min
    allocate cruncher
    depends !t_330 { gapduration 29min }
  }

  task t_332 "Link 332" {
    effort 73min
    allocate cruncher
    depends !t_331 { gapduration 29min }
  }

  task t_333 "Link 333" {
    effort 73min
    allocate cruncher
    depends !t_332 { gapduration 29min }
  }

  task t_334 "Link 334" {
    effort 73min
    allocate cruncher
    depends !t_333 { gapduration 29min }
  }

  task t_335 "Link 335" {
    effort 73min
    allocate cruncher
    depends !t_334 { gapduration 29min }
  }

  task t_336 "Link 336" {
    effort 73min
    allocate cruncher
    depends !t_335 { gapduration 29min }
  }

  task t_337 "Link 337" {
    effort 73min
    allocate cruncher
    depends !t_336 { gapduration 29min }
  }

  task t_338 "Link 338" {
    effort 73min
    allocate cruncher
    depends !t_337 { gapduration 29min }
  }

  task t_339 "Link 339" {
    effort 73min
    allocate cruncher
    depends !t_338 { gapduration 29min }
  }

  task t_340 "Link 340" {
    effort 73min
    allocate cruncher
    depends !t_339 { gapduration 29min }
  }

  task t_341 "Link 341" {
    effort 73min
    allocate cruncher
    depends !t_340 { gapduration 29min }
  }

  task t_342 "Link 342" {
    effort 73min
    allocate cruncher
    depends !t_341 { gapduration 29min }
  }

  task t_343 "Link 343" {
    effort 73min
    allocate cruncher
    depends !t_342 { gapduration 29min }
  }

  task t_344 "Link 344" {
    effort 73min
    allocate cruncher
    depends !t_343 { gapduration 29min }
  }

  task t_345 "Link 345" {
    effort 73min
    allocate cruncher
    depends !t_344 { gapduration 29min }
  }

  task t_346 "Link 346" {
    effort 73min
    allocate cruncher
    depends !t_345 { gapduration 29min }
  }

  task t_347 "Link 347" {
    effort 73min
    allocate cruncher
    depends !t_346 { gapduration 29min }
  }

  task t_348 "Link 348" {
    effort 73min
    allocate cruncher
    depends !t_347 { gapduration 29min }
  }

  task t_349 "Link 349" {
    effort 73min
    allocate cruncher
    depends !t_348 { gapduration 29min }
  }

  task t_350 "Link 350" {
    effort 73min
    allocate cruncher
    depends !t_349 { gapduration 29min }
  }

  task t_351 "Link 351" {
    effort 73min
    allocate cruncher
    depends !t_350 { gapduration 29min }
  }

  task t_352 "Link 352" {
    effort 73min
    allocate cruncher
    depends !t_351 { gapduration 29min }
  }

  task t_353 "Link 353" {
    effort 73min
    allocate cruncher
    depends !t_352 { gapduration 29min }
  }

  task t_354 "Link 354" {
    effort 73min
    allocate cruncher
    depends !t_353 { gapduration 29min }
  }

  task t_355 "Link 355" {
    effort 73min
    allocate cruncher
    depends !t_354 { gapduration 29min }
  }

  task t_356 "Link 356" {
    effort 73min
    allocate cruncher
    depends !t_355 { gapduration 29min }
  }

  task t_357 "Link 357" {
    effort 73min
    allocate cruncher
    depends !t_356 { gapduration 29min }
  }

  task t_358 "Link 358" {
    effort 73min
    allocate cruncher
    depends !t_357 { gapduration 29min }
  }

  task t_359 "Link 359" {
    effort 73min
    allocate cruncher
    depends !t_358 { gapduration 29min }
  }

  task t_360 "Link 360" {
    effort 73min
    allocate cruncher
    depends !t_359 { gapduration 29min }
  }

  task t_361 "Link 361" {
    effort 73min
    allocate cruncher
    depends !t_360 { gapduration 29min }
  }

  task t_362 "Link 362" {
    effort 73min
    allocate cruncher
    depends !t_361 { gapduration 29min }
  }

  task t_363 "Link 363" {
    effort 73min
    allocate cruncher
    depends !t_362 { gapduration 29min }
  }

  task t_364 "Link 364" {
    effort 73min
    allocate cruncher
    depends !t_363 { gapduration 29min }
  }

  task t_365 "Link 365" {
    effort 73min
    allocate cruncher
    depends !t_364 { gapduration 29min }
  }

  task t_366 "Link 366" {
    effort 73min
    allocate cruncher
    depends !t_365 { gapduration 29min }
  }

  task t_367 "Link 367" {
    effort 73min
    allocate cruncher
    depends !t_366 { gapduration 29min }
  }

  task t_368 "Link 368" {
    effort 73min
    allocate cruncher
    depends !t_367 { gapduration 29min }
  }

  task t_369 "Link 369" {
    effort 73min
    allocate cruncher
    depends !t_368 { gapduration 29min }
  }

  task t_370 "Link 370" {
    effort 73min
    allocate cruncher
    depends !t_369 { gapduration 29min }
  }

  task t_371 "Link 371" {
    effort 73min
    allocate cruncher
    depends !t_370 { gapduration 29min }
  }

  task t_372 "Link 372" {
    effort 73min
    allocate cruncher
    depends !t_371 { gapduration 29min }
  }

  task t_373 "Link 373" {
    effort 73min
    allocate cruncher
    depends !t_372 { gapduration 29min }
  }

  task t_374 "Link 374" {
    effort 73min
    allocate cruncher
    depends !t_373 { gapduration 29min }
  }

  task t_375 "Link 375" {
    effort 73min
    allocate cruncher
    depends !t_374 { gapduration 29min }
  }

  task t_376 "Link 376" {
    effort 73min
    allocate cruncher
    depends !t_375 { gapduration 29min }
  }

  task t_377 "Link 377" {
    effort 73min
    allocate cruncher
    depends !t_376 { gapduration 29min }
  }

  task t_378 "Link 378" {
    effort 73min
    allocate cruncher
    depends !t_377 { gapduration 29min }
  }

  task t_379 "Link 379" {
    effort 73min
    allocate cruncher
    depends !t_378 { gapduration 29min }
  }

  task t_380 "Link 380" {
    effort 73min
    allocate cruncher
    depends !t_379 { gapduration 29min }
  }

  task t_381 "Link 381" {
    effort 73min
    allocate cruncher
    depends !t_380 { gapduration 29min }
  }

  task t_382 "Link 382" {
    effort 73min
    allocate cruncher
    depends !t_381 { gapduration 29min }
  }

  task t_383 "Link 383" {
    effort 73min
    allocate cruncher
    depends !t_382 { gapduration 29min }
  }

  task t_384 "Link 384" {
    effort 73min
    allocate cruncher
    depends !t_383 { gapduration 29min }
  }

  task t_385 "Link 385" {
    effort 73min
    allocate cruncher
    depends !t_384 { gapduration 29min }
  }

  task t_386 "Link 386" {
    effort 73min
    allocate cruncher
    depends !t_385 { gapduration 29min }
  }

  task t_387 "Link 387" {
    effort 73min
    allocate cruncher
    depends !t_386 { gapduration 29min }
  }

  task t_388 "Link 388" {
    effort 73min
    allocate cruncher
    depends !t_387 { gapduration 29min }
  }

  task t_389 "Link 389" {
    effort 73min
    allocate cruncher
    depends !t_388 { gapduration 29min }
  }

  task t_390 "Link 390" {
    effort 73min
    allocate cruncher
    depends !t_389 { gapduration 29min }
  }

  task t_391 "Link 391" {
    effort 73min
    allocate cruncher
    depends !t_390 { gapduration 29min }
  }

  task t_392 "Link 392" {
    effort 73min
    allocate cruncher
    depends !t_391 { gapduration 29min }
  }

  task t_393 "Link 393" {
    effort 73min
    allocate cruncher
    depends !t_392 { gapduration 29min }
  }

  task t_394 "Link 394" {
    effort 73min
    allocate cruncher
    depends !t_393 { gapduration 29min }
  }

  task t_395 "Link 395" {
    effort 73min
    allocate cruncher
    depends !t_394 { gapduration 29min }
  }

  task t_396 "Link 396" {
    effort 73min
    allocate cruncher
    depends !t_395 { gapduration 29min }
  }

  task t_397 "Link 397" {
    effort 73min
    allocate cruncher
    depends !t_396 { gapduration 29min }
  }

  task t_398 "Link 398" {
    effort 73min
    allocate cruncher
    depends !t_397 { gapduration 29min }
  }

  task t_399 "Link 399" {
    effort 73min
    allocate cruncher
    depends !t_398 { gapduration 29min }
  }

  task t_400 "Link 400" {
    effort 73min
    allocate cruncher
    depends !t_399 { gapduration 29min }
  }

  task t_401 "Link 401" {
    effort 73min
    allocate cruncher
    depends !t_400 { gapduration 29min }
  }

  task t_402 "Link 402" {
    effort 73min
    allocate cruncher
    depends !t_401 { gapduration 29min }
  }

  task t_403 "Link 403" {
    effort 73min
    allocate cruncher
    depends !t_402 { gapduration 29min }
  }

  task t_404 "Link 404" {
    effort 73min
    allocate cruncher
    depends !t_403 { gapduration 29min }
  }

  task t_405 "Link 405" {
    effort 73min
    allocate cruncher
    depends !t_404 { gapduration 29min }
  }

  task t_406 "Link 406" {
    effort 73min
    allocate cruncher
    depends !t_405 { gapduration 29min }
  }

  task t_407 "Link 407" {
    effort 73min
    allocate cruncher
    depends !t_406 { gapduration 29min }
  }

  task t_408 "Link 408" {
    effort 73min
    allocate cruncher
    depends !t_407 { gapduration 29min }
  }

  task t_409 "Link 409" {
    effort 73min
    allocate cruncher
    depends !t_408 { gapduration 29min }
  }

  task t_410 "Link 410" {
    effort 73min
    allocate cruncher
    depends !t_409 { gapduration 29min }
  }

  task t_411 "Link 411" {
    effort 73min
    allocate cruncher
    depends !t_410 { gapduration 29min }
  }

  task t_412 "Link 412" {
    effort 73min
    allocate cruncher
    depends !t_411 { gapduration 29min }
  }

  task t_413 "Link 413" {
    effort 73min
    allocate cruncher
    depends !t_412 { gapduration 29min }
  }

  task t_414 "Link 414" {
    effort 73min
    allocate cruncher
    depends !t_413 { gapduration 29min }
  }

  task t_415 "Link 415" {
    effort 73min
    allocate cruncher
    depends !t_414 { gapduration 29min }
  }

  task t_416 "Link 416" {
    effort 73min
    allocate cruncher
    depends !t_415 { gapduration 29min }
  }

  task t_417 "Link 417" {
    effort 73min
    allocate cruncher
    depends !t_416 { gapduration 29min }
  }

  task t_418 "Link 418" {
    effort 73min
    allocate cruncher
    depends !t_417 { gapduration 29min }
  }

  task t_419 "Link 419" {
    effort 73min
    allocate cruncher
    depends !t_418 { gapduration 29min }
  }

  task t_420 "Link 420" {
    effort 73min
    allocate cruncher
    depends !t_419 { gapduration 29min }
  }

  task t_421 "Link 421" {
    effort 73min
    allocate cruncher
    depends !t_420 { gapduration 29min }
  }

  task t_422 "Link 422" {
    effort 73min
    allocate cruncher
    depends !t_421 { gapduration 29min }
  }

  task t_423 "Link 423" {
    effort 73min
    allocate cruncher
    depends !t_422 { gapduration 29min }
  }

  task t_424 "Link 424" {
    effort 73min
    allocate cruncher
    depends !t_423 { gapduration 29min }
  }

  task t_425 "Link 425" {
    effort 73min
    allocate cruncher
    depends !t_424 { gapduration 29min }
  }

  task t_426 "Link 426" {
    effort 73min
    allocate cruncher
    depends !t_425 { gapduration 29min }
  }

  task t_427 "Link 427" {
    effort 73min
    allocate cruncher
    depends !t_426 { gapduration 29min }
  }

  task t_428 "Link 428" {
    effort 73min
    allocate cruncher
    depends !t_427 { gapduration 29min }
  }

  task t_429 "Link 429" {
    effort 73min
    allocate cruncher
    depends !t_428 { gapduration 29min }
  }

  task t_430 "Link 430" {
    effort 73min
    allocate cruncher
    depends !t_429 { gapduration 29min }
  }

  task t_431 "Link 431" {
    effort 73min
    allocate cruncher
    depends !t_430 { gapduration 29min }
  }

  task t_432 "Link 432" {
    effort 73min
    allocate cruncher
    depends !t_431 { gapduration 29min }
  }

  task t_433 "Link 433" {
    effort 73min
    allocate cruncher
    depends !t_432 { gapduration 29min }
  }

  task t_434 "Link 434" {
    effort 73min
    allocate cruncher
    depends !t_433 { gapduration 29min }
  }

  task t_435 "Link 435" {
    effort 73min
    allocate cruncher
    depends !t_434 { gapduration 29min }
  }

  task t_436 "Link 436" {
    effort 73min
    allocate cruncher
    depends !t_435 { gapduration 29min }
  }

  task t_437 "Link 437" {
    effort 73min
    allocate cruncher
    depends !t_436 { gapduration 29min }
  }

  task t_438 "Link 438" {
    effort 73min
    allocate cruncher
    depends !t_437 { gapduration 29min }
  }

  task t_439 "Link 439" {
    effort 73min
    allocate cruncher
    depends !t_438 { gapduration 29min }
  }

  task t_440 "Link 440" {
    effort 73min
    allocate cruncher
    depends !t_439 { gapduration 29min }
  }

  task t_441 "Link 441" {
    effort 73min
    allocate cruncher
    depends !t_440 { gapduration 29min }
  }

  task t_442 "Link 442" {
    effort 73min
    allocate cruncher
    depends !t_441 { gapduration 29min }
  }

  task t_443 "Link 443" {
    effort 73min
    allocate cruncher
    depends !t_442 { gapduration 29min }
  }

  task t_444 "Link 444" {
    effort 73min
    allocate cruncher
    depends !t_443 { gapduration 29min }
  }

  task t_445 "Link 445" {
    effort 73min
    allocate cruncher
    depends !t_444 { gapduration 29min }
  }

  task t_446 "Link 446" {
    effort 73min
    allocate cruncher
    depends !t_445 { gapduration 29min }
  }

  task t_447 "Link 447" {
    effort 73min
    allocate cruncher
    depends !t_446 { gapduration 29min }
  }

  task t_448 "Link 448" {
    effort 73min
    allocate cruncher
    depends !t_447 { gapduration 29min }
  }

  task t_449 "Link 449" {
    effort 73min
    allocate cruncher
    depends !t_448 { gapduration 29min }
  }

  task t_450 "Link 450" {
    effort 73min
    allocate cruncher
    depends !t_449 { gapduration 29min }
  }

  task t_451 "Link 451" {
    effort 73min
    allocate cruncher
    depends !t_450 { gapduration 29min }
  }

  task t_452 "Link 452" {
    effort 73min
    allocate cruncher
    depends !t_451 { gapduration 29min }
  }

  task t_453 "Link 453" {
    effort 73min
    allocate cruncher
    depends !t_452 { gapduration 29min }
  }

  task t_454 "Link 454" {
    effort 73min
    allocate cruncher
    depends !t_453 { gapduration 29min }
  }

  task t_455 "Link 455" {
    effort 73min
    allocate cruncher
    depends !t_454 { gapduration 29min }
  }

  task t_456 "Link 456" {
    effort 73min
    allocate cruncher
    depends !t_455 { gapduration 29min }
  }

  task t_457 "Link 457" {
    effort 73min
    allocate cruncher
    depends !t_456 { gapduration 29min }
  }

  task t_458 "Link 458" {
    effort 73min
    allocate cruncher
    depends !t_457 { gapduration 29min }
  }

  task t_459 "Link 459" {
    effort 73min
    allocate cruncher
    depends !t_458 { gapduration 29min }
  }

  task t_460 "Link 460" {
    effort 73min
    allocate cruncher
    depends !t_459 { gapduration 29min }
  }

  task t_461 "Link 461" {
    effort 73min
    allocate cruncher
    depends !t_460 { gapduration 29min }
  }

  task t_462 "Link 462" {
    effort 73min
    allocate cruncher
    depends !t_461 { gapduration 29min }
  }

  task t_463 "Link 463" {
    effort 73min
    allocate cruncher
    depends !t_462 { gapduration 29min }
  }

  task t_464 "Link 464" {
    effort 73min
    allocate cruncher
    depends !t_463 { gapduration 29min }
  }

  task t_465 "Link 465" {
    effort 73min
    allocate cruncher
    depends !t_464 { gapduration 29min }
  }

  task t_466 "Link 466" {
    effort 73min
    allocate cruncher
    depends !t_465 { gapduration 29min }
  }

  task t_467 "Link 467" {
    effort 73min
    allocate cruncher
    depends !t_466 { gapduration 29min }
  }

  task t_468 "Link 468" {
    effort 73min
    allocate cruncher
    depends !t_467 { gapduration 29min }
  }

  task t_469 "Link 469" {
    effort 73min
    allocate cruncher
    depends !t_468 { gapduration 29min }
  }

  task t_470 "Link 470" {
    effort 73min
    allocate cruncher
    depends !t_469 { gapduration 29min }
  }

  task t_471 "Link 471" {
    effort 73min
    allocate cruncher
    depends !t_470 { gapduration 29min }
  }

  task t_472 "Link 472" {
    effort 73min
    allocate cruncher
    depends !t_471 { gapduration 29min }
  }

  task t_473 "Link 473" {
    effort 73min
    allocate cruncher
    depends !t_472 { gapduration 29min }
  }

  task t_474 "Link 474" {
    effort 73min
    allocate cruncher
    depends !t_473 { gapduration 29min }
  }

  task t_475 "Link 475" {
    effort 73min
    allocate cruncher
    depends !t_474 { gapduration 29min }
  }

  task t_476 "Link 476" {
    effort 73min
    allocate cruncher
    depends !t_475 { gapduration 29min }
  }

  task t_477 "Link 477" {
    effort 73min
    allocate cruncher
    depends !t_476 { gapduration 29min }
  }

  task t_478 "Link 478" {
    effort 73min
    allocate cruncher
    depends !t_477 { gapduration 29min }
  }

  task t_479 "Link 479" {
    effort 73min
    allocate cruncher
    depends !t_478 { gapduration 29min }
  }

  task t_480 "Link 480" {
    effort 73min
    allocate cruncher
    depends !t_479 { gapduration 29min }
  }

  task t_481 "Link 481" {
    effort 73min
    allocate cruncher
    depends !t_480 { gapduration 29min }
  }

  task t_482 "Link 482" {
    effort 73min
    allocate cruncher
    depends !t_481 { gapduration 29min }
  }

  task t_483 "Link 483" {
    effort 73min
    allocate cruncher
    depends !t_482 { gapduration 29min }
  }

  task t_484 "Link 484" {
    effort 73min
    allocate cruncher
    depends !t_483 { gapduration 29min }
  }

  task t_485 "Link 485" {
    effort 73min
    allocate cruncher
    depends !t_484 { gapduration 29min }
  }

  task t_486 "Link 486" {
    effort 73min
    allocate cruncher
    depends !t_485 { gapduration 29min }
  }

  task t_487 "Link 487" {
    effort 73min
    allocate cruncher
    depends !t_486 { gapduration 29min }
  }

  task t_488 "Link 488" {
    effort 73min
    allocate cruncher
    depends !t_487 { gapduration 29min }
  }

  task t_489 "Link 489" {
    effort 73min
    allocate cruncher
    depends !t_488 { gapduration 29min }
  }

  task t_490 "Link 490" {
    effort 73min
    allocate cruncher
    depends !t_489 { gapduration 29min }
  }

  task t_491 "Link 491" {
    effort 73min
    allocate cruncher
    depends !t_490 { gapduration 29min }
  }

  task t_492 "Link 492" {
    effort 73min
    allocate cruncher
    depends !t_491 { gapduration 29min }
  }

  task t_493 "Link 493" {
    effort 73min
    allocate cruncher
    depends !t_492 { gapduration 29min }
  }

  task t_494 "Link 494" {
    effort 73min
    allocate cruncher
    depends !t_493 { gapduration 29min }
  }

  task t_495 "Link 495" {
    effort 73min
    allocate cruncher
    depends !t_494 { gapduration 29min }
  }

  task t_496 "Link 496" {
    effort 73min
    allocate cruncher
    depends !t_495 { gapduration 29min }
  }

  task t_497 "Link 497" {
    effort 73min
    allocate cruncher
    depends !t_496 { gapduration 29min }
  }

  task t_498 "Link 498" {
    effort 73min
    allocate cruncher
    depends !t_497 { gapduration 29min }
  }

  task t_499 "Link 499" {
    effort 73min
    allocate cruncher
    depends !t_498 { gapduration 29min }
  }

  task t_500 "Link 500" {
    effort 73min
    allocate cruncher
    depends !t_499 { gapduration 29min }
  }
}

taskreport math_check "math_check" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
  leaftasksonly true
}
```

### Generated Report (JSON)

**Report ID**: `68567fe6e9db7964501e8afdab94500f77dc1d593e1f105b5be62dc4c1c8add4`
**Columns**: 3
**Rows**: 501
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "chain",
      "start": "2024-02-28-08:13",
      "end": "2024-06-06-17:22"
    },
    {
      "id": "chain.t_001",
      "start": "2024-02-28-08:13",
      "end": "2024-02-28-09:26"
    },
    {
      "id": "chain.t_002",
      "start": "2024-02-28-09:55",
      "end": "2024-02-28-11:08"
    },
    {
      "id": "chain.t_003",
      "start": "2024-02-28-11:37",
      "end": "2024-02-28-13:58"
    },
    {
      "id": "chain.t_004",
      "start": "2024-02-28-14:27",
      "end": "2024-02-28-15:40"
    },
    {
      "id": "chain.t_005",
      "start": "2024-02-28-16:09",
      "end": "2024-02-28-17:22"
    },
    {
      "id": "chain.t_006",
      "start": "2024-02-29-08:13",
      "end": "2024-02-29-09:26"
    },
    {
      "id": "chain.t_007",
      "start": "2024-02-29-09:55",
      "end": "2024-02-29-11:08"
    },
    {
      "id": "chain.t_008",
      "start": "2024-02-29-11:37",
      "end": "2024-02-29-13:58"
    },
    {
      "id": "chain.t_009",
      "start": "2024-02-29-14:27",
      "end": "2024-02-29-15:40"
    },
    {
      "id": "chain.t_010",
      "start": "2024-02-29-16:09",
      "end": "2024-02-29-17:22"
    },
    {
      "id": "chain.t_011",
      "start": "2024-03-01-08:13",
      "end": "2024-03-01-09:26"
    },
    {
      "id": "chain.t_012",
      "start": "2024-03-01-09:55",
      "end": "2024-03-01-11:08"
    },
    {
      "id": "chain.t_013",
      "start": "2024-03-01-11:37",
      "end": "2024-03-01-13:58"
    },
    {
      "id": "chain.t_014",
      "start": "2024-03-01-14:27",
      "end": "2024-03-01-15:40"
    },
    {
      "id": "chain.t_015",
      "start": "2024-03-01-16:09",
      "end": "2024-03-01-17:22"
    },
    {
      "id": "chain.t_016",
      "start": "2024-03-02-08:13",
      "end": "2024-03-02-09:26"
    },
    {
      "id": "chain.t_017",
      "start": "2024-03-02-09:55",
      "end": "2024-03-02-11:08"
    },
    {
      "id": "chain.t_018",
      "start": "2024-03-02-11:37",
      "end": "2024-03-02-13:58"
    },
    {
      "id": "chain.t_019",
      "start": "2024-03-02-14:27",
      "end": "2024-03-02-15:40"
    },
    {
      "id": "chain.t_020",
      "start": "2024-03-02-16:09",
      "end": "2024-03-02-17:22"
    },
    {
      "id": "chain.t_021",
      "start": "2024-03-03-08:13",
      "end": "2024-03-03-09:26"
    },
    {
      "id": "chain.t_022",
      "start": "2024-03-03-09:55",
      "end": "2024-03-03-11:08"
    },
    {
      "id": "chain.t_023",
      "start": "2024-03-03-11:37",
      "end": "2024-03-03-13:58"
    },
    {
      "id": "chain.t_024",
      "start": "2024-03-03-14:27",
      "end": "2024-03-03-15:40"
    },
    {
      "id": "chain.t_025",
      "start": "2024-03-03-16:09",
      "end": "2024-03-03-17:22"
    },
    {
      "id": "chain.t_026",
      "start": "2024-03-04-08:13",
      "end": "2024-03-04-09:26"
    },
    {
      "id": "chain.t_027",
      "start": "2024-03-04-09:55",
      "end": "2024-03-04-11:08"
    },
    {
      "id": "chain.t_028",
      "start": "2024-03-04-11:37",
      "end": "2024-03-04-13:58"
    },
    {
      "id": "chain.t_029",
      "start": "2024-03-04-14:27",
      "end": "2024-03-04-15:40"
    },
    {
      "id": "chain.t_030",
      "start": "2024-03-04-16:09",
      "end": "2024-03-04-17:22"
    },
    {
      "id": "chain.t_031",
      "start": "2024-03-05-08:13",
      "end": "2024-03-05-09:26"
    },
    {
      "id": "chain.t_032",
      "start": "2024-03-05-09:55",
      "end": "2024-03-05-11:08"
    },
    {
      "id": "chain.t_033",
      "start": "2024-03-05-11:37",
      "end": "2024-03-05-13:58"
    },
    {
      "id": "chain.t_034",
      "start": "2024-03-05-14:27",
      "end": "2024-03-05-15:40"
    },
    {
      "id": "chain.t_035",
      "start": "2024-03-05-16:09",
      "end": "2024-03-05-17:22"
    },
    {
      "id": "chain.t_036",
      "start": "2024-03-06-08:13",
      "end": "2024-03-06-09:26"
    },
    {
      "id": "chain.t_037",
      "start": "2024-03-06-09:55",
      "end": "2024-03-06-11:08"
    },
    {
      "id": "chain.t_038",
      "start": "2024-03-06-11:37",
      "end": "2024-03-06-13:58"
    },
    {
      "id": "chain.t_039",
      "start": "2024-03-06-14:27",
      "end": "2024-03-06-15:40"
    },
    {
      "id": "chain.t_040",
      "start": "2024-03-06-16:09",
      "end": "2024-03-06-17:22"
    },
    {
      "id": "chain.t_041",
      "start": "2024-03-07-08:13",
      "end": "2024-03-07-09:26"
    },
    {
      "id": "chain.t_042",
      "start": "2024-03-07-09:55",
      "end": "2024-03-07-11:08"
    },
    {
      "id": "chain.t_043",
      "start": "2024-03-07-11:37",
      "end": "2024-03-07-13:58"
    },
    {
      "id": "chain.t_044",
      "start": "2024-03-07-14:27",
      "end": "2024-03-07-15:40"
    },
    {
      "id": "chain.t_045",
      "start": "2024-03-07-16:09",
      "end": "2024-03-07-17:22"
    },
    {
      "id": "chain.t_046",
      "start": "2024-03-08-08:13",
      "end": "2024-03-08-09:26"
    },
    {
      "id": "chain.t_047",
      "start": "2024-03-08-09:55",
      "end": "2024-03-08-11:08"
    },
    {
      "id": "chain.t_048",
      "start": "2024-03-08-11:37",
      "end": "2024-03-08-13:58"
    },
    {
      "id": "chain.t_049",
      "start": "2024-03-08-14:27",
      "end": "2024-03-08-15:40"
    },
    {
      "id": "chain.t_050",
      "start": "2024-03-08-16:09",
      "end": "2024-03-08-17:22"
    },
    {
      "id": "chain.t_051",
      "start": "2024-03-09-08:13",
      "end": "2024-03-09-09:26"
    },
    {
      "id": "chain.t_052",
      "start": "2024-03-09-09:55",
      "end": "2024-03-09-11:08"
    },
    {
      "id": "chain.t_053",
      "start": "2024-03-09-11:37",
      "end": "2024-03-09-13:58"
    },
    {
      "id": "chain.t_054",
      "start": "2024-03-09-14:27",
      "end": "2024-03-09-15:40"
    },
    {
      "id": "chain.t_055",
      "start": "2024-03-09-16:09",
      "end": "2024-03-09-17:22"
    },
    {
      "id": "chain.t_056",
      "start": "2024-03-10-08:13",
      "end": "2024-03-10-09:26"
    },
    {
      "id": "chain.t_057",
      "start": "2024-03-10-09:55",
      "end": "2024-03-10-11:08"
    },
    {
      "id": "chain.t_058",
      "start": "2024-03-10-11:37",
      "end": "2024-03-10-13:58"
    },
    {
      "id": "chain.t_059",
      "start": "2024-03-10-14:27",
      "end": "2024-03-10-15:40"
    },
    {
      "id": "chain.t_060",
      "start": "2024-03-10-16:09",
      "end": "2024-03-10-17:22"
    },
    {
      "id": "chain.t_061",
      "start": "2024-03-11-08:13",
      "end": "2024-03-11-09:26"
    },
    {
      "id": "chain.t_062",
      "start": "2024-03-11-09:55",
      "end": "2024-03-11-11:08"
    },
    {
      "id": "chain.t_063",
      "start": "2024-03-11-11:37",
      "end": "2024-03-11-13:58"
    },
    {
      "id": "chain.t_064",
      "start": "2024-03-11-14:27",
      "end": "2024-03-11-15:40"
    },
    {
      "id": "chain.t_065",
      "start": "2024-03-11-16:09",
      "end": "2024-03-11-17:22"
    },
    {
      "id": "chain.t_066",
      "start": "2024-03-12-08:13",
      "end": "2024-03-12-09:26"
    },
    {
      "id": "chain.t_067",
      "start": "2024-03-12-09:55",
      "end": "2024-03-12-11:08"
    },
    {
      "id": "chain.t_068",
      "start": "2024-03-12-11:37",
      "end": "2024-03-12-13:58"
    },
    {
      "id": "chain.t_069",
      "start": "2024-03-12-14:27",
      "end": "2024-03-12-15:40"
    },
    {
      "id": "chain.t_070",
      "start": "2024-03-12-16:09",
      "end": "2024-03-12-17:22"
    },
    {
      "id": "chain.t_071",
      "start": "2024-03-13-08:13",
      "end": "2024-03-13-09:26"
    },
    {
      "id": "chain.t_072",
      "start": "2024-03-13-09:55",
      "end": "2024-03-13-11:08"
    },
    {
      "id": "chain.t_073",
      "start": "2024-03-13-11:37",
      "end": "2024-03-13-13:58"
    },
    {
      "id": "chain.t_074",
      "start": "2024-03-13-14:27",
      "end": "2024-03-13-15:40"
    },
    {
      "id": "chain.t_075",
      "start": "2024-03-13-16:09",
      "end": "2024-03-13-17:22"
    },
    {
      "id": "chain.t_076",
      "start": "2024-03-14-08:13",
      "end": "2024-03-14-09:26"
    },
    {
      "id": "chain.t_077",
      "start": "2024-03-14-09:55",
      "end": "2024-03-14-11:08"
    },
    {
      "id": "chain.t_078",
      "start": "2024-03-14-11:37",
      "end": "2024-03-14-13:58"
    },
    {
      "id": "chain.t_079",
      "start": "2024-03-14-14:27",
      "end": "2024-03-14-15:40"
    },
    {
      "id": "chain.t_080",
      "start": "2024-03-14-16:09",
      "end": "2024-03-14-17:22"
    },
    {
      "id": "chain.t_081",
      "start": "2024-03-15-08:13",
      "end": "2024-03-15-09:26"
    },
    {
      "id": "chain.t_082",
      "start": "2024-03-15-09:55",
      "end": "2024-03-15-11:08"
    },
    {
      "id": "chain.t_083",
      "start": "2024-03-15-11:37",
      "end": "2024-03-15-13:58"
    },
    {
      "id": "chain.t_084",
      "start": "2024-03-15-14:27",
      "end": "2024-03-15-15:40"
    },
    {
      "id": "chain.t_085",
      "start": "2024-03-15-16:09",
      "end": "2024-03-15-17:22"
    },
    {
      "id": "chain.t_086",
      "start": "2024-03-16-08:13",
      "end": "2024-03-16-09:26"
    },
    {
      "id": "chain.t_087",
      "start": "2024-03-16-09:55",
      "end": "2024-03-16-11:08"
    },
    {
      "id": "chain.t_088",
      "start": "2024-03-16-11:37",
      "end": "2024-03-16-13:58"
    },
    {
      "id": "chain.t_089",
      "start": "2024-03-16-14:27",
      "end": "2024-03-16-15:40"
    },
    {
      "id": "chain.t_090",
      "start": "2024-03-16-16:09",
      "end": "2024-03-16-17:22"
    },
    {
      "id": "chain.t_091",
      "start": "2024-03-17-08:13",
      "end": "2024-03-17-09:26"
    },
    {
      "id": "chain.t_092",
      "start": "2024-03-17-09:55",
      "end": "2024-03-17-11:08"
    },
    {
      "id": "chain.t_093",
      "start": "2024-03-17-11:37",
      "end": "2024-03-17-13:58"
    },
    {
      "id": "chain.t_094",
      "start": "2024-03-17-14:27",
      "end": "2024-03-17-15:40"
    },
    {
      "id": "chain.t_095",
      "start": "2024-03-17-16:09",
      "end": "2024-03-17-17:22"
    },
    {
      "id": "chain.t_096",
      "start": "2024-03-18-08:13",
      "end": "2024-03-18-09:26"
    },
    {
      "id": "chain.t_097",
      "start": "2024-03-18-09:55",
      "end": "2024-03-18-11:08"
    },
    {
      "id": "chain.t_098",
      "start": "2024-03-18-11:37",
      "end": "2024-03-18-13:58"
    },
    {
      "id": "chain.t_099",
      "start": "2024-03-18-14:27",
      "end": "2024-03-18-15:40"
    },
    {
      "id": "chain.t_100",
      "start": "2024-03-18-16:09",
      "end": "2024-03-18-17:22"
    },
    {
      "id": "chain.t_101",
      "start": "2024-03-19-08:13",
      "end": "2024-03-19-09:26"
    },
    {
      "id": "chain.t_102",
      "start": "2024-03-19-09:55",
      "end": "2024-03-19-11:08"
    },
    {
      "id": "chain.t_103",
      "start": "2024-03-19-11:37",
      "end": "2024-03-19-13:58"
    },
    {
      "id": "chain.t_104",
      "start": "2024-03-19-14:27",
      "end": "2024-03-19-15:40"
    },
    {
      "id": "chain.t_105",
      "start": "2024-03-19-16:09",
      "end": "2024-03-19-17:22"
    },
    {
      "id": "chain.t_106",
      "start": "2024-03-20-08:13",
      "end": "2024-03-20-09:26"
    },
    {
      "id": "chain.t_107",
      "start": "2024-03-20-09:55",
      "end": "2024-03-20-11:08"
    },
    {
      "id": "chain.t_108",
      "start": "2024-03-20-11:37",
      "end": "2024-03-20-13:58"
    },
    {
      "id": "chain.t_109",
      "start": "2024-03-20-14:27",
      "end": "2024-03-20-15:40"
    },
    {
      "id": "chain.t_110",
      "start": "2024-03-20-16:09",
      "end": "2024-03-20-17:22"
    },
    {
      "id": "chain.t_111",
      "start": "2024-03-21-08:13",
      "end": "2024-03-21-09:26"
    },
    {
      "id": "chain.t_112",
      "start": "2024-03-21-09:55",
      "end": "2024-03-21-11:08"
    },
    {
      "id": "chain.t_113",
      "start": "2024-03-21-11:37",
      "end": "2024-03-21-13:58"
    },
    {
      "id": "chain.t_114",
      "start": "2024-03-21-14:27",
      "end": "2024-03-21-15:40"
    },
    {
      "id": "chain.t_115",
      "start": "2024-03-21-16:09",
      "end": "2024-03-21-17:22"
    },
    {
      "id": "chain.t_116",
      "start": "2024-03-22-08:13",
      "end": "2024-03-22-09:26"
    },
    {
      "id": "chain.t_117",
      "start": "2024-03-22-09:55",
      "end": "2024-03-22-11:08"
    },
    {
      "id": "chain.t_118",
      "start": "2024-03-22-11:37",
      "end": "2024-03-22-13:58"
    },
    {
      "id": "chain.t_119",
      "start": "2024-03-22-14:27",
      "end": "2024-03-22-15:40"
    },
    {
      "id": "chain.t_120",
      "start": "2024-03-22-16:09",
      "end": "2024-03-22-17:22"
    },
    {
      "id": "chain.t_121",
      "start": "2024-03-23-08:13",
      "end": "2024-03-23-09:26"
    },
    {
      "id": "chain.t_122",
      "start": "2024-03-23-09:55",
      "end": "2024-03-23-11:08"
    },
    {
      "id": "chain.t_123",
      "start": "2024-03-23-11:37",
      "end": "2024-03-23-13:58"
    },
    {
      "id": "chain.t_124",
      "start": "2024-03-23-14:27",
      "end": "2024-03-23-15:40"
    },
    {
      "id": "chain.t_125",
      "start": "2024-03-23-16:09",
      "end": "2024-03-23-17:22"
    },
    {
      "id": "chain.t_126",
      "start": "2024-03-24-08:13",
      "end": "2024-03-24-09:26"
    },
    {
      "id": "chain.t_127",
      "start": "2024-03-24-09:55",
      "end": "2024-03-24-11:08"
    },
    {
      "id": "chain.t_128",
      "start": "2024-03-24-11:37",
      "end": "2024-03-24-13:58"
    },
    {
      "id": "chain.t_129",
      "start": "2024-03-24-14:27",
      "end": "2024-03-24-15:40"
    },
    {
      "id": "chain.t_130",
      "start": "2024-03-24-16:09",
      "end": "2024-03-24-17:22"
    },
    {
      "id": "chain.t_131",
      "start": "2024-03-25-08:13",
      "end": "2024-03-25-09:26"
    },
    {
      "id": "chain.t_132",
      "start": "2024-03-25-09:55",
      "end": "2024-03-25-11:08"
    },
    {
      "id": "chain.t_133",
      "start": "2024-03-25-11:37",
      "end": "2024-03-25-13:58"
    },
    {
      "id": "chain.t_134",
      "start": "2024-03-25-14:27",
      "end": "2024-03-25-15:40"
    },
    {
      "id": "chain.t_135",
      "start": "2024-03-25-16:09",
      "end": "2024-03-25-17:22"
    },
    {
      "id": "chain.t_136",
      "start": "2024-03-26-08:13",
      "end": "2024-03-26-09:26"
    },
    {
      "id": "chain.t_137",
      "start": "2024-03-26-09:55",
      "end": "2024-03-26-11:08"
    },
    {
      "id": "chain.t_138",
      "start": "2024-03-26-11:37",
      "end": "2024-03-26-13:58"
    },
    {
      "id": "chain.t_139",
      "start": "2024-03-26-14:27",
      "end": "2024-03-26-15:40"
    },
    {
      "id": "chain.t_140",
      "start": "2024-03-26-16:09",
      "end": "2024-03-26-17:22"
    },
    {
      "id": "chain.t_141",
      "start": "2024-03-27-08:13",
      "end": "2024-03-27-09:26"
    },
    {
      "id": "chain.t_142",
      "start": "2024-03-27-09:55",
      "end": "2024-03-27-11:08"
    },
    {
      "id": "chain.t_143",
      "start": "2024-03-27-11:37",
      "end": "2024-03-27-13:58"
    },
    {
      "id": "chain.t_144",
      "start": "2024-03-27-14:27",
      "end": "2024-03-27-15:40"
    },
    {
      "id": "chain.t_145",
      "start": "2024-03-27-16:09",
      "end": "2024-03-27-17:22"
    },
    {
      "id": "chain.t_146",
      "start": "2024-03-28-08:13",
      "end": "2024-03-28-09:26"
    },
    {
      "id": "chain.t_147",
      "start": "2024-03-28-09:55",
      "end": "2024-03-28-11:08"
    },
    {
      "id": "chain.t_148",
      "start": "2024-03-28-11:37",
      "end": "2024-03-28-13:58"
    },
    {
      "id": "chain.t_149",
      "start": "2024-03-28-14:27",
      "end": "2024-03-28-15:40"
    },
    {
      "id": "chain.t_150",
      "start": "2024-03-28-16:09",
      "end": "2024-03-28-17:22"
    },
    {
      "id": "chain.t_151",
      "start": "2024-03-29-08:13",
      "end": "2024-03-29-09:26"
    },
    {
      "id": "chain.t_152",
      "start": "2024-03-29-09:55",
      "end": "2024-03-29-11:08"
    },
    {
      "id": "chain.t_153",
      "start": "2024-03-29-11:37",
      "end": "2024-03-29-13:58"
    },
    {
      "id": "chain.t_154",
      "start": "2024-03-29-14:27",
      "end": "2024-03-29-15:40"
    },
    {
      "id": "chain.t_155",
      "start": "2024-03-29-16:09",
      "end": "2024-03-29-17:22"
    },
    {
      "id": "chain.t_156",
      "start": "2024-03-30-08:13",
      "end": "2024-03-30-09:26"
    },
    {
      "id": "chain.t_157",
      "start": "2024-03-30-09:55",
      "end": "2024-03-30-11:08"
    },
    {
      "id": "chain.t_158",
      "start": "2024-03-30-11:37",
      "end": "2024-03-30-13:58"
    },
    {
      "id": "chain.t_159",
      "start": "2024-03-30-14:27",
      "end": "2024-03-30-15:40"
    },
    {
      "id": "chain.t_160",
      "start": "2024-03-30-16:09",
      "end": "2024-03-30-17:22"
    },
    {
      "id": "chain.t_161",
      "start": "2024-03-31-08:13",
      "end": "2024-03-31-09:26"
    },
    {
      "id": "chain.t_162",
      "start": "2024-03-31-09:55",
      "end": "2024-03-31-11:08"
    },
    {
      "id": "chain.t_163",
      "start": "2024-03-31-11:37",
      "end": "2024-03-31-13:58"
    },
    {
      "id": "chain.t_164",
      "start": "2024-03-31-14:27",
      "end": "2024-03-31-15:40"
    },
    {
      "id": "chain.t_165",
      "start": "2024-03-31-16:09",
      "end": "2024-03-31-17:22"
    },
    {
      "id": "chain.t_166",
      "start": "2024-04-01-08:13",
      "end": "2024-04-01-09:26"
    },
    {
      "id": "chain.t_167",
      "start": "2024-04-01-09:55",
      "end": "2024-04-01-11:08"
    },
    {
      "id": "chain.t_168",
      "start": "2024-04-01-11:37",
      "end": "2024-04-01-13:58"
    },
    {
      "id": "chain.t_169",
      "start": "2024-04-01-14:27",
      "end": "2024-04-01-15:40"
    },
    {
      "id": "chain.t_170",
      "start": "2024-04-01-16:09",
      "end": "2024-04-01-17:22"
    },
    {
      "id": "chain.t_171",
      "start": "2024-04-02-08:13",
      "end": "2024-04-02-09:26"
    },
    {
      "id": "chain.t_172",
      "start": "2024-04-02-09:55",
      "end": "2024-04-02-11:08"
    },
    {
      "id": "chain.t_173",
      "start": "2024-04-02-11:37",
      "end": "2024-04-02-13:58"
    },
    {
      "id": "chain.t_174",
      "start": "2024-04-02-14:27",
      "end": "2024-04-02-15:40"
    },
    {
      "id": "chain.t_175",
      "start": "2024-04-02-16:09",
      "end": "2024-04-02-17:22"
    },
    {
      "id": "chain.t_176",
      "start": "2024-04-03-08:13",
      "end": "2024-04-03-09:26"
    },
    {
      "id": "chain.t_177",
      "start": "2024-04-03-09:55",
      "end": "2024-04-03-11:08"
    },
    {
      "id": "chain.t_178",
      "start": "2024-04-03-11:37",
      "end": "2024-04-03-13:58"
    },
    {
      "id": "chain.t_179",
      "start": "2024-04-03-14:27",
      "end": "2024-04-03-15:40"
    },
    {
      "id": "chain.t_180",
      "start": "2024-04-03-16:09",
      "end": "2024-04-03-17:22"
    },
    {
      "id": "chain.t_181",
      "start": "2024-04-04-08:13",
      "end": "2024-04-04-09:26"
    },
    {
      "id": "chain.t_182",
      "start": "2024-04-04-09:55",
      "end": "2024-04-04-11:08"
    },
    {
      "id": "chain.t_183",
      "start": "2024-04-04-11:37",
      "end": "2024-04-04-13:58"
    },
    {
      "id": "chain.t_184",
      "start": "2024-04-04-14:27",
      "end": "2024-04-04-15:40"
    },
    {
      "id": "chain.t_185",
      "start": "2024-04-04-16:09",
      "end": "2024-04-04-17:22"
    },
    {
      "id": "chain.t_186",
      "start": "2024-04-05-08:13",
      "end": "2024-04-05-09:26"
    },
    {
      "id": "chain.t_187",
      "start": "2024-04-05-09:55",
      "end": "2024-04-05-11:08"
    },
    {
      "id": "chain.t_188",
      "start": "2024-04-05-11:37",
      "end": "2024-04-05-13:58"
    },
    {
      "id": "chain.t_189",
      "start": "2024-04-05-14:27",
      "end": "2024-04-05-15:40"
    },
    {
      "id": "chain.t_190",
      "start": "2024-04-05-16:09",
      "end": "2024-04-05-17:22"
    },
    {
      "id": "chain.t_191",
      "start": "2024-04-06-08:13",
      "end": "2024-04-06-09:26"
    },
    {
      "id": "chain.t_192",
      "start": "2024-04-06-09:55",
      "end": "2024-04-06-11:08"
    },
    {
      "id": "chain.t_193",
      "start": "2024-04-06-11:37",
      "end": "2024-04-06-13:58"
    },
    {
      "id": "chain.t_194",
      "start": "2024-04-06-14:27",
      "end": "2024-04-06-15:40"
    },
    {
      "id": "chain.t_195",
      "start": "2024-04-06-16:09",
      "end": "2024-04-06-17:22"
    },
    {
      "id": "chain.t_196",
      "start": "2024-04-07-08:13",
      "end": "2024-04-07-09:26"
    },
    {
      "id": "chain.t_197",
      "start": "2024-04-07-09:55",
      "end": "2024-04-07-11:08"
    },
    {
      "id": "chain.t_198",
      "start": "2024-04-07-11:37",
      "end": "2024-04-07-13:58"
    },
    {
      "id": "chain.t_199",
      "start": "2024-04-07-14:27",
      "end": "2024-04-07-15:40"
    },
    {
      "id": "chain.t_200",
      "start": "2024-04-07-16:09",
      "end": "2024-04-07-17:22"
    },
    {
      "id": "chain.t_201",
      "start": "2024-04-08-08:13",
      "end": "2024-04-08-09:26"
    },
    {
      "id": "chain.t_202",
      "start": "2024-04-08-09:55",
      "end": "2024-04-08-11:08"
    },
    {
      "id": "chain.t_203",
      "start": "2024-04-08-11:37",
      "end": "2024-04-08-13:58"
    },
    {
      "id": "chain.t_204",
      "start": "2024-04-08-14:27",
      "end": "2024-04-08-15:40"
    },
    {
      "id": "chain.t_205",
      "start": "2024-04-08-16:09",
      "end": "2024-04-08-17:22"
    },
    {
      "id": "chain.t_206",
      "start": "2024-04-09-08:13",
      "end": "2024-04-09-09:26"
    },
    {
      "id": "chain.t_207",
      "start": "2024-04-09-09:55",
      "end": "2024-04-09-11:08"
    },
    {
      "id": "chain.t_208",
      "start": "2024-04-09-11:37",
      "end": "2024-04-09-13:58"
    },
    {
      "id": "chain.t_209",
      "start": "2024-04-09-14:27",
      "end": "2024-04-09-15:40"
    },
    {
      "id": "chain.t_210",
      "start": "2024-04-09-16:09",
      "end": "2024-04-09-17:22"
    },
    {
      "id": "chain.t_211",
      "start": "2024-04-10-08:13",
      "end": "2024-04-10-09:26"
    },
    {
      "id": "chain.t_212",
      "start": "2024-04-10-09:55",
      "end": "2024-04-10-11:08"
    },
    {
      "id": "chain.t_213",
      "start": "2024-04-10-11:37",
      "end": "2024-04-10-13:58"
    },
    {
      "id": "chain.t_214",
      "start": "2024-04-10-14:27",
      "end": "2024-04-10-15:40"
    },
    {
      "id": "chain.t_215",
      "start": "2024-04-10-16:09",
      "end": "2024-04-10-17:22"
    },
    {
      "id": "chain.t_216",
      "start": "2024-04-11-08:13",
      "end": "2024-04-11-09:26"
    },
    {
      "id": "chain.t_217",
      "start": "2024-04-11-09:55",
      "end": "2024-04-11-11:08"
    },
    {
      "id": "chain.t_218",
      "start": "2024-04-11-11:37",
      "end": "2024-04-11-13:58"
    },
    {
      "id": "chain.t_219",
      "start": "2024-04-11-14:27",
      "end": "2024-04-11-15:40"
    },
    {
      "id": "chain.t_220",
      "start": "2024-04-11-16:09",
      "end": "2024-04-11-17:22"
    },
    {
      "id": "chain.t_221",
      "start": "2024-04-12-08:13",
      "end": "2024-04-12-09:26"
    },
    {
      "id": "chain.t_222",
      "start": "2024-04-12-09:55",
      "end": "2024-04-12-11:08"
    },
    {
      "id": "chain.t_223",
      "start": "2024-04-12-11:37",
      "end": "2024-04-12-13:58"
    },
    {
      "id": "chain.t_224",
      "start": "2024-04-12-14:27",
      "end": "2024-04-12-15:40"
    },
    {
      "id": "chain.t_225",
      "start": "2024-04-12-16:09",
      "end": "2024-04-12-17:22"
    },
    {
      "id": "chain.t_226",
      "start": "2024-04-13-08:13",
      "end": "2024-04-13-09:26"
    },
    {
      "id": "chain.t_227",
      "start": "2024-04-13-09:55",
      "end": "2024-04-13-11:08"
    },
    {
      "id": "chain.t_228",
      "start": "2024-04-13-11:37",
      "end": "2024-04-13-13:58"
    },
    {
      "id": "chain.t_229",
      "start": "2024-04-13-14:27",
      "end": "2024-04-13-15:40"
    },
    {
      "id": "chain.t_230",
      "start": "2024-04-13-16:09",
      "end": "2024-04-13-17:22"
    },
    {
      "id": "chain.t_231",
      "start": "2024-04-14-08:13",
      "end": "2024-04-14-09:26"
    },
    {
      "id": "chain.t_232",
      "start": "2024-04-14-09:55",
      "end": "2024-04-14-11:08"
    },
    {
      "id": "chain.t_233",
      "start": "2024-04-14-11:37",
      "end": "2024-04-14-13:58"
    },
    {
      "id": "chain.t_234",
      "start": "2024-04-14-14:27",
      "end": "2024-04-14-15:40"
    },
    {
      "id": "chain.t_235",
      "start": "2024-04-14-16:09",
      "end": "2024-04-14-17:22"
    },
    {
      "id": "chain.t_236",
      "start": "2024-04-15-08:13",
      "end": "2024-04-15-09:26"
    },
    {
      "id": "chain.t_237",
      "start": "2024-04-15-09:55",
      "end": "2024-04-15-11:08"
    },
    {
      "id": "chain.t_238",
      "start": "2024-04-15-11:37",
      "end": "2024-04-15-13:58"
    },
    {
      "id": "chain.t_239",
      "start": "2024-04-15-14:27",
      "end": "2024-04-15-15:40"
    },
    {
      "id": "chain.t_240",
      "start": "2024-04-15-16:09",
      "end": "2024-04-15-17:22"
    },
    {
      "id": "chain.t_241",
      "start": "2024-04-16-08:13",
      "end": "2024-04-16-09:26"
    },
    {
      "id": "chain.t_242",
      "start": "2024-04-16-09:55",
      "end": "2024-04-16-11:08"
    },
    {
      "id": "chain.t_243",
      "start": "2024-04-16-11:37",
      "end": "2024-04-16-13:58"
    },
    {
      "id": "chain.t_244",
      "start": "2024-04-16-14:27",
      "end": "2024-04-16-15:40"
    },
    {
      "id": "chain.t_245",
      "start": "2024-04-16-16:09",
      "end": "2024-04-16-17:22"
    },
    {
      "id": "chain.t_246",
      "start": "2024-04-17-08:13",
      "end": "2024-04-17-09:26"
    },
    {
      "id": "chain.t_247",
      "start": "2024-04-17-09:55",
      "end": "2024-04-17-11:08"
    },
    {
      "id": "chain.t_248",
      "start": "2024-04-17-11:37",
      "end": "2024-04-17-13:58"
    },
    {
      "id": "chain.t_249",
      "start": "2024-04-17-14:27",
      "end": "2024-04-17-15:40"
    },
    {
      "id": "chain.t_250",
      "start": "2024-04-17-16:09",
      "end": "2024-04-17-17:22"
    },
    {
      "id": "chain.t_251",
      "start": "2024-04-18-08:13",
      "end": "2024-04-18-09:26"
    },
    {
      "id": "chain.t_252",
      "start": "2024-04-18-09:55",
      "end": "2024-04-18-11:08"
    },
    {
      "id": "chain.t_253",
      "start": "2024-04-18-11:37",
      "end": "2024-04-18-13:58"
    },
    {
      "id": "chain.t_254",
      "start": "2024-04-18-14:27",
      "end": "2024-04-18-15:40"
    },
    {
      "id": "chain.t_255",
      "start": "2024-04-18-16:09",
      "end": "2024-04-18-17:22"
    },
    {
      "id": "chain.t_256",
      "start": "2024-04-19-08:13",
      "end": "2024-04-19-09:26"
    },
    {
      "id": "chain.t_257",
      "start": "2024-04-19-09:55",
      "end": "2024-04-19-11:08"
    },
    {
      "id": "chain.t_258",
      "start": "2024-04-19-11:37",
      "end": "2024-04-19-13:58"
    },
    {
      "id": "chain.t_259",
      "start": "2024-04-19-14:27",
      "end": "2024-04-19-15:40"
    },
    {
      "id": "chain.t_260",
      "start": "2024-04-19-16:09",
      "end": "2024-04-19-17:22"
    },
    {
      "id": "chain.t_261",
      "start": "2024-04-20-08:13",
      "end": "2024-04-20-09:26"
    },
    {
      "id": "chain.t_262",
      "start": "2024-04-20-09:55",
      "end": "2024-04-20-11:08"
    },
    {
      "id": "chain.t_263",
      "start": "2024-04-20-11:37",
      "end": "2024-04-20-13:58"
    },
    {
      "id": "chain.t_264",
      "start": "2024-04-20-14:27",
      "end": "2024-04-20-15:40"
    },
    {
      "id": "chain.t_265",
      "start": "2024-04-20-16:09",
      "end": "2024-04-20-17:22"
    },
    {
      "id": "chain.t_266",
      "start": "2024-04-21-08:13",
      "end": "2024-04-21-09:26"
    },
    {
      "id": "chain.t_267",
      "start": "2024-04-21-09:55",
      "end": "2024-04-21-11:08"
    },
    {
      "id": "chain.t_268",
      "start": "2024-04-21-11:37",
      "end": "2024-04-21-13:58"
    },
    {
      "id": "chain.t_269",
      "start": "2024-04-21-14:27",
      "end": "2024-04-21-15:40"
    },
    {
      "id": "chain.t_270",
      "start": "2024-04-21-16:09",
      "end": "2024-04-21-17:22"
    },
    {
      "id": "chain.t_271",
      "start": "2024-04-22-08:13",
      "end": "2024-04-22-09:26"
    },
    {
      "id": "chain.t_272",
      "start": "2024-04-22-09:55",
      "end": "2024-04-22-11:08"
    },
    {
      "id": "chain.t_273",
      "start": "2024-04-22-11:37",
      "end": "2024-04-22-13:58"
    },
    {
      "id": "chain.t_274",
      "start": "2024-04-22-14:27",
      "end": "2024-04-22-15:40"
    },
    {
      "id": "chain.t_275",
      "start": "2024-04-22-16:09",
      "end": "2024-04-22-17:22"
    },
    {
      "id": "chain.t_276",
      "start": "2024-04-23-08:13",
      "end": "2024-04-23-09:26"
    },
    {
      "id": "chain.t_277",
      "start": "2024-04-23-09:55",
      "end": "2024-04-23-11:08"
    },
    {
      "id": "chain.t_278",
      "start": "2024-04-23-11:37",
      "end": "2024-04-23-13:58"
    },
    {
      "id": "chain.t_279",
      "start": "2024-04-23-14:27",
      "end": "2024-04-23-15:40"
    },
    {
      "id": "chain.t_280",
      "start": "2024-04-23-16:09",
      "end": "2024-04-23-17:22"
    },
    {
      "id": "chain.t_281",
      "start": "2024-04-24-08:13",
      "end": "2024-04-24-09:26"
    },
    {
      "id": "chain.t_282",
      "start": "2024-04-24-09:55",
      "end": "2024-04-24-11:08"
    },
    {
      "id": "chain.t_283",
      "start": "2024-04-24-11:37",
      "end": "2024-04-24-13:58"
    },
    {
      "id": "chain.t_284",
      "start": "2024-04-24-14:27",
      "end": "2024-04-24-15:40"
    },
    {
      "id": "chain.t_285",
      "start": "2024-04-24-16:09",
      "end": "2024-04-24-17:22"
    },
    {
      "id": "chain.t_286",
      "start": "2024-04-25-08:13",
      "end": "2024-04-25-09:26"
    },
    {
      "id": "chain.t_287",
      "start": "2024-04-25-09:55",
      "end": "2024-04-25-11:08"
    },
    {
      "id": "chain.t_288",
      "start": "2024-04-25-11:37",
      "end": "2024-04-25-13:58"
    },
    {
      "id": "chain.t_289",
      "start": "2024-04-25-14:27",
      "end": "2024-04-25-15:40"
    },
    {
      "id": "chain.t_290",
      "start": "2024-04-25-16:09",
      "end": "2024-04-25-17:22"
    },
    {
      "id": "chain.t_291",
      "start": "2024-04-26-08:13",
      "end": "2024-04-26-09:26"
    },
    {
      "id": "chain.t_292",
      "start": "2024-04-26-09:55",
      "end": "2024-04-26-11:08"
    },
    {
      "id": "chain.t_293",
      "start": "2024-04-26-11:37",
      "end": "2024-04-26-13:58"
    },
    {
      "id": "chain.t_294",
      "start": "2024-04-26-14:27",
      "end": "2024-04-26-15:40"
    },
    {
      "id": "chain.t_295",
      "start": "2024-04-26-16:09",
      "end": "2024-04-26-17:22"
    },
    {
      "id": "chain.t_296",
      "start": "2024-04-27-08:13",
      "end": "2024-04-27-09:26"
    },
    {
      "id": "chain.t_297",
      "start": "2024-04-27-09:55",
      "end": "2024-04-27-11:08"
    },
    {
      "id": "chain.t_298",
      "start": "2024-04-27-11:37",
      "end": "2024-04-27-13:58"
    },
    {
      "id": "chain.t_299",
      "start": "2024-04-27-14:27",
      "end": "2024-04-27-15:40"
    },
    {
      "id": "chain.t_300",
      "start": "2024-04-27-16:09",
      "end": "2024-04-27-17:22"
    },
    {
      "id": "chain.t_301",
      "start": "2024-04-28-08:13",
      "end": "2024-04-28-09:26"
    },
    {
      "id": "chain.t_302",
      "start": "2024-04-28-09:55",
      "end": "2024-04-28-11:08"
    },
    {
      "id": "chain.t_303",
      "start": "2024-04-28-11:37",
      "end": "2024-04-28-13:58"
    },
    {
      "id": "chain.t_304",
      "start": "2024-04-28-14:27",
      "end": "2024-04-28-15:40"
    },
    {
      "id": "chain.t_305",
      "start": "2024-04-28-16:09",
      "end": "2024-04-28-17:22"
    },
    {
      "id": "chain.t_306",
      "start": "2024-04-29-08:13",
      "end": "2024-04-29-09:26"
    },
    {
      "id": "chain.t_307",
      "start": "2024-04-29-09:55",
      "end": "2024-04-29-11:08"
    },
    {
      "id": "chain.t_308",
      "start": "2024-04-29-11:37",
      "end": "2024-04-29-13:58"
    },
    {
      "id": "chain.t_309",
      "start": "2024-04-29-14:27",
      "end": "2024-04-29-15:40"
    },
    {
      "id": "chain.t_310",
      "start": "2024-04-29-16:09",
      "end": "2024-04-29-17:22"
    },
    {
      "id": "chain.t_311",
      "start": "2024-04-30-08:13",
      "end": "2024-04-30-09:26"
    },
    {
      "id": "chain.t_312",
      "start": "2024-04-30-09:55",
      "end": "2024-04-30-11:08"
    },
    {
      "id": "chain.t_313",
      "start": "2024-04-30-11:37",
      "end": "2024-04-30-13:58"
    },
    {
      "id": "chain.t_314",
      "start": "2024-04-30-14:27",
      "end": "2024-04-30-15:40"
    },
    {
      "id": "chain.t_315",
      "start": "2024-04-30-16:09",
      "end": "2024-04-30-17:22"
    },
    {
      "id": "chain.t_316",
      "start": "2024-05-01-08:13",
      "end": "2024-05-01-09:26"
    },
    {
      "id": "chain.t_317",
      "start": "2024-05-01-09:55",
      "end": "2024-05-01-11:08"
    },
    {
      "id": "chain.t_318",
      "start": "2024-05-01-11:37",
      "end": "2024-05-01-13:58"
    },
    {
      "id": "chain.t_319",
      "start": "2024-05-01-14:27",
      "end": "2024-05-01-15:40"
    },
    {
      "id": "chain.t_320",
      "start": "2024-05-01-16:09",
      "end": "2024-05-01-17:22"
    },
    {
      "id": "chain.t_321",
      "start": "2024-05-02-08:13",
      "end": "2024-05-02-09:26"
    },
    {
      "id": "chain.t_322",
      "start": "2024-05-02-09:55",
      "end": "2024-05-02-11:08"
    },
    {
      "id": "chain.t_323",
      "start": "2024-05-02-11:37",
      "end": "2024-05-02-13:58"
    },
    {
      "id": "chain.t_324",
      "start": "2024-05-02-14:27",
      "end": "2024-05-02-15:40"
    },
    {
      "id": "chain.t_325",
      "start": "2024-05-02-16:09",
      "end": "2024-05-02-17:22"
    },
    {
      "id": "chain.t_326",
      "start": "2024-05-03-08:13",
      "end": "2024-05-03-09:26"
    },
    {
      "id": "chain.t_327",
      "start": "2024-05-03-09:55",
      "end": "2024-05-03-11:08"
    },
    {
      "id": "chain.t_328",
      "start": "2024-05-03-11:37",
      "end": "2024-05-03-13:58"
    },
    {
      "id": "chain.t_329",
      "start": "2024-05-03-14:27",
      "end": "2024-05-03-15:40"
    },
    {
      "id": "chain.t_330",
      "start": "2024-05-03-16:09",
      "end": "2024-05-03-17:22"
    },
    {
      "id": "chain.t_331",
      "start": "2024-05-04-08:13",
      "end": "2024-05-04-09:26"
    },
    {
      "id": "chain.t_332",
      "start": "2024-05-04-09:55",
      "end": "2024-05-04-11:08"
    },
    {
      "id": "chain.t_333",
      "start": "2024-05-04-11:37",
      "end": "2024-05-04-13:58"
    },
    {
      "id": "chain.t_334",
      "start": "2024-05-04-14:27",
      "end": "2024-05-04-15:40"
    },
    {
      "id": "chain.t_335",
      "start": "2024-05-04-16:09",
      "end": "2024-05-04-17:22"
    },
    {
      "id": "chain.t_336",
      "start": "2024-05-05-08:13",
      "end": "2024-05-05-09:26"
    },
    {
      "id": "chain.t_337",
      "start": "2024-05-05-09:55",
      "end": "2024-05-05-11:08"
    },
    {
      "id": "chain.t_338",
      "start": "2024-05-05-11:37",
      "end": "2024-05-05-13:58"
    },
    {
      "id": "chain.t_339",
      "start": "2024-05-05-14:27",
      "end": "2024-05-05-15:40"
    },
    {
      "id": "chain.t_340",
      "start": "2024-05-05-16:09",
      "end": "2024-05-05-17:22"
    },
    {
      "id": "chain.t_341",
      "start": "2024-05-06-08:13",
      "end": "2024-05-06-09:26"
    },
    {
      "id": "chain.t_342",
      "start": "2024-05-06-09:55",
      "end": "2024-05-06-11:08"
    },
    {
      "id": "chain.t_343",
      "start": "2024-05-06-11:37",
      "end": "2024-05-06-13:58"
    },
    {
      "id": "chain.t_344",
      "start": "2024-05-06-14:27",
      "end": "2024-05-06-15:40"
    },
    {
      "id": "chain.t_345",
      "start": "2024-05-06-16:09",
      "end": "2024-05-06-17:22"
    },
    {
      "id": "chain.t_346",
      "start": "2024-05-07-08:13",
      "end": "2024-05-07-09:26"
    },
    {
      "id": "chain.t_347",
      "start": "2024-05-07-09:55",
      "end": "2024-05-07-11:08"
    },
    {
      "id": "chain.t_348",
      "start": "2024-05-07-11:37",
      "end": "2024-05-07-13:58"
    },
    {
      "id": "chain.t_349",
      "start": "2024-05-07-14:27",
      "end": "2024-05-07-15:40"
    },
    {
      "id": "chain.t_350",
      "start": "2024-05-07-16:09",
      "end": "2024-05-07-17:22"
    },
    {
      "id": "chain.t_351",
      "start": "2024-05-08-08:13",
      "end": "2024-05-08-09:26"
    },
    {
      "id": "chain.t_352",
      "start": "2024-05-08-09:55",
      "end": "2024-05-08-11:08"
    },
    {
      "id": "chain.t_353",
      "start": "2024-05-08-11:37",
      "end": "2024-05-08-13:58"
    },
    {
      "id": "chain.t_354",
      "start": "2024-05-08-14:27",
      "end": "2024-05-08-15:40"
    },
    {
      "id": "chain.t_355",
      "start": "2024-05-08-16:09",
      "end": "2024-05-08-17:22"
    },
    {
      "id": "chain.t_356",
      "start": "2024-05-09-08:13",
      "end": "2024-05-09-09:26"
    },
    {
      "id": "chain.t_357",
      "start": "2024-05-09-09:55",
      "end": "2024-05-09-11:08"
    },
    {
      "id": "chain.t_358",
      "start": "2024-05-09-11:37",
      "end": "2024-05-09-13:58"
    },
    {
      "id": "chain.t_359",
      "start": "2024-05-09-14:27",
      "end": "2024-05-09-15:40"
    },
    {
      "id": "chain.t_360",
      "start": "2024-05-09-16:09",
      "end": "2024-05-09-17:22"
    },
    {
      "id": "chain.t_361",
      "start": "2024-05-10-08:13",
      "end": "2024-05-10-09:26"
    },
    {
      "id": "chain.t_362",
      "start": "2024-05-10-09:55",
      "end": "2024-05-10-11:08"
    },
    {
      "id": "chain.t_363",
      "start": "2024-05-10-11:37",
      "end": "2024-05-10-13:58"
    },
    {
      "id": "chain.t_364",
      "start": "2024-05-10-14:27",
      "end": "2024-05-10-15:40"
    },
    {
      "id": "chain.t_365",
      "start": "2024-05-10-16:09",
      "end": "2024-05-10-17:22"
    },
    {
      "id": "chain.t_366",
      "start": "2024-05-11-08:13",
      "end": "2024-05-11-09:26"
    },
    {
      "id": "chain.t_367",
      "start": "2024-05-11-09:55",
      "end": "2024-05-11-11:08"
    },
    {
      "id": "chain.t_368",
      "start": "2024-05-11-11:37",
      "end": "2024-05-11-13:58"
    },
    {
      "id": "chain.t_369",
      "start": "2024-05-11-14:27",
      "end": "2024-05-11-15:40"
    },
    {
      "id": "chain.t_370",
      "start": "2024-05-11-16:09",
      "end": "2024-05-11-17:22"
    },
    {
      "id": "chain.t_371",
      "start": "2024-05-12-08:13",
      "end": "2024-05-12-09:26"
    },
    {
      "id": "chain.t_372",
      "start": "2024-05-12-09:55",
      "end": "2024-05-12-11:08"
    },
    {
      "id": "chain.t_373",
      "start": "2024-05-12-11:37",
      "end": "2024-05-12-13:58"
    },
    {
      "id": "chain.t_374",
      "start": "2024-05-12-14:27",
      "end": "2024-05-12-15:40"
    },
    {
      "id": "chain.t_375",
      "start": "2024-05-12-16:09",
      "end": "2024-05-12-17:22"
    },
    {
      "id": "chain.t_376",
      "start": "2024-05-13-08:13",
      "end": "2024-05-13-09:26"
    },
    {
      "id": "chain.t_377",
      "start": "2024-05-13-09:55",
      "end": "2024-05-13-11:08"
    },
    {
      "id": "chain.t_378",
      "start": "2024-05-13-11:37",
      "end": "2024-05-13-13:58"
    },
    {
      "id": "chain.t_379",
      "start": "2024-05-13-14:27",
      "end": "2024-05-13-15:40"
    },
    {
      "id": "chain.t_380",
      "start": "2024-05-13-16:09",
      "end": "2024-05-13-17:22"
    },
    {
      "id": "chain.t_381",
      "start": "2024-05-14-08:13",
      "end": "2024-05-14-09:26"
    },
    {
      "id": "chain.t_382",
      "start": "2024-05-14-09:55",
      "end": "2024-05-14-11:08"
    },
    {
      "id": "chain.t_383",
      "start": "2024-05-14-11:37",
      "end": "2024-05-14-13:58"
    },
    {
      "id": "chain.t_384",
      "start": "2024-05-14-14:27",
      "end": "2024-05-14-15:40"
    },
    {
      "id": "chain.t_385",
      "start": "2024-05-14-16:09",
      "end": "2024-05-14-17:22"
    },
    {
      "id": "chain.t_386",
      "start": "2024-05-15-08:13",
      "end": "2024-05-15-09:26"
    },
    {
      "id": "chain.t_387",
      "start": "2024-05-15-09:55",
      "end": "2024-05-15-11:08"
    },
    {
      "id": "chain.t_388",
      "start": "2024-05-15-11:37",
      "end": "2024-05-15-13:58"
    },
    {
      "id": "chain.t_389",
      "start": "2024-05-15-14:27",
      "end": "2024-05-15-15:40"
    },
    {
      "id": "chain.t_390",
      "start": "2024-05-15-16:09",
      "end": "2024-05-15-17:22"
    },
    {
      "id": "chain.t_391",
      "start": "2024-05-16-08:13",
      "end": "2024-05-16-09:26"
    },
    {
      "id": "chain.t_392",
      "start": "2024-05-16-09:55",
      "end": "2024-05-16-11:08"
    },
    {
      "id": "chain.t_393",
      "start": "2024-05-16-11:37",
      "end": "2024-05-16-13:58"
    },
    {
      "id": "chain.t_394",
      "start": "2024-05-16-14:27",
      "end": "2024-05-16-15:40"
    },
    {
      "id": "chain.t_395",
      "start": "2024-05-16-16:09",
      "end": "2024-05-16-17:22"
    },
    {
      "id": "chain.t_396",
      "start": "2024-05-17-08:13",
      "end": "2024-05-17-09:26"
    },
    {
      "id": "chain.t_397",
      "start": "2024-05-17-09:55",
      "end": "2024-05-17-11:08"
    },
    {
      "id": "chain.t_398",
      "start": "2024-05-17-11:37",
      "end": "2024-05-17-13:58"
    },
    {
      "id": "chain.t_399",
      "start": "2024-05-17-14:27",
      "end": "2024-05-17-15:40"
    },
    {
      "id": "chain.t_400",
      "start": "2024-05-17-16:09",
      "end": "2024-05-17-17:22"
    },
    {
      "id": "chain.t_401",
      "start": "2024-05-18-08:13",
      "end": "2024-05-18-09:26"
    },
    {
      "id": "chain.t_402",
      "start": "2024-05-18-09:55",
      "end": "2024-05-18-11:08"
    },
    {
      "id": "chain.t_403",
      "start": "2024-05-18-11:37",
      "end": "2024-05-18-13:58"
    },
    {
      "id": "chain.t_404",
      "start": "2024-05-18-14:27",
      "end": "2024-05-18-15:40"
    },
    {
      "id": "chain.t_405",
      "start": "2024-05-18-16:09",
      "end": "2024-05-18-17:22"
    },
    {
      "id": "chain.t_406",
      "start": "2024-05-19-08:13",
      "end": "2024-05-19-09:26"
    },
    {
      "id": "chain.t_407",
      "start": "2024-05-19-09:55",
      "end": "2024-05-19-11:08"
    },
    {
      "id": "chain.t_408",
      "start": "2024-05-19-11:37",
      "end": "2024-05-19-13:58"
    },
    {
      "id": "chain.t_409",
      "start": "2024-05-19-14:27",
      "end": "2024-05-19-15:40"
    },
    {
      "id": "chain.t_410",
      "start": "2024-05-19-16:09",
      "end": "2024-05-19-17:22"
    },
    {
      "id": "chain.t_411",
      "start": "2024-05-20-08:13",
      "end": "2024-05-20-09:26"
    },
    {
      "id": "chain.t_412",
      "start": "2024-05-20-09:55",
      "end": "2024-05-20-11:08"
    },
    {
      "id": "chain.t_413",
      "start": "2024-05-20-11:37",
      "end": "2024-05-20-13:58"
    },
    {
      "id": "chain.t_414",
      "start": "2024-05-20-14:27",
      "end": "2024-05-20-15:40"
    },
    {
      "id": "chain.t_415",
      "start": "2024-05-20-16:09",
      "end": "2024-05-20-17:22"
    },
    {
      "id": "chain.t_416",
      "start": "2024-05-21-08:13",
      "end": "2024-05-21-09:26"
    },
    {
      "id": "chain.t_417",
      "start": "2024-05-21-09:55",
      "end": "2024-05-21-11:08"
    },
    {
      "id": "chain.t_418",
      "start": "2024-05-21-11:37",
      "end": "2024-05-21-13:58"
    },
    {
      "id": "chain.t_419",
      "start": "2024-05-21-14:27",
      "end": "2024-05-21-15:40"
    },
    {
      "id": "chain.t_420",
      "start": "2024-05-21-16:09",
      "end": "2024-05-21-17:22"
    },
    {
      "id": "chain.t_421",
      "start": "2024-05-22-08:13",
      "end": "2024-05-22-09:26"
    },
    {
      "id": "chain.t_422",
      "start": "2024-05-22-09:55",
      "end": "2024-05-22-11:08"
    },
    {
      "id": "chain.t_423",
      "start": "2024-05-22-11:37",
      "end": "2024-05-22-13:58"
    },
    {
      "id": "chain.t_424",
      "start": "2024-05-22-14:27",
      "end": "2024-05-22-15:40"
    },
    {
      "id": "chain.t_425",
      "start": "2024-05-22-16:09",
      "end": "2024-05-22-17:22"
    },
    {
      "id": "chain.t_426",
      "start": "2024-05-23-08:13",
      "end": "2024-05-23-09:26"
    },
    {
      "id": "chain.t_427",
      "start": "2024-05-23-09:55",
      "end": "2024-05-23-11:08"
    },
    {
      "id": "chain.t_428",
      "start": "2024-05-23-11:37",
      "end": "2024-05-23-13:58"
    },
    {
      "id": "chain.t_429",
      "start": "2024-05-23-14:27",
      "end": "2024-05-23-15:40"
    },
    {
      "id": "chain.t_430",
      "start": "2024-05-23-16:09",
      "end": "2024-05-23-17:22"
    },
    {
      "id": "chain.t_431",
      "start": "2024-05-24-08:13",
      "end": "2024-05-24-09:26"
    },
    {
      "id": "chain.t_432",
      "start": "2024-05-24-09:55",
      "end": "2024-05-24-11:08"
    },
    {
      "id": "chain.t_433",
      "start": "2024-05-24-11:37",
      "end": "2024-05-24-13:58"
    },
    {
      "id": "chain.t_434",
      "start": "2024-05-24-14:27",
      "end": "2024-05-24-15:40"
    },
    {
      "id": "chain.t_435",
      "start": "2024-05-24-16:09",
      "end": "2024-05-24-17:22"
    },
    {
      "id": "chain.t_436",
      "start": "2024-05-25-08:13",
      "end": "2024-05-25-09:26"
    },
    {
      "id": "chain.t_437",
      "start": "2024-05-25-09:55",
      "end": "2024-05-25-11:08"
    },
    {
      "id": "chain.t_438",
      "start": "2024-05-25-11:37",
      "end": "2024-05-25-13:58"
    },
    {
      "id": "chain.t_439",
      "start": "2024-05-25-14:27",
      "end": "2024-05-25-15:40"
    },
    {
      "id": "chain.t_440",
      "start": "2024-05-25-16:09",
      "end": "2024-05-25-17:22"
    },
    {
      "id": "chain.t_441",
      "start": "2024-05-26-08:13",
      "end": "2024-05-26-09:26"
    },
    {
      "id": "chain.t_442",
      "start": "2024-05-26-09:55",
      "end": "2024-05-26-11:08"
    },
    {
      "id": "chain.t_443",
      "start": "2024-05-26-11:37",
      "end": "2024-05-26-13:58"
    },
    {
      "id": "chain.t_444",
      "start": "2024-05-26-14:27",
      "end": "2024-05-26-15:40"
    },
    {
      "id": "chain.t_445",
      "start": "2024-05-26-16:09",
      "end": "2024-05-26-17:22"
    },
    {
      "id": "chain.t_446",
      "start": "2024-05-27-08:13",
      "end": "2024-05-27-09:26"
    },
    {
      "id": "chain.t_447",
      "start": "2024-05-27-09:55",
      "end": "2024-05-27-11:08"
    },
    {
      "id": "chain.t_448",
      "start": "2024-05-27-11:37",
      "end": "2024-05-27-13:58"
    },
    {
      "id": "chain.t_449",
      "start": "2024-05-27-14:27",
      "end": "2024-05-27-15:40"
    },
    {
      "id": "chain.t_450",
      "start": "2024-05-27-16:09",
      "end": "2024-05-27-17:22"
    },
    {
      "id": "chain.t_451",
      "start": "2024-05-28-08:13",
      "end": "2024-05-28-09:26"
    },
    {
      "id": "chain.t_452",
      "start": "2024-05-28-09:55",
      "end": "2024-05-28-11:08"
    },
    {
      "id": "chain.t_453",
      "start": "2024-05-28-11:37",
      "end": "2024-05-28-13:58"
    },
    {
      "id": "chain.t_454",
      "start": "2024-05-28-14:27",
      "end": "2024-05-28-15:40"
    },
    {
      "id": "chain.t_455",
      "start": "2024-05-28-16:09",
      "end": "2024-05-28-17:22"
    },
    {
      "id": "chain.t_456",
      "start": "2024-05-29-08:13",
      "end": "2024-05-29-09:26"
    },
    {
      "id": "chain.t_457",
      "start": "2024-05-29-09:55",
      "end": "2024-05-29-11:08"
    },
    {
      "id": "chain.t_458",
      "start": "2024-05-29-11:37",
      "end": "2024-05-29-13:58"
    },
    {
      "id": "chain.t_459",
      "start": "2024-05-29-14:27",
      "end": "2024-05-29-15:40"
    },
    {
      "id": "chain.t_460",
      "start": "2024-05-29-16:09",
      "end": "2024-05-29-17:22"
    },
    {
      "id": "chain.t_461",
      "start": "2024-05-30-08:13",
      "end": "2024-05-30-09:26"
    },
    {
      "id": "chain.t_462",
      "start": "2024-05-30-09:55",
      "end": "2024-05-30-11:08"
    },
    {
      "id": "chain.t_463",
      "start": "2024-05-30-11:37",
      "end": "2024-05-30-13:58"
    },
    {
      "id": "chain.t_464",
      "start": "2024-05-30-14:27",
      "end": "2024-05-30-15:40"
    },
    {
      "id": "chain.t_465",
      "start": "2024-05-30-16:09",
      "end": "2024-05-30-17:22"
    },
    {
      "id": "chain.t_466",
      "start": "2024-05-31-08:13",
      "end": "2024-05-31-09:26"
    },
    {
      "id": "chain.t_467",
      "start": "2024-05-31-09:55",
      "end": "2024-05-31-11:08"
    },
    {
      "id": "chain.t_468",
      "start": "2024-05-31-11:37",
      "end": "2024-05-31-13:58"
    },
    {
      "id": "chain.t_469",
      "start": "2024-05-31-14:27",
      "end": "2024-05-31-15:40"
    },
    {
      "id": "chain.t_470",
      "start": "2024-05-31-16:09",
      "end": "2024-05-31-17:22"
    },
    {
      "id": "chain.t_471",
      "start": "2024-06-01-08:13",
      "end": "2024-06-01-09:26"
    },
    {
      "id": "chain.t_472",
      "start": "2024-06-01-09:55",
      "end": "2024-06-01-11:08"
    },
    {
      "id": "chain.t_473",
      "start": "2024-06-01-11:37",
      "end": "2024-06-01-13:58"
    },
    {
      "id": "chain.t_474",
      "start": "2024-06-01-14:27",
      "end": "2024-06-01-15:40"
    },
    {
      "id": "chain.t_475",
      "start": "2024-06-01-16:09",
      "end": "2024-06-01-17:22"
    },
    {
      "id": "chain.t_476",
      "start": "2024-06-02-08:13",
      "end": "2024-06-02-09:26"
    },
    {
      "id": "chain.t_477",
      "start": "2024-06-02-09:55",
      "end": "2024-06-02-11:08"
    },
    {
      "id": "chain.t_478",
      "start": "2024-06-02-11:37",
      "end": "2024-06-02-13:58"
    },
    {
      "id": "chain.t_479",
      "start": "2024-06-02-14:27",
      "end": "2024-06-02-15:40"
    },
    {
      "id": "chain.t_480",
      "start": "2024-06-02-16:09",
      "end": "2024-06-02-17:22"
    },
    {
      "id": "chain.t_481",
      "start": "2024-06-03-08:13",
      "end": "2024-06-03-09:26"
    },
    {
      "id": "chain.t_482",
      "start": "2024-06-03-09:55",
      "end": "2024-06-03-11:08"
    },
    {
      "id": "chain.t_483",
      "start": "2024-06-03-11:37",
      "end": "2024-06-03-13:58"
    },
    {
      "id": "chain.t_484",
      "start": "2024-06-03-14:27",
      "end": "2024-06-03-15:40"
    },
    {
      "id": "chain.t_485",
      "start": "2024-06-03-16:09",
      "end": "2024-06-03-17:22"
    },
    {
      "id": "chain.t_486",
      "start": "2024-06-04-08:13",
      "end": "2024-06-04-09:26"
    },
    {
      "id": "chain.t_487",
      "start": "2024-06-04-09:55",
      "end": "2024-06-04-11:08"
    },
    {
      "id": "chain.t_488",
      "start": "2024-06-04-11:37",
      "end": "2024-06-04-13:58"
    },
    {
      "id": "chain.t_489",
      "start": "2024-06-04-14:27",
      "end": "2024-06-04-15:40"
    },
    {
      "id": "chain.t_490",
      "start": "2024-06-04-16:09",
      "end": "2024-06-04-17:22"
    },
    {
      "id": "chain.t_491",
      "start": "2024-06-05-08:13",
      "end": "2024-06-05-09:26"
    },
    {
      "id": "chain.t_492",
      "start": "2024-06-05-09:55",
      "end": "2024-06-05-11:08"
    },
    {
      "id": "chain.t_493",
      "start": "2024-06-05-11:37",
      "end": "2024-06-05-13:58"
    },
    {
      "id": "chain.t_494",
      "start": "2024-06-05-14:27",
      "end": "2024-06-05-15:40"
    },
    {
      "id": "chain.t_495",
      "start": "2024-06-05-16:09",
      "end": "2024-06-05-17:22"
    },
    {
      "id": "chain.t_496",
      "start": "2024-06-06-08:13",
      "end": "2024-06-06-09:26"
    },
    {
      "id": "chain.t_497",
      "start": "2024-06-06-09:55",
      "end": "2024-06-06-11:08"
    },
    {
      "id": "chain.t_498",
      "start": "2024-06-06-11:37",
      "end": "2024-06-06-13:58"
    },
    {
      "id": "chain.t_499",
      "start": "2024-06-06-14:27",
      "end": "2024-06-06-15:40"
    },
    {
      "id": "chain.t_500",
      "start": "2024-06-06-16:09",
      "end": "2024-06-06-17:22"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "68567fe6e9db7964501e8afdab94500f77dc1d593e1f105b5be62dc4c1c8add4"
}
```

---

## Test 13: paradox.tjp

**File**: `tests/data/paradox.tjp`
**Size**: 832 bytes
**Lines**: 48 lines

### Input File Content

```tjp
/*
 * Issue #58: "Blindfolded" Edition - Date Line + ALAP Gap Paradox
 * Tests gapduration subtraction in ALAP backward pass with extreme timezones
 */

project "Paradox" 2025-12-25 +2w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-12-25
  scheduling alap
}

shift daily "Daily" {
  workinghours mon - sun 09:00 - 15:00
}

resource k "K" {
  timezone "Pacific/Kiritimati"
  workinghours daily
  efficiency 0.5
}

resource n "N" {
  timezone "Pacific/Niue"
  workinghours daily
  efficiency 2.0
}

task sequence "Event" {
  end 2025-12-31-23:00

  task b "Omega" {
    effort 3h
    allocate k
  }

  task a "Alpha" {
    effort 12h
    allocate n
    depends !!b { gapduration 48h onstart }
  }
}

taskreport paradox_output "paradox_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `53d757486e0d571bb06ee086a0dfaf2e8c8ec0a8d25fa45475f3ca986abae371`
**Columns**: 3
**Rows**: 3
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "sequence",
      "start": "2025-12-27-23:00",
      "end": "2025-12-31-23:00"
    },
    {
      "id": "sequence.b",
      "start": "2025-12-30-23:00",
      "end": "2025-12-31-23:00"
    },
    {
      "id": "sequence.a",
      "start": "2025-12-27-23:00",
      "end": "2025-12-28-23:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "53d757486e0d571bb06ee086a0dfaf2e8c8ec0a8d25fa45475f3ca986abae371"
}
```

---

## Test 14: priority_clash.tjp

**File**: `tests/data/priority_clash.tjp`
**Size**: 701 bytes
**Lines**: 36 lines

### Input File Content

```tjp
/*
 * Issue #50: Priority Clash
 * Tests priority-based scheduling when tasks compete for same resource
 */

project priority "Priority_War" 2025-08-01 +1w {
  timezone "UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-08-01
}

resource consultant "Expert" {
  workinghours mon - fri 09:00 - 13:00
}

task conflict "Resource Conflict" {
  task low_prio "Documentation" {
    priority 100
    effort 4h
    allocate consultant
    start 2025-08-01-09:00
  }

  task high_prio "Server Crash Fix" {
    priority 1000
    effort 4h
    allocate consultant
    start 2025-08-01-09:00
  }
}

taskreport priority_output "priority_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `b469370a7c76292f9bb829ffeb0c6383bfb3bd1873dd75ae9e8dbef6f8145848`
**Columns**: 3
**Rows**: 3
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "conflict",
      "start": "2025-08-01-09:00",
      "end": "2025-08-04-13:00"
    },
    {
      "id": "conflict.low_prio",
      "start": "2025-08-04-09:00",
      "end": "2025-08-04-13:00"
    },
    {
      "id": "conflict.high_prio",
      "start": "2025-08-01-09:00",
      "end": "2025-08-01-13:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "b469370a7c76292f9bb829ffeb0c6383bfb3bd1873dd75ae9e8dbef6f8145848"
}
```

---

## Test 15: quota.tjp

**File**: `tests/data/quota.tjp`
**Size**: 1026 bytes
**Lines**: 49 lines

### Input File Content

```tjp
/*
 * Issue #62: The "Shared Quota" Protocol
 * Tests hierarchical resource limits (parent dailymax applies to child resources)
 * 3 tasks using 3 child resources, but parent has dailymax 6h
 */

project "Shared_Quota" 2025-07-01 +1w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-07-01
}

shift standard "Standard" {
  workinghours mon - sun 09:00 - 17:00
}

resource api_gateway "Global Rate Limiter" {
  workinghours standard
  limits { dailymax 6h }

  resource slot_1 "Connection A" { workinghours standard }
  resource slot_2 "Connection B" { workinghours standard }
  resource slot_3 "Connection C" { workinghours standard }
}

task batch "Daily Processing" {
  task job_a "A" {
    effort 3h
    allocate slot_1
    start 2025-07-01-09:00
  }

  task job_b "B" {
    effort 3h
    allocate slot_2
    start 2025-07-01-09:00
  }

  task job_c "C" {
    effort 3h
    allocate slot_3
  }
}

taskreport quota_output "quota_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `65c892f9bc97a1f52e5cb28c0ba4937727db350f173714236f1afb4e677fe4c8`
**Columns**: 3
**Rows**: 4
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "batch",
      "start": "2025-07-01-09:00",
      "end": "2025-07-02-12:00"
    },
    {
      "id": "batch.job_a",
      "start": "2025-07-01-09:00",
      "end": "2025-07-01-12:00"
    },
    {
      "id": "batch.job_b",
      "start": "2025-07-01-09:00",
      "end": "2025-07-01-12:00"
    },
    {
      "id": "batch.job_c",
      "start": "2025-07-02-09:00",
      "end": "2025-07-02-12:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "65c892f9bc97a1f52e5cb28c0ba4937727db350f173714236f1afb4e677fe4c8"
}
```

---

## Test 16: simple.tjp

**File**: `tests/data/simple.tjp`
**Size**: 795 bytes
**Lines**: 50 lines

### Input File Content

```tjp
/*
 * Simple test project for parser testing
 */
project simple "Simple Project" 2024-01-01 +3m {
  timezone "America/New_York"
  timeformat "%Y-%m-%d"
  currency "USD"
  now 2024-02-01

  scenario plan "Plan" {
    scenario delayed "Delayed" {}
  }
}

copyright "Test Copyright"
rate 400.0
flags team

resource dev "Developers" {
  resource dev1 "Alice" {
    email "alice@example.com"
    rate 350.0
  }
  resource dev2 "Bob" {
    email "bob@example.com"
  }
}

account cost "Project Cost" {
  account dev "Development" {}
}

task project "Project" {
  task spec "Specification" {
    effort 10d
    allocate dev1, dev2
  }

  task impl "Implementation" {
    effort 20d
    depends !spec
    allocate dev1
  }

  task test "Testing" {
    effort 5d
    depends !impl
    allocate dev2
  }
}
```

### Generated Report (JSON)

**Report ID**: `ea3f901dd6426dfa58288d945819c75485fd9ff1875db59def350f219e2d62ca`
**Columns**: 3
**Rows**: 4
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "project",
      "start": "2024-01-01-09:00",
      "end": "2024-02-16-17:00"
    },
    {
      "id": "project.spec",
      "start": "2024-01-01-09:00",
      "end": "2024-01-12-17:00"
    },
    {
      "id": "project.impl",
      "start": "2024-01-15-09:00",
      "end": "2024-02-09-17:00"
    },
    {
      "id": "project.test",
      "start": "2024-02-12-09:00",
      "end": "2024-02-16-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "ea3f901dd6426dfa58288d945819c75485fd9ff1875db59def350f219e2d62ca"
}
```

---

## Test 17: synchrony.tjp

**File**: `tests/data/synchrony.tjp`
**Size**: 1438 bytes
**Lines**: 70 lines

### Input File Content

```tjp
project "Zero_Buffer" 2025-10-09 +1w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-10-09
}

# 1. Shifts
shift factory_shift {
  workinghours mon - fri 08:00 - 18:00
}

# The Train only runs twice a day: 12:00-13:00 and 16:00-17:00
shift train_schedule {
  workinghours mon - fri 12:00 - 13:00, 16:00 - 17:00
}

shift site_shift {
  workinghours mon - fri 08:00 - 18:00
}

# 2. Resources
resource factory "Manufacturing" {
  workinghours factory_shift
  # POWER OUTAGE: The factory is down from 10:00 to 11:00
  booking "Outage" 2025-10-09-10:00 +1h
}

resource train "Logistics" {
  workinghours train_schedule
}

resource site "Construction" {
  workinghours site_shift
}

# 3. The Chain
task supply_chain "JIT Flow" {

  # Step 1: Make (3 Hours Effort)
  task make "Produce" {
    effort 3h
    allocate factory
  }

  # Step 2: Move (1 Hour Fixed Effort)
  task move "Transport" {
    effort 1h
    allocate train

    # ZERO BUFFER CONSTRAINT:
    # Must start EXACTLY when 'make' finishes.
    depends !make { gapduration 0min maxgapduration 0min }
  }

  # Step 3: Install (3 Hours Effort)
  task install "Assemble" {
    effort 3h
    allocate site

    # ZERO BUFFER CONSTRAINT:
    # Must start EXACTLY when 'move' finishes.
    depends !move { gapduration 0min maxgapduration 0min }
  }
}

taskreport synchrony_output "synchrony_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `1746be233a34e9791fa528f12a0e6f60fb466aaae47897bc58064adc8ec439ce`
**Columns**: 3
**Rows**: 4
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "supply_chain",
      "start": "2025-10-09-08:00",
      "end": "2025-10-09-16:00"
    },
    {
      "id": "supply_chain.make",
      "start": "2025-10-09-08:00",
      "end": "2025-10-09-12:00"
    },
    {
      "id": "supply_chain.move",
      "start": "2025-10-09-12:00",
      "end": "2025-10-09-13:00"
    },
    {
      "id": "supply_chain.install",
      "start": "2025-10-09-13:00",
      "end": "2025-10-09-16:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "1746be233a34e9791fa528f12a0e6f60fb466aaae47897bc58064adc8ec439ce"
}
```

---

## Test 18: thermal.tjp

**File**: `tests/data/thermal.tjp`
**Size**: 872 bytes
**Lines**: 43 lines

### Input File Content

```tjp
/*
 * Issue #65: The "Thermal Shock" Protocol
 * Tests maxgapduration constraint (maximum time between dependent tasks)
 * Forge must start within 1h of heat ending, or metal cracks
 */

project "Thermal_Shock" 2025-05-10 +1w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-05-10
}

shift standard "Standard" {
  workinghours mon - fri 09:00 - 17:00
}

resource heater "Furnace" {
  workinghours standard
}

resource press "Hydraulic Press" {
  workinghours standard
  booking "Maintenance" 2025-05-12-09:00 +6h
}

task process "Forging Line" {
  task heat "Heat Ingot" {
    effort 2h
    allocate heater
  }

  task forge "Shape Metal" {
    effort 2h
    allocate press
    depends !heat { gapduration 0min maxgapduration 60min }
  }
}

taskreport thermal_output "thermal_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `bcf3857746102509e6ade09b5dfc7af05024596a2ffe29855d4b60540bfb487f`
**Columns**: 3
**Rows**: 3
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "process",
      "start": "2025-05-12-13:00",
      "end": "2025-05-12-17:00"
    },
    {
      "id": "process.heat",
      "start": "2025-05-12-13:00",
      "end": "2025-05-12-15:00"
    },
    {
      "id": "process.forge",
      "start": "2025-05-12-15:00",
      "end": "2025-05-12-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "bcf3857746102509e6ade09b5dfc7af05024596a2ffe29855d4b60540bfb487f"
}
```

---

## Test 19: throughput.tjp

**File**: `tests/data/throughput.tjp`
**Size**: 883 bytes
**Lines**: 37 lines

### Input File Content

```tjp
/*
 * Issue #61: The "Sine Wave" Capacity Protocol
 * Tests variable daily throughput (batch capacity changes per day)
 * Weekly pattern: 2h, 4h, 8h, 16h, 8h, 4h, 2h = 44h/week
 */

project "Data_Tsunami" 2025-09-01 +1m {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-09-01
}

shift variable_throughput "Variable" {
  workinghours mon 09:00 - 11:00
  workinghours tue 09:00 - 13:00
  workinghours wed 09:00 - 17:00
  workinghours thu 06:00 - 22:00
  workinghours fri 09:00 - 17:00
  workinghours sat 09:00 - 13:00
  workinghours sun 09:00 - 11:00
}

resource server_cluster "Cluster X" {
  workinghours variable_throughput
}

task processing "Ingest 100TB" {
  effort 100h
  allocate server_cluster
  start 2025-09-01-09:00
}

taskreport throughput_output "throughput_output" {
  formats csv
  columns id, start, end, effort, duration
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `3f89e958579ac0bee1b1e79ba68d44179fadc49e251789cf185bc1367c8377da`
**Columns**: 3
**Rows**: 1
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "processing",
      "start": "2025-09-01-09:00",
      "end": "2025-09-17-15:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "3f89e958579ac0bee1b1e79ba68d44179fadc49e251789cf185bc1367c8377da"
}
```

---

## Test 20: time_traveler.tjp

**File**: `tests/data/time_traveler.tjp`
**Size**: 1370 bytes
**Lines**: 63 lines

### Input File Content

```tjp
/*
 * Issue #55: The Time Traveler (ALAP + Timezones)
 * Tests global backward pass with timezone-aware resources
 */

project "Time_Traveler" 2025-06-01 +2w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-06-01

  # Global ALAP: We plan from the deadline backwards
  scheduling alap
}

shift standard "Standard" {
  workinghours mon - fri 09:00 - 18:00
}

resource team "Global" {

  # TOKYO: UTC+9
  resource dev_tokyo "Tokyo Dev" {
    timezone "Asia/Tokyo"
    workinghours mon - fri 09:00 - 18:00
  }

  # LONDON: UTC+1 (British Summer Time in June)
  resource des_london "London Designer" {
    timezone "Europe/London"
    workinghours mon - fri 09:00 - 18:00
  }
}

task launch "Global Launch" {

  # HARD CONSTRAINT: Must finish Friday June 13th, 18:00 JST
  # Note: 18:00 JST = 09:00 UTC
  end 2025-06-13-09:00

  # Task 2: Implementation (Tokyo)
  # Effort: 9h (1 Day)
  # Must finish at the deadline.
  task impl "Implementation" {
    effort 9h
    allocate dev_tokyo
  }

  # Task 1: Design (London)
  # Effort: 9h (1 Day)
  # Implementation depends on Design.
  # So Design must finish before Tokyo starts.
  task design "Blueprint" {
    effort 9h
    allocate des_london
    depends !!impl { onstart }
  }
}

taskreport time_traveler_output "time_traveler_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `866ae6129244234fcaf5b024a509dfa2e1fa9232b8fe928e225e049ad9da33f8`
**Columns**: 3
**Rows**: 3
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "launch",
      "start": "2025-06-12-08:00",
      "end": "2025-06-13-09:00"
    },
    {
      "id": "launch.impl",
      "start": "2025-06-13-00:00",
      "end": "2025-06-13-09:00"
    },
    {
      "id": "launch.design",
      "start": "2025-06-12-08:00",
      "end": "2025-06-12-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "866ae6129244234fcaf5b024a509dfa2e1fa9232b8fe928e225e049ad9da33f8"
}
```

---

## Test 21: timezone_stress.tjp

**File**: `tests/data/timezone_stress.tjp`
**Size**: 1619 bytes
**Lines**: 65 lines

### Input File Content

```tjp
project "Global_Ops" 2025-05-01 +1w {
  timezone "Etc/UTC" # The project clock is UTC
  timeformat "%Y-%m-%d %H:%M"
  now 2025-05-01
}

# 1. Shifts (Defined in Local Time logic, but applied to Timezoned resources)
# We define a standard "9 to 6" shift.
shift local_9to6 {
  workinghours mon - fri 09:00 - 18:00
}

# 2. Resources with Timezones
resource team "Global Team" {

  # TOKYO: UTC+9
  # Local 09:00 is UTC 00:00.
  # Local 18:00 is UTC 09:00.
  resource dev_jp "Tokyo Dev" {
    timezone "Asia/Tokyo"
    workinghours local_9to6
  }

  # NEW YORK: UTC-5 (Assuming Standard Time for simplicity in this test date)
  # Local 09:00 is UTC 14:00.
  # Local 18:00 is UTC 23:00.
  resource qa_ny "NY QA" {
    timezone "America/New_York"
    workinghours local_9to6
  }
}

# 3. The Relay Race
task follow_sun "Handover" {

  # Step 1: Tokyo Work
  # Starts: Mon May 1, 09:00 JST (Local) -> May 1, 00:00 UTC.
  # Effort: 9h (1 Full Day).
  # Ends: Mon May 1, 18:00 JST -> May 1, 09:00 UTC.
  task step1_jp "Build" {
    effort 9h
    allocate dev_jp
    start 2025-05-01-00:00 # Explicit UTC start
  }

  # Step 2: NY Work
  # Dependency: After Tokyo finishes (May 1, 09:00 UTC).
  # Challenge:
  #   At 09:00 UTC, it is 04:00 AM in New York.
  #   NY cannot start yet. They must wait for their shift (09:00 NY time).
  #   09:00 NY Time = 14:00 UTC.
  #   Gap: 5 Hours of "Earth Rotation Delay".
  # Effort: 4h.
  task step2_ny "Test" {
    effort 4h
    allocate qa_ny
    depends !step1_jp
  }
}

taskreport "timezone_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M" # Output in UTC
}
```

### Generated Report (JSON)

**Report ID**: `0df9bccc702de624915c8c02e209b39af24cb34810ea5a30a82075224493d44a`
**Columns**: 3
**Rows**: 3
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "follow_sun",
      "start": "2025-05-01-00:00",
      "end": "2025-05-01-17:00"
    },
    {
      "id": "follow_sun.step1_jp",
      "start": "2025-05-01-00:00",
      "end": "2025-05-01-09:00"
    },
    {
      "id": "follow_sun.step2_ny",
      "start": "2025-05-01-13:00",
      "end": "2025-05-01-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "0df9bccc702de624915c8c02e209b39af24cb34810ea5a30a82075224493d44a"
}
```

---

## Test 22: tutorial.tjp

**File**: `tests/data/tutorial.tjp`
**Size**: 15004 bytes
**Lines**: 496 lines

### Input File Content

```tjp
/*
 * This file contains an example project. It is part of the
 * TaskJuggler project management tool. It uses a made up software
 * development project to demonstrate some of the basic features of
 * TaskJuggler. Please see the TaskJuggler manual for a more detailed
 * description of the various syntax elements.
 */
project acso "Accounting Software"  2002-01-16 +4m {
  # Set the default time zone for the project. If not specified, UTC
  # is used.
  timezone "Europe/Paris"
  # Hide the clock time. Only show the date.
  timeformat "%Y-%m-%d"
  # Use US format for numbers
  numberformat "-" "" "," "." 1
  # Use US financial format for currency values. Don't show cents.
  currencyformat "(" ")" "," "." 0
  # Pick a day during the project that will be reported as 'today' in
  # the project reports. If not specified, the current day will be
  # used, but this will likely be outside of the project range, so it
  # can't be seen in the reports.
  now 2002-03-05-13:00
  # The currency for all money values is the US Dollar.
  currency "USD"

  # We want to compare the baseline scenario to one with a slightly
  # delayed start.
  scenario plan "Plan" {
    scenario delayed "Delayed"
  }
  extend resource {
    text Phone "Phone"
  }
}

# This is not a real copyright for this file. It's just used as an example.
copyright "© 2002 Crappy Software, Inc."

# The daily default rate of all resources. This can be overridden for each
# resource. We specify this, so that we can do a good calculation of
# the costs of the project.
rate 390.0

# Register Good Friday as a global holiday for all resources.
leaves holiday "Good Friday" 2002-03-29
flags team

# This is one way to form teams
macro allocate_developers [
  allocate dev1
  allocate dev2
  allocate dev3
]

# In order to do a simple profit and loss analysis of the project we
# specify accounts. One for the development costs, one for the
# documentation costs, and one account to credit the customer payments
# to.
account cost "Project Cost" {
  account dev "Development"
  account doc "Documentation"
}
account rev "Payments"
# The Profit&Loss analysis should be rev - cost accounts.
balance cost rev

resource boss "Paul Henry Bullock" {
  email "phb@crappysoftware.com"
  Phone "x100"
  rate 480
}
resource dev "Developers" {
  managers boss
  resource dev1 "Paul Smith" {
    email "paul@crappysoftware.com"
    Phone "x362"
    rate 350.0
  }
  resource dev2 "Sébastien Bono" {
    email "SBono@crappysoftware.com"
    Phone "x234"
  }
  resource dev3 "Klaus Müller" {
    email "Klaus.Mueller@crappysoftware.com"
    Phone "x490"
    leaves annual 2002-02-01 - 2002-02-05
  }
  flags team
}
resource misc "The Others" {
  managers boss
  resource test "Peter Murphy" {
    email "murphy@crappysoftware.com"
    Phone "x666"
    limits { dailymax 6.4h }
    rate 310.0
  }
  resource doc "Dim Sung" {
    email "sung@crappysoftware.com"
    Phone "x482"
    rate 300.0
    leaves annual 2002-03-11 - 2002-03-16
  }

  flags team
}

# Now we specify the work packages. The whole project is described as
# a task that contains subtasks. These subtasks are then broken down
# into smaller tasks and so on. The innermost tasks describe the real
# work and have resources allocated to them. Many attributes of tasks
# are inherited from the enclosing task. This saves you a lot of typing.
task AcSo "Accounting Software" {

  # All work-related costs will be booked to this account unless the
  # subtasks specify something different.
  chargeset dev
  # For the duration of the project we have running cost that are not
  # included in the labor cost.
  charge 170 perday
  responsible boss

  task spec "Specification" {
    # The effort to finish this task is 20 man-days.
    effort 20d
    # Now we use the macro declared above to allocate the resources
    # for this task. Because they can work in parallel, they may finish this
    # task earlier than in 20 working-days.
    ${allocate_developers}
    # Each task without subtasks must have a start or an end
    # criterion and a duration. For this task we use a reference to a
    # milestone defined further below as the start criterion. So this task
    # can not start before the specified milestone has been reached.
    # References to other tasks may be relative. Each exclamation mark (!)
    # means 'in the scope of the enclosing task'. To descent into a task, the
    # fullstop (.) together with the id of the tasks have to be specified.
    depends !deliveries.start
  }

  task software "Software Development" {

    # The software is the most critical task of the project. So we set
    # the priority of this task (and all its subtasks) to 1000, the top
    # priority. The higher the priority, the more likely the task will
    # get the requested resources.
    priority 1000

    # All subtasks depend on the specification task.
    depends !spec

    responsible dev1
    task database "Database coupling" {
      effort 20d
      allocate dev1, dev2
      journalentry 2002-02-03 "Problems with the SQL Libary" {
        author dev1
        alert yellow
        summary -8<-
          We ran into some compatibility problems with the SQL
          Library.
        ->8-
        details -8<-
          We have already contacted the vendor and are now waiting for
          their advise.
        ->8-
      }
    }

    task gui "Graphical User Interface" {
      effort 35d
      # This task has taken 5 man-days more than originally planned.
      # We record this as well, so that we can generate reports that
      # compare the delayed schedule of the project to the original plan.
      delayed:effort 40d
      depends !database, !backend
      allocate dev2, dev3
      # Resource dev2 should only work 6 hours per day on this task.
      limits {
        dailymax 6h {
          resources dev2
        }
      }
    }

    task backend "Back-End Functions" {
      effort 30d
      # This task is behind schedule, because it should have been
      # finished already. To document this, we specify that the task
      # is 95% completed. If nothing is specified, TaskJuggler assumes
      # that the task is on schedule and computes the completion rate
      # according to the current day and the plan data.
      complete 95
      depends !database
      allocate dev1, dev2
    }
  }

  task test "Software testing" {

    task alpha "Alpha Test" {
      # Efforts can not only be specified as man-days, but also as
      # man-weeks, man-hours, etc. By default, TaskJuggler assumes
      # that a man-week is 5 man-days or 40 man-hours. These values
      # can be changed, of course.
      effort 1w
      # This task depends on a task in the scope of the enclosing
      # task's enclosing task. So we need two exclamation marks (!!)
      # to get there.
      depends !!software
      allocate test, dev2
      note "Hopefully most bugs will be found and fixed here."
      journalentry 2002-03-01 "Contract with Peter not yet signed" {
        author boss
        alert red
        summary -8<-
          The paperwork is stuck with HR and I can't hunt it down.
        ->8-
        details -8<-
          If we don't get the contract closed within the next week,
          the start of the testing is at risk.
        ->8-
      }
    }

    task beta "Beta Test" {
      effort 4w
      depends !alpha
      allocate test, dev1
    }
  }

  task manual "Manual" {
    effort 10w
    depends !deliveries.start
    allocate doc, dev3
    purge chargeset
    chargeset doc
    journalentry 2002-02-28 "User manual completed" {
      author boss
      summary "The doc writers did a really great job to finish on time."
    }
  }

  task deliveries "Milestones" {

    # Some milestones have customer payments associated with them. We
    # credit these payments to the 'rev' account.
    purge chargeset
    chargeset rev

    task start "Project start" {
      # A task that has no duration is a milestone. It only needs a
      # start or end criterion. All other tasks depend on this task.
      # Here we use the built-in macro ${projectstart} to align the
      # start of the task with the above specified project time frame.
      start ${projectstart}
      # For some reason the actual start of the project got delayed.
      # We record this, so that we can compare the planned run to the
      # delayed run of the project.
      delayed:start 2002-01-20
      # At the beginning of this task we receive a payment from the
      # customer. This is credited to the account associated with this
      # task when the task starts.
      charge 21000.0 onstart
    }

    task prev "Technology Preview" {
      depends !!software.backend
      charge 31000.0 onstart
      note "All '''major''' features should be usable."
    }

    task beta "Beta version" {
      depends !!test.alpha
      charge 13000.0 onstart
      note "Fully functional, may contain bugs."
    }

    task done "Ship Product to Customer" {
      # The next line can be uncommented to trigger a warning about
      # the project being late. For all tasks, limits for the start and
      # end values can be specified. Those limits are checked after the
      # project has been scheduled. For all violated limits a warning
      # is issued.
      # maxend 2002-04-17
      depends !!test.beta, !!manual
      charge 33000.0 onstart
      note "All priority 1 and 2 bugs must be fixed."
    }
  }
}

# Now the project has been specified completely. Stopping here would
# result in a valid TaskJuggler file that could be processed and
# scheduled. But no reports would be generated to visualize the
# results.

navigator navbar {
  hidereport @none
}

macro TaskTip [
  tooltip istask() -8<-
    '''Start: ''' <-query attribute='start'->
    '''End: ''' <-query attribute='end'->
    ----
    '''Resources:'''

    <-query attribute='resources'->
    ----
    '''Precursors: '''

    <-query attribute='precursors'->
    ----
    '''Followers: '''

    <-query attribute='followers'->
    ->8-
]

textreport frame "" {
  header -8<-
    == Accounting Software Project ==
    <[navigator id="navbar"]>
  ->8-
  footer "----"
  textreport index "Overview" {
    formats html
    center '<[report id="overview"]>'
  }

  textreport "Status" {
    formats html
    center -8<-
      <[report id="status.dashboard"]>
      ----
      <[report id="status.completed"]>
      ----
      <[report id="status.ongoing"]>
      ----
      <[report id="status.future"]>
    ->8-
  }

  textreport development "Development" {
    formats html
    center '<[report id="development"]>'
  }

  textreport "Deliveries" {
    formats html
    center '<[report id="deliveries"]>'
  }

  textreport "ContactList" {
    formats html
    title "Contact List"
    center '<[report id="contactList"]>'
  }
  textreport "ResourceGraph" {
    formats html
    title "Resource Graph"
    center '<[report id="resourceGraph"]>'
  }
}

# A traditional Gantt chart with a project overview.
taskreport overview "" {
  header -8<-
    === Project Overview ===

    The project is structured into 3 phases.

    # Specification
    # <-reportlink id='frame.development'->
    # Testing

    === Original Project Plan ===
  ->8-
  columns bsi { title 'WBS' },
          name, start, end, effort, cost,
          revenue, chart { ${TaskTip} }
  # For this report we like to have the abbreviated weekday in front
  # of the date. %a is the tag for this.
  timeformat "%a %Y-%m-%d"
  loadunit days
  hideresource @all
  balance cost rev
  caption 'All effort values are in man days.'

  footer -8<-
    === Staffing ===

    All project phases are properly staffed. See [[ResourceGraph]] for
    detailed resource allocations.

    === Current Status ===

    The project started off with a delay of 4 days. This slightly affected
    the original schedule. See [[Deliveries]] for the impact on the
    delivery dates.
  ->8-
}

# Macro to set the background color of a cell according to the alert
# level of the task.
macro AlertColor [
  cellcolor plan.alert = 0 "#90FF90" # green
  cellcolor plan.alert = 1 "#FFFF90" # yellow
  cellcolor plan.alert = 2 "#FF9090" # red
]

taskreport status "" {
  columns bsi { width 50 title 'WBS' }, name { width 150 },
          start { width 100 }, end { width 100 },
          effort { width 100 },
          alert { tooltip plan.journal
                          != '' "<-query attribute='journal'->" width 150 },
          status { width 150 }
  scenarios delayed

  taskreport dashboard "" {
    headline "Project Dashboard (<-query attribute='now'->)"
    columns name { title "Task" ${AlertColor} width 200},
            resources { width 200 ${AlertColor}
                        listtype bullets
                        listitem "<-query attribute='name'->"
                        start ${projectstart} end ${projectend} },
            alerttrend { title "Trend" ${AlertColor} width 50 },
            journal { width 350 ${AlertColor} }
    journalmode status_up
    journalattributes headline, author, date, summary, details
    hidetask ~hasalert(0)
    sorttasks alert.down, delayed.end.up
    period %{${now} - 1w} +1w
  }
  taskreport completed "" {
    headline "Already completed tasks"
    hidetask ~(delayed.end <= ${now})
  }
  taskreport ongoing "" {
    headline "Ongoing tasks"
    hidetask ~((delayed.start <= ${now}) & (delayed.end > ${now}))
  }
  taskreport future "" {
    headline "Future tasks"
    hidetask ~(delayed.start > ${now})
  }
}

# A list of tasks showing the resources assigned to each task.
taskreport development "" {
  scenarios delayed
  headline "Development - Resource Allocation Report"
  columns bsi { title 'WBS' }, name, start, end, effort { title "Work" },
          duration, chart { ${TaskTip} scale day width 500 }
  timeformat "%Y-%m-%d"
  hideresource ~(isleaf() & isleaf_())
  sortresources name.up
}

# A list of all tasks with the percentage completed for each task
taskreport deliveries "" {
  headline "Project Deliverables"
  columns bsi { title 'WBS' }, name, start, end, note { width 150 }, complete,
          chart { ${TaskTip} }
  taskroot AcSo.deliveries
  hideresource @all
  scenarios plan, delayed
}
# A list of all employees with their contact details.
resourcereport contactList "" {
  scenarios delayed
  headline "Contact list and duty plan"
  columns name,
          email { celltext 1 "[mailto:<-email-> <-email->]" },
          Phone,
          managers { title "Manager" },
          chart { scale day }
  hideresource ~isleaf()
  sortresources name.up
  hidetask @all
}

# A graph showing resource allocation. It identifies whether each
# resource is under- or over-allocated for.
resourcereport resourceGraph "" {
  scenarios delayed
  headline "Resource Allocation Graph"
  columns no, name, effort, rate, weekly { ${TaskTip} }
  loadunit shortauto
  # We only like to show leaf tasks for leaf resources.
  hidetask ~(isleaf() & isleaf_())
  sorttasks plan.start.up
}

```

### Generated Report (JSON)

**Report ID**: `4d19c406e83cce84ba018154c0df2e373bf7df29009c738a90febfaecb3d31c1`
**Columns**: 3
**Rows**: 15
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "AcSo",
      "start": "2002-01-16-00:00",
      "end": "2002-07-25-13:00"
    },
    {
      "id": "AcSo.spec",
      "start": "2002-01-16-09:00",
      "end": "2002-02-14-17:00"
    },
    {
      "id": "AcSo.software",
      "start": "2002-02-15-09:00",
      "end": "2002-06-20-13:00"
    },
    {
      "id": "AcSo.software.database",
      "start": "2002-02-15-09:00",
      "end": "2002-03-14-17:00"
    },
    {
      "id": "AcSo.software.gui",
      "start": "2002-04-29-09:00",
      "end": "2002-06-20-13:00"
    },
    {
      "id": "AcSo.software.backend",
      "start": "2002-03-15-09:00",
      "end": "2002-04-26-17:00"
    },
    {
      "id": "AcSo.test",
      "start": "2002-06-20-13:00",
      "end": "2002-07-25-13:00"
    },
    {
      "id": "AcSo.test.alpha",
      "start": "2002-06-20-13:00",
      "end": "2002-06-27-13:00"
    },
    {
      "id": "AcSo.test.beta",
      "start": "2002-06-27-13:00",
      "end": "2002-07-25-13:00"
    },
    {
      "id": "AcSo.manual",
      "start": "2002-02-15-09:00",
      "end": "2002-06-21-17:00"
    },
    {
      "id": "AcSo.deliveries",
      "start": "2002-01-16-00:00",
      "end": "2002-07-25-13:00"
    },
    {
      "id": "AcSo.deliveries.start",
      "start": "2002-01-16-00:00",
      "end": "2002-01-16-00:00"
    },
    {
      "id": "AcSo.deliveries.prev",
      "start": "2002-04-26-17:00",
      "end": "2002-04-26-17:00"
    },
    {
      "id": "AcSo.deliveries.beta",
      "start": "2002-06-27-13:00",
      "end": "2002-06-27-13:00"
    },
    {
      "id": "AcSo.deliveries.done",
      "start": "2002-07-25-13:00",
      "end": "2002-07-25-13:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "4d19c406e83cce84ba018154c0df2e373bf7df29009c738a90febfaecb3d31c1"
}
```

---

## Test 23: union_contract.tjp

**File**: `tests/data/union_contract.tjp`
**Size**: 950 bytes
**Lines**: 53 lines

### Input File Content

```tjp
/*
 * Issue #56: The "Union Limit" Split
 * Tests weeklymax limit enforcement with ISO week boundaries
 * Task must split across week boundary when hitting 20h weekly cap
 */

project "Union_Contract" 2025-10-01 +2w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-10-01
}

shift standard "Standard" {
  workinghours mon - fri 09:00 - 17:00
}

resource worker "Part Timer" {
  workinghours mon - fri 09:00 - 17:00
  limits { weeklymax 20h }
}

task chain "The Split" {

  task step1 "Wed Work" {
    effort 8h
    allocate worker
    start 2025-10-01-09:00
  }

  task step2 "Thu Work" {
    effort 8h
    allocate worker
    depends !step1
  }

  task step3 "The Split Task" {
    effort 8h
    allocate worker
    depends !step2
  }

  task step4 "Follow Up" {
    effort 4h
    allocate worker
    depends !step3
  }
}

taskreport union_output "union_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
```

### Generated Report (JSON)

**Report ID**: `53256c2039837631b43b3cd9562a6ab152d898c234095920553aa0cff573e56a`
**Columns**: 3
**Rows**: 5
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "chain",
      "start": "2025-10-01-09:00",
      "end": "2025-10-06-17:00"
    },
    {
      "id": "chain.step1",
      "start": "2025-10-01-09:00",
      "end": "2025-10-01-17:00"
    },
    {
      "id": "chain.step2",
      "start": "2025-10-02-09:00",
      "end": "2025-10-02-17:00"
    },
    {
      "id": "chain.step3",
      "start": "2025-10-03-09:00",
      "end": "2025-10-06-13:00"
    },
    {
      "id": "chain.step4",
      "start": "2025-10-06-13:00",
      "end": "2025-10-06-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "53256c2039837631b43b3cd9562a6ab152d898c234095920553aa0cff573e56a"
}
```

---

## Test 24: workflow_engine.tjp

**File**: `tests/data/workflow_engine.tjp`
**Size**: 1381 bytes
**Lines**: 66 lines

### Input File Content

```tjp
project "Cloud_Migration_Workflow" 2025-11-03 +2w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-11-03
}

# 1. Shifts
# Standard: Mon-Fri
shift standard {
  workinghours mon - fri 09:00 - 17:00
}

# Ops Shift: Tue-Sat (Sunday/Monday off)
shift ops_week {
  workinghours tue - sat 09:00 - 17:00
}

# 2. Resources
resource devops "DevOps Team" {

  # The Intern: 50% efficiency.
  # 1 hour of effort takes 2 hours of clock time.
  resource intern "Junior Dev" {
    workinghours standard
    efficiency 0.5
  }

  # The Admin: Standard efficiency, but works Tue-Sat.
  resource admin "SysAdmin" {
    workinghours ops_week
    efficiency 1.0
  }
}

# 3. Workflow
task migration "Migration Pipeline" {

  # Step 1: Code Prep
  # Effort: 16h
  # Resource: Intern (0.5 eff) -> Requires 32h of work time.
  # Calendar: Mon-Fri.
  # Calculation: Mon(8) + Tue(8) + Wed(8) + Thu(8).
  task prep "Code Refactor" {
    effort 16h
    allocate intern
    start 2025-11-03-09:00
  }

  # Step 2: Deployment
  # Effort: 16h
  # Resource: Admin (1.0 eff) -> Requires 16h of work time.
  # Dependency: Must wait for Prep (ends Thu 17:00).
  # Calendar: Tue-Sat.
  task deploy "Server Deployment" {
    effort 16h
    allocate admin
    depends !prep
  }
}

taskreport "workflow_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
  leaftasksonly true
}
```

### Generated Report (JSON)

**Report ID**: `8565eb772606ba218f19cc02b0325ecea3decbdbad159bd99e6590d14bde5389`
**Columns**: 3
**Rows**: 3
**Status**: ✓ Success

```json
{
  "data": [
    {
      "id": "migration",
      "start": "2025-11-03-09:00",
      "end": "2025-11-08-17:00"
    },
    {
      "id": "migration.prep",
      "start": "2025-11-03-09:00",
      "end": "2025-11-06-17:00"
    },
    {
      "id": "migration.deploy",
      "start": "2025-11-07-09:00",
      "end": "2025-11-08-17:00"
    }
  ],
  "columns": [
    "id",
    "start",
    "end"
  ],
  "report_id": "8565eb772606ba218f19cc02b0325ecea3decbdbad159bd99e6590d14bde5389"
}
```

---

## Summary

**Total Test Files**: 24
**Generated**: 2025-11-28 05:35:06 UTC
**Tool Version**: ScriptPlan version 0.9.0

### Verification Checklist

- [ ] All .tjp files parsed successfully
- [ ] All reports contain valid JSON
- [ ] All report_id fields contain SHA256 hashes
- [ ] All column names are lowercase
- [ ] No HTML metadata in JSON output
- [ ] Data structure matches: `{data: [...], columns: [...], report_id: "..."}`

### Notes for Audit Team

This document was automatically generated by the ScriptPlan certification script.
Each test case shows:

1. **Input**: Complete .tjp project file content
2. **Output**: JSON report generated by `plan report` command
3. **Metadata**: Report ID (SHA256 hash), column count, row count

To verify correctness, the audit team can:

1. Re-run any test: `plan report tests/data/<filename>.tjp`
2. Compare output against this document
3. Verify report_id matches SHA256 of input file: `sha256sum tests/data/<filename>.tjp`
4. Validate JSON structure and data completeness

---

**End of Certification Exam Document**
