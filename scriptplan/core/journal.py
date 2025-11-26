"""
Journal - Project journal for tracking status and progress.

This module implements the Journal and JournalEntry classes for storing
and managing status reports and progress updates on tasks and resources.

A JournalEntry stores RichText strings to describe a status or property
of the project at a certain point in time. Additionally, the entry can
contain a reference to a Resource as author and an alert level.
"""

from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from scriptplan.core.project import Project
    from scriptplan.core.resource import Resource
    from scriptplan.core.task import Task


class AlertLevel(IntEnum):
    """Alert levels for journal entries."""

    GREEN = 0  # On track
    YELLOW = 1  # Minor issues
    RED = 2  # Major issues/blocked


class JournalEntry:
    """
    A journal entry stores status or progress information about a task
    or resource at a specific point in time.

    The text is structured in 3 elements:
    - headline: A very short description (should not exceed ~40 characters)
    - summary: An introductory or summarizing paragraph (optional)
    - details: A longer text segment (optional)

    Attributes:
        journal: Reference to the parent Journal object
        date: The date of the entry
        headline: Short description (mandatory)
        property: Reference to the Task or Resource this entry is about
        source_file_info: Source file location of this entry
        author: Reference to the Resource who authored this entry
        moderators: List of Resources who moderated this entry
        summary: Introductory/summarizing RichText paragraph
        details: RichText of arbitrary length
        alert_level: The alert level (GREEN, YELLOW, RED)
        flags: List of flag identifiers
        timesheet_record: Reference to associated TimeSheetRecord
    """

    def __init__(
        self, journal: "Journal", date: datetime, headline: str, property_node: Any, source_file_info: Any = None
    ):
        """
        Create a new JournalEntry object.

        Args:
            journal: The parent Journal object
            date: The date of the entry
            headline: Short description text
            property_node: The Task or Resource this entry is about
            source_file_info: Optional source file location
        """
        self.journal = journal
        self.date = date
        self.headline = headline
        self.property = property_node
        self.source_file_info = source_file_info

        self.author: Optional[Resource] = None
        self.moderators: list[Resource] = []
        self.summary: Optional[str] = None
        self.details: Optional[str] = None
        self.alert_level: AlertLevel = AlertLevel.GREEN
        self.flags: list[str] = []
        self.timesheet_record: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "date": self.date.isoformat() if self.date else None,
            "headline": self.headline,
            "property_id": self.property.fullId if self.property else None,
            "author_id": self.author.fullId if self.author else None,
            "alert_level": self.alert_level.name,
            "summary": str(self.summary) if self.summary else None,
            "details": str(self.details) if self.details else None,
            "flags": self.flags,
        }

    def __repr__(self) -> str:
        return (
            f"JournalEntry(date={self.date}, headline='{self.headline}', "
            f"property={self.property.fullId if self.property else None})"
        )


class JournalEntryList(list[JournalEntry]):
    """
    A list of JournalEntry objects with sorting capabilities.

    This class provides methods to sort journal entries and apply
    various filtering operations.
    """

    def __init__(self, entries: Optional[list[JournalEntry]] = None):
        """Initialize with optional list of entries."""
        super().__init__(entries or [])

    def sort_by(self, criteria: list[tuple[str, bool]]) -> "JournalEntryList":
        """
        Sort entries by multiple criteria.

        Args:
            criteria: List of (attribute, ascending) tuples

        Returns:
            Self for chaining
        """

        def sort_key(entry: JournalEntry) -> tuple[Any, ...]:
            key_parts = []
            for attr, ascending in criteria:
                val = getattr(entry, attr, None)
                if val is None:
                    val = ""
                if not ascending:
                    if isinstance(val, (int, float)):
                        val = -val
                    elif isinstance(val, datetime):
                        # Invert datetime for descending
                        val = datetime.max - val
                key_parts.append(val)
            return tuple(key_parts)

        self.sort(key=sort_key)
        return self

    def filter(self, predicate: Callable[[JournalEntry], bool]) -> "JournalEntryList":
        """
        Filter entries using a predicate function.

        Args:
            predicate: Function that returns True for entries to keep

        Returns:
            New JournalEntryList with filtered entries
        """
        return JournalEntryList([e for e in self if predicate(e)])


class Journal:
    """
    Container for all JournalEntry objects of a project.

    The Journal provides methods to add entries and query them by
    task, resource, date range, and other criteria.

    Attributes:
        project: Reference to the Project object
        entries: List of all journal entries
    """

    def __init__(self, project: Optional["Project"] = None):
        """
        Create a new Journal.

        Args:
            project: Optional reference to the Project
        """
        self.project = project
        self._entries: list[JournalEntry] = []
        self._entries_by_property: dict[str, list[JournalEntry]] = {}

    def add_entry(self, entry: JournalEntry) -> JournalEntry:
        """
        Add a journal entry to the journal.

        Args:
            entry: The JournalEntry to add

        Returns:
            The added entry
        """
        self._entries.append(entry)

        # Index by property ID for fast lookup
        if entry.property:
            prop_id = entry.property.fullId
            if prop_id not in self._entries_by_property:
                self._entries_by_property[prop_id] = []
            self._entries_by_property[prop_id].append(entry)

        return entry

    def create_entry(
        self, date: datetime, headline: str, property_node: Any, source_file_info: Any = None
    ) -> JournalEntry:
        """
        Create and add a new journal entry.

        Args:
            date: The date of the entry
            headline: Short description text
            property_node: The Task or Resource this entry is about
            source_file_info: Optional source file location

        Returns:
            The created JournalEntry
        """
        entry = JournalEntry(self, date, headline, property_node, source_file_info)
        return self.add_entry(entry)

    @property
    def entries(self) -> JournalEntryList:
        """Get all entries as a JournalEntryList."""
        return JournalEntryList(self._entries)

    def __len__(self) -> int:
        """Return the number of entries."""
        return len(self._entries)

    def __iter__(self) -> Any:
        """Iterate over entries."""
        return iter(self._entries)

    def entries_by_task(
        self,
        task: "Task",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        alert_level: Optional[AlertLevel] = None,
    ) -> JournalEntryList:
        """
        Get journal entries for a specific task.

        Args:
            task: The task to get entries for
            start: Optional start date filter
            end: Optional end date filter
            alert_level: Optional minimum alert level filter

        Returns:
            JournalEntryList of matching entries
        """
        entries = self._entries_by_property.get(task.fullId, [])
        return self._filter_entries(entries, start, end, alert_level)

    def entries_by_task_recursive(
        self,
        task: Any,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        alert_level: Optional[AlertLevel] = None,
    ) -> JournalEntryList:
        """
        Get journal entries for a task and all its children.

        Args:
            task: The root task (or any property-like object with fullId and children)
            start: Optional start date filter
            end: Optional end date filter
            alert_level: Optional minimum alert level filter

        Returns:
            JournalEntryList of matching entries from task and children
        """
        result = []

        # Get entries for this task
        result.extend(self._entries_by_property.get(task.fullId, []))

        # Get entries for all children recursively
        if hasattr(task, "children"):
            for child in task.children:
                result.extend(self.entries_by_task_recursive(child, start, end, alert_level))

        return self._filter_entries(result, start, end, alert_level)

    def entries_by_resource(
        self, resource: "Resource", start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> JournalEntryList:
        """
        Get journal entries authored by a specific resource.

        Args:
            resource: The author resource
            start: Optional start date filter
            end: Optional end date filter

        Returns:
            JournalEntryList of entries by this resource
        """
        entries = [e for e in self._entries if e.author == resource]
        return self._filter_entries(entries, start, end)

    def entries_by_date(self, date: datetime) -> JournalEntryList:
        """
        Get all journal entries for a specific date.

        Args:
            date: The date to query

        Returns:
            JournalEntryList of entries on that date
        """
        # Compare dates only (ignore time)
        target_date = date.date() if isinstance(date, datetime) else date
        entries = [e for e in self._entries if e.date and e.date.date() == target_date]
        return JournalEntryList(entries)

    def entries_in_range(self, start: datetime, end: datetime) -> JournalEntryList:
        """
        Get all journal entries within a date range.

        Args:
            start: Start date (inclusive)
            end: End date (exclusive)

        Returns:
            JournalEntryList of entries in the range
        """
        return self._filter_entries(self._entries, start, end)

    def current_entries(
        self,
        scenario_idx: int,
        property_node: Any,
        start: datetime,
        end: datetime,
        alert_level: Optional[AlertLevel] = None,
    ) -> JournalEntryList:
        """
        Get current (most recent) entries for a property within a time range.

        This is used to get the latest status for tasks/resources.

        Args:
            scenario_idx: Scenario index
            property_node: The task or resource
            start: Start of time range
            end: End of time range
            alert_level: Optional minimum alert level

        Returns:
            JournalEntryList of current entries
        """
        entries = self._entries_by_property.get(property_node.fullId, [])
        filtered = self._filter_entries(entries, start, end, alert_level)

        # Sort by date descending and return most recent
        filtered.sort_by([("date", False)])
        return filtered

    def _filter_entries(
        self,
        entries: list[JournalEntry],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        alert_level: Optional[AlertLevel] = None,
    ) -> JournalEntryList:
        """
        Apply date and alert level filters to entries.

        Args:
            entries: List of entries to filter
            start: Optional start date (inclusive)
            end: Optional end date (exclusive)
            alert_level: Optional minimum alert level

        Returns:
            Filtered JournalEntryList
        """
        result = list(entries)

        if start:
            result = [e for e in result if e.date and e.date >= start]

        if end:
            result = [e for e in result if e.date and e.date < end]

        if alert_level is not None:
            result = [e for e in result if e.alert_level >= alert_level]

        return JournalEntryList(result)

    def clear(self) -> None:
        """Remove all entries from the journal."""
        self._entries.clear()
        self._entries_by_property.clear()

    def to_list(self) -> list[dict[str, Any]]:
        """Convert all entries to a list of dictionaries."""
        return [entry.to_dict() for entry in self._entries]
