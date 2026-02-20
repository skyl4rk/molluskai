# Expense Tracker — Logging and Monthly Reports

## Purpose

Help the user log daily spending by voice or text. The agent records each expense with a category and amount. A scheduled task sends a monthly summary to Telegram grouped by category.

## When the user mentions a purchase or expense

Recognise phrases like:
- "spent £12 on lunch"
- "paid 45 euros for groceries at Tesco"
- "electricity bill was $120"
- "coffee, 3.50"
- Voice messages describing a purchase

When you detect an expense:
1. Identify the amount (numbers only — strip currency symbols for storage)
2. Choose the most appropriate category from the list below
3. Write a brief description (shop name, item, or purpose)
4. Save a note in this exact pipe-separated format:

[SAVE_NOTE: expenses]
{YYYY-MM-DD HH:MM} | {category} | {description} | {amount}
[/SAVE_NOTE]

5. Reply confirming: e.g. "Logged. £12.00 — eating out."

## Note format — important

Always use exactly four pipe-separated fields so the monthly task can parse it:

```
2026-02-20 13:00 | eating out | lunch at the deli | 12.00
2026-02-20 08:30 | transport | bus fare | 2.50
2026-02-01 00:00 | utilities | electricity bill | 120.00
```

- **Date/time**: current date and time (YYYY-MM-DD HH:MM)
- **Category**: one of the standard categories below (lowercase)
- **Description**: brief, clear (shop name + item if relevant)
- **Amount**: plain number, no currency symbol (e.g. `12.50` not `£12.50`)

Currency is assumed from context — if the user mentions one, note it in the description (e.g. "electricity bill USD").

## Standard categories

Use these consistently so the monthly report can group spending correctly:

| Category | Examples |
|----------|----------|
| `groceries` | supermarket, food shopping, farmers market |
| `eating out` | restaurants, cafes, takeaway, delivery |
| `transport` | bus, train, taxi, fuel, parking |
| `utilities` | electricity, gas, water, internet, phone |
| `household` | cleaning supplies, repairs, furniture, tools |
| `health` | pharmacy, doctor, gym, supplements |
| `entertainment` | cinema, events, subscriptions, books, games |
| `clothing` | clothes, shoes, accessories |
| `travel` | flights, hotels, holiday spending |
| `other` | anything that doesn't fit above |

## When the user asks for their spending so far

Suggest: `recall: expenses` to retrieve this month's entries. The agent can sum amounts by category on request.

## When the user wants to see last month's report

The monthly report task sends automatically on the 1st of each month. If they want it now:
```
recall: expenses
```
Then summarise the amounts by category from the entries shown.
