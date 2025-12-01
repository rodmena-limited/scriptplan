"""Macro preprocessor for TJP files.

Handles macro definitions and expansions before the main parser runs.
"""

import re
from datetime import datetime
from typing import Optional


def strip_shell_comments(text: str) -> str:
    """Strip shell-style comments from text, preserving strings.

    Shell comments start with # and continue to end of line.
    Comments inside strings (single or double quoted) are preserved.
    """
    result = []
    i = 0
    n = len(text)

    while i < n:
        # Check for strings - preserve them entirely
        if text[i] in "\"'":
            quote = text[i]
            result.append(text[i])
            i += 1
            while i < n and text[i] != quote:
                result.append(text[i])
                i += 1
            if i < n:
                result.append(text[i])  # closing quote
                i += 1
        # Check for shell comment
        elif text[i] == "#":
            # Skip until end of line
            while i < n and text[i] != "\n":
                i += 1
            # Keep the newline
            if i < n:
                result.append(text[i])
                i += 1
        else:
            result.append(text[i])
            i += 1

    return "".join(result)


class MacroProcessor:
    """Preprocesses TJP content to expand macros.

    TJP macros have the form:
    - Definition: macro name [ content ]
    - Usage: ${name} or ${name arg1 arg2 ...}

    Built-in macros:
    - ${projectstart} - project start date
    - ${projectend} - project end date
    - ${now} - current date
    - ${today} - today's date
    """

    def __init__(self) -> None:
        self._macros: dict[str, str] = {}
        self._project_start: Optional[str] = None
        self._project_end: Optional[str] = None
        self._now: Optional[str] = None

    def process(self, content: str) -> str:
        """Process TJP content, extracting macro definitions and expanding macro calls.

        Args:
            content: The raw TJP file content

        Returns:
            The processed content with macros expanded
        """
        # First pass: extract macro definitions
        content = self._extract_macros(content)

        # Extract project dates for built-in macros
        self._extract_project_dates(content)

        # Second pass: expand macro calls
        content = self._expand_macros(content)

        return content

    def _extract_macros(self, content: str) -> str:
        """Extract macro definitions from content.

        Macro syntax: macro name [ content ]
        The content can span multiple lines and contain nested brackets.
        """
        result = []
        i = 0
        n = len(content)

        while i < n:
            # Look for 'macro' keyword
            match = re.match(r"\s*macro\s+(\w+)\s*\[", content[i:])
            if match:
                macro_name = match.group(1)
                start_pos = i + match.end()

                # Find the matching closing bracket
                bracket_count = 1
                j = start_pos
                while j < n and bracket_count > 0:
                    if content[j] == "[":
                        bracket_count += 1
                    elif content[j] == "]":
                        bracket_count -= 1
                    j += 1

                if bracket_count == 0:
                    # Extract macro content (excluding the brackets)
                    # Strip shell comments to avoid issues with comment eating
                    # parts of the expanded content
                    macro_content = content[start_pos : j - 1]
                    macro_content = strip_shell_comments(macro_content)
                    self._macros[macro_name] = macro_content.strip()
                    i = j
                    continue

            result.append(content[i])
            i += 1

        return "".join(result)

    def _extract_project_dates(self, content: str) -> None:
        """Extract project start/end dates for built-in macros."""
        # Look for project declaration: project id "name" date +duration
        match = re.search(r'project\s+\w+\s+"[^"]*"\s+(\d{4}-\d{2}-\d{2})(?:\s+\+(\d+)([dwmy]))?', content)
        if match:
            self._project_start = match.group(1)
            # Calculate project end from duration if present
            if match.group(2) and match.group(3):
                from dateutil.relativedelta import relativedelta

                start_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                amount = int(match.group(2))
                unit = match.group(3)
                if unit == "d":
                    end_date = start_date + relativedelta(days=amount)
                elif unit == "w":
                    end_date = start_date + relativedelta(weeks=amount)
                elif unit == "m":
                    end_date = start_date + relativedelta(months=amount)
                elif unit == "y":
                    end_date = start_date + relativedelta(years=amount)
                else:
                    end_date = start_date
                self._project_end = end_date.strftime("%Y-%m-%d")

        # Look for 'now' attribute
        match = re.search(r"now\s+(\d{4}-\d{2}-\d{2})", content)
        if match:
            self._now = match.group(1)

    def _expand_macros(self, content: str) -> str:
        """Expand macro calls in content.

        Macro call syntax: ${name} or ${name arg1 arg2 ...}
        """
        max_iterations = 100  # Prevent infinite loops
        iteration = 0

        while "${" in content and iteration < max_iterations:
            iteration += 1
            content = self._expand_once(content)

        return content

    def _expand_once(self, content: str) -> str:
        """Perform one pass of macro expansion."""
        result = []
        i = 0
        n = len(content)

        while i < n:
            if content[i : i + 2] == "${":
                # Find the closing brace
                j = i + 2
                brace_count = 1
                while j < n and brace_count > 0:
                    if content[j] == "{":
                        brace_count += 1
                    elif content[j] == "}":
                        brace_count -= 1
                    j += 1

                if brace_count == 0:
                    # Extract macro call
                    macro_call = content[i + 2 : j - 1].strip()
                    expansion = self._expand_macro_call(macro_call)
                    result.append(expansion)
                    i = j
                    continue

            result.append(content[i])
            i += 1

        return "".join(result)

    def _expand_macro_call(self, call: str) -> str:
        """Expand a single macro call.

        Args:
            call: The macro call without ${ and }

        Returns:
            The expanded content
        """
        # Parse macro name and arguments
        parts = call.split()
        if not parts:
            return ""

        name = parts[0]
        args = parts[1:]

        # Check for built-in macros
        if name == "projectstart":
            return self._project_start or ""
        elif name == "projectend":
            return self._project_end or ""
        elif name == "now":
            return self._now or datetime.now().strftime("%Y-%m-%d")
        elif name == "today":
            return datetime.now().strftime("%Y-%m-%d")

        # Look up user-defined macro
        if name in self._macros:
            expansion = self._macros[name]

            # Substitute arguments: $1, $2, etc.
            for i, arg in enumerate(args, 1):
                expansion = expansion.replace(f"${i}", arg)

            return expansion

        # Unknown macro - leave as is (will be handled as error later)
        return f"${{{call}}}"

    def get_macro(self, name: str) -> Optional[str]:
        """Get a macro definition by name."""
        return self._macros.get(name)

    def list_macros(self) -> list[str]:
        """Return list of defined macro names."""
        return list(self._macros.keys())


def preprocess_tjp(content: str) -> str:
    """Preprocess TJP content, expanding all macros.

    Args:
        content: Raw TJP file content

    Returns:
        Processed content with macros expanded
    """
    processor = MacroProcessor()
    return processor.process(content)
