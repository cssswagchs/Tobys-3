from tobys_terminal.shared.customer_utils import get_customer_ids_by_company
from tobys_terminal.shared.db import get_connection
# Import the config
from config import P_STATUS

def sync_printavo_orders_from_invoices(customer_label: str):
    label = customer_label.lower()

    if label.startswith("imm"):
        source_table = "invoices"
        target_table = "imm_orders"
        field_map = {
            "invoice_status": "p_status",
            "invoice_number": "invoice_number",
            "nickname": "nickname",
            "po_number": "po_number"
        }
        
        # Only skip truly cancelled/archived orders
        skip_statuses = {'cancelled', 'archived'}

        # Get customer IDs for IMM
        customer_ids = get_customer_ids_by_company("IMM")
        if not customer_ids:
            print("❌ No IMM customer IDs found.")
            return

    # Rest of the function remains the same


    else:
        print(f"⚠️ Unknown label for invoice sync: {customer_label}")
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT invoice_number, invoice_status, nickname, po_number
        FROM {source_table}
        WHERE
            invoice_number IS NOT NULL
            AND TRIM(invoice_number) != ''
            AND customer_id IN ({','.join(['?'] * len(customer_ids))})
    """, customer_ids)

    rows = cur.fetchall()

    inserted, updated = 0, 0

    for invoice, status, nickname, po in rows:
        invoice = invoice.strip()
        status_clean = (status or "").strip().lower()

        if not invoice or status_clean in skip_statuses:
            continue

        cur.execute("SELECT id FROM imm_orders WHERE TRIM(invoice_number) = ?", (invoice,))
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE imm_orders
                SET p_status = ?
                WHERE invoice_number = ?
            """, (status, invoice))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO imm_orders (
                    invoice_number, p_status, nickname, po_number, status
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                invoice,
                status,
                nickname or "",
                po or "",
                "Need Review"
            ))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ IMM sync complete. Inserted: {inserted}, Updated: {updated}")


def sync_printavo_orders_for_harlestons():
    source_table = "invoices"
    target_table = "harlestons_orders"
    field_map = {
        "invoice_status": "p_status",
        "invoice_number": "invoice_number",
        "nickname": "club_nickname",
        "po_number": "po_number"
    }
    
    skip_statuses = {
        'done', 'complete', 'CANCELLED', 'ARCHIVED',
        'DONE DONE', 'QUOTE', 'TEMPLATE', 'shipped',
        'PICKED UP', 'HARLESTONS-INVOICED', 'HARLESTONS--NO ORDER PENDING',
        'HARLESTONS--PICKED UP', 'HARLESTONS-NEED SEWOUT'
    }

    # ✅ Get customer IDs for Harlestons
    customer_ids = get_customer_ids_by_company("Harlestons")
    if not customer_ids:
        print("❌ No Harlestons customer IDs found.")
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT invoice_number, invoice_status, nickname, po_number
        FROM {source_table}
        WHERE
            invoice_number IS NOT NULL
            AND TRIM(invoice_number) != ''
            AND customer_id IN ({','.join(['?'] * len(customer_ids))})
    """, customer_ids)

    rows = cur.fetchall()
    inserted, updated = 0, 0

    for invoice, status, nickname, po in rows:
        invoice = invoice.strip()
        status_clean = (status or "").strip().lower()

        if not invoice or status_clean in skip_statuses:
            continue

        cur.execute("SELECT id FROM harlestons_orders WHERE TRIM(invoice_number) = ?", (invoice,))
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE harlestons_orders
                SET p_status = ?
                WHERE invoice_number = ?
            """, (status, invoice))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO harlestons_orders (
                    invoice_number, p_status, club_nickname, po_number, status
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                invoice,
                status,
                nickname or "",
                po or "",
                "Need Review"
            ))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ Harlestons sync complete. Inserted: {inserted}, Updated: {updated}")
