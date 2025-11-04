"""
ScriptPlan - A Python implementation inspired by TaskJuggler.

This package provides project scheduling and resource management capabilities
compatible with the TaskJuggler Project Definition Language (.tjp files).

ScriptPlan owes its existence to TaskJuggler (https://taskjuggler.org/),
the pioneering open-source project management tool created by Chris Schlaeger.
The TJP file format and scheduling concepts originate from TaskJuggler.
"""

__version__ = "0.9.2"
__author__ = "ScriptPlan Team"

from scriptplan.core.project import Project
from scriptplan.core.resource import Resource
from scriptplan.core.scenario import Scenario
from scriptplan.core.task import Task

__all__ = [
    "Project",
    "Resource",
    "Scenario",
    "Task",
    "__version__",
]
