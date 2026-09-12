"""Shared fixtures.

Two things every test needs and should not each solve: where the example
projects live, and a message handler that does not carry one test's warnings
into the next.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scriptplan.utils.message_handler import get_message_handler_instance

TESTS_DIR = Path(__file__).resolve().parent


@pytest.fixture
def data_dir() -> Path:
    """The directory holding the example .tjp projects.

    Resolved from this file, so the suite runs from any working directory.
    """
    return TESTS_DIR / "data"


@pytest.fixture(autouse=True)
def clean_message_handler():
    """Start each test with an empty message handler.

    It is a process-wide singleton that accumulates, so without this a test
    asserting "no errors were reported" passes or fails depending on which
    tests ran before it.
    """
    handler = get_message_handler_instance()
    handler.clear()
    yield handler
    handler.clear()
