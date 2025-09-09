# utils/tobys_terminal.utils.statement_logic.py

from typing import List, Tuple, Dict, Optional, Union, Literal
from datetime import date
from tobys_terminal.shared.db import get_connection


InvoiceRow = Tuple[Optional[date], Literal["Invoice"], str, float, str, Optional[str]]
PaymentRow = Tuple[Optional[date], Literal["Payment"], str, float, Optional[str], Optional[str], Optional[str]]
Row = Union[InvoiceRow, PaymentRow]

Totals = Dict[str, float]

class StatementCalculator:
    """Calculates invoice/payment statement rows and totals for a customer."""

    BILLABLE_STATUSES = {
        "complete and ready for pickup", "shipped", "picked up",
        "payment request sent", "harlestons -- invoiced",
        "past due invoice - followed up", "on hold - need payment please",
        "done done", "pickup reminder sent", "harlestons -- picked up"
    }

    NON_BILLABLE_STATUSES = {
        "cancelled", "archived", "quote", "void", "do not bill",
        "harlestons-need sewout", "template", "harlestons -- no order pending",
        "emb - flats - inline", "harlestons -- file sent for approval",
        "file sent for approval", "harlestons -- waiting on product", "print dtf",
        "harlestons -- emb inline", "emb - hats - inline",
        "hold - need more information", "waiting product only",
        "goods on backorder", "harlestons -- on deck",
        "patches - ready to apply"
    }

    def __init__(
        self,
        customer_ids: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        unpaid_only: bool = False,
        unreconciled_only: bool = False
    ):
        self.customer_ids = customer_ids
        self.start_date = start_date
        self.end_date = end_date
        self.unpaid_only = unpaid_only
        self.unreconciled_only = unreconciled_only

    def fetch(self) -> Tuple[List[Row], Totals]:
        """Fetch invoice/payment rows and compute totals."""
        conn = get_connection()
        cursor = conn.cursor()

        invoice_rows = []
        total_billed = 0.0
        filtered_invoice_numbers = set()

        if self.customer_ids:
            placeholders = ','.join('?' for _ in self.customer_ids)
            cursor.execute(f"""
                SELECT invoice_date, invoice_number, total, paid, invoice_status, po_number
                FROM invoices
                WHERE customer_id IN ({placeholders})
            """, self.customer_ids)



            invoices = cursor.fetchall()

            for inv_date, inv_num, total, paid, status, po_number in invoices:
                status_norm = (status or "").strip().lower()
                paid_clean = str(paid or "").strip().lower()
                if float(total or 0) == 0.0:
                    continue  # 🚫 Skip $0 invoices


                is_nonbillable = status_norm in self.NON_BILLABLE_STATUSES
                is_billable    = status_norm in self.BILLABLE_STATUSES

                if self.unpaid_only:
                    # Strict for active cycles: must be in whitelist AND not non‑billable
                    if is_nonbillable or not is_billable:
                        continue
                else:
                    # Looser for historical/paid cycles: only exclude explicit non‑billables
                    if is_nonbillable:
                        continue
                if self.unpaid_only and paid_clean in {"yes", "true", "paid", "y", "1"}:
                    continue

                parsed_date = self._parse_date(inv_date)
                if not self._in_range(parsed_date):
                    continue

                invoice_rows.append((parsed_date, "Invoice", inv_num, float(total), paid_clean, po_number or ""))

                total_billed += float(total)
                filtered_invoice_numbers.add(inv_num)

                # --- Payments ---
        payment_rows = []
        total_paid = 0.0
        payments = []

        if filtered_invoice_numbers:
            # Statement mode: pull ALL payments for the invoices we decided to show,
            # regardless of date/status.
            placeholders = ",".join("?" for _ in filtered_invoice_numbers)
            cursor.execute(f"""
                SELECT
                    p.transaction_date,
                    p.amount,
                    p.invoice_number,
                    p.payment_method,
                    p.reference
                FROM payments_clean p
                WHERE p.invoice_number IN ({placeholders})
            """, tuple(filtered_invoice_numbers))
            payments = cursor.fetchall()

        else:
            # Reconcile / generic mode: build query dynamically
            base_sql = """
                SELECT
                    p.transaction_date,
                    p.amount,
                    p.invoice_number,
                    p.payment_method,
                    p.reference
                FROM payments_clean p
                JOIN invoices i ON p.invoice_number = i.invoice_number
                WHERE
            """
            clauses = []
            params = []

            # Optional customer filter (only if provided)
            if self.customer_ids:
                clauses.append(f"p.customer_id IN ({','.join('?' for _ in self.customer_ids)})")
                params.extend(self.customer_ids)

            # Always exclude non-billable invoice statuses
            clauses.append(
                f"LOWER(TRIM(COALESCE(i.invoice_status, ''))) NOT IN ({','.join('?' for _ in self.NON_BILLABLE_STATUSES)})"
            )
            params.extend(list(self.NON_BILLABLE_STATUSES))

            # Reconcile single-day filter
            if self.start_date and self.end_date and self.start_date == self.end_date:
                clauses.append("DATE(p.transaction_date) = ?")
                params.append(self.start_date.strftime("%Y-%m-%d"))

            payment_query = base_sql + " AND ".join(clauses)
            cursor.execute(payment_query, tuple(params))
            payments = cursor.fetchall()

        #print(f"💬 Payment rows returned: {len(payments)}")


        for tx_date, amount, inv_num, method, ref in payments:
            # (No unpaid_only filtering here — we want ALL payments for shown invoices.)
            parsed_date = self._parse_date(tx_date)

            cursor.execute("SELECT reconciled, notes FROM payment_tracking WHERE invoice_number = ?", (inv_num,))
            row = cursor.fetchone()
            rec_flag = row[0] if row else None
            note = row[1] if row else ""

            if self.unreconciled_only and str(rec_flag).strip().lower() == "yes":
                continue

            payment_rows.append((parsed_date, "Payment", inv_num, float(amount), method, ref or "", note))
            total_paid += float(amount)




            total_paid += float(amount)

        conn.close()

        all_rows = sorted(invoice_rows + payment_rows, key=lambda r: (
            r[0],                                  # sort by date
            int("".join(filter(str.isdigit, r[2]))) if r[2] else 0  # numeric sort on invoice #
        ))

        # Recompute totals from the rows we are actually returning,
        # so the numbers always match what the table displays.
        total_billed = sum(r[3] for r in all_rows if r[1] == "Invoice")
        total_paid   = sum(r[3] for r in all_rows if r[1] == "Payment")

        totals = {
            "billed": total_billed,
            "paid": total_paid,
            "balance": total_billed - total_paid
        }
        return all_rows, totals

    def _parse_date(self, s: Optional[str]) -> Optional[date]:
        from datetime import datetime
        if not s:
            #print("⚠️ _parse_date: Empty input")
            return None

        s = str(s).strip().rstrip("Z")
        formats = [
            "%m-%d-%Y",
            "%m/%d/%Y",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue

        # last‑chance: try first 10 chars as YYYY-MM-DD
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            pass

        #print(f"⚠️ Failed to parse date: {s}")
        return None



    def _in_range(self, d: Optional[date]) -> bool:
        if not d:
            return False
        if self.start_date and d < self.start_date:
            return False
        if self.end_date and d > self.end_date:
            return False
        return True


def get_statement_summaries(customer_ids: list[int]) -> list[dict]:
    if not customer_ids:
        return []

    conn = get_connection()
    cur = conn.cursor()

    # Prepare WHERE clause for exact + group match
    in_placeholders = ",".join("?" for _ in customer_ids)
    like_clause = " OR ".join(
        "(s.customer_ids_text IS NOT NULL AND (',' || s.customer_ids_text || ',') LIKE '%,' || ? || ',%')"
        for _ in customer_ids
    )
    where_clause = f"(s.customer_id IN ({in_placeholders}) OR {like_clause})"
    params = tuple(customer_ids) + tuple(str(x) for x in customer_ids)

    sql = f"""
    WITH pay AS (
      SELECT invoice_number, SUM(amount) AS paid
      FROM payments_clean
      GROUP BY invoice_number
    )
    SELECT
      s.statement_number,
      COALESCE(s.start_date,'') AS s_start,
      COALESCE(s.end_date,'')   AS s_end,
      COUNT(DISTINCT it.invoice_number) AS invoice_count,
      ROUND(SUM(COALESCE(inv.total, 0)), 2) AS billed,
      ROUND(SUM(COALESCE(pay.paid, 0)), 2)  AS paid
    FROM statement_tracking s
    LEFT JOIN invoice_tracking it ON it.statement_number = s.statement_number
    LEFT JOIN invoices inv ON TRIM(inv.invoice_number) = TRIM(it.invoice_number)
    LEFT JOIN pay ON TRIM(pay.invoice_number) = TRIM(it.invoice_number)
    WHERE {where_clause}
    GROUP BY s.statement_number, s_start, s_end
    ORDER BY s_start DESC, s_end DESC
    """
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    data = []
    for stmt, s_start, s_end, cnt, billed, paid in rows:
        billed = billed or 0.0
        paid = paid or 0.0
        bal = round(billed - paid, 2)
        status = "Paid" if abs(bal) < 0.01 else ("Credit" if bal < 0 else "Due")
        data.append({
            "stmt": stmt,
            "period": f"{s_start or '—'} to {s_end or '—'}",
            "count": int(cnt or 0),
            "billed": billed,
            "paid": paid,
            "balance": bal,
            "status": status
        })
    return data

def get_customer_ids_by_company(company_name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM customers
        WHERE TRIM(LOWER(company)) = TRIM(LOWER(?))
    """, (company_name,))
    ids = [r[0] for r in cur.fetchall()]
    conn.close()
    return ids

def void_statement(statement_number):
    """
    Mark a statement as void in the database.
    
    Args:
        statement_number (str): The statement number to void
        
    Returns:
        tuple: (success, message) where success is a boolean and message is a string
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Check if statement exists
        cur.execute("SELECT statement_number FROM statement_tracking WHERE statement_number = ?", 
                   (statement_number,))
        if not cur.fetchone():
            return False, f"Statement {statement_number} not found."
        
        # Update statement status to void
        cur.execute("""
            UPDATE statement_tracking 
            SET status = 'VOID', 
                voided_at = DATETIME('now'),
                notes = COALESCE(notes, '') || ' Voided on ' || DATETIME('now')
            WHERE statement_number = ?
        """, (statement_number,))
        
        # Get affected invoices
        cur.execute("""
            SELECT invoice_number FROM invoice_tracking
            WHERE statement_number = ?
        """, (statement_number,))
        
        invoices = [row[0] for row in cur.fetchall()]
        
        # Remove invoice-statement associations
        cur.execute("""
            DELETE FROM invoice_tracking
            WHERE statement_number = ?
        """, (statement_number,))
        
        conn.commit()
        
        return True, f"Statement {statement_number} voided successfully. {len(invoices)} invoices released."
    
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Error voiding statement: {str(e)}"
    
    finally:
        if conn:
            conn.close()


def void_statement_cli():
    """Command-line interface for voiding statements."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Void a statement")
    parser.add_argument("statement_number", help="Statement number to void")
    parser.add_argument("--force", action="store_true", help="Force void without confirmation")
    
    args = parser.parse_args()
    
    if not args.force:
        confirm = input(f"Are you sure you want to void statement {args.statement_number}? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
    
    success, message = void_statement(args.statement_number)
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

def fix_invoice_tracking_table():
    """Fix the invoice_tracking table to prevent duplicate invoices on statements."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Check if we need to modify the table structure
        cur.execute("PRAGMA table_info(invoice_tracking)")
        columns = {row[1]: row for row in cur.fetchall()}
        
        # Check if the primary key is on invoice_number
        primary_key_on_invoice = any(row[5] == 1 and row[1] == 'invoice_number' for row in cur.fetchall())
        
        # Find any duplicate invoices (same invoice on multiple statements)
        cur.execute("""
            SELECT invoice_number, COUNT(DISTINCT statement_number) as stmt_count,
                   GROUP_CONCAT(statement_number) as statements
            FROM invoice_tracking
            GROUP BY invoice_number
            HAVING stmt_count > 1
        """)
        
        duplicates = cur.fetchall()
        if duplicates:
            print(f"Found {len(duplicates)} invoices on multiple statements:")
            for inv, count, statements in duplicates:
                print(f"  Invoice {inv} appears on {count} statements: {statements}")
                
                # Keep only the most recent statement for each invoice
                cur.execute("""
                    DELETE FROM invoice_tracking
                    WHERE invoice_number = ?
                    AND statement_number NOT IN (
                        SELECT statement_number
                        FROM invoice_tracking
                        WHERE invoice_number = ?
                        ORDER BY ROWID DESC
                        LIMIT 1
                    )
                """, (inv, inv))
        
        conn.commit()
        return len(duplicates)
    except Exception as e:
        conn.rollback()
        print(f"Error fixing invoice_tracking table: {e}")
        return 0
    finally:
        conn.close()

def check_invoices_on_statements(invoice_numbers):
    """
    Check if any invoices are already on statements.
    
    Args:
        invoice_numbers (list): List of invoice numbers to check
        
    Returns:
        dict: Dictionary mapping invoice numbers to statement numbers
    """
    if not invoice_numbers:
        return {}
        
    conn = get_connection()
    cur = conn.cursor()
    
    placeholders = ','.join('?' for _ in invoice_numbers)
    cur.execute(f"""
        SELECT invoice_number, statement_number 
        FROM invoice_tracking 
        WHERE invoice_number IN ({placeholders})
    """, invoice_numbers)
    
    already_on_statements = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    
    return already_on_statements

def track_invoices_on_statement(statement_number, invoice_numbers):
    """
    Track which invoices are included in a statement, preventing duplicates.
    
    Args:
        statement_number (str): The statement number
        invoice_numbers (list): List of invoice numbers to track
        
    Returns:
        tuple: (success, skipped_invoices)
    """
    if not invoice_numbers:
        return True, []
        
    # First check if any invoices are already on statements
    already_on_statements = check_invoices_on_statements(invoice_numbers)
    if already_on_statements:
        # Filter out invoices that are already on statements
        invoice_numbers = [inv for inv in invoice_numbers if inv not in already_on_statements]
    
    if not invoice_numbers:
        return True, list(already_on_statements.keys())
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        for inv in invoice_numbers:
            cur.execute("""
                INSERT OR REPLACE INTO invoice_tracking (invoice_number, statement_number, tagged_on)
                VALUES (?, ?, DATETIME('now'))
            """, (inv, statement_number))
        
        conn.commit()
        return True, list(already_on_statements.keys())
    except Exception as e:
        conn.rollback()
        print(f"Error tracking invoices: {e}")
        return False, list(already_on_statements.keys())
    finally:
        conn.close()

def ensure_statement_integrity():
    """Ensure statement and invoice tracking integrity."""
    # Fix any duplicate invoices in the invoice_tracking table
    duplicates_fixed = fix_invoice_tracking_table()
    if duplicates_fixed:
        print(f"Fixed {duplicates_fixed} duplicate invoice entries in statements.")
    
    # Ensure the statement_tracking table has the necessary columns
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Check if status column exists
        cur.execute("PRAGMA table_info(statement_tracking)")
        columns = [row[1] for row in cur.fetchall()]
        
        if "status" not in columns:
            cur.execute("ALTER TABLE statement_tracking ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
        
        if "voided_at" not in columns:
            cur.execute("ALTER TABLE statement_tracking ADD COLUMN voided_at TEXT")
            
        if "notes" not in columns:
            cur.execute("ALTER TABLE statement_tracking ADD COLUMN notes TEXT")
        
        conn.commit()
    except Exception as e:
        print(f"Error ensuring statement integrity: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Statement Logic Utility")
    print("======================")
    print("1. Fix invoice tracking table")
    print("2. Void a statement")
    print("3. Exit")
    
    choice = input("Enter your choice (1-3): ")
    
    if choice == "1":
        duplicates = fix_invoice_tracking_table()
        print(f"Fixed {duplicates} duplicate invoice entries.")
    elif choice == "2":
        statement_number = input("Enter statement number to void: ")
        void_statement_cli()
    else:
        print("Exiting.")

