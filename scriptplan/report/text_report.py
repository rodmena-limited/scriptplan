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
        html_content: Generated HTML content
    """

    def __init__(self, report: 'Report'):
        """
        Initialize TextReport.

        Args:
            report: The parent Report object
        """
        super().__init__(report)
        self.html_content = ''

    def generate_intermediate_format(self) -> None:
        """
        Generate the intermediate format for text report.

        This method processes all RichText elements and prepares them
        for output.
        """
        super().generate_intermediate_format()

        # Build the content from various text blocks
        parts = []

        # Prolog
        prolog = self.a('prolog')
        if prolog:
            parts.append(self._rich_text_to_html(prolog))

        # Header
        header = self.a('header')
        if header:
            parts.append(f'<div class="tj_header">{self._rich_text_to_html(header)}</div>')

        # Headline
        headline = self.a('headline')
        if headline:
            parts.append(f'<div class="tj_headline">{self._rich_text_to_html(headline)}</div>')

        # Left/Center/Right blocks
        left = self.a('left')
        center = self.a('center')
        right = self.a('right')

        if left or center or right:
            parts.append('<div class="tj_columns">')
            if left:
                parts.append(f'<div class="tj_left">{self._rich_text_to_html(left)}</div>')
            if center:
                parts.append(f'<div class="tj_center">{self._rich_text_to_html(center)}</div>')
            if right:
                parts.append(f'<div class="tj_right">{self._rich_text_to_html(right)}</div>')
            parts.append('</div>')

        # Caption
        caption = self.a('caption')
        if caption:
            parts.append(f'<div class="tj_caption">{self._rich_text_to_html(caption)}</div>')

        # Footer
        footer = self.a('footer')
        if footer:
            parts.append(f'<div class="tj_footer">{self._rich_text_to_html(footer)}</div>')

        # Epilog
        epilog = self.a('epilog')
        if epilog:
            parts.append(self._rich_text_to_html(epilog))

        self.html_content = '\n'.join(parts)

    def to_html(self) -> Optional[str]:
        """
        Convert the text report to HTML.

        Returns:
            HTML string representation
        """
        return self.html_content if self.html_content else None

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

        prolog = self.a('prolog')
        if prolog:
            parts.append(self._to_plain_text(prolog))

        headline = self.a('headline')
        if headline:
            parts.append(self._to_plain_text(headline))
            parts.append('=' * 60)

        left = self.a('left')
        center = self.a('center')
        right = self.a('right')

        if left:
            parts.append(self._to_plain_text(left))
        if center:
            parts.append(self._to_plain_text(center))
        if right:
            parts.append(self._to_plain_text(right))

        caption = self.a('caption')
        if caption:
            parts.append('-' * 60)
            parts.append(self._to_plain_text(caption))

        epilog = self.a('epilog')
        if epilog:
            parts.append(self._to_plain_text(epilog))

        return '\n\n'.join(filter(None, parts))

    def _to_plain_text(self, text: Any) -> str:
        """
        Convert RichText or string to plain text.

        Args:
            text: RichText object or string

        Returns:
            Plain text string
        """
        if text is None:
            return ''
        if hasattr(text, 'to_text'):
            return text.to_text()
        if hasattr(text, 'to_s'):
            return text.to_s()
        return str(text)
