# AI IT Help Desk Bot

An offline Tier 1 IT support chatbot powered by a local LLM (GLM-4.7-Flash via Ollama).
It answers **only** from a knowledge base, escalates unresolved issues as tickets,
and includes a technician panel for ticket management.

No cloud APIs, no subscriptions — all data stays on the local machine.

## Demo

**Small talk, then a real issue solved from the knowledge base**

![Chat and KB answer](screenshots/chat-and-kb-answer.png)

**Steps didn't help → escalation with user details (new user confirmed)**

![Escalation](screenshots/escalation-new-user.png)

**Server outage → no article fits → Critical ticket created immediately**

![Critical ticket](screenshots/critical-ticket.png)

**Tickets saved with category and priority**

![tickets.csv](screenshots/tickets-csv.png)

## Features

- **Knowledge-base answers only** — troubleshooting steps come from `kb/*.md` articles, not the model's guesses
- **Code-level routing + verification** — one LLM call picks an article, a second checks it really fits; if not, a ticket is created
- **Ticket lifecycle** — steps → "Did this solve your problem?" → resolve or escalate
- **AI ticket classification** — category (Hardware / Software / Network / Account / Security / Other) and priority (Critical / High / Medium / Low)
- **User details** — name and department (reused only after confirmation) and the device for each ticket
- **Personality** — off-topic messages get a short, witty reply from "Byte" and a nudge back to IT, without creating tickets
- **Technician panel** (`admin.py`) — view tickets by urgency, filter, close, and see statistics
- **Safety rules** — never asks for passwords; off-topic messages get a polite redirect, not a ticket

## How it works

```
User message
    │
    ▼
Router (LLM) ── off-topic ──► friendly reply
    │
    ├── no article ──────────────────────────┐
    ▼                                        │
Verifier (LLM) ── article doesn't fit ───────┤
    │                                        ▼
    ▼                              Collect user info
Steps from KB article                        │
    │                                        ▼
    ▼                         Classify (category + priority)
"Did this solve it?" ── no ──►               │
    │                                        ▼
   yes → resolved                     tickets.csv
```

## Project structure

```
helpdesk-bot/
├── hdbot.py      # user-facing chatbot
├── admin.py      # technician panel
├── kb/           # knowledge base articles (Markdown)
├── screenshots/  # demo images for this README
└── tickets.csv   # created automatically (not uploaded)
```

## How to run

1. Install [Ollama](https://ollama.com/download) and pull the model:
   ```
   ollama pull glm-4.7-flash
   ```
2. Install the Python library:
   ```
   pip install ollama
   ```
3. Start the bot:
   ```
   python hdbot.py
   ```
4. Open the technician panel:
   ```
   python admin.py
   ```

## Limitations & lessons learned

- **Prompt rules weren't enough.** The model ignored "answer only from the knowledge base"
  and invented plausible-sounding steps for issues with no article (hallucination).
  Fixed by moving the decision into code: the model can only answer after an article is selected and verified.
- **The model triggered tickets on its own.** When an article said "escalate with a ticket,"
  the model added the ticket tag immediately. Fixed by removing ticket decisions from the model entirely.
- **Small models are inconsistent.** The same input sometimes produced `offtopic`, `off-topic`, or `OFFTOPIC.`;
  output parsing was made tolerant. Temperature is set to 0 for troubleshooting.
- **The verifier needed tuning.** A strict "exact match" question rejected valid cases;
  few-shot examples made it accept single-user issues and reject office-wide outages.
- Runs on 32 GB RAM, CPU-only; each reply takes several seconds because of multiple model calls.

## Built with

Python · Ollama · GLM-4.7-Flash · CSV
