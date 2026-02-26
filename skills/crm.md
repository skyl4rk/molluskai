# CRM — Personal Relationship Manager

MolluskAI includes a personal CRM backed by `data/crm.db`. Import `crm` for all contact operations. Import `calendar_client` for calendar operations.

## Contact Management

| User says | Action |
|-----------|--------|
| "add contact Jane Smith jane@co.com" | `crm.add_contact(name, email)` then confirm |
| "crm add jane@co.com" | `crm.approve_proposal("jane@co.com")` |
| "crm skip jane@co.com" | `crm.reject_proposal("jane@co.com")` |
| "find contact Jane" / "who is Jane?" | `crm.search_contacts("Jane")` then summarise |
| "contacts at Acme" | `crm.search_contacts("Acme")` |
| "crm stats" | `crm.get_stats()` formatted |
| "add note about Jane: …" | `crm.add_context(contact_id, content)` |

## Follow-Ups

| User says | Action |
|-----------|--------|
| "remind me to follow up with Jane in 2 weeks" | `crm.add_follow_up(contact_id, due_date)` |
| "what follow-ups are due?" | `crm.get_pending_follow_ups(days_ahead=7)` |

## Calendar Events

To add a local khal calendar event, output exactly this block — the agent will show a preview and ask for confirmation:

```
[ADD_CALENDAR_EVENT:]
title: <event title>
date: YYYY-MM-DD
time: HH:MM
duration_minutes: 60
description: <optional>
location: <optional>
[/ADD_CALENDAR_EVENT]
```

For calendar queries:
- "what's on my calendar this week?" → `calendar_client.get_upcoming_events(days=7)`
- "am I free Tuesday?" → `calendar_client.get_events(start, end)` and check for conflicts

## Email Drafting

When asked to draft an email to a contact:
1. Check `config.CRM_EMAIL_DRAFT_ENABLED` — if False, tell the user to set it to true in .env
2. If enabled: `import crm_email_draft; crm_email_draft.generate(contact_name, topic, reply_fn)`

## Relationship Intelligence

When asked "who should I reach out to?" or "any neglected contacts?":

```python
import crm
conn = crm._connect()
rows = conn.execute(
    "SELECT name, email, last_contact_date, relationship_score FROM contacts "
    "WHERE relationship_score < 20 ORDER BY relationship_score ASC LIMIT 5"
).fetchall()
conn.close()
```

Present names with last-contact dates and suggest reaching out.

When asked about a specific person's history: use `crm.get_contact_context(contact_id, query)` for rich context plus `crm.get_contact()` for the profile.
