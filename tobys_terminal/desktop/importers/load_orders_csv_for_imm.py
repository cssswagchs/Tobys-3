import csv
from datetime import datetime

def load_orders_csv_for_imm(csv_path: str) -> list[dict]:
    orders = []

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            invoice = row.get("Invoice", "").strip()
            if not invoice:
                continue

            mapped = {
                "invoice_number": invoice,
                "po_number": row.get("PO #", "").strip(),
                "nickname": row.get("Nickname", "").strip(),
                "p_status": row.get("Status", "").strip(),
                "in_hand_date": normalize_date(row.get("Customer Due Date", ""))
            }

            orders.append(mapped)

    return orders

def normalize_date(date_str: str) -> str:
    """Convert MM/DD/YYYY or YYYY-MM-DD to YYYY-MM-DD. Return '' if invalid."""
    if not date_str:
        return ""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""
