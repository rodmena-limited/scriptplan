"""Setup shim.

ScriptPlan is pure Python. The build configuration lives in pyproject.toml;
this file exists only so that tooling which still shells out to setup.py has
something to call.

There were once three Cython extensions here. They accelerated the flat
per-slot scoreboard, and they made the published wheel compute different
schedules from the source it was built from: under `cdivision=True`,
`(0 - 1) % 7` is -1 rather than 6, so a resource with a Sunday night shift
lost its Monday morning in every wheel and kept it in every checkout. One
implementation that is right is worth more than two that disagree.
"""

from setuptools import setup

setup()
