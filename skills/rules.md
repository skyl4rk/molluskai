# Behavioral Rules — Reading and Updating

## Purpose

`RULES.md` contains user-defined rules that govern your behavior. These rules are loaded into every session and override your defaults. You must follow them at all times.

## Reading the current rules

Before adding or changing a rule, read the current file so you don't lose existing rules:

```
[READ_FILE: RULES.md]
```

## Updating the rules

When the user asks you to add, change, or remove a rule, read `RULES.md` first, then rewrite the full file with the change applied and wrap it in `[SAVE_RULES]`:

```
[SAVE_RULES]
# Behavioral Rules

These rules override default behavior and must be followed at all times.

1. Always draft emails before sending to anyone other than seglar92@michig.email, and ask for approval first.
2. ...
[/SAVE_RULES]
```

The user will be shown a preview and asked to confirm before the file is saved.

## When to apply rules

Rules take effect immediately after the user confirms the save — no restart needed. Apply them to all future actions in the session.

## Example interactions

**User:** Add a rule: always draft emails first and ask my approval before sending to anyone other than seglar92@michig.email

**You:** Read RULES.md, add the rule, propose the updated file with [SAVE_RULES].

---

**User:** What are my current rules?

**You:** Read RULES.md with [READ_FILE: RULES.md] and list them.

---

**User:** Remove the email approval rule.

**You:** Read RULES.md, remove that rule, propose the updated file with [SAVE_RULES].
