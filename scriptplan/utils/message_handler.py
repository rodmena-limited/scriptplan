"""MessageHandler module for managing application messages.

Contains Message, MessageHandlerInstance singleton, and MessageHandler mixin
for handling fatal errors, errors, warnings, info, and debug messages.
"""

import sys
import threading
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Optional, Union

from scriptplan.utils.logger import ANSIColor


class TjRuntimeError(RuntimeError):
    """TaskJuggler runtime error exception."""

    pass


class TjException(Exception):
    """TaskJuggler exception for controlled abort."""

    pass


class SourceFileInfo:
    """Holds information about a source file location.

    This is a simplified version - full implementation would be in TextParser module.
    """

    def __init__(self, file_name: str, line_no: int = 0, column_no: int = 0):
        self._file_name = file_name
        self._line_no = line_no
        self._column_no = column_no

    @property
    def fileName(self) -> str:
        return self._file_name

    @property
    def lineNo(self) -> int:
        return self._line_no

    @property
    def columnNo(self) -> int:
        return self._column_no

    def __repr__(self) -> str:
        return f"SourceFileInfo({self._file_name}:{self._line_no}:{self._column_no})"


class MessageType(Enum):
    """Message severity types."""

    FATAL = "fatal"
    ERROR = "error"
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


class Message:
    """Stores a single message with type, ID, content, and optional source info.

    Supports five message types: fatal, error, warning, info, and debug.
    Messages can include source file locations and specific line content for debugging.
    """

    VALID_TYPES: ClassVar[list[MessageType]] = [
        MessageType.FATAL,
        MessageType.ERROR,
        MessageType.WARNING,
        MessageType.INFO,
        MessageType.DEBUG,
    ]

    def __init__(
        self,
        msg_type: MessageType,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ):
        """Create a new Message object.

        Args:
            msg_type: Message type (fatal, error, warning, info, debug).
            msg_id: Unique identifier for the message source.
            message: The actual message content.
            source_file_info: Optional source file location reference.
            line: Optional line content from the source file.
            data: Optional context-sensitive data.
            scenario: Optional Scenario where the message originated.
        """
        if msg_type not in self.VALID_TYPES:
            raise ValueError(f"Unknown message type: {msg_type}")
        self._type = msg_type

        self._id = msg_id

        if message is not None and not isinstance(message, str):
            raise TypeError(f"String object expected as message but got {type(message).__name__}")
        self._message = message

        if source_file_info is not None and not isinstance(source_file_info, SourceFileInfo):
            raise TypeError(f"SourceFileInfo object expected but got {type(source_file_info).__name__}")
        self._source_file_info = source_file_info

        if line is not None and not isinstance(line, str):
            raise TypeError(f"String object expected as line but got {type(line).__name__}")
        self._line = line

        self._data = data
        self._scenario = scenario

    @property
    def type(self) -> MessageType:
        return self._type

    @property
    def id(self) -> str:
        return self._id

    @property
    def message(self) -> str:
        return self._message

    @property
    def sourceFileInfo(self) -> Optional[SourceFileInfo]:
        return self._source_file_info

    @sourceFileInfo.setter
    def sourceFileInfo(self, value: Optional[SourceFileInfo]) -> None:
        self._source_file_info = value

    @property
    def line(self) -> Optional[str]:
        return self._line

    @property
    def data(self) -> Any:
        return self._data

    @property
    def scenario(self) -> Any:
        return self._scenario

    def __str__(self) -> str:
        """Return formatted string with ANSI colors for console output."""
        result = ""

        if self._source_file_info:
            result += f"{self._source_file_info.fileName}:{self._source_file_info.lineNo}: "

        if self._scenario and hasattr(self._scenario, "id"):
            tag = f"{self._type.value.capitalize()} in scenario {self._scenario.id}: "
        else:
            tag = f"{self._type.value.capitalize()}: "

        colors = {
            MessageType.FATAL: ANSIColor.red,
            MessageType.ERROR: ANSIColor.red,
            MessageType.WARNING: ANSIColor.yellow,
            MessageType.INFO: ANSIColor.blue,
            MessageType.DEBUG: ANSIColor.green,
        }

        color_func = colors.get(self._type, lambda x: x)
        result += color_func(tag + (self._message or ""))

        if self._line:
            result += "\n" + self._line

        return result

    def to_log(self) -> str:
        """Return plain text string for log file output."""
        result = ""

        if self._source_file_info:
            result += f"{self._source_file_info.fileName}:{self._source_file_info.lineNo}: "

        if self._scenario and hasattr(self._scenario, "id"):
            result += f"Scenario {self._scenario.id}: "

        result += self._message or ""

        return result


class MessageHandlerInstance:
    """Singleton class for managing messages and logging.

    Manages message storage and output, tracks error counts, and controls
    output levels for both console and log files.
    """

    _instance: ClassVar[Optional["MessageHandlerInstance"]] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    LOG_LEVELS: ClassVar[dict[Union[str, MessageType], int]] = {
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
    _log_file: Optional[str]
    _hide_scenario: bool
    _app_name: str
    _abort_on_warning: bool
    _baseline_sfi: dict[int, SourceFileInfo]
    _trap_setup: dict[int, bool]
    _errors: int
    _messages: list[Message]

    def __new__(cls) -> "MessageHandlerInstance":
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
    def logFile(self) -> Optional[str]:
        return self._log_file

    @logFile.setter
    def logFile(self, value: Optional[str]) -> None:
        self._log_file = value

    @property
    def appName(self) -> str:
        return self._app_name

    @appName.setter
    def appName(self, value: str) -> None:
        self._app_name = value

    @property
    def abortOnWarning(self) -> bool:
        return self._abort_on_warning

    @abortOnWarning.setter
    def abortOnWarning(self, value: bool) -> None:
        self._abort_on_warning = value

    @property
    def baselineSFI(self) -> Optional[SourceFileInfo]:
        thread_id = threading.current_thread().ident
        if thread_id is None:
            return None
        return self._baseline_sfi.get(thread_id)

    @baselineSFI.setter
    def baselineSFI(self, value: Optional[SourceFileInfo]) -> None:
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
    def outputLevel(self, level: Union[int, str, MessageType]) -> None:
        self._output_level = self._check_level(level)

    @property
    def logLevel(self) -> int:
        return self._log_level

    @logLevel.setter
    def logLevel(self, level: Union[int, str, MessageType]) -> None:
        self._log_level = self._check_level(level)

    @property
    def hideScenario(self) -> bool:
        return self._hide_scenario

    @hideScenario.setter
    def hideScenario(self, value: bool) -> None:
        self._hide_scenario = value

    def _check_level(self, level: Union[int, str, MessageType]) -> int:
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
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
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
            if self.trapSetup:
                raise TjRuntimeError()
            else:
                sys.exit(1)
        elif msg_type == MessageType.FATAL:
            raise RuntimeError(message)

    def fatal(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a fatal error and raise RuntimeError."""
        self._add_message(MessageType.FATAL, msg_id, message, source_file_info, line, data, scenario)

    def error(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log an error. Will exit or raise TjRuntimeError based on trapSetup."""
        self._add_message(MessageType.ERROR, msg_id, message, source_file_info, line, data, scenario)

    def critical(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a critical error. Increments error count but does not exit."""
        self._add_message(MessageType.CRITICAL, msg_id, message, source_file_info, line, data, scenario)

    def warning(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a warning. May raise TjException if abortOnWarning is set."""
        self._add_message(MessageType.WARNING, msg_id, message, source_file_info, line, data, scenario)

    def info(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log an info message."""
        self._add_message(MessageType.INFO, msg_id, message, source_file_info, line, data, scenario)

    def debug(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
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
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a fatal error and raise RuntimeError."""
        MessageHandlerInstance().fatal(msg_id, message, source_file_info, line, data, scenario)

    def error(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log an error."""
        MessageHandlerInstance().error(msg_id, message, source_file_info, line, data, scenario)

    def critical(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a critical error."""
        MessageHandlerInstance().critical(msg_id, message, source_file_info, line, data, scenario)

    def warning(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a warning."""
        MessageHandlerInstance().warning(msg_id, message, source_file_info, line, data, scenario)

    def info(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log an info message."""
        MessageHandlerInstance().info(msg_id, message, source_file_info, line, data, scenario)

    def debug(
        self,
        msg_id: str,
        message: str,
        source_file_info: Optional[SourceFileInfo] = None,
        line: Optional[str] = None,
        data: Any = None,
        scenario: Any = None,
    ) -> None:
        """Log a debug message."""
        MessageHandlerInstance().debug(msg_id, message, source_file_info, line, data, scenario)
