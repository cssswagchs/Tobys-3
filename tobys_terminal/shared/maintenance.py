import sys
import os


from tobys_terminal.shared.db import get_connection

def reset_statements_for_company(company_name: str, fuzzy_match: bool = False, delete_statement_headers: bool = True):
    """
    Unassign statements for all invoices belonging to the given company.
    Keeps invoice notes intact.
    """
    conn = get_connection()
    cur = conn.cursor()

    # 1) Ensure invoice_tracking has a notes column (one-time)
    try:
        cur.execute("ALTER TABLE invoice_tracking ADD COLUMN notes TEXT")
    except Exception:
        pass  # already exists

    # 2) Find customer IDs for the company
    if fuzzy_match:
        cur.execute("""
            SELECT id FROM customers
            WHERE LOWER(TRIM(company)) LIKE LOWER(TRIM(?)) || '%'
        """, (company_name,))
    else:
        cur.execute("""
            SELECT id FROM customers
            WHERE LOWER(TRIM(company)) = LOWER(TRIM(?))
        """, (company_name,))
    cust_ids = [r[0] for r in cur.fetchall()]
    if not cust_ids:
        conn.close()
        return 0, 0  # no customers found

    # 3) Find all invoice_numbers belonging to those customers
    placeholders = ",".join("?" for _ in cust_ids)
    cur.execute(f"""
        SELECT invoice_number FROM invoices
        WHERE customer_id IN ({placeholders})
          AND invoice_number IS NOT NULL AND TRIM(invoice_number) != ''
    """, tuple(cust_ids))
    inv_nums = [r[0] for r in cur.fetchall()]
    if not inv_nums:
        conn.close()
        return 0, 0  # no invoices

    # 4) Clear statement assignment on invoice_tracking but keep notes
    qmarks = ",".join("?" for _ in inv_nums)
    cur.execute(f"""
        UPDATE invoice_tracking
        SET statement_number = NULL,
            tagged_on = NULL
        WHERE invoice_number IN ({qmarks})
    """, tuple(inv_nums))
    cleared = cur.rowcount or 0

    # 5) (Optional) Remove the header rows so fresh numbers get issued
    deleted_headers = 0
    if delete_statement_headers:
        ph = ",".join("?" for _ in cust_ids)
        cur.execute(f"DELETE FROM statement_tracking WHERE customer_id IN ({ph})", tuple(cust_ids))
        deleted_headers = cur.rowcount or 0

    conn.commit()
    conn.close()
    return cleared, deleted_headers
