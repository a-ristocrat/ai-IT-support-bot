import ollama
import csv
import datetime
import json
from pathlib import Path


MODEL = "glm-4.7-flash"
DEBUG = False
BASE_DIR = Path(__file__).parent
KB_DIR = BASE_DIR / "kb"
TICKETS_FILE = BASE_DIR / "tickets.csv"


def debug(*args):
    if DEBUG:
        print("DEBUG", *args)


def load_kb():
    text = ""
    for file in KB_DIR.glob("*.md"):
        text += f"\n### ARTICLE: {file.stem}\n"
        text += file.read_text(encoding="utf-8")
    return text


def find_article(problem):
    titles = []
    article_list = ""
    for file in KB_DIR.glob("*.md"):
        content = file.read_text(encoding="utf-8").strip()
        if not content:
            print(f"WARNING: {file.name} is empty, skipping it")
            continue
        name = file.stem.lower()
        first_line = content.splitlines()[0]
        titles.append(name)
        article_list += f"- {name}: {first_line}\n"

    question = f"""You route IT help desk requests to knowledge base articles.

Articles:
{article_list}
Examples:
Problem: "cant print anything" -> printer
Problem: "my keyboard is broken" -> NONE
Problem: "write me a poem" -> OFFTOPIC

Problem: "{problem}"
Reply with ONLY the article name from the list, NONE if it's an IT problem
with no matching article, or OFFTOPIC if it's not an IT question at all."""


    answer = ollama.chat(model=MODEL,
                         messages=[{"role": "user", "content": question}],
                         options={"temperature": 0},
                         think=False)
    choice = answer["message"]["content"].strip().lower().strip(".`'\" ")

    debug("router answer:", choice)

    def normalize(text):
        return text.replace("-", "").replace("_", "").replace(" ", "")

    clean = normalize(choice)
    if "offtopic" in clean:
        return "offtopic"
    for title in titles:
        if clean == normalize(title) or clean.startswith(normalize(title)):
            return title
    return None


def article_matches(problem, article):
    text = (KB_DIR / f"{article}.md").read_text(encoding="utf-8")
    question = f"""Article:
{text}

User problem: "{problem}"

Is this article about the same kind of problem, so that its steps are a
reasonable first thing for this ONE user to try?
Answer NO only if the article is about a different topic, or if the problem
affects many users or the whole office (then a technician is needed).

Examples:
- Printer article, "cant print anything" -> YES
- Wi-Fi article, "wifi keeps dropping" -> YES
- Wi-Fi article, "the whole office has no internet" -> NO
- Printer article, "no internet" -> NO

Reply only YES or NO."""

    answer = ollama.chat(model=MODEL,
                         messages=[{"role": "user", "content": question}],
                         options={"temperature": 0}, think=False)
    verdict = answer["message"]["content"].strip().upper()
    debug("verifier answer:", verdict)
    return verdict.startswith("YES")


def classify_ticket(problem):
    question = f"""Classify this IT support ticket.

Categories: Hardware, Software, Network, Account, Security, Other
(Security = hacking, data breach, malware, phishing, stolen passwords)
Priorities:
- Critical: many users or the whole office is affected, or a critical security issue
- High: a single user is affected and cannot work, or a security issue that affects a single user
- Medium: one user can work but is slowed down, or work with problems
- Low: minor annoyance, cosmetic issue, or a question

Problem: "{problem}"

Reply ONLY with JSON like: {{"category": "Network", "priority": "High"}}"""

    answer = ollama.chat(model=MODEL,
                         messages=[{"role": "user", "content": question}],
                         options={"temperature": 0},
                         think=False, format="json")
    try:
        data = json.loads(answer["message"]["content"])
        return data.get("category", "Other"), data.get("priority", "Medium")
    except json.JSONDecodeError:
        return "Other", "Medium"


user_info = {}


def ask_user_info():
    """Name and department are reused only if the user confirms; device is asked per ticket."""
    if user_info:
        same = input(f"Bot: Is this ticket for {user_info['name']} ({user_info['department']})? (yes/no): ")
        if not same.strip().lower().startswith("y"):
            user_info.clear()

    if not user_info:
        print("Bot: Before I create a ticket, I need a few details.")
        user_info["name"] = ask_required("Bot: Your full name: ")
        user_info["department"] = ask_required("Bot: Your department: ")

    # device is not reused, because it may change per ticket
    user_info["device"] = ask_required("Bot: Device name or type (e.g. Dell laptop, PC-0142, or 'none'): ")
    return user_info


def ask_required(prompt):
    """Keep asking until the user types something."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Bot: This field is required.")


def create_ticket(problem):
    info = ask_user_info()
    category, priority = classify_ticket(problem)
    ticket_id = "HD-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_exists = TICKETS_FILE.exists()

    with open(TICKETS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["ticket_id", "date", "name", "department", "device",
                             "problem", "category", "priority", "status"])
        writer.writerow([ticket_id,
                         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         info["name"], info["department"], info["device"],
                         problem, category, priority, "open"])

    print(f">>> Category: {category} | Priority: {priority}")
    return ticket_id


SYSTEM_PROMPT = """You are a friendly Tier 1 IT Help Desk assistant.
- Give short, numbered troubleshooting steps.
- Ask one clarifying question if the problem is unclear.
- Never ask for the user's password.
- Only help with IT support topics. Politely refuse anything else.
- Never use your own knowledge. Only use the articles below.
- Do not create tickets or talk about escalation. The system asks the user
  afterwards whether the steps worked.
- Mention which article you used.
KNOWLEDGE BASE:
"""

SMALL_TALK_PROMPT = """You are Byte, the IT help desk bot. You have a dry, witty
sense of humor, like a sysadmin who has seen too many "have you tried turning it off
and on again" tickets.

Rules for off-topic messages:
- React to what the user ACTUALLY said, with one specific, clever joke about it.
  Connect it to IT if you can (servers, Wi-Fi, passwords, updates, printers).
- Be playful, never rude, never sarcastic toward the user.
- Don't help with the off-topic request itself, and never give technical steps.
- 2 sentences max. End by inviting them to bring you a real IT problem,
  phrased differently each time. Never use the phrase "How can I help you today".

Examples:
User: "how are you?"
Byte: "Running at 99.9% uptime, the other 0.1% was a Windows update. Got anything broken for me?"

User: "help me sell boots for cats"
Byte: "Cat boots are a bold market, but my skills end where the Wi-Fi does. If your online store crashes, though, I'm your bot."

User: "tell me a joke"
Byte: "There are 10 kinds of people: those who understand binary and those who don't. Now, anything on your computer acting up?"
"""


history = [{"role": "system", "content": SYSTEM_PROMPT + load_kb()}]
current_article = None

print("=== IT Help Desk Bot ===")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()

    if user_input.lower() == "exit":
        break
    if not user_input:
        continue

    # find a matching article (only for a new issue)
    if current_article is None:
        current_article = find_article(user_input)

        if current_article == "offtopic":
            answer = ollama.chat(model=MODEL, messages=[
                {"role": "system", "content": SMALL_TALK_PROMPT},
                {"role": "user", "content": user_input}],
                options={"temperature": 0.9}, think=False)
            print("Bot:", answer["message"]["content"].strip(), "\n")
            current_article = None
            continue

        # does the chosen article really fit this problem?
        if current_article and not article_matches(user_input, current_article):
            debug("article rejected")
            current_article = None

        if current_article is None:
            ticket_id = create_ticket(user_input)
            print("Bot: This looks like an issue a technician needs to handle. Escalating now.")
            print(f">>> Ticket {ticket_id} created.\n")
            continue

    # ask the model, print, remember
    history.append({"role": "user", "content": user_input})

    answer = ollama.chat(model=MODEL, messages=history,
                         options={"temperature": 0}, think=False)
    reply = answer["message"]["content"]

    print("Bot:", reply.strip(), "\n")

    history.append({"role": "assistant", "content": reply})

    # resolve or escalate (decided in code, not by the model)
    solved = input("Bot: Did this solve your problem? (yes/no): ").strip().lower()

    if solved.startswith("y"):
        print("Bot: Great! Glad I could help. Anything else?\n")
    else:
        ticket_id = create_ticket(user_input)
        print(f">>> Ticket {ticket_id} created. A technician will contact you shortly.\n")

    current_article = None