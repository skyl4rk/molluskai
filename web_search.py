# web_search.py — DuckDuckGo search utility
#
# Uses the DDG instant answer API for a summary, then scrapes
# lite.duckduckgo.com for up to max_results web results.
# No API key required.

import json
import re
import urllib.parse
import urllib.request


def search(query: str, max_results: int = 5) -> str:
    """
    Search DuckDuckGo and return a formatted string of results.
    Returns an error string if both sources fail.
    """
    encoded = urllib.parse.quote_plus(query)
    parts   = []

    # --- Instant answer (abstract/definition) ---
    try:
        req = urllib.request.Request(
            f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1",
            headers={"User-Agent": "MolluskAI/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        if data.get("AbstractText"):
            parts.append(f"[Instant Answer]\n{data['AbstractText']}")
            if data.get("AbstractURL"):
                parts.append(f"Source: {data['AbstractURL']}")
    except Exception:
        pass

    # --- Web results from DDG Lite (requires POST) ---
    try:
        post_data = urllib.parse.urlencode({"q": query}).encode()
        req = urllib.request.Request(
            "https://lite.duckduckgo.com/lite/",
            data=post_data,
            headers={"User-Agent": "MolluskAI/1.0",
                     "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")

        # Extract result titles+URLs and snippets from the lite HTML table
        titles   = re.findall(r"<a[^>]+class='result-link'[^>]*>(.*?)</a>", html, re.DOTALL)
        urls     = re.findall(r'href="([^"]+)"[^>]+class=\'result-link\'', html)
        snippets = re.findall(r"class='result-snippet'>(.*?)</td>", html, re.DOTALL)

        # Clean HTML tags and decode entities
        def _clean(s):
            s = re.sub(r'<[^>]+>', '', s)
            import html
            return html.unescape(s).strip()

        results = []
        for i, (title, snippet) in enumerate(zip(titles, snippets)):
            if i >= max_results:
                break
            url  = urls[i] if i < len(urls) else ""
            line = f"{i+1}. {_clean(title)}\n   {_clean(snippet)}"
            if url:
                line += f"\n   {url}"
            results.append(line)

        if results:
            parts.append("[Web Results]\n" + "\n\n".join(results))

    except Exception:
        pass

    if not parts:
        return f"Web search ran successfully but returned no results for: {query}. Try rephrasing the query."

    return "\n\n".join(parts)
