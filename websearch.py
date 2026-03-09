# websearch.py — Shared web search utility using DuckDuckGo (no API key required)
#
# Usage from a task:
#   from websearch import search
#   results = search("python programming", max_results=10)
#   # Each result: {"title": str, "url": str, "snippet": str}

from __future__ import annotations


def search(query: str, max_results: int = 10) -> list[dict]:
    """Return up to max_results web search results for query.

    Each result dict has keys: title, url, snippet.
    Returns an empty list on error.
    """
    try:
        from ddgs import DDGS
        raw = DDGS().text(query, max_results=max_results)
        return [
            {
                "title":   r.get("title", ""),
                "url":     r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in (raw or [])
        ]
    except Exception as e:
        print(f"[websearch] Search error: {e}")
        return []


def format_results(results: list[dict]) -> str:
    """Format a list of search results into a human-readable string."""
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['url']}")
        if r["snippet"]:
            lines.append(f"   {r['snippet'][:200]}")
        lines.append("")
    return "\n".join(lines).strip()
