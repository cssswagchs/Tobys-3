# 📁 routes/dashboard.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from collections import defaultdict
import string
from tobys_terminal.shared.db import get_connection

dashboard_bp = Blueprint("dashboard", __name__)

def fetch_customers(customer_type=None):
    conn = get_connection()
    cur = conn.cursor()
    if customer_type:
        cur.execute("""
            SELECT DISTINCT company FROM customers
            WHERE TRIM(company) != '' AND LOWER(customer_type) = LOWER(?)
            ORDER BY company
        """, (customer_type,))
    else:
        cur.execute("""
            SELECT DISTINCT company FROM customers
            WHERE TRIM(company) != ''
            ORDER BY company
        """)
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

@dashboard_bp.route('/')
def index():
    if session.get('role') == 'admin':
        # Redirect to admin dashboard
        return redirect(url_for('admin.dashboard'))
        company = session.get("company")
        if not company:
            return redirect(url_for("auth.login"))
        flash("This page is for admins only.")
        return redirect(url_for("customer.customer_portal", company=company))


    customer_type = request.args.get("type")
    filter_letter = request.args.get("letter", "").upper()
    companies = fetch_customers(customer_type)

    grouped = defaultdict(list)
    for name in companies:
        first_letter = (name[0].upper() if name else '#')
        grouped[first_letter].append(name)

    grouped = dict(sorted(grouped.items()))
    visible_group = {filter_letter: grouped.get(filter_letter, [])} if filter_letter else grouped

    return render_template("index.html", grouped=visible_group, filter_letter=filter_letter, filter_type=customer_type, letters=string.ascii_uppercase)
