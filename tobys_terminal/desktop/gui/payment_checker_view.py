# gui/payment_checker_view.py
import sys
import os

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.statement_logic import StatementCalculator
from tobys_terminal.shared.brand_ui import apply_brand, zebra_tree

def open_payment_checker():
    win = tk.Toplevel()
    win.title("Payment Integrity Checker")
    win.geometry("1000x600")
    apply_brand(win)

    ttk.Label(win, text="Payment Integrity Checker",
              style="Header.TLabel").pack(pady=10)

    # Customer selector
    top_frame = tk.Frame(win)
    top_frame.pack(pady=5)

    tk.Label(top_frame, text="Customer:", font=("Arial", 11)).grid(row=0, column=0, padx=5)

    customer_combo = ttk.Combobox(top_frame, width=60, state="readonly", font=("Arial", 11))
    customer_combo.grid(row=0, column=1, padx=5)

    mismatch_only_var = tk.BooleanVar()
    tk.Checkbutton(top_frame, text="Show Only Mismatches", variable=mismatch_only_var).grid(row=0, column=2, padx=5)

    hide_unpaid_var = tk.BooleanVar()
    tk.Checkbutton(top_frame, text="Hide Truly Unpaid", variable=hide_unpaid_var).grid(row=0, column=3, padx=5)


    # Treeview setup
    columns = ("Invoice #", "Invoice Total", "Paid Flag", "Actual Paid", "Difference", "Status")
    tree = ttk.Treeview(win, columns=columns, show="headings", style="Sage.Treeview")


    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=140)
    tree.column("Invoice #", width=180)

    tree.pack(expand=True, fill="both", padx=10, pady=10)

    # Load customers
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT c.id, c.first_name, c.last_name, c.company
        FROM customers c
        LEFT JOIN invoices i ON c.id = i.customer_id
        WHERE i.invoice_number IS NOT NULL
    """)
    customers = cursor.fetchall()
    conn.close()

    customer_dict = {}
    display_list = []

    for cid, first, last, company in customers:
        label = company.strip() if company and company.strip() else f"No Company - {first} {last}"
        if label not in customer_dict:
            customer_dict[label] = []
        customer_dict[label].append(cid)
        if label not in display_list:
            display_list.append(label)

    # Build sorted, case-insensitive customer list
    sorted_customers = sorted(display_list, key=lambda name: name.strip().lower())

    # Prepend "All Customers" so user can run checker without filtering
    customer_combo["values"] = ["All Customers"] + sorted_customers

    # Optional: set default selection to "All Customers"
    customer_combo.current(0)



    def load_checker():
        tree.delete(*tree.get_children())
        selected = customer_combo.get()
        if selected not in customer_dict:
            messagebox.showwarning("Invalid", "Please select a valid customer.")
            return

        customer_ids = customer_dict[selected]

        calc = StatementCalculator(customer_ids=customer_ids, unpaid_only=False)
        rows, _ = calc.fetch()

        conn = get_connection()
        cursor = conn.cursor()

        for row in rows:
            if row[1] != "Invoice":
                continue

            inv_num = row[2]
            invoice_total = row[3]
            paid_flag = row[4]

            cursor.execute("""
                SELECT SUM(amount) FROM payments_clean
                WHERE invoice_number = ?
            """, (inv_num,))
            paid_result = cursor.fetchone()
            actual_paid = paid_result[0] if paid_result and paid_result[0] else 0.0

            difference = invoice_total - actual_paid

            # Status logic
            if paid_flag.lower() in {"yes", "true", "paid"} and actual_paid == 0:
                status = "❌ Paid Flag True, No $"
            elif difference == 0:
                status = "✅ Fully Paid"
            elif difference < 0:
                status = "🔴 Overpaid"
            elif actual_paid > 0:
                status = "🟠 Partial"
            else:
                status = "🟡 Unpaid"
            if mismatch_only_var.get() and status == "✅ Fully Paid":
                continue  # Skip this one unless it's a mismatch
            if hide_unpaid_var.get() and status == "🟡 Unpaid":
                continue
            tree.insert("", "end", values=(
                inv_num,
                f"${invoice_total:,.2f}",
                paid_flag,
                f"${actual_paid:,.2f}",
                f"${difference:,.2f}",
                status
            ))
        zebra_tree(tree)
        conn.close()

    tk.Button(win, text="🕵️ Check Payments", command=load_checker).pack(pady=10)

