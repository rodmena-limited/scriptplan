"""
TextReport - Simple text-based report content generator.

This module provides the TextReport class which generates simple text-based
reports that can contain RichText blocks for header, body, and footer sections.
"""

from typing import TYPE_CHECKING, Any, Optional

from scriptplan.report.report_base import ReportBase

if TYPE_CHECKING:
    from scriptplan.report.report import Report


class TextReport(ReportBase):
    """
    Simple text report generator.

    This report type generates a simple text-based output that can contain
    RichText blocks for prolog, header, center, epilog, etc.

    Attributes:
        content_data: Generated content data
    """

    def __init__(self, report: "Report"):
        """
        Initialize TextReport.

        Args:
            report: The parent Report object
        """
        super().__init__(report)
        self.content_data: dict[str, Any] = {}

    def generate_intermediate_format(self) -> None:
        """
        Generate the intermediate format for text report.

        This method processes all RichText elements and prepares them
        for output.
        """
        super().generate_intermediate_format()

        # Build the content from various text blocks
        self.content_data = {}

        # Prolog
        prolog = self.a("prolog")
        if prolog:
            self.content_data["prolog"] = self._to_plain_text(prolog)

        # Header
        header = self.a("header")
        if header:
            self.content_data["header"] = self._to_plain_text(header)

        # Headline
        headline = self.a("headline")
        if headline:
            self.content_data["headline"] = self._to_plain_text(headline)

        # Left/Center/Right blocks
        left = self.a("left")
        center = self.a("center")
        right = self.a("right")

        if left:
            self.content_data["left"] = self._to_plain_text(left)
        if center:
            self.content_data["center"] = self._to_plain_text(center)
        if right:
            self.content_data["right"] = self._to_plain_text(right)

        # Caption
        caption = self.a("caption")
        if caption:
            self.content_data["caption"] = self._to_plain_text(caption)

        # Footer
        footer = self.a("footer")
        if footer:
            self.content_data["footer"] = self._to_plain_text(footer)

        # Epilog
        epilog = self.a("epilog")
        if epilog:
            self.content_data["epilog"] = self._to_plain_text(epilog)

    def to_json(self) -> Optional[dict[str, Any]]:
        """
        Convert the text report to JSON.

        Returns:
            Dictionary representation
        """
        return self.content_data if self.content_data else None

    def to_csv(self) -> Optional[list[list[str]]]:
        """
        Convert the text report to CSV.

        Text reports don't have tabular data, so this returns None.

        Returns:
            None (text reports are not suitable for CSV)
        """
        return None

    def to_text(self) -> str:
        """
        Convert the report to plain text.

        Returns:
            Plain text representation
        """
        parts = []

        prolog = self.a("prolog")
        if prolog:
            parts.append(self._to_plain_text(prolog))

        headline = self.a("headline")
        if headline:
            parts.append(self._to_plain_text(headline))
            parts.append("=" * 60)

        left = self.a("left")
        center = self.a("center")
        right = self.a("right")

        if left:
            parts.append(self._to_plain_text(left))
        if center:
            parts.append(self._to_plain_text(center))
        if right:
            parts.append(self._to_plain_text(right))

        caption = self.a("caption")
        if caption:
            parts.append("-" * 60)
            parts.append(self._to_plain_text(caption))

        epilog = self.a("epilog")
        if epilog:
            parts.append(self._to_plain_text(epilog))

        return "\n\n".join(filter(None, parts))

    def _to_plain_text(self, text: Any) -> str:
        """
        Convert RichText or string to plain text.

        Args:
            text: RichText object or string

        Returns:
            Plain text string
        """
        if text is None:
            return ""
        if hasattr(text, "to_text"):
            result = text.to_text()
            return str(result) if result is not None else ""
        if hasattr(text, "to_s"):
            result = text.to_s()
            return str(result) if result is not None else ""
        return str(text)
