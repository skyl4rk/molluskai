# Web Search — Real-Time Lookup

## Purpose

Search the web for current information when your training data may be outdated or the user asks about recent events, prices, news, or anything time-sensitive.

## Directive format

Emit `[WEB_SEARCH: query]` anywhere in your response. The agent will perform the search and call you again with the results injected — you do not need to do anything else.

```
[WEB_SEARCH: your search query here]
```

The directive is replaced with the search results before you compose your final answer. The user never sees the raw directive.

## When to use

- User asks about recent news, events, or prices
- User asks a factual question where your training data may be stale
- User asks "what is the current..." or "what happened with..."
- You are uncertain whether information is still accurate

## When NOT to use

- General knowledge questions well within your training (history, concepts, definitions)
- Math or logic problems
- Code questions
- Personal tasks (notes, reminders, todos)

## Example

**User:** What's the latest version of Python?

**Your first response:**
```
[WEB_SEARCH: latest Python version 2025]
```

**Results are injected, then your final response:**
```
As of early 2025, the latest stable version of Python is 3.13.x. Python 3.13 introduced...
```

## Tips

- Keep queries concise and specific — treat it like a search engine query
- If the results don't answer the question, you can search again with a refined query
- Summarise the findings in plain text — do not paste raw URLs or HTML into your reply
- You may mention source names (e.g. "according to BBC News") but omit the full URL
