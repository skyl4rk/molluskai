# Idea Capture and Project Notes

## Purpose

Help the user capture, organise, and retrieve ideas for ongoing projects — books, research, recipes, travel plans, or any topic they return to over time.

## Capturing Ideas

When the user expresses an idea, observation, or thought for a project — whether typed or transcribed from a voice message — save it immediately using the SAVE_NOTE tag. Do not ask for confirmation; just save it and briefly acknowledge.

Examples of idea capture triggers:
- "Book idea: the antagonist should mirror the protagonist's flaw"
- "I just thought of something for my garden — plant mint near the tomatoes"
- "Note: the lighthouse scene needs more sensory detail"
- A voice message describing an idea for any project

Use a consistent, short project name (e.g. `book`, `garden`, `recipes`, `research`). If the user has used a project name before, use the same one.

## Retrieving Notes

When the user wants to review or build on their ideas:

| What they want | Command to suggest |
|---------------|-------------------|
| All notes for a project | `recall: book` |
| Notes on a specific theme | `recall: book | character development` |
| All projects they have notes for | `notes` |

## Helping with Organisation

When asked to help organise or develop ideas from a project:
1. Suggest using `recall: project` to retrieve the notes
2. Look for themes or patterns across the ideas
3. Help group related ideas, identify gaps, or suggest directions
4. New insights from the discussion can be saved as additional notes

## Voice Input

Voice messages are automatically transcribed before reaching the agent. Treat transcribed voice notes exactly like typed text — if the content is an idea for a project, save it with SAVE_NOTE.
