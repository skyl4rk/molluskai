# AI Usage and Cost Report

When the user asks for a usage report, cost summary, token count, or API spending:

1. Read the file `data/usage.log`. Each line has the format:
   `YYYY-MM-DD HH:MM:SS | model=<model> | prompt=<n> completion=<n> total=<n>`

2. Summarise in 3–5 bullet points:
   - Total API calls to date
   - Total tokens used (prompt + completion separately)
   - Rough cost estimate — most models cost $0.10–$1.00 per million tokens; use $0.50/M as a default estimate if unknown
   - Most recent call (date, model, tokens)

3. If `data/usage.log` does not exist yet, say so and note that usage is logged after the first AI call.

Keep the report concise. No tables, no headers — just bullets.
