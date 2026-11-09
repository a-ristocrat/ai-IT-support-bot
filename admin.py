"""
Technician Panel for the IT Support Bot.
View, filter, and close tickets from tickets.csv, and see statistics.
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).parent
TICKETS_FILE = BASE_DIR / "tickets.csv"

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def load_tickets():
    if not TICKETS_FILE.exists():
        return []
    with open(TICKETS_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_tickets(tickets):
    if not tickets:
        return
    with open(TICKETS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=tickets[0].keys())
        writer.writeheader()
        writer.writerows(tickets)


def show_tickets(tickets):
    if not tickets:
        print("No tickets found.\n")
        return

    # Most urgent first
    tickets = sorted(tickets, key=lambda t: PRIORITY_ORDER.get(t["priority"], 9))

    print(f"\n{'ID':<18} {'Priority':<9} {'Status':<7} {'Category':<9} {'User':<15} Problem")
    print("-" * 90)
    for t in tickets:
        print(f"{t['ticket_id']:<18} {t['priority']:<9} {t['status']:<7} "
              f"{t['category']:<9} {t.get('name', '')[:14]:<15} {t['problem'][:35]}")
    print()


def filter_tickets(tickets):
    field = input("Filter by (1) priority or (2) status? ").strip()
    if field == "1":
        value = input("Priority (Critical/High/Medium/Low): ").strip().lower()
        show_tickets([t for t in tickets if t["priority"].lower() == value])
    elif field == "2":
        value = input("Status (open/closed): ").strip().lower()
        show_tickets([t for t in tickets if t["status"].lower() == value])
    else:
        print("Invalid choice.\n")


def close_ticket(tickets):
    ticket_id = input("Ticket ID to close: ").strip().upper()
    for t in tickets:
        if t["ticket_id"] == ticket_id:
            if t["status"] == "closed":
                print("This ticket is already closed.\n")
                return
            t["status"] = "closed"
            save_tickets(tickets)
            print(f"Ticket {ticket_id} closed.\n")
            return
    print("Ticket not found.\n")


def show_stats(tickets):
    total = len(tickets)
    if total == 0:
        print("No tickets yet.\n")
        return

    open_count = sum(1 for t in tickets if t["status"] == "open")
    print(f"\nTotal tickets: {total}")
    print(f"Open: {open_count} | Closed: {total - open_count}")

    for field in ["priority", "category"]:
        counts = {}
        for t in tickets:
            counts[t[field]] = counts.get(t[field], 0) + 1
        print(f"\nBy {field}:")
        for name, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {name:<10} {count:>3}  {'#' * count}")
    print()


def main():
    print("=== Technician Panel ===")
    while True:
        tickets = load_tickets()
        print("1. View all tickets")
        print("2. Filter tickets")
        print("3. Close a ticket")
        print("4. Statistics")
        print("5. Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            show_tickets(tickets)
        elif choice == "2":
            filter_tickets(tickets)
        elif choice == "3":
            close_ticket(tickets)
        elif choice == "4":
            show_stats(tickets)
        elif choice == "5":
            break
        else:
            print("Invalid choice.\n")


if __name__ == "__main__":
    main()