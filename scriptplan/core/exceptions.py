"""
ScriptPlan exception hierarchy.

This module defines all custom exceptions used throughout the ScriptPlan
application for comprehensive error handling.
"""

import logging
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)


class ScriptPlanError(Exception):
    """Base exception for all ScriptPlan errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            return "%s [%s]: %s" % (self.error_code, self.context, self.message)  # noqa: UP031
        return "%s: %s" % (self.error_code, self.message)  # noqa: UP031


# ============================================================================
# Parsing Errors
# ============================================================================


class ParsingError(ScriptPlanError):
    """Base class for all parsing-related errors."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        line_no: Optional[int] = None,
        column_no: Optional[int] = None,
        **kwargs: Any,
    ):
        context = kwargs.pop("context", {})
        if file_path:
            context["file"] = file_path
        if line_no is not None:
            context["line"] = line_no
        if column_no is not None:
            context["column"] = column_no
        super().__init__(message, context=context, **kwargs)
        self.file_path = file_path
        self.line_no = line_no
        self.column_no = column_no


class SyntaxParsingError(ParsingError):
    """Raised when TJP syntax is invalid."""

    pass


class SemanticError(ParsingError):
    """Raised when TJP content is syntactically valid but semantically incorrect."""

    pass


class InvalidAttributeError(ParsingError):
    """Raised when an invalid attribute is specified."""

    pass


class DuplicateDefinitionError(ParsingError):
    """Raised when a task, resource, or other entity is defined twice."""

    pass


# ============================================================================
# Scheduling Errors
# ============================================================================


class SchedulingError(ScriptPlanError):
    """Base class for all scheduling-related errors."""

    pass


class ResourceConflictError(SchedulingError):
    """Raised when resource allocation conflicts cannot be resolved."""

    def __init__(
        self,
        message: str,
        resource_id: Optional[str] = None,
        task_id: Optional[str] = None,
        slot_idx: Optional[int] = None,
        **kwargs: Any,
    ):
        context = kwargs.pop("context", {})
        if resource_id:
            context["resource"] = resource_id
        if task_id:
            context["task"] = task_id
        if slot_idx is not None:
            context["slot"] = slot_idx
        super().__init__(message, context=context, **kwargs)


class DependencyError(SchedulingError):
    """Raised when task dependencies cannot be satisfied."""

    def __init__(self, message: str, task_id: Optional[str] = None, dependency_id: Optional[str] = None, **kwargs: Any):
        context = kwargs.pop("context", {})
        if task_id:
            context["task"] = task_id
        if dependency_id:
            context["dependency"] = dependency_id
        super().__init__(message, context=context, **kwargs)


class CircularDependencyError(DependencyError):
    """Raised when circular task dependencies are detected."""

    pass


class UnschedulableTaskError(SchedulingError):
    """Raised when a task cannot be scheduled within project constraints."""

    def __init__(self, message: str, task_id: Optional[str] = None, reason: Optional[str] = None, **kwargs: Any):
        context = kwargs.pop("context", {})
        if task_id:
            context["task"] = task_id
        if reason:
            context["reason"] = reason
        super().__init__(message, context=context, **kwargs)


class DeadlineMissedError(SchedulingError):
    """Raised when a task cannot meet its deadline."""

    pass


# ============================================================================
# Resource Errors
# ============================================================================


class ResourceError(ScriptPlanError):
    """Base class for resource-related errors."""

    pass


class ResourceNotFoundError(ResourceError):
    """Raised when a referenced resource does not exist."""

    pass


class ResourceOverloadError(ResourceError):
    """Raised when resource capacity limits are exceeded."""

    pass


# ============================================================================
# Configuration Errors
# ============================================================================


class ConfigurationError(ScriptPlanError):
    """Raised when project configuration is invalid."""

    pass


class InvalidDateRangeError(ConfigurationError):
    """Raised when date ranges are invalid (e.g., end before start)."""

    pass


class InvalidGranularityError(ConfigurationError):
    """Raised when timing resolution/granularity is invalid."""

    pass


# ============================================================================
# Report Errors
# ============================================================================


class ReportError(ScriptPlanError):
    """Base class for report generation errors."""

    pass


class ReportGenerationError(ReportError):
    """Raised when report generation fails."""

    pass


class UnsupportedFormatError(ReportError):
    """Raised when an unsupported output format is requested."""

    pass


# ============================================================================
# I/O Errors
# ============================================================================


class FileError(ScriptPlanError):
    """Base class for file-related errors."""

    pass


class FileNotFoundError(FileError):
    """Raised when a required file is not found."""

    pass


class FilePermissionError(FileError):
    """Raised when file access is denied."""

    pass


class OutputDirectoryError(FileError):
    """Raised when output directory is invalid or inaccessible."""

    pass


# ============================================================================
# Runtime Errors
# ============================================================================


class RuntimeError(ScriptPlanError):
    """Base class for runtime errors during execution."""

    pass


class InternalError(RuntimeError):
    """Raised for internal errors that should not occur."""

    pass


class TimeoutError(RuntimeError):
    """Raised when an operation exceeds time limits."""

    pass


# ============================================================================
# Error Handler Decorator
# ============================================================================


F = TypeVar("F", bound=Callable[..., Any])


def handle_errors(
    error_code: str = "UNKNOWN", reraise: bool = True, log_level: int = logging.ERROR
) -> Callable[[F], F]:
    """
    Decorator for comprehensive error handling on functions.

    Args:
        error_code: Error code prefix for logging
        reraise: Whether to reraise the exception after logging
        log_level: Logging level to use

    Usage:
        @handle_errors("SCHEDULING")
        def schedule_task(task):
            ...
    """

    def decorator(func):  # type: ignore[no-untyped-def]
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            try:
                return func(*args, **kwargs)
            except ScriptPlanError:
                # Already a ScriptPlan error, just log and reraise
                logger.log(log_level, "%s error in %s", error_code, func.__name__, exc_info=True)
                if reraise:
                    raise
            except Exception as e:
                # Wrap in ScriptPlanError
                logger.log(log_level, "%s unexpected error in %s: %s", error_code, func.__name__, str(e), exc_info=True)
                if reraise:
                    raise InternalError(
                        "Unexpected error: %s" % str(e),  # noqa: UP031
                        error_code=error_code,
                        context={"function": func.__name__, "original_error": type(e).__name__},
                    ) from e

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
