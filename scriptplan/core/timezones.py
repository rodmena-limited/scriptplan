"""Moving between the times written in a file and the times scheduled against.

A .tjp file is written in the project's timezone: "start 2025-01-06-09:00" in a
project declared `timezone "America/New_York"` means nine in the morning in New
York. Scheduling happens in UTC, so that a resource in Tokyo and a resource in
New York can be laid on the same axis. Reports convert back.

Times are carried as naive datetimes throughout, so what a naive datetime
*means* depends on where it is: local in the file and in a report, UTC once it
reaches the model. These two functions are the only places that changes.
"""

from __future__ import annotations

from datetime import datetime, timezone

__all__ = ["from_utc", "is_utc", "resolve_zone", "to_utc"]

_UTC_NAMES = {"utc", "etc/utc", "etc/gmt", "gmt", "z", "zulu", "universal"}


def is_utc(name: str | None) -> bool:
    """Whether this zone name is UTC, so conversion is a no-op."""
    return not name or str(name).strip().lower() in _UTC_NAMES


def resolve_zone(name: str | None) -> object | None:
    """The tzinfo for a zone name, or None if it is UTC or unknown."""
    if is_utc(name):
        return None
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(str(name))
    except Exception:
        return None


def to_utc(moment: datetime | None, zone_name: str | None) -> datetime | None:
    """Read a naive datetime as local to ``zone_name`` and return naive UTC."""
    if moment is None:
        return None
    if moment.tzinfo is not None:
        return moment.astimezone(timezone.utc).replace(tzinfo=None)
    zone = resolve_zone(zone_name)
    if zone is None:
        return moment
    return moment.replace(tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)  # type: ignore[arg-type]


def from_utc(moment: datetime | None, zone_name: str | None) -> datetime | None:
    """Read a naive datetime as UTC and return it naive in ``zone_name``."""
    if moment is None:
        return None
    zone = resolve_zone(zone_name)
    if zone is None:
        return moment.replace(tzinfo=None) if moment.tzinfo is not None else moment
    aware = moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment
    return aware.astimezone(zone).replace(tzinfo=None)  # type: ignore[arg-type]
