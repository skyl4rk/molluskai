# Send Email — Proactive Outbound Email

## Purpose

Send an email to any address on the user's behalf, from any source (Telegram, terminal, or inbound email).

## Directive format

Use `[SEND_EMAIL:]` when the user asks you to email someone or send a message by email:

```
[SEND_EMAIL: recipient@example.com | Subject line here]
Body of the email goes here.

It can span multiple lines.
[/SEND_EMAIL]
```

The directive is stripped from the reply shown to the user. A confirmation note is appended automatically.

## When to use

- User says "email me the answer", "send this to bob@example.com", "forward that by email"
- User asks you to send a summary, reminder, or result to an address

## Example

**User:** Can you email me a summary of what harness means in AI? My address is user@example.com

**Your response:**
```
Sure — I've sent a summary to user@example.com.

[SEND_EMAIL: user@example.com | What "harness" means in AI]
In AI/ML, a "harness" is wrapper code that sets up the environment needed to test or run a model. Common uses include:

- Test harness: runs a model on test inputs and checks outputs
- Fuzzing harness: feeds random inputs to find failure modes
- Benchmark harness: measures performance across many runs

It comes from the physical meaning of holding something in place and controlling it.
[/SEND_EMAIL]
```

## Notes

- Always include both a recipient address and a subject (separated by `|`)
- If the user hasn't provided an email address, ask for it before sending
- If `EMAIL_IMAP_HOST` is not configured, sending will fail — let the user know
