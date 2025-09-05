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
