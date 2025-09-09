from datetime import datetime
import os
from tobys_terminal.shared.statement_logic import StatementCalculator
from tobys_terminal.shared.pdf_export import generate_pdf

from tobys_terminal.shared.db import get_connection, get_statement_meta, get_statement_invoices

def _get_statement_header(stmt):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT customer_id, start_date, end_date, company_label
        FROM statement_tracking
        WHERE statement_number = ?
    """, (stmt,))
    row = cur.fetchone()
    conn.close()
    return row if row else (None, None, None, None)

def save_field_value(table, field, value, record_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE {table} SET {field} = ? WHERE id = ?",
        (value, record_id)
    )
    conn.commit()
    conn.close()


def reprint_statement(statement_number: str):
    # --- header + invoice list
    customer_id, start_date, end_date, company_label = _get_statement_header(statement_number)
    if start_date is None and end_date is None:
        raise ValueError(f"Statement {statement_number} not found.")
    invoice_numbers = get_statement_invoices(statement_number)
    if not invoice_numbers:
        raise ValueError(f"No invoices recorded for {statement_number}.")

    # --- fetch invoices and payments
    conn = get_connection()
    cur = conn.cursor()

    qmarks = ",".join("?" for _ in invoice_numbers)

    cur.execute(f"""
        SELECT invoice_date, invoice_number, total, paid, invoice_status, nickname, po_number
        FROM invoices
        WHERE invoice_number IN ({qmarks})
    """, tuple(invoice_numbers))
    invs = cur.fetchall()

    cur.execute(f"""
        SELECT transaction_date, amount, invoice_number, payment_method, reference
        FROM payments_clean
        WHERE invoice_number IN ({qmarks})
    """, tuple(invoice_numbers))
    pays = cur.fetchall()
    conn.close()

    # --- build rows
    rows = []
    for inv_date, inv_num, total, paid, _status, nick, po in invs:
        dt = StatementCalculator._parse_date(None, inv_date)
        # First, check if we have payment info for this invoice
        payment_info = {}
        for tx_date, amount, inv_num, method, ref in pays:
            if inv_num == inv_num:  # Match this invoice
                payment_info[inv_num] = f"Paid - {method} {ref}".strip()
                if payment_info[inv_num].endswith("-"):
                    payment_info[inv_num] = "Paid"

        # Then use that info if available
        if inv_num in payment_info:
            status = payment_info[inv_num]
        else:
            status = "Paid" if str(paid or "").strip().lower() in {"yes", "true", "paid", "y", "1"} else "Unpaid"
        rows.append((dt, "Invoice", inv_num, (po or ""), (nick or ""), float(total or 0), status))

    for tx_date, amount, inv_num, method, ref in pays:
        dt = StatementCalculator._parse_date(None, tx_date)
        payload = f"{(method or '').strip()} {(ref or '').strip()}".strip()
        rows.append((dt, "Payment", inv_num, None, None, float(amount or 0), payload))

    rows.sort(key=lambda r: (
        r[0],
        int("".join(filter(str.isdigit, r[2]))) if r[2] else 0
    ))

    billed = sum(float(r[5] or 0) for r in rows if r[1] == "Invoice")
    paid = sum(float(r[5] or 0) for r in rows if r[1] == "Payment")
    totals = {"billed": billed, "paid": paid, "balance": billed - paid}

    # --- Get customer name
    customer_name = company_label
    if not customer_name:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(NULLIF(TRIM(c.company), ''), TRIM(c.first_name)||' '||TRIM(c.last_name))
            FROM invoices i
            JOIN customers c ON c.id = i.customer_id
            WHERE i.invoice_number = ?
        """, (invoice_numbers[0],))
        r = cur.fetchone()
        conn.close()
        customer_name = r[0] if r else "Unknown_Customer"

    # --- Safe folder name
    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in customer_name)

    # --- NEW: Output path with subfolder per customer
    base_dir = os.path.join(os.path.dirname(__file__), "exports", "statements", safe_name)
    os.makedirs(base_dir, exist_ok=True)

    safe_start = (start_date or "").replace("/", "-")
    safe_end   = (end_date or "").replace("/", "-")
    date_str   = f"{safe_start}_to_{safe_end}" if safe_start and safe_end else "Full_Range"

    output_filename = f"{statement_number}_statement_{safe_name}_{date_str}.pdf"

    output_path = os.path.join(base_dir, output_filename)

    generate_pdf(
        customer_name=customer_name,
        rows=rows,
        totals=totals,
        start_date=start_date,
        end_date=end_date,
        nickname=None,
        statement_number=statement_number,
        output_path=output_path,
        interactive=False
    )

    #print(f"Returning PDF path to Flask: {output_path}")
    return output_path






    invoice_numbers = get_statement_invoices(statement_number)
    if not invoice_numbers:
        # Fallback: compute from header
        # Use customer_ids_text if you store it, else customer_id
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT customer_ids_text, customer_id, start_date, end_date
            FROM statement_tracking
            WHERE statement_number = ?
        """, (statement_number,))
        ids_text, primary_id, s, e = cur.fetchone() or (None, None, None, None)
        ids = [int(x) for x in (ids_text or "").split(",") if x] or ([primary_id] if primary_id else [])
        placeholders = ",".join("?" for _ in ids)
        cur.execute(f"""
            SELECT invoice_number
            FROM invoices
            WHERE customer_id IN ({placeholders})
            AND date(invoice_date) BETWEEN date(?) AND date(?)
        """, (*ids, s, e))
        invoice_numbers = [r[0] for r in cur.fetchall()]
        conn.close()

    if not invoice_numbers:
        raise ValueError(f"No invoices recorded for {statement_number}.")
