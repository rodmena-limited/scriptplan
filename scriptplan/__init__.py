"""
ScriptPlan - A Python implementation of TaskJuggler.

This package provides project scheduling and resource management capabilities
similar to TaskJuggler, implemented in Python.
"""

__version__ = "0.9.0"
__author__ = "ScriptPlan Team"

from scriptplan.core.project import Project
from scriptplan.core.resource import Resource
from scriptplan.core.scenario import Scenario
from scriptplan.core.task import Task

__all__ = [
    'Project',
    'Resource',
    'Scenario',
    'Task',
    '__version__',
]
