"""
Rodmena Resource Management - A Python implementation of TaskJuggler.

This package provides project scheduling and resource management capabilities
similar to TaskJuggler, implemented in Python.
"""

__version__ = "0.1.0"
__author__ = "Rodmena Team"

from rodmena_resource_management.core.project import Project
from rodmena_resource_management.core.task import Task
from rodmena_resource_management.core.resource import Resource
from rodmena_resource_management.core.scenario import Scenario

__all__ = [
    '__version__',
    'Project',
    'Task',
    'Resource',
    'Scenario',
]
