"""
HTML Generator - Complete HTML document generation for reports.

This module provides utilities for generating complete HTML documents
with proper CSS styling, similar to TaskJuggler's output.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


def get_default_css() -> str:
    """Get the default CSS for TaskJuggler-style reports."""
    return """
/* TaskJuggler Style CSS */
:root {
    --tj-primary: #4a90d9;
    --tj-primary-dark: #2c6eb3;
    --tj-header-bg: #4a5568;
    --tj-header-text: #ffffff;
    --tj-border: #e2e8f0;
    --tj-row-alt: #f7fafc;
    --tj-row-hover: #edf2f7;
    --tj-text: #2d3748;
    --tj-text-muted: #718096;
    --tj-success: #48bb78;
    --tj-warning: #ed8936;
    --tj-danger: #f56565;
}

* {
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    color: var(--tj-text);
    background-color: #f5f5f5;
    margin: 0;
    padding: 0;
}

.tj_container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
    background: white;
    min-height: 100vh;
}

/* Header Styles */
.tj_page_header {
    background: var(--tj-header-bg);
    color: var(--tj-header-text);
    padding: 20px 30px;
    margin: -20px -20px 20px -20px;
}

.tj_page_header h1 {
    margin: 0 0 5px 0;
    font-size: 24px;
    font-weight: 600;
}

.tj_page_header .subtitle {
    font-size: 14px;
    opacity: 0.9;
}

/* Navigation */
.tj_navigation {
    background: #f8f9fa;
    border-bottom: 1px solid var(--tj-border);
    padding: 10px 20px;
    margin: -20px -20px 20px -20px;
}

.tj_navigation a {
    color: var(--tj-primary);
    text-decoration: none;
    margin-right: 20px;
    font-size: 13px;
}

.tj_navigation a:hover {
    text-decoration: underline;
}

.tj_navigation a.active {
    font-weight: 600;
}

/* Table Styles */
.tj_report_table {
    width: 100%;
    border-collapse: collapse;
    border: 1px solid var(--tj-border);
    font-size: 13px;
}

.tj_report_table thead {
    background: var(--tj-header-bg);
}

.tj_report_table th {
    color: var(--tj-header-text);
    font-weight: 600;
    text-align: left;
    padding: 12px 15px;
    border-bottom: 2px solid var(--tj-primary-dark);
    white-space: nowrap;
}

.tj_report_table td {
    padding: 10px 15px;
    border-bottom: 1px solid var(--tj-border);
    vertical-align: middle;
}

.tj_report_table tbody tr:nth-child(even) {
    background-color: var(--tj-row-alt);
}

.tj_report_table tbody tr:hover {
    background-color: var(--tj-row-hover);
}

/* Task hierarchy indentation */
.tj_report_table .indent-0 { padding-left: 15px; }
.tj_report_table .indent-1 { padding-left: 35px; }
.tj_report_table .indent-2 { padding-left: 55px; }
.tj_report_table .indent-3 { padding-left: 75px; }
.tj_report_table .indent-4 { padding-left: 95px; }

/* Row types */
.tj_report_table tr.container_task {
    font-weight: 600;
    background-color: #f0f4f8 !important;
}

.tj_report_table tr.milestone {
    font-style: italic;
}

.tj_report_table tr.nested_resource {
    background-color: #fafbfc !important;
    font-size: 12px;
}

/* Table Frame */
.tj_table_frame {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}

.tj_table_frame td {
    padding: 0;
}

/* Headline */
.tj_table_headline {
    font-size: 18px;
    font-weight: 600;
    color: var(--tj-text);
    padding: 15px 0;
    border-bottom: 2px solid var(--tj-primary);
    margin-bottom: 15px;
}

/* Caption */
.tj_table_caption {
    font-style: italic;
    color: var(--tj-text-muted);
    padding: 15px 0;
    border-top: 1px solid var(--tj-border);
    margin-top: 15px;
}

/* Legend */
.tj_table_legend {
    margin-top: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 4px;
}

.tj_table_legend table {
    border: none;
}

.tj_table_legend td {
    padding: 5px 15px 5px 0;
    vertical-align: middle;
}

/* Alert Colors */
.alert-green {
    color: var(--tj-success);
}

.alert-yellow {
    color: var(--tj-warning);
}

.alert-red {
    color: var(--tj-danger);
}

.alert-indicator {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
}

.alert-indicator.green { background-color: var(--tj-success); }
.alert-indicator.yellow { background-color: var(--tj-warning); }
.alert-indicator.red { background-color: var(--tj-danger); }

/* Gantt Chart Placeholder */
.tj_gantt_bar {
    height: 18px;
    background: var(--tj-primary);
    border-radius: 3px;
    position: relative;
}

.tj_gantt_bar.milestone {
    width: 12px;
    height: 12px;
    background: var(--tj-text);
    transform: rotate(45deg);
    margin: 3px auto;
}

.tj_gantt_container {
    position: relative;
    height: 24px;
}

/* Text Report Sections */
.tj_header, .tj_footer {
    padding: 15px 0;
}

.tj_headline {
    font-size: 20px;
    font-weight: 600;
    padding: 20px 0 10px 0;
    border-bottom: 2px solid var(--tj-primary);
    margin-bottom: 20px;
}

.tj_columns {
    display: flex;
    gap: 30px;
    margin: 20px 0;
}

.tj_left, .tj_center, .tj_right {
    flex: 1;
}

.tj_center { text-align: center; }
.tj_right { text-align: right; }

/* Journal Entries */
.tj_journal_entry {
    border-left: 4px solid var(--tj-border);
    padding: 10px 15px;
    margin: 10px 0;
}

.tj_journal_entry.alert-green { border-left-color: var(--tj-success); }
.tj_journal_entry.alert-yellow { border-left-color: var(--tj-warning); }
.tj_journal_entry.alert-red { border-left-color: var(--tj-danger); }

.tj_journal_date {
    font-size: 12px;
    color: var(--tj-text-muted);
}

.tj_journal_headline {
    font-weight: 600;
    margin: 5px 0;
}

.tj_journal_author {
    font-size: 12px;
    color: var(--tj-text-muted);
}

.tj_journal_summary {
    margin-top: 10px;
}

/* Footer */
.tj_page_footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--tj-border);
    text-align: center;
    font-size: 12px;
    color: var(--tj-text-muted);
}

/* Print Styles */
@media print {
    body {
        background: white;
    }

    .tj_container {
        padding: 0;
        max-width: none;
    }

    .tj_navigation {
        display: none;
    }

    .tj_report_table {
        font-size: 11px;
    }

    .tj_report_table th,
    .tj_report_table td {
        padding: 6px 10px;
    }
}
"""


def build_html_document(title: str, content: str,
                       project_name: str = '',
                       subtitle: str = '',
                       navigation: Optional[List[Dict[str, str]]] = None,
                       include_css: bool = True,
                       custom_css: str = '',
                       footer: bool = True) -> str:
    """
    Build a complete HTML document for a report.

    Args:
        title: Page title
        content: Main content HTML
        project_name: Project name for header
        subtitle: Subtitle for header
        navigation: List of nav items [{'title': '...', 'url': '...', 'active': bool}]
        include_css: Whether to include default CSS
        custom_css: Additional CSS to include
        footer: Whether to include footer

    Returns:
        Complete HTML document string
    """
    css = ''
    if include_css:
        css = f'<style>{get_default_css()}</style>'
    if custom_css:
        css += f'<style>{custom_css}</style>'

    nav_html = ''
    if navigation:
        nav_items = []
        for item in navigation:
            active = ' class="active"' if item.get('active') else ''
            nav_items.append(f'<a href="{item["url"]}"{active}>{item["title"]}</a>')
        nav_html = f'<nav class="tj_navigation">{" ".join(nav_items)}</nav>'

    header_html = ''
    if project_name or subtitle:
        header_html = f'''
        <header class="tj_page_header">
            <h1>{project_name or title}</h1>
            {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}
        </header>
        '''

    footer_html = ''
    if footer:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        footer_html = f'''
        <footer class="tj_page_footer">
            Generated by Rodmena Resource Management on {now}
        </footer>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="Rodmena Resource Management">
    <title>{title}</title>
    {css}
</head>
<body>
    <div class="tj_container">
        {header_html}
        {nav_html}
        <main class="tj_content">
            {content}
        </main>
        {footer_html}
    </div>
</body>
</html>'''


def format_date(date: datetime, fmt: str = '%Y-%m-%d') -> str:
    """Format a date for display."""
    if date is None:
        return ''
    return date.strftime(fmt)


def format_duration(hours: float, unit: str = 'days') -> str:
    """Format a duration for display."""
    if hours is None:
        return ''

    if unit == 'hours':
        return f'{hours:.1f}h'
    elif unit == 'days':
        days = hours / 8.0
        return f'{days:.1f}d'
    elif unit == 'weeks':
        weeks = hours / 40.0
        return f'{weeks:.1f}w'
    else:
        return f'{hours:.1f}h'


def format_percentage(value: float) -> str:
    """Format a percentage for display."""
    if value is None:
        return ''
    return f'{value:.0f}%'


def alert_indicator_html(level: str) -> str:
    """Generate HTML for an alert level indicator."""
    level_lower = level.lower() if level else 'green'
    return f'<span class="alert-indicator {level_lower}"></span>'


def journal_entry_html(entry: Any) -> str:
    """
    Generate HTML for a journal entry.

    Args:
        entry: JournalEntry object

    Returns:
        HTML string for the entry
    """
    alert_class = f'alert-{entry.alert_level.name.lower()}' if hasattr(entry, 'alert_level') else ''
    date_str = format_date(entry.date, '%Y-%m-%d %H:%M') if entry.date else ''
    author_str = f'by {entry.author.name}' if hasattr(entry, 'author') and entry.author else ''

    summary_html = ''
    if hasattr(entry, 'summary') and entry.summary:
        summary_html = f'<div class="tj_journal_summary">{entry.summary}</div>'

    return f'''
    <div class="tj_journal_entry {alert_class}">
        <div class="tj_journal_date">{date_str}</div>
        <div class="tj_journal_headline">{entry.headline}</div>
        {f'<div class="tj_journal_author">{author_str}</div>' if author_str else ''}
        {summary_html}
    </div>
    '''
