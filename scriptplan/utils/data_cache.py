"""The list of files a project was read from."""

from __future__ import annotations

__all__ = ["FileList"]


class FileList(list):
    """The input files a project was built from, in the order they were read."""
