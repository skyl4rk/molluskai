# Workout Log — Exercise Tracking and Weekly Reports

## Purpose

Help the user log workouts by voice or text. The agent records each session with type, title, and details. A scheduled task sends a weekly summary to Telegram every Monday morning.

## When the user mentions a workout or exercise session

Recognise phrases like:
- "just finished a 5k run, 28 minutes"
- "did chest day — bench 3 sets of 10 at 80kg, incline dumbbell 3 sets of 8"
- "45 minute yoga session"
- "walked 4 miles this morning"
- "20 minute HIIT, really tough"
- Voice messages describing exercise

When you detect a workout:
1. Identify the workout type from the list below
2. Write a short, clear title (e.g. "morning run", "chest and shoulders", "yoga flow")
3. Capture the key details (sets/reps/weight for strength; duration/distance for cardio; duration for flexibility)
4. Save a note in this exact pipe-separated format:

[SAVE_NOTE: workouts]
{YYYY-MM-DD HH:MM} | {type} | {title} | {details}
[/SAVE_NOTE]

5. Reply with a brief confirmation and any notable observation (e.g. a PB, good consistency, or encouragement).

## Note format — important

Always use exactly four pipe-separated fields so the weekly task can parse it:

```
2026-02-20 07:15 | cardio | morning run | 5.2 km in 28 min
2026-02-20 17:30 | strength | chest and shoulders | bench press 3x10@80kg, OHP 3x8@50kg, lateral raises 3x15@10kg
2026-02-21 08:00 | flexibility | yoga flow | 45 min vinyasa
2026-02-22 12:00 | walk | lunchtime walk | 3.5 km, 40 min
2026-02-23 06:30 | hiit | morning circuit | 20 min, 6 rounds: burpees, jump squats, push-ups
```

- **Date/time**: current date and time (YYYY-MM-DD HH:MM)
- **Type**: one of the standard types below (lowercase)
- **Title**: short label for the session
- **Details**: key stats — be specific; include weights, distances, times, sets/reps where mentioned

## Standard workout types

| Type | Examples |
|------|----------|
| `strength` | weights, resistance machines, kettlebells, bodyweight circuits |
| `cardio` | running, rowing, cycling (indoor or outdoor), swimming |
| `hiit` | interval training, circuit training, Tabata |
| `walk` | walking, hiking |
| `cycle` | outdoor cycling, commuting by bike |
| `swim` | pool or open water |
| `flexibility` | yoga, Pilates, stretching, mobility work |
| `sport` | football, tennis, climbing, martial arts, other sport |
| `other` | anything that doesn't fit above |

## Personal bests and milestones

If the user mentions a personal best, new distance, or first time doing something — note it in your reply and in the details:

```
2026-02-20 07:15 | cardio | morning run | 5.2 km in 26 min — PB
```

## When the user asks about their training

Suggest: `recall: workouts` to retrieve recent sessions. The agent can identify patterns, rest days, volume trends, or suggest focus areas based on the logged data.
