"""
Cython-optimized modules for ScriptPlan.

This package contains Cython implementations of performance-critical code.
Pure Python fallbacks are used if Cython extensions are not compiled.
"""

# Track which optimized modules are available
CYTHON_AVAILABLE = {
    "scoreboard": False,
    "time_utils": False,
    "working_hours": False,
}

# Try to import Cython modules
try:
    from scriptplan._cython import scoreboard_cy  # noqa: F401

    CYTHON_AVAILABLE["scoreboard"] = True
except ImportError:
    pass

try:
    from scriptplan._cython import time_utils_cy  # noqa: F401

    CYTHON_AVAILABLE["time_utils"] = True
except ImportError:
    pass

try:
    from scriptplan._cython import working_hours_cy  # noqa: F401

    CYTHON_AVAILABLE["working_hours"] = True
except ImportError:
    pass


def is_optimized(module: str) -> bool:
    """Check if a Cython-optimized module is available."""
    return CYTHON_AVAILABLE.get(module, False)


def get_available_optimizations() -> list[str]:
    """Get list of available Cython optimizations."""
    return [k for k, v in CYTHON_AVAILABLE.items() if v]
