"""
ScriptPlan - a project scheduling engine for .tjp project files.

This package provides project scheduling and resource management capabilities
for project files written in the .tjp project definition language.
"""

# The single source of truth for the version; pyproject reads it from here.
# 0.10.2: every stated date and dependency is kept or refused, never overridden.
__version__ = "0.10.2"
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
