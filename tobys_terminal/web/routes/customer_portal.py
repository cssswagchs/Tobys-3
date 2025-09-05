# 📁 routes/customer_portal.py
from flask import Blueprint, session, request, render_template, redirect, url_for, flash, Response, send_file
import io, os, csv
from datetime import datetime
from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.invoice_logic import fetch_invoice_rows
from tobys_terminal.shared.statement_logic import get_statement_summaries, get_customer_ids_by_company
from tobys_terminal.shared.reprint import reprint_statement
from tobys_terminal.shared.export_csv import export_invoice_csv

customer_bp = Blueprint("customer", __name__)


def check_authorized(company: str):
    user_company = session.get("company")
    role = session.get("role")
    if role != "admin" and company != user_company:
        flash("You are not authorized to view that customer page.", "error")
        return False
    return True


@customer_bp.route("/customer/<company>")
def customer_portal(company):
    if not check_authorized(company):
        return redirect(url_for("customer.customer_portal", company=session.get("company")))

    customer_ids = get_customer_ids_by_company(company)
    rows = get_statement_summaries(customer_ids)

    if not rows:
        invoice_rows, invoice_totals = fetch_invoice_rows(customer_ids)
        return render_template("customer_invoices.html", company=company, invoices=invoice_rows, totals=invoice_totals)

    totals = {
        "billed": sum(r["billed"] for r in rows),
        "paid": sum(r["paid"] for r in rows),
        "balance": sum(r["balance"] for r in rows),
        "count": sum(r["count"] for r in rows),
    }

    return render_template("customer_portal.html", company=company, rows=rows, totals=totals)


@customer_bp.route("/customer/<company>/export.csv")
def export_csv(company):
    if not check_authorized(company):
        return redirect(url_for("customer.customer_portal", company=session.get("company")))

    group_name = session.get("group_name") or session.get("company")
    customer_ids = get_customer_ids_by_company(group_name)
    rows = get_statement_summaries(customer_ids)

    q = (request.args.get("q") or "").strip().lower()
    show = (request.args.get("show") or "all").lower()

    def keep(row):
        if q and q not in (row["stmt"] or "").lower() and q not in row["period"].lower():
            return False
        if show == "due" and row["status"] != "Due":
            return False
        if show == "paid" and row["status"] != "Paid":
            return False
        if show == "credit" and row["status"] != "Credit":
            return False
        return True

    filtered = [r for r in rows if keep(r)]

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Statement #", "Period", "Invoices", "Billed", "Paid", "Balance", "Status"])
    for r in filtered:
        w.writerow([r["stmt"], r["period"], r["count"], f"{r['billed']:.2f}", f"{r['paid']:.2f}", f"{r['balance']:.2f}", r["status"]])
    out.seek(0)
    filename = f"{company}_statements_{datetime.now():%Y%m%d}.csv"
    return Response(out.read(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})


@customer_bp.route("/customer/<company>/statement/<stmt>/pdf")
def download_pdf(company, stmt):
    if not check_authorized(company):
        return redirect(url_for("customer.customer_portal", company=session.get("company")))

    try:
        path = reprint_statement(stmt)
        if not os.path.exists(path):
            raise ValueError("File not found on disk.")
        return send_file(path, mimetype="application/pdf")
    except Exception as e:
        return render_template("error.html", message=str(e)), 404


@customer_bp.route("/customer/<company>/invoices/export.csv")
def export_invoices_csv(company):
    q = request.args.get("q", "").lower()
    status_filter = request.args.get("status", "all")

    group_name = session.get("group_name") or session.get("company")
    customer_ids = get_customer_ids_by_company(group_name)

    invoice_rows, totals = fetch_invoice_rows(customer_ids)

    filtered = []
    for inv in invoice_rows:
        if q and q not in str(inv["number"]).lower() and q not in str(inv["po"] or "").lower():
            continue
        if status_filter != "all" and inv["status"].lower() != status_filter:
            continue
        filtered.append(inv)

    temp_path = export_invoice_csv(company, filtered, totals, interactive=False)
    with open(temp_path, "r", encoding="utf-8") as f:
        csv_data = f.read()

    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=invoices_{company}.csv"})
