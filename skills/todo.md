# To-Do List

MolluskAI manages your to-do list using direct commands or natural language.

## Direct commands (handled instantly, no AI cost)

- `todo: pick up dry cleaning` — add an item
- `done: dry cleaning` — mark matching item(s) done
- `remove: dry cleaning` — delete matching item(s) from the list
- `recall: todo` — show all open items
- `recall: todo all` — show full history including done items

Done items are automatically removed the following morning.

## Natural language

When the user says "remind me to X", "add to do: X", or similar natural phrasing
and has NOT used the `todo:` command prefix, save the item using:

[SAVE_NOTE: todo]
[ ] X
[/SAVE_NOTE]

Confirm briefly: "Added to your to-do list."

When the user says "I finished X", "mark X as done", or similar natural phrasing
and has NOT used the `done:` command prefix, save a done entry:

[SAVE_NOTE: todo]
[x] X
[/SAVE_NOTE]

Confirm briefly: "Marked as done."

## Notes

- Items starting with `[ ]` are open; `[x]` are done.
- `recall: todo` shows only open items by default.
- The daily reminder (05:00) shows open items and cleans up done items older than 24 hours.
