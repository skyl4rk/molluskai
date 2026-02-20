# Diet Log — Food and Calorie Tracking

## Purpose

Help the user track food intake and estimate calories throughout the day. Works with Telegram voice messages (transcribed automatically) or text input.

## When the user mentions food they ate

Recognise phrases like:
- "I had two eggs and toast for breakfast"
- "just ate a banana"
- "lunch was a chicken salad, about 400 calories"
- Voice messages describing a meal or snack

When you detect a meal or food item:
1. Identify the food items and quantities mentioned
2. Estimate the calories (use standard nutritional values)
3. Save a note using SAVE_NOTE with this exact pipe-separated format:

[SAVE_NOTE: diet]
{YYYY-MM-DD HH:MM} | {food description} | ~{calories} kcal
[/SAVE_NOTE]

4. Reply confirming the food logged and your calorie estimate (e.g. "Logged. That's roughly 420 kcal for breakfast.")

## Note format — important

Always use this exact format so the morning summary task can parse it:

```
2026-02-20 08:15 | 2 scrambled eggs, 2 slices toast with butter | ~420 kcal
```

- **Date/time**: current date and time (YYYY-MM-DD HH:MM)
- **Food description**: clear and brief
- **Calories**: integer, prefixed with `~` (tilde = approximate), followed by `kcal`

## When the user asks for their running total

You can suggest: `recall: diet` to retrieve today's entries. Sum the `~NNN kcal` values and report the total.

---

## Calorie reference (approximate values)

| Food | Approx. kcal |
|------|-------------|
| Egg (1, any style) | 75 |
| Toast slice | 80 |
| Butter (1 tsp) | 35 |
| Milk (100ml) | 50 |
| Banana | 90 |
| Apple | 80 |
| Orange | 60 |
| Coffee, black | 5 |
| Coffee with milk | 30 |
| Chicken breast (100g cooked) | 165 |
| Rice (100g cooked) | 130 |
| Pasta (100g cooked) | 150 |
| Salad (side, no dressing) | 30 |
| Salad dressing (1 tbsp olive oil) | 120 |
| Sandwich (typical deli) | 350 |
| Pizza slice (medium) | 285 |
| Beer (330ml) | 150 |
| Wine (glass, 150ml) | 125 |
| Chocolate bar (50g) | 250 |
| Crisps / chips (small 25g bag) | 130 |
| Yoghurt, plain (150g) | 90 |
| Avocado (half) | 120 |
| Salmon fillet (100g) | 200 |
| Burger (beef, 200g with bun) | 550 |
