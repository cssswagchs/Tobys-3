import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import re
import sys
import subprocess

from tobys_terminal.shared.db import get_connection, generate_statement_number
from tobys_terminal.shared.statement_logic import StatementCalculator
from tobys_terminal.shared.pdf_export import generate_pdf
from tobys_terminal.shared.customer_utils import get_customer_ids_by_company

def open_customer_statement_creator(preselect):
    win = tk.Toplevel()
    win.title(f"Generate Statement – {preselect}")
    win.geometry("900x600")
    win.grab_set()
    ttk.Label(win, text=f"Generate Statement for: {preselect}", font=("Arial", 14, "bold")).pack(pady=10)

    # Date filter section
    form = ttk.Frame(win)
    form.pack(pady=5)

    ttk.Label(form, text="Start Date (MM/DD/YYYY):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    start_entry = ttk.Entry(form)
    start_entry.grid(row=0, column=1, padx=5)

    ttk.Label(form, text="End Date (MM/DD/YYYY):").grid(row=0, column=2, padx=5, pady=5, sticky="e")
    end_entry = ttk.Entry(form)
    end_entry.grid(row=0, column=3, padx=5)

    unpaid_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(form, text="Unpaid Invoices Only", variable=unpaid_var).grid(row=1, column=0, columnspan=2, padx=5, sticky="w")

    # Treeview
    tree = ttk.Treeview(win, columns=("Date", "Type", "Invoice", "PO", "Amount", "Status"), show="headings")
    tree.heading("Date", text="Date")
    tree.heading("Type", text="Type")
    tree.heading("Invoice", text="Invoice #")
    tree.heading("PO", text="PO #")
    tree.heading("Amount", text="Amount")
    tree.heading("Status", text="Status")
    tree.pack(fill="both", expand=True, pady=10, padx=10)

    total_label = ttk.Label(win, text="", font=("Arial", 11, "bold"))
    total_label.pack()

    def parse_date(text):
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text.strip(), fmt).date()
            except:
                continue
        return None

    def load_data():
        tree.delete(*tree.get_children())
        ids = get_customer_ids_by_company(preselect)
        if not ids:
            messagebox.showerror("Missing", f"No customer ID found for {preselect}")
            return

        start = parse_date(start_entry.get())
        end = parse_date(end_entry.get())
        if (start_entry.get() and not start) or (end_entry.get() and not end):
            messagebox.showerror("Invalid Date", "Please use MM/DD/YYYY format.")
            return

        calc = StatementCalculator(
            customer_ids=ids,
            start_date=start,
            end_date=end,
            unpaid_only=unpaid_var.get()
        )
        rows, totals = calc.fetch()

        for row in rows:
            dt = row[0].strftime("%m/%d/%Y") if hasattr(row[0], "strftime") else str(row[0])
            typ = row[1]
            inv = row[2]
            po = row[5] if len(row) > 5 and typ == "Invoice" else ""
            amt = f"${float(row[3]):,.2f}"
            status = row[4]
            tree.insert("", "end", values=(dt, typ, inv, po, amt, status))

        total_label.config(
            text=f"Billed: ${totals['billed']:,.2f} | Paid: ${totals['paid']:,.2f} | Balance: ${totals['balance']:,.2f}"
        )

    def export_and_close():
        ids = get_customer_ids_by_company(preselect)
        if not ids:
            messagebox.showerror("Missing", f"No customer ID found for {preselect}")
            return

        start_text = start_entry.get().strip()
        end_text = end_entry.get().strip()
        start = parse_date(start_text)
        end = parse_date(end_text)

        if not start or not end:
            messagebox.showerror("Missing Dates", "Please enter valid start and end dates.")
            return

        # Fetch data again
        calc = StatementCalculator(
            customer_ids=ids,
            start_date=start,
            end_date=end,
            unpaid_only=unpaid_var.get()
        )
        rows, totals = calc.fetch()

        # Convert to export format
        export_rows = []
        for row in rows:
            dt, typ, inv, amt, status, *rest = row
            po = rest[1] if len(rest) > 1 and typ == "Invoice" else None
            export_rows.append((dt, typ, inv, po, None, float(amt), status))

        # Generate statement number
        statement_number = generate_statement_number(
            customer_id=ids,
            start_date=start_text,
            end_date=end_text,
            company_label=preselect,
            customer_ids_list=ids
        )

        # Export to PDF
        generate_pdf(
            customer_name=preselect,
            rows=export_rows,
            totals=totals,
            start_date=start_text,
            end_date=end_text,
            statement_number=statement_number
        )

        # Auto-open the PDF
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', preselect.strip())
        export_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'exports', 'statements', safe_name))
        for fname in os.listdir(export_dir):
            if fname.startswith(statement_number):
                subprocess.Popen(["start", "", os.path.join(export_dir, fname)], shell=True)
                break

        messagebox.showinfo("Done", f"Statement {statement_number} generated and opened.")
        win.destroy()

    # Buttons
    button_frame = ttk.Frame(win)
    button_frame.pack(pady=10)

    ttk.Button(button_frame, text="📄 Preview Invoices", command=load_data).pack(side="left", padx=10)
    ttk.Button(button_frame, text="💾 Generate Statement", command=export_and_close).pack(side="left", padx=10)
    ttk.Button(button_frame, text="Cancel", command=win.destroy).pack(side="right", padx=10)
