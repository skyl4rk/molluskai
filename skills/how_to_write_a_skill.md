# How to Write a Skill

A skill is a markdown file in the `skills/` directory. All skill files are loaded at startup and included in the system prompt, so every instruction here applies to every conversation.

Skills should:
- Be concise (under 150 words each)
- Describe one specific behaviour or response pattern
- Be written in plain, direct language
- Have a clear `# Title` as the first line

To write a new skill, create a `.md` file in `skills/` with a descriptive name. You can do this yourself in a text editor, or ask me to write one for you.

When I write or edit a skill file, I will confirm the filename and full content before saving.

Skills are loaded automatically when the agent starts — no code changes required. To remove a skill, delete or rename its file.
