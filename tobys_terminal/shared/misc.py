import os, csv, io
from datetime import datetime
from flask import Flask, request, render_template_string, send_file, redirect, url_for, abort, Response
import sqlite3
import sys

from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.reprint import reprint_statement  # makes + returns a PDF path via generate_pdf()

app = Flask(__name__)

from functools import wraps
from flask import request, Response

@app.route("/webhook", methods=["POST"])
def webhook():
    import os

    repo_path = "/home/cssembroidery/css-billing-portal"
    pull_result = os.popen(f"cd {repo_path} && git pull origin main").read()
    os.system("touch /var/www/cssembroidery_pythonanywhere_com_wsgi.py")

    with open("/home/cssembroidery/deploy_log.txt", "a") as log:
        log.write("=== Webhook Triggered ===\n")
        log.write(pull_result + "\n")

    return "✅ Deployment successful!", 200



PORTAL_USER = "harlestons"
PORTAL_PASS = "harlestons"  # <- set your password

def check_auth(u, p): return u == PORTAL_USER and p == PORTAL_PASS
def authenticate():
    return Response("Auth required", 401, {"WWW-Authenticate": 'Basic realm="Portal"'})

def requires_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return wrapper




# ---------- helpers ----------
def get_customer_ids_by_company(company_name: str):
    """Return list of customer IDs that match a given company label (exact, trimmed)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM customers
        WHERE TRIM(LOWER(company)) = TRIM(LOWER(?))
    """, (company_name,))
    ids = [r[0] for r in cur.fetchall()]
    conn.close()
    return ids

def fetch_statement_rows(customer_ids):
    """
    Match your Statement Register logic:
    For the given customer IDs, return one row per statement with billed/paid/balance.
    """
    if not customer_ids:
        return []

    conn = get_connection()
    cur = conn.cursor()

    # Same structure you use in the desktop Statement Register view (summed billed/paid per statement):contentReference[oaicite:3]{index=3}
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
    LEFT JOIN invoice_tracking it
      ON it.statement_number = s.statement_number
    LEFT JOIN invoices inv
      ON TRIM(inv.invoice_number) = TRIM(it.invoice_number)
    LEFT JOIN pay
      ON TRIM(pay.invoice_number) = TRIM(it.invoice_number)
    WHERE {where_clause}
    GROUP BY s.statement_number, s_start, s_end
    ORDER BY s_start DESC, s_end DESC
    """
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    # Normalize for the template
    data = []
    for stmt, s_start, s_end, cnt, billed, paid in rows:
        billed = billed or 0.0
        paid   = paid or 0.0
        bal    = round(billed - paid, 2)
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

def dollars(x):  # simple Jinja filter
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"

app.jinja_env.filters["dollars"] = dollars

# ---------- routes ----------
@app.route("/")
@requires_auth
def home():
    return redirect(url_for("harlestons_view"))

@app.route("/harlestons")
@requires_auth
def harlestons_view():
    # You can change this to any company name exactly as stored in DB
    company = request.args.get("company", "Harlestons")
    customer_ids = get_customer_ids_by_company(company)

    rows = fetch_statement_rows(customer_ids)
    # Filters
    q = (request.args.get("q") or "").strip().lower()
    show = (request.args.get("show") or "all").lower()  # all | due | paid | credit

    def keep(row):
        if q and q not in (row["stmt"] or "").lower() and q not in row["period"].lower():
            return False
        if show == "due" and not (row["status"] == "Due"):
            return False
        if show == "paid" and not (row["status"] == "Paid"):
            return False
        if show == "credit" and not (row["status"] == "Credit"):
            return False
        return True

    filtered = [r for r in rows if keep(r)]

    totals = {
        "billed": sum(r["billed"] for r in filtered),
        "paid":   sum(r["paid"] for r in filtered),
        "balance": sum(r["balance"] for r in filtered),
        "count":   len(filtered)
    }

    return render_template_string(TEMPLATE, company=company, rows=filtered, totals=totals, q=q, show=show)

@app.route("/harlestons/export.csv")
@requires_auth
def export_csv():
    company = request.args.get("company", "Harlestons")
    customer_ids = get_customer_ids_by_company(company)
    rows = fetch_statement_rows(customer_ids)

    q = (request.args.get("q") or "").strip().lower()
    show = (request.args.get("show") or "all").lower()

    def keep(row):
        if q and q not in (row["stmt"] or "").lower() and q not in row["period"].lower():
            return False
        if show == "due" and not (row["status"] == "Due"):
            return False
        if show == "paid" and not (row["status"] == "Paid"):
            return False
        if show == "credit" and not (row["status"] == "Credit"):
            return False
        return True

    filtered = [r for r in rows if keep(r)]

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Statement #", "Period", "Invoices", "Billed", "Paid", "Balance", "Status"])
    for r in filtered:
        w.writerow([r["stmt"], r["period"], r["count"], f"{r['billed']:.2f}", f"{r['paid']:.2f}", f"{r['balance']:.2f}", r["status"]])
    out.seek(0)
    filename = f"harlestons_statements_{datetime.now():%Y%m%d}.csv"
    return Response(out.read(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.route("/harlestons/statement/<stmt>/pdf")
@requires_auth
def download_pdf(stmt):
    path = reprint_statement(stmt)          # <-- now returns a file path
    return send_file(path, as_attachment=True)



"""

if __name__ == "__main__":
    # Run locally:  http://127.0.0.1:5000/harlestons
    app.run(debug=True)"""
