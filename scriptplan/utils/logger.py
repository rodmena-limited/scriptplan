"""Terminal colours for diagnostic output.

This module once also held a Log class implementing segmented execution
traces. Nothing called it, it kept its nesting stack in class variables with
no lock, and it wrote to stdout, which a library has no business owning. It
was removed rather than fixed: unreachable code cannot be verified.
"""

from __future__ import annotations

from typing import ClassVar

__all__ = ["ANSIColor"]


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
