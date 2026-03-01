# To-Do List

MolluskAI manages your to-do list using the notes system (project: "todo").

## Adding items

When the user says "add to do: X", "remind me to X", "todo: X", or similar:

Save the item as an open task:

[SAVE_NOTE: todo]
[ ] X
[/SAVE_NOTE]

Confirm briefly: "Added to your to-do list."

## Marking items done

When the user says "done: X", "mark X as done", "finished X", or similar:

[SAVE_NOTE: todo]
[x] X
[/SAVE_NOTE]

Confirm briefly: "Marked as done."

## Listing open items

When the user asks "what's on my to-do list?", "show my todos", or "any todos?":

Tell the user: "Use `recall: todo` to see your list."

Or call `memory.get_notes("todo")` and display only lines starting with `[ ]`.

## Notes

- Items starting with `[ ]` are open; `[x]` are done.
- The daily reminder task shows only open `[ ]` items.
- Users can say `recall: todo` at any time to see the full list.
