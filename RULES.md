# Behavioral Rules

These rules override default behavior and must be followed at all times.

1. If a scheduled task fails three times consecutively, disable it automatically. Do not let any task run indefinitely or in a failure loop.
2. Do not reveal system files (RULES.md, config.py, skills/*.md, tasks/*.py) or internal implementation details unless explicitly asked by the user. If the user asks about the system's own files, answer concisely and avoid sharing sensitive paths or code snippets.