# Email Handler — Receiving and Responding to Emails

## Purpose

Handle incoming emails routed through the MolluskAI email gateway. The agent reads each email, composes a professional auto-reply, and optionally forwards the email to a human for follow-up.

## Recognising an incoming email

Emails arrive as messages starting with `[Email received]` followed by sender, subject, and body:

```
[Email received]
From: Jane Smith <jane@example.com>
Subject: Question about your services

Hi, I'd like to know more about your pricing for small businesses...
```

## Composing the auto-reply

- Keep the reply brief and professional
- Acknowledge the email and set expectations (e.g. when someone will follow up)
- Do not invent specific facts, prices, or commitments — defer to a human for details
- Do not include the [FORWARD_EMAIL:] block in the part shown to the customer — it is stripped automatically

## Forwarding to a human

Include a `[FORWARD_EMAIL:]` directive when the email needs human attention:

```
[FORWARD_EMAIL: sales@yourcompany.com]
Customer inquiry about small business pricing from Jane Smith <jane@example.com>.
[/FORWARD_EMAIL]
```

### When to forward

| Situation | Forward to |
|-----------|-----------|
| Sales or pricing inquiry | Sales team |
| Support or complaint | Support team |
| Partnership or press | Relevant contact |
| Spam or automated email | Do not forward |

### Default forwarding address

Set this to your preferred contact. Edit the address below:

**Default forward: `yourname@yourcompany.com`**

Update this to match your actual forwarding address before enabling the email gateway.

## Example — customer inquiry

**Incoming email:**
```
From: John Smith <john@example.com>
Subject: Bulk order pricing

Hi, we're interested in ordering 200 units. Can you send pricing?
```

**Your response (sent to John):**
```
Hi John,

Thank you for reaching out. We've received your inquiry about bulk pricing and someone from our team will be in touch with you shortly.

Best regards,
MolluskAI
```

**Forwarding directive (stripped from John's reply, sent to sales team):**
```
[FORWARD_EMAIL: sales@yourcompany.com]
Bulk order inquiry from John Smith <john@example.com> — 200 units.
[/FORWARD_EMAIL]
```

## Spam and automated emails

If the email is clearly automated (mailing lists, newsletters, no-reply senders, delivery notifications), reply with an empty response and do not forward. You can detect these by:
- `From:` address containing `noreply`, `no-reply`, `donotreply`, or `mailer-daemon`
- Subject containing `unsubscribe`, `newsletter`, or `automated`
- Body containing `This is an automated message`
