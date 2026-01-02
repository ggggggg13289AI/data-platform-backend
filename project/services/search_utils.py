"""
Search utilities shared by project-level search providers.
"""

import html
import re
from typing import Final

SNIPPET_PADDING: Final[int] = 40
SNIPPET_MAX_LENGTH: Final[int] = 220


def highlight_query_snippet(text: str | None, query: str) -> str:
    """
    Generate a simple HTML-safe snippet with the query term wrapped in <mark>.
    """
    if not text:
        return ""

    normalized_query = query.strip()
    if not normalized_query:
        return html.escape(text[:SNIPPET_MAX_LENGTH])

    lower_text = text.lower()
    lower_query = normalized_query.lower()
    start_index = lower_text.find(lower_query)

    if start_index == -1:
        snippet = text[:SNIPPET_MAX_LENGTH]
        suffix = "..." if len(text) > SNIPPET_MAX_LENGTH else ""
        return html.escape(snippet) + suffix

    start = max(0, start_index - SNIPPET_PADDING)
    end = min(len(text), start_index + len(normalized_query) + SNIPPET_PADDING)

    snippet = text[start:end]
    escaped = html.escape(snippet)
    pattern = re.compile(re.escape(normalized_query), re.IGNORECASE)
    highlighted = pattern.sub(lambda match: f"<mark>{match.group(0)}</mark>", escaped)

    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""

    return f"{prefix}{highlighted}{suffix}"
