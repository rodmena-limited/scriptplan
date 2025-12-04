"""Log module implementing segmented execution traces.

The Log class implements a filter for segmented execution traces. The
trace messages are filtered based on their segment name and the nesting
level of the segments. The class uses a Singleton pattern.
"""

import sys
import threading
from typing import Callable, ClassVar, Optional, Union


class ANSIColor:
    """ANSI color codes for terminal output."""

    GREEN: ClassVar[str] = "\033[32m"
    RED: ClassVar[str] = "\033[31m"
    YELLOW: ClassVar[str] = "\033[33m"
    BLUE: ClassVar[str] = "\033[34m"
    RESET: ClassVar[str] = "\033[0m"

    @classmethod
    def green(cls, text: str) -> str:
        return f"{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def red(cls, text: str) -> str:
        return f"{cls.RED}{text}{cls.RESET}"

    @classmethod
    def yellow(cls, text: str) -> str:
        return f"{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def blue(cls, text: str) -> str:
        return f"{cls.BLUE}{text}{cls.RESET}"


class Log:
    """Singleton class for segmented execution trace logging.

    The trace messages are filtered based on their segment name and the nesting
    level of the segments.
    """

    _instance: ClassVar[Optional["Log"]] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    # Class-level variables (equivalent to Ruby's @@)
    _level: ClassVar[int] = 0
    _stack: ClassVar[list[str]] = []
    _segments: ClassVar[list[str]] = []
    _silent: ClassVar[bool] = True
    _progress: ClassVar[Union[int, float]] = 0
    _progressMeter: ClassVar[str] = ""

    def __new__(cls) -> "Log":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_level(cls) -> int:
        """Get the current log level."""
        return cls._level

    @classmethod
    def set_level(cls, level: int) -> None:
        """Set the maximum nesting level that should be shown.

        Segments with a nesting level greater than level will be silently dropped.
        """
        cls._level = level

    # Property-style accessors
    level = property(lambda cls: cls._level)

    @classmethod
    def get_segments(cls) -> list[str]:
        """Get the current segment filter list."""
        return cls._segments

    @classmethod
    def set_segments(cls, segments: list[str]) -> None:
        """Set the segment filter list.

        Messages not in these segments will be ignored. Messages from segments
        that are nested into the shown segments will be shown for the next
        _level nested segments.
        """
        cls._segments = segments

    @classmethod
    def get_silent(cls) -> bool:
        """Get the silent mode status."""
        return cls._silent

    @classmethod
    def set_silent(cls, silent: bool) -> None:
        """Set silent mode. If True, progress information will not be shown."""
        cls._silent = silent

    @classmethod
    def enter(cls, segment: str, message: str) -> None:
        """Open a new segment.

        Args:
            segment: The name of the segment.
            message: A description of the segment.
        """
        if cls._level == 0:
            return

        cls._stack.append(segment)
        cls.msg(lambda: f">> [{segment}] {message}")

    @classmethod
    def exit(cls, segment: str, message: Optional[str] = None) -> None:
        """Close an open segment.

        Will search the stack of open segments for a segment with that name
        and will close all nested segments as well.

        Args:
            segment: The name of the segment to close.
            message: Optional exit message.
        """
        if cls._level == 0:
            return

        if message:
            cls.msg(lambda: f"<< [{segment}] {message}")

        if segment in cls._stack:
            while cls._stack:
                m = cls._stack.pop()
                if m == segment:
                    break

    @classmethod
    def msg(cls, message_func: Callable[[], str]) -> None:
        """Show a log message within the currently active segment.

        The message is the result of the passed callable. The callable will
        only be evaluated if the message will actually be shown.

        Args:
            message_func: A callable that returns the message string.
        """
        if cls._level == 0:
            return

        offset = 0
        if cls._segments:
            showMessage = False
            for segment in cls._stack:
                if segment in cls._segments:
                    offset = cls._stack.index(segment)
                    showMessage = True
                    break
            if not showMessage:
                return

        if len(cls._stack) - offset < cls._level:
            indent = " " * (len(cls._stack) - offset)
            print(indent + message_func(), file=sys.stderr)

    @classmethod
    def status(cls, message: str) -> None:
        """Print out a status message unless in silent mode."""
        if cls._silent:
            return
        print(message)

    @classmethod
    def startProgressMeter(cls, text: str) -> None:
        """Start the progress meter display or change the info text.

        While the meter is active, the text cursor is always returned to
        the start of the same line.
        """
        if cls._silent:
            return

        maxlen = 60
        text = text.ljust(maxlen)
        if len(text) > maxlen:
            text = text[:maxlen]
        cls._progressMeter = text
        print(f"{cls._progressMeter} ...", end="\r")
        sys.stdout.flush()

    @classmethod
    def stopProgressMeter(cls) -> None:
        """Set the progress meter status to 'done' and move to the next line."""
        if cls._silent:
            return
        print(f"{cls._progressMeter} [      {ANSIColor.green('Done')}      ]")

    @classmethod
    def activity(cls) -> None:
        """Update the progress indicator to the next symbol.

        May only be called after startProgressMeter.
        """
        if cls._silent:
            return

        indicator = ["-", "\\", "|", "/"]
        int_progress = int(cls._progress) if isinstance(cls._progress, float) else cls._progress
        cls._progress = (int_progress + 1) % len(indicator)
        int_idx = int(cls._progress) if isinstance(cls._progress, float) else cls._progress
        print(f"{cls._progressMeter} [{indicator[int_idx]}]", end="\r")
        sys.stdout.flush()

    @classmethod
    def progress(cls, percent: float) -> None:
        """Update the progress bar to the given percent completion.

        May only be called after startProgressMeter.

        Args:
            percent: Completion value between 0.0 and 1.0.
        """
        if cls._silent:
            return

        percent = max(0.0, min(1.0, percent))
        cls._progress = percent

        length = 16
        full = int(length * percent)
        bar = "=" * full + " " * (length - full)
        label = f"{int(percent * 100.0)}%"
        start = length // 2 - len(label) // 2
        bar = bar[:start] + label + bar[start + len(label) :]
        print(f"{cls._progressMeter} [{ANSIColor.green(bar)}]", end="\r")
        sys.stdout.flush()


# Convenience function to get the singleton instance
def get_logger() -> Log:
    """Return the Log singleton instance."""
    return Log()
