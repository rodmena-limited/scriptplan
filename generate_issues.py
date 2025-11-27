import os
import json
import glob
import subprocess

RUBY_LIB_DIR = "../TaskJuggler/lib/taskjuggler"
PROJECT_ROOT = "rodmena_resource_management"

# Mapping Ruby files to Python modules/classes
FILE_MAPPING = {
    "Project.rb": {"module": "core.project", "class": "Project", "priority": "critical"},
    "Task.rb": {"module": "core.task", "class": "Task", "priority": "critical"},
    "Resource.rb": {"module": "core.resource", "class": "Resource", "priority": "critical"},
    "Scenario.rb": {"module": "core.scenario", "class": "Scenario", "priority": "high"},
    "PropertyTreeNode.rb": {"module": "core.property", "class": "PropertyTreeNode", "priority": "high"},
    "PropertySet.rb": {"module": "core.property", "class": "PropertySet", "priority": "high"},
    "PropertyList.rb": {"module": "core.property", "class": "PropertyList", "priority": "medium"},
    "AttributeBase.rb": {"module": "core.attribute", "class": "AttributeBase", "priority": "medium"},
    "AttributeDefinition.rb": {"module": "core.attribute", "class": "AttributeDefinition", "priority": "medium"},
    "Booking.rb": {"module": "core.booking", "class": "Booking", "priority": "high"},
    "Allocation.rb": {"module": "core.allocation", "class": "Allocation", "priority": "high"},
    "Shift.rb": {"module": "core.shift", "class": "Shift", "priority": "medium"},
    "Account.rb": {"module": "core.account", "class": "Account", "priority": "medium"},
    "Journal.rb": {"module": "core.journal", "class": "Journal", "priority": "low"},
    "TjTime.rb": {"module": "utils.time", "class": "TjTime", "priority": "high"},
    "ProjectFileParser.rb": {"module": "parser.tjp_parser", "class": "ProjectFileParser", "priority": "critical"},
    "BatchProcessor.rb": {"module": "scheduler.batch_processor", "class": "BatchProcessor", "priority": "medium"},
    "Scoreboard.rb": {"module": "scheduler.scoreboard", "class": "Scoreboard", "priority": "high"},
    "TimeSheets.rb": {"module": "core.timesheet", "class": "TimeSheets", "priority": "medium"},
    "Log.rb": {"module": "utils.logger", "class": "Log", "priority": "medium"},
    "MessageHandler.rb": {"module": "utils.message_handler", "class": "MessageHandler", "priority": "medium"},
}

issues = []

# 1. Architecture Issues
issues.append({
    "title": "Initialize Project Structure",
    "description": "Create the initial directory structure for the python package `rodmena_resource_management`.\n\nStructure:\n- core/\n- parser/\n- scheduler/\n- report/\n- utils/\n- cli/\n- tests/",
    "priority": "critical",
    "status": "open"
})

# 2. Porting Issues
for filename, info in FILE_MAPPING.items():
    file_path = os.path.join(RUBY_LIB_DIR, filename)
    
    # Read Ruby file content for context (truncated)
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(2000) # Read first 2000 chars for context
    except FileNotFoundError:
        content = "File not found."
    
    issue = {
        "title": f"Port {filename} to {info['module']}",
        "description": f"Implement the {info['class']} class in {info['module']}.py.\n\nOriginal Ruby file: {filename}\nTarget Python Module: {info['module']}\n\nContext:\n{content}...",
        "priority": info['priority'],
        "status": "open"
    }
    issues.append(issue)

# 3. Functional Issues (Scheduling, Parsing, Reporting)
issues.append({
    "title": "Implement TJP Parser",
    "description": "Implement the parser for TaskJuggler Project (TJP) files. \nReference `ProjectFileParser.rb`.\nConsider using a Python parser library like Lark or PLY.",
    "priority": "critical",
    "status": "open"
})

issues.append({
    "title": "Implement Scheduling Logic",
    "description": "Implement the main scheduling loop. \nReference `Project.rb` method `scheduleScenario` and `Task.rb` method `schedule`.\nThis is the core logic for resource leveling and path criticalness.",
    "priority": "critical",
    "status": "open"
})

issues.append({
    "title": "Implement Reporting System",
    "description": "Implement the base reporting system. \nReference `reports/Report.rb`.",
    "priority": "high",
    "status": "open"
})

issues.append({
    "title": "Implement CLI",
    "description": "Implement the Command Line Interface for the application. \nIt should accept a TJP file and optional flags (like TaskJuggler's `tj3`).",
    "priority": "high",
    "status": "open"
})

# 4. Testing
issues.append({
    "title": "Setup Testing Framework",
    "description": "Set up `pytest` and create initial tests for the core modules.",
    "priority": "high",
    "status": "open"
})

# Save to JSON
with open('issues.json', 'w') as f:
    json.dump(issues, f, indent=2)

print(f"Generated {len(issues)} issues in issues.json")
