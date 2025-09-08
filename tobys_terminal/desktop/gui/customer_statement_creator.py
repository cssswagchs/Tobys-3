import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import re
import sys
import subprocess

from tkcalendar import DateEntry

from tobys_terminal.shared.db import get_connection, generate_statement_number
from tobys_terminal.shared.statement_logic import StatementCalculator
from tobys_terminal.shared.pdf_export import generate_pdf
from tobys_terminal.shared.customer_utils import get_customer_ids_by_company

def open_customer_statement_creator(preselect=""):
    win = tk.Toplevel()
    win.title("Customer Statement Creator")
    win.geometry("900x600")
    win.resizable(True, True)

    # Header
    header = ttk.Label(win, text=f"Statement Creator - {preselect}", font=("Arial", 14, "bold"))
    header.pack(pady=10)

    # Form frame
    form = ttk.Frame(win)
    form.pack(pady=5)

    # Create date entries directly like in the test file
    ttk.Label(form, text="Start Date:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    
    # Create DateEntry directly with simple styling
    start_entry = DateEntry(
        form,
        width=12,
        background="darkgreen",  # Use simple color names first
        foreground="white",
        borderwidth=2,
        date_pattern='mm/dd/yyyy'
    )
    start_entry.grid(row=0, column=1, padx=5)

    ttk.Label(form, text="End Date:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
    
    # Create DateEntry directly with simple styling
    end_entry = DateEntry(
        form,
        width=12,
        background="darkgreen",  # Use simple color names first
        foreground="white",
        borderwidth=2,
        date_pattern='mm/dd/yyyy'
    )
    end_entry.grid(row=0, column=3, padx=5)

    unpaid_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(form, text="Unpaid Invoices Only", variable=unpaid_var).grid(row=1, column=0, columnspan=2, padx=5, sticky="w")

    # Buttons
    btn_frame = ttk.Frame(win)
    btn_frame.pack(pady=5)

    tree = ttk.Treeview(win, columns=("Date", "Type", "Invoice", "PO", "Amount", "Balance"), show="headings")
    for col in ("Date", "Type", "Invoice", "PO", "Amount", "Balance"):
        tree.heading(col, text=col)
        tree.column(col, width=100)

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
    # Your existing load_data function
        tree.delete(*tree.get_children())
        ids = get_customer_ids_by_company(preselect)
        if not ids:
            messagebox.showerror("Missing", f"No customer ID found for {preselect}")
            return

        start = start_entry.get_date() if start_entry.get() else None
        end = end_entry.get_date() if end_entry.get() else None
        
        # For statements, we want ALL orders regardless of status
        calc = StatementCalculator(
            customer_ids=ids,
            start_date=start,
            end_date=end,
            unpaid_only=unpaid_var.get(),
            include_hidden=True  # Make sure your StatementCalculator has this parameter
        )
        rows, totals = calc.fetch()
    
    # Rest of your function...


        for row in rows:
            dt = row[0].strftime("%m/%d/%Y") if hasattr(row[0], "strftime") else str(row[0])
            typ = row[1]
            inv = row[2]
            po = row[5] if len(row) > 5 and typ == "Invoice" else ""
            amt = f"${float(row[3]):,.2f}"
            bal = f"${float(row[4]):,.2f}" if row[4] else "$0.00"
            tree.insert("", "end", values=(dt, typ, inv, po, amt, bal))

        total_label.config(text=f"Total: ${totals['total']:,.2f} | Outstanding: ${totals['outstanding']:,.2f}")

    def export_to_pdf():
        ids = get_customer_ids_by_company(preselect)
        if not ids:
            messagebox.showerror("Missing", f"No customer ID found for {preselect}")
            return

        start = start_entry.get_date()
        end = end_entry.get_date()
        
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
            start_date=start.strftime("%m/%d/%Y"),
            end_date=end.strftime("%m/%d/%Y"),
            company_label=preselect,
            customer_ids_list=ids
        )

        # Export to PDF
        generate_pdf(
            customer_name=preselect,
            rows=export_rows,
            totals=totals,
            start_date=start.strftime("%m/%d/%Y"),
            end_date=end.strftime("%m/%d/%Y"),
            statement_number=statement_number
        )

        # Auto-open the PDF
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', preselect.strip())
        export_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'exports', 'statements', safe_name))
        for fname in os.listdir(export_dir):
            if fname.startswith(statement_number):
                subprocess.Popen(["start", "", os.path.join(export_dir, fname)], shell=True)
                break

    ttk.Button(btn_frame, text="Load Data", command=load_data).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Export PDF", command=export_to_pdf).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Close", command=win.destroy).pack(side="left", padx=5)

    # Pre-load data if preselect is provided
    if preselect:
        load_data()

    win.focus_set()
