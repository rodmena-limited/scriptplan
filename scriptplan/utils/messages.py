"""What a diagnostic is: its severity, where it came from, how it prints.

Split from message_handler so that the types a caller needs in order to read a
message do not drag in the handler that produces them.
"""

from enum import Enum
from typing import Any, ClassVar, Optional

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
