from typing import List, Tuple, Dict
from tobys_terminal.shared.db import get_connection
from sqlite3 import Row

def fetch_invoice_rows(customer_ids: List[str]) -> Tuple[List[Dict], Dict]:
    """Fetch invoice/payment rows and compute totals."""
    conn = get_connection()
    cursor = conn.cursor()

    invoice_rows = []
    total_billed = 0.0
    total_paid = 0.0

    if customer_ids:
        placeholders = ','.join('?' for _ in customer_ids)
        cursor.execute(f"""
            SELECT invoice_date, invoice_number, total, paid, invoice_status, po_number
            FROM invoices
            WHERE customer_id IN ({placeholders})
        """, customer_ids)

        for row in cursor.fetchall():
            paid_val = float(row["paid"]) if isinstance(row["paid"], (int, float)) else 0.0
            total_val = float(row["total"]) if isinstance(row["total"], (int, float)) else 0.0

            row_dict = {
                "date": row["invoice_date"],
                "number": row["invoice_number"],
                "total": total_val,
                "paid": paid_val,
                "status": row["invoice_status"],
                "po": row["po_number"]
            }
            invoice_rows.append(row_dict)
            total_billed += total_val
            total_paid += paid_val

    totals = {
        "billed": total_billed,
        "paid": total_paid,
        "balance": total_billed - total_paid,
        "count": len(invoice_rows)
    }

    return invoice_rows, totals
