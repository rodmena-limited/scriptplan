"""
Setup script for building scriptplan with optional Cython extensions.

Cython extensions provide ~25% performance improvement but are optional.
Pure Python fallbacks are used when extensions are not available.
"""

import os
from setuptools import setup, Extension

# Allow disabling Cython via environment variable
USE_CYTHON = os.environ.get("SCRIPTPLAN_NO_CYTHON", "0") != "1"

try:
    if USE_CYTHON:
        from Cython.Build import cythonize
        HAS_CYTHON = True
    else:
        HAS_CYTHON = False
except ImportError:
    HAS_CYTHON = False


def get_extensions():
    """Get Cython extensions if Cython is available."""
    if not HAS_CYTHON:
        return []

    extensions = [
        Extension(
            "scriptplan._cython.scoreboard_cy",
            ["scriptplan/_cython/scoreboard_cy.pyx"],
            language="c",
        ),
        Extension(
            "scriptplan._cython.time_utils_cy",
            ["scriptplan/_cython/time_utils_cy.pyx"],
            language="c",
        ),
        Extension(
            "scriptplan._cython.working_hours_cy",
            ["scriptplan/_cython/working_hours_cy.pyx"],
            language="c",
        ),
    ]

    try:
        return cythonize(
            extensions,
            compiler_directives={
                "language_level": "3",
                "boundscheck": False,
                "wraparound": False,
                "cdivision": True,
                "initializedcheck": False,
            },
            annotate=False,
        )
    except Exception:
        # Cython compilation failed, fall back to pure Python
        return []


setup(
    ext_modules=get_extensions(),
)
