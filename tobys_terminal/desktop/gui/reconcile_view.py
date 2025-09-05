import sys
import os

from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.statement_logic import StatementCalculator
from tobys_terminal.shared.brand_ui import apply_brand, zebra_tree

def open_reconcile_view():
    win = tk.Toplevel()
    win.title("Payment Reconciliation")
    win.geometry("1100x550")
    apply_brand(win)

    # Inside open_reconcile_view()

    # Input frame for search bar and dropdown
    input_frame = tk.Frame(win)
    input_frame.pack(pady=10)

    # Label
    tk.Label(input_frame, text="Search:").pack(side="left", padx=5)

    # ✅ Entry box for date or reference
    search_entry = tk.Entry(input_frame, width=20)
    search_entry.pack(side="left", padx=5)

    # ✅ Dropdown to select search mode
    search_type = tk.StringVar(value="Date")
    search_menu = ttk.Combobox(
        input_frame,
        textvariable=search_type,
        values=["Date", "Reference"],
        width=10,
        state="readonly"
    )
    search_menu.pack(side="left", padx=5)

    # ✅ Search button with lambda that now sees `search_entry`
    search_btn = tk.Button(
        input_frame,
        text="Search",
        command=lambda: run_search(search_entry.get(), search_type.get())
    )
    search_btn.pack(side="left", padx=5)


    # Treeview for results
    tree = ttk.Treeview(
        win,
        columns=("Date", "Invoice#", "Amount", "Method", "Memo", "Reconciled", "Notes"),
        show="headings",
        style="Sage.Treeview" 
    )
    for col in tree["columns"]:
        tree.heading(col, text=col)
        tree.column(col, width=130)
    tree.column("Notes", width=250)
    tree.tag_configure("reconciled", background="#ccffcc")
    tree.pack(expand=True, fill="both", padx=10, pady=10)

    # Reconcile button
    def mark_selected_reconciled():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select one or more payments to reconcile.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        for item_id in selected:
            invoice_number = tree.item(item_id)["values"][1]
            cursor.execute("""
                INSERT INTO payment_tracking (invoice_number, reconciled)
                VALUES (?, 1)
                ON CONFLICT(invoice_number) DO UPDATE SET reconciled = 1
            """, (invoice_number,))
        conn.commit()
        conn.close()
        for item_id in selected:
            # Mark visually
            tree.set(item_id, "Reconciled", "✔")
            tree.item(item_id, tags=("reconciled",))

        messagebox.showinfo("Reconciled", "Selected payments marked as reconciled.")



    # Add note button
    def add_note_to_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select one or more payments to add a note.")
            return

        # Ask once
        note = simpledialog.askstring("Add/Edit Note", "Enter your note for selected payments:")
        if note is None:
            return  # cancelled

        conn = get_connection()
        cursor = conn.cursor()

        updated = 0

        for item_id in selected:
            values = tree.item(item_id)["values"]
            if len(values) < 2:
                continue
            invoice_number = values[1]

            cursor.execute("""
                INSERT INTO payment_tracking (invoice_number, notes)
                VALUES (?, ?)
                ON CONFLICT(invoice_number) DO UPDATE SET notes = excluded.notes
            """, (invoice_number, note))

            # Update UI
            tree.set(item_id, column="Notes", value=note)
            updated += 1

        conn.commit()
        conn.close()

        messagebox.showinfo("Note Saved", f"Note added to {updated} payment(s).")




    def show_total():
        total = 0.0
        for child in tree.get_children():
            # Get the amount column (column index 2, or name "Amount")
            value = tree.item(child)["values"][2]  # should be like "$205.00"
            if isinstance(value, str):
                value = value.replace("$", "").replace(",", "").strip()
            try:
                total += float(value)
            except ValueError:
                continue  # skip bad rows

        messagebox.showinfo("Total", f"Total of visible payments: ${total:,.2f}")






    button_frame = tk.Frame(win)
    button_frame.pack(pady=5)

    tk.Button(button_frame, text="✔ Mark Reconciled", command=mark_selected_reconciled, width=20).grid(row=0, column=0, padx=5)
    tk.Button(button_frame, text="📝 Add/Edit Note", command=add_note_to_selected, width=20).grid(row=0, column=1, padx=5)
    tk.Button(button_frame, text="💰 Show Total", command=show_total, width=20).grid(row=0, column=2, padx=5)



    def run_search(query: str, mode: str):

        tree.delete(*tree.get_children())
        q = query.strip()
        # print(f"🔍 Reconciliation search: {q} (mode: {mode})")

        rows = []

        if mode == "Date":
            parsed_date = None
            for fmt in ("%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    parsed_date = datetime.strptime(q, fmt).date()
                    break
                except ValueError:
                    continue

            if not parsed_date:
                messagebox.showerror("Invalid Date", "Use MM-DD-YYYY or YYYY-MM-DD format.")
                return

            calc = StatementCalculator(
                start_date=parsed_date,
                end_date=parsed_date,
                unpaid_only=False,
                unreconciled_only=False
            )
            rows, _ = calc.fetch()

            # Get tracking info
            conn = get_connection()
            cursor = conn.cursor()
            tracking = {}
            for r in rows:
                inv = r[2]
                cursor.execute("SELECT reconciled, notes FROM payment_tracking WHERE invoice_number = ?", (inv,))
                trow = cursor.fetchone()
                if trow:
                    tracking[inv] = {"reconciled": trow[0], "notes": trow[1]}
            conn.close()

            for row in rows:
                if row[1] != "Payment":
                    continue
                tx_date, _, inv_num, amount, method, reference, note = row
                date_str = tx_date.strftime("%Y-%m-%d") if hasattr(tx_date, "strftime") else str(tx_date)
                rec = tracking.get(inv_num, {}).get("reconciled")
                note = tracking.get(inv_num, {}).get("notes") or ""
                is_rec = str(rec).strip().lower() in {"yes", "true", "1"}
                check = "✔" if is_rec else ""
                tags = ("reconciled",) if is_rec else ()
                tree.insert("", "end", values=(
                    date_str, inv_num, f"${amount:,.2f}", method, reference or "", check, note
                ), tags=tags)

        elif mode == "Reference":
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    p.transaction_date,
                    p.invoice_number,
                    p.amount,
                    p.payment_method,
                    p.reference,
                    t.reconciled,
                    t.notes
                FROM payments_clean p
                LEFT JOIN payment_tracking t ON p.invoice_number = t.invoice_number
                WHERE p.reference = ?
            """, (q,))
            raw = cursor.fetchall()
            conn.close()

            for row in raw:
                tx_date, inv_num, amount, method, reference, rec, note = row
                date_str = tx_date.strftime("%Y-%m-%d") if hasattr(tx_date, "strftime") else str(tx_date)
                is_rec = str(rec).strip().lower() in {"yes", "true", "1"}
                check = "✔" if is_rec else ""
                tags = ("reconciled",) if is_rec else ()
                tree.insert("", "end", values=(
                    date_str, inv_num, f"${amount:,.2f}", method, reference, check, note
                ), tags=tags)
        zebra_tree(tree)
        # print(f"✅ Found {len(tree.get_children())} result(s).")






