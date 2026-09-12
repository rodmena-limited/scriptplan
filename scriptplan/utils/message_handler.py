"""Collecting and rendering diagnostics.

The handler is a process-wide singleton, which is why it can collect errors
rather than raise them only where a caller has said so: see ``collecting``.
A library never terminates its host process, so an error raises or is recorded;
it never exits.
"""

from __future__ import annotations

import contextlib
import sys
import threading
from collections.abc import Iterator
from datetime import datetime
from typing import Any, ClassVar

from scriptplan.utils.messages import (
    Message,
    MessageType,
    SourceFileInfo,
    TjException,
    TjRuntimeError,
)

__all__ = [
    # Re-exported so existing imports from this module keep working.
    "Message",
    "MessageHandler",
    "MessageHandlerInstance",
    "MessageType",
    "SourceFileInfo",
    "TjException",
    "TjRuntimeError",
    "get_message_handler_instance",
]


class MessageHandlerInstance:
    """Singleton class for managing messages and logging.

    Manages message storage and output, tracks error counts, and controls
    output levels for both console and log files.
    """

    _instance: ClassVar[MessageHandlerInstance | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    LOG_LEVELS: ClassVar[dict[str | MessageType, int]] = {
        "none": 0,
        MessageType.FATAL: 1,
        MessageType.ERROR: 2,
        MessageType.CRITICAL: 2,
        MessageType.WARNING: 3,
        MessageType.INFO: 4,
        MessageType.DEBUG: 5,
    }

    _initialized: bool
    _output_level: int
    _log_level: int
    _log_file: str | None
    _hide_scenario: bool
    _app_name: str
    _abort_on_warning: bool
    _collect_errors: bool
    _baseline_sfi: dict[int, SourceFileInfo]
    _trap_setup: dict[int, bool]
    _errors: int
    _messages: list[Message]

    def __new__(cls) -> MessageHandlerInstance:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.reset()

    def reset(self) -> None:
        """Reset all handler state to defaults."""
        self._output_level = 4
        self._log_level = 3
        self._log_file = None
        self._hide_scenario = True
        self._app_name = "unknown"
        self._abort_on_warning = False
        self._collect_errors = False
        self._baseline_sfi = {}
        self._trap_setup = {}

        self.clear()

    @property
    def messages(self) -> list[Message]:
        return self._messages

    @property
    def errors(self) -> int:
        return self._errors

    @property
    def logFile(self) -> str | None:
        return self._log_file

    @logFile.setter
    def logFile(self, value: str | None) -> None:
        self._log_file = value

    @property
    def appName(self) -> str:
        return self._app_name

    @appName.setter
    def appName(self, value: str) -> None:
        self._app_name = value

    @property
    def collectErrors(self) -> bool:
        """When True, an error is recorded instead of raised.

        Applications that want to report every problem in one run (the CLIs, and
        the scheduler's own pre-flight checks) turn this on for the duration of
        the run and inspect ``messages`` afterwards.
        """
        return self._collect_errors

    @collectErrors.setter
    def collectErrors(self, value: bool) -> None:
        self._collect_errors = bool(value)

    @contextlib.contextmanager
    def collecting(self) -> Iterator[MessageHandlerInstance]:
        """Collect errors for the duration of the block, then restore."""
        previous = self._collect_errors
        self._collect_errors = True
        try:
            yield self
        finally:
            self._collect_errors = previous

    @property
    def abortOnWarning(self) -> bool:
        return self._abort_on_warning

    @abortOnWarning.setter
    def abortOnWarning(self, value: bool) -> None:
        self._abort_on_warning = value

    @property
    def baselineSFI(self) -> SourceFileInfo | None:
        thread_id = threading.current_thread().ident
        if thread_id is None:
            return None
        return self._baseline_sfi.get(thread_id)

    @baselineSFI.setter
    def baselineSFI(self, value: SourceFileInfo | None) -> None:
        thread_id = threading.current_thread().ident
        if thread_id is not None and value is not None:
            self._baseline_sfi[thread_id] = value

    @property
    def trapSetup(self) -> bool:
        thread_id = threading.current_thread().ident
        if thread_id is None:
            return False
        return self._trap_setup.get(thread_id, False)

    @trapSetup.setter
    def trapSetup(self, value: bool) -> None:
        thread_id = threading.current_thread().ident
        if thread_id is not None:
            self._trap_setup[thread_id] = value

    def clear(self) -> None:
        """Clear all stored messages and reset error count."""
        self._errors = 0
        self._messages = []

    @property
    def outputLevel(self) -> int:
        return self._output_level

    @outputLevel.setter
    def outputLevel(self, level: int | str | MessageType) -> None:
        self._output_level = self._check_level(level)

    @property
    def logLevel(self) -> int:
        return self._log_level

    @logLevel.setter
    def logLevel(self, level: int | str | MessageType) -> None:
        self._log_level = self._check_level(level)

    @property
    def hideScenario(self) -> bool:
        return self._hide_scenario

    @hideScenario.setter
    def hideScenario(self, value: bool) -> None:
        self._hide_scenario = value

    def _check_level(self, level: int | str | MessageType) -> int:
        """Validate and convert log level to integer."""
        if isinstance(level, int):
            if level < 0 or level > 5:
                raise ValueError(f"Unsupported level {level}")
            return level

        if isinstance(level, MessageType):
            return self.LOG_LEVELS.get(level, 0)

        if isinstance(level, str):
            level_lower = level.lower()
            for key, val in self.LOG_LEVELS.items():
                if (isinstance(key, str) and key == level_lower) or (
                    isinstance(key, MessageType) and key.value == level_lower
                ):
                    return val

        raise ValueError(f"Unsupported level {level}")

    def _log(self, msg_type: MessageType, message: str) -> None:
        """Write message to log file if configured."""
        if not self._log_file:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import os

        pid = os.getpid()

        try:
            with open(self._log_file, "a") as f:
                f.write(f"{timestamp} {msg_type.value} {self._app_name}[{pid}]: {message}\n")
        except Exception as e:
            print(f"Cannot write to log file {self._log_file}: {e}", file=sys.stderr)

    def _add_message(
        self,
        msg_type: MessageType,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Add a message and handle based on type."""
        # Adjust source file info based on baseline
        baseline_sfi = self.baselineSFI
        if source_file_info and baseline_sfi:
            source_file_info = SourceFileInfo(
                baseline_sfi.fileName, source_file_info.lineNo + baseline_sfi.lineNo - 1, source_file_info.columnNo
            )

        # Create message - convert critical to error for display
        display_type = MessageType.ERROR if msg_type == MessageType.CRITICAL else msg_type
        msg = Message(
            display_type, msg_id, message, source_file_info, line, data, None if self._hide_scenario else scenario
        )
        self._messages.append(msg)

        # Log if level is appropriate
        if self._log_level >= self.LOG_LEVELS.get(msg_type, 0):
            self._log(msg_type, msg.to_log())

        # Output to stderr if level is appropriate
        if self._output_level >= self.LOG_LEVELS.get(msg_type, 0):
            print(str(msg), file=sys.stderr)

        # Handle message type-specific actions
        if msg_type == MessageType.WARNING:
            if self._abort_on_warning:
                raise TjException("")
        elif msg_type == MessageType.CRITICAL:
            self._errors += 1
        elif msg_type == MessageType.ERROR:
            self._errors += 1
            # A library never terminates its host process. An error is raised so
            # the caller can collect it, or handled by an application that has
            # opted into collecting rather than raising.
            if not self._collect_errors:
                raise TjRuntimeError(str(msg))
        elif msg_type == MessageType.FATAL:
            raise RuntimeError(message)

    def fatal(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a fatal error and raise RuntimeError."""
        self._add_message(MessageType.FATAL, msg_id, message, source_file_info, line, data, scenario)

    def error(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log an error.

        Raises TjRuntimeError unless the caller has opted into collecting
        errors with ``collectErrors``. Never terminates the process.
        """
        self._add_message(MessageType.ERROR, msg_id, message, source_file_info, line, data, scenario)

    def critical(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a critical error. Increments error count but does not exit."""
        self._add_message(MessageType.CRITICAL, msg_id, message, source_file_info, line, data, scenario)

    def warning(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a warning. May raise TjException if abortOnWarning is set."""
        self._add_message(MessageType.WARNING, msg_id, message, source_file_info, line, data, scenario)

    def info(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log an info message."""
        self._add_message(MessageType.INFO, msg_id, message, source_file_info, line, data, scenario)

    def debug(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a debug message."""
        self._add_message(MessageType.DEBUG, msg_id, message, source_file_info, line, data, scenario)

    def __str__(self) -> str:
        """Return all messages as a single string."""
        return "".join(str(msg) for msg in self._messages)


# Singleton accessor
def get_message_handler_instance() -> MessageHandlerInstance:
    """Return the MessageHandlerInstance singleton."""
    return MessageHandlerInstance()


class MessageHandler:
    """Mixin class providing message handling methods.

    Classes that inherit from MessageHandler can use fatal, error, critical,
    warning, info, and debug methods to send messages through the global
    MessageHandlerInstance singleton.
    """

    def fatal(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a fatal error and raise RuntimeError."""
        MessageHandlerInstance().fatal(msg_id, message, source_file_info, line, data, scenario)

    def error(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log an error."""
        MessageHandlerInstance().error(msg_id, message, source_file_info, line, data, scenario)

    def critical(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a critical error."""
        MessageHandlerInstance().critical(msg_id, message, source_file_info, line, data, scenario)

    def warning(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a warning."""
        MessageHandlerInstance().warning(msg_id, message, source_file_info, line, data, scenario)

    def info(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log an info message."""
        MessageHandlerInstance().info(msg_id, message, source_file_info, line, data, scenario)

    def debug(
        self,
        msg_id: str,
        message: str,
        source_file_info: SourceFileInfo | None = None,
        line: str | None = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a debug message."""
        MessageHandlerInstance().debug(msg_id, message, source_file_info, line, data, scenario)
