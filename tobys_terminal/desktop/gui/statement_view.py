import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime, date
import sys
import os
import csv
import sqlite3
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from collections import defaultdict

from tobys_terminal.shared.db import get_connection, generate_statement_number
from tobys_terminal.shared.pdf_export import generate_pdf
from tobys_terminal.shared.export_csv import export_statement_csv

# testing webhook deploy
global customer_map, start_entry, end_entry
from tobys_terminal.shared.statement_logic import StatementCalculator  # make sure this is imported
from tobys_terminal.shared.reprint import reprint_statement
from tobys_terminal.shared.maintenance import reset_statements_for_company
from tobys_terminal.shared.brand_ui import apply_brand, zebra_tree
from tobys_terminal.shared.customer_utils import get_company_label, get_company_label_from_row
print("statement_view loaded")


def open_statement_view():
    win = tk.Toplevel()
    win.title("Customer Statement")
    win.geometry("1200x800")
    apply_brand(win)

    ttk.Label(win, text="Customer Statement Viewer",
              style="Header.TLabel").pack(pady=10)

    # Controls Frame
    top_frame = tk.Frame(win)
    top_frame.pack(pady=5)

    # Customer dropdown
    tk.Label(top_frame, text="Customer:", font=("Arial", 11)).grid(row=0, column=0, padx=5)
    customer_combo = ttk.Combobox(top_frame, width=50, state="readonly", font=("Arial", 11))
    customer_combo.grid(row=0, column=1, columnspan=3, padx=5)

    # Date filters
    tk.Label(top_frame, text="Start Date (MM-DD-YYYY):", font=("Arial", 11)).grid(row=1, column=0, padx=5, pady=5, sticky="e")
    start_date_entry = tk.Entry(top_frame, font=("Arial", 11))
    start_date_entry.grid(row=1, column=1)

    tk.Label(top_frame, text="End Date (MM-DD-YYYY):", font=("Arial", 11)).grid(row=1, column=2, padx=5, pady=5, sticky="e")
    end_date_entry = tk.Entry(top_frame, font=("Arial", 11))
    end_date_entry.grid(row=1, column=3)

    # Unpaid only checkbox
    unpaid_var = tk.BooleanVar()
    unpaid_check = tk.Checkbutton(top_frame, text="Unpaid Invoices Only", variable=unpaid_var, font=("Arial", 11))
    unpaid_check.grid(row=2, column=0, columnspan=2, pady=5)



    # Treeview
    tree = ttk.Treeview(
            win,
            columns=("Date", "Type", "Invoice#", "PO #", "Amount", "Status", "Notes")
,
            show="headings",
            style="Sage.Treeview"
    )
    tree.heading("Date", text="Date")
    tree.heading("Type", text="Type")
    tree.heading("Invoice#", text="Inv. #")
    tree.column("Invoice#", width=80)
    tree.heading("Amount", text="Amount")
    tree.heading("Status", text="Status")
    tree.heading("Notes", text="Notes")
    tree.column("Notes", width=250)
    tree.heading("PO #", text="PO #")
    tree.column("PO #", width=120)
    tree.pack(fill="both", expand=True)

    # Totals section
    #total_all_label = tk.Label(win, text="", font=("Arial", 11, "bold"), fg="gray")
    #total_all_label.pack()
    total_filtered_label = tk.Label(win, text="", font=("Arial", 12, "bold"))
    total_filtered_label.pack(pady=5)

    # Load customers
    conn = get_connection()
    cursor = conn.cursor()
   

    # Step 1: Query only customers with invoices or payments
    cursor.execute("""
        SELECT DISTINCT c.id, c.first_name, c.last_name, c.company
        FROM customers c
        LEFT JOIN invoices i ON c.id = i.customer_id
        LEFT JOIN payments p ON c.id = p.customer_id
        WHERE i.invoice_number IS NOT NULL OR p.invoice_number IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()

    # Step 2: Group by company name (or 'No Company')
    company_group = defaultdict(list)
    display_map = {}

    for cid, first, last, company in rows:
        label = company.strip() if company and company.strip() else f"No Company - {first} {last}"
        company_group[label].append(cid)

    # Step 3: Sort and store in dropdown
    sorted_labels = sorted(company_group.keys())
    customer_combo['values'] = sorted_labels

    # Map display label to customer ID list
    customer_group_map = dict(company_group)


    def parse_date(text):
        for fmt in ("%m-%d-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt).date()

            except ValueError:
                continue
        return None

    def parse_date_str(text):
        for fmt in ("%m-%d-%Y", "%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()

            except ValueError:
                continue
        return None

    def fetch_invoice_note(invoice_number):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT notes FROM invoice_tracking WHERE invoice_number = ?", (invoice_number,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] else ""


    def load_statement():
        tree.delete(*tree.get_children())
        selected_name = customer_combo.get()

        if selected_name not in customer_group_map:
            messagebox.showwarning("Invalid Customer", "Please select a valid customer.")
            return

        customer_ids = customer_group_map[selected_name]

        start_date = parse_date(start_date_entry.get())
        end_date = parse_date(end_date_entry.get())

        if (start_date_entry.get() and not start_date) or (end_date_entry.get() and not end_date):
            messagebox.showerror("Invalid Date", "Please enter dates in MM-DD-YYYY format.")
            return



        # Use the updated StatementCalculator
        calc = StatementCalculator(
            customer_ids=customer_ids,
            start_date=start_date,
            end_date=end_date,
            unpaid_only=unpaid_var.get()
        )
        rows, totals = calc.fetch()

        # Display rows
        for row in rows:
            # ... inside the rows loop ...
            dt = row[0].strftime("%m/%d/%Y") if hasattr(row[0], "strftime") else str(row[0])
            po_num = (row[5] if len(row) > 5 and row[1] == "Invoice" else "")
            note = fetch_invoice_note(row[2]) if row[1] == "Invoice" else row[5] if len(row) > 5 else ""
            tree.insert("", "end",
                values=(dt, row[1], row[2], po_num, f"${row[3]:,.2f}", row[4], note)
            )


        zebra_tree(tree)
        # Show totals
        if unpaid_var.get():
            total_filtered_label.config(
                text=f"🧾 Unpaid Invoices Only: Billed ${totals['billed']:,.2f} | Paid $0.00 | Balance (Not Adjusted): ${totals['billed']:,.2f}",
                fg="orange"
            )
        else:
            total_filtered_label.config(
                text=f"✅ TRUE BALANCE: Billed ${totals['billed']:,.2f} | Paid ${totals['paid']:,.2f} | Balance Owed: ${totals['balance']:,.2f}",
                fg="green"
            )

    


    def track_invoices_on_statement(invoice_numbers, statement_number):
        conn = get_connection()
        cursor = conn.cursor()
        skipped = []
        retagged = 0
        inserted = 0

        for inv in invoice_numbers:
            cursor.execute("SELECT statement_number FROM invoice_tracking WHERE invoice_number = ?", (inv,))
            result = cursor.fetchone()

            if result:
                existing_stmt = (result[0] or "").strip()
                if existing_stmt:  # truly assigned elsewhere
                    skipped.append((inv, existing_stmt))
                else:
                    cursor.execute("""
                        UPDATE invoice_tracking
                        SET statement_number = ?, tagged_on = DATE('now')
                        WHERE invoice_number = ?
                    """, (statement_number, inv))
                    retagged += 1
            else:
                cursor.execute("""
                    INSERT INTO invoice_tracking (invoice_number, statement_number, tagged_on)
                    VALUES (?, ?, DATE('now'))
                """, (inv, statement_number))
                inserted += 1

        conn.commit()
        conn.close()

        if skipped:
            print("⚠️ Skipped invoices already assigned to other statements:")
            for inv, stmt in skipped:
                print(f"  Invoice {inv} ➜ Statement {stmt}")
            messagebox.showwarning(
                "Invoice Conflict",
                f"{len(skipped)} invoice(s) were skipped because they were already assigned to a prior statement."
            )

        # Optional: let yourself know how many were re-tagged vs inserted
        print(f"🔁 Re-tagged {retagged}, 🆕 Inserted {inserted}, ⏭️ Skipped {len(skipped)}")





    def handle_export_pdf():
        selected_name = customer_combo.get()
        if not selected_name:
            messagebox.showerror("Export Failed", "No customer selected.")
            return

        customer_ids = customer_group_map.get(selected_name)
        if not customer_ids:
            messagebox.showerror("Export Failed", "Customer ID not found.")
            return

        company_label = get_company_label(first, last, company)
        statement_number = generate_statement_number(
            customer_id=customer_ids,
            start_date=start_date_entry.get().strip(),
            end_date=end_date_entry.get().strip(),
            company_label=company_label
        )

        # Recompute from source so we have payment method/reference
        start_d = parse_date_str(start_date_entry.get().strip())
        end_d   = parse_date_str(end_date_entry.get().strip())

        calc = StatementCalculator(
            customer_ids=customer_ids,
            start_date=start_d,
            end_date=end_d,
            unpaid_only=unpaid_var.get()
        )
        raw_rows, totals = calc.fetch()  # includes payment rows with method & reference:contentReference[oaicite:2]{index=2}

        # Add Nickname for invoice rows (bulk lookup to avoid N queries)
        inv_nums = [r[2] for r in raw_rows if r[1] == "Invoice"]
        nickname_map = {}
        if inv_nums:
            conn = get_connection()
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in inv_nums)
            cursor.execute(f"SELECT invoice_number, nickname FROM invoices WHERE invoice_number IN ({placeholders})", tuple(inv_nums))
            nickname_map = dict(cursor.fetchall())
            conn.close()

        # Build export rows in the format the PDF expects:
        # (date, type, invoice#, nickname, amount, status_or_paymentinfo)
        export_rows = []
        for row in raw_rows:
            if row[1] == "Invoice":
                dt, _, inv, amt, paid_flag, po_num = row
                nickname = nickname_map.get(inv)
                status = "Paid" if str(paid_flag).strip().lower() in {"yes","true","paid","y","1"} else "Unpaid"
                export_rows.append((dt, "Invoice", inv, po_num, nickname, float(amt), status))
            else:  # Payment row
                dt, _, inv, amt, method, ref, _note = row
                payload = f"{(method or '').strip()} {(ref or '').strip()}".strip()
                export_rows.append((dt, "Payment", inv, None, None, float(amt), payload))

        # Tag invoices to statement
        invoice_numbers = [r[2] for r in export_rows if r[1] == "Invoice"]
        track_invoices_on_statement(invoice_numbers, statement_number)

        # Export
        generate_pdf(
            customer_name=selected_name,
            rows=export_rows,
            totals=totals,  # already matches the rows we’re exporting:contentReference[oaicite:3]{index=3}:contentReference[oaicite:4]{index=4}
            start_date=start_date_entry.get().strip(),
            end_date=end_date_entry.get().strip(),
            nickname=None,
            statement_number=statement_number
        )
        messagebox.showinfo("Export Complete", f"PDF exported for {selected_name}.")

    

    # --- add this function next to handle_export_pdf() ---
    def handle_export_csv():
        try:
            selected_name = customer_combo.get().strip()
            if not selected_name:
                messagebox.showerror("Export Failed", "No customer selected.")
                return

            customer_ids = customer_group_map.get(selected_name)
            if not customer_ids:
                messagebox.showerror("Export Failed", "Customer ID not found.")
                return

            # Parse date range and unpaid filter just like PDF export
            start_s = start_date_entry.get().strip()
            end_s   = end_date_entry.get().strip()
            start_d = parse_date_str(start_s) if start_s else None
            end_d   = parse_date_str(end_s) if end_s else None

            calc = StatementCalculator(
                customer_ids=customer_ids,
                start_date=start_d,
                end_date=end_d,
                unpaid_only=unpaid_var.get()
            )
            raw_rows, totals = calc.fetch()  # includes both Invoice and Payment rows w/ method+ref

            # Build nickname map for invoice rows to match the PDF/Treeview
            inv_nums = [r[2] for r in raw_rows if r[1] == "Invoice"]
            nickname_map = {}
            if inv_nums:
                conn = get_connection()
                cur = conn.cursor()
                placeholders = ",".join("?" for _ in inv_nums)
                cur.execute(f"""
                    SELECT invoice_number, nickname
                    FROM invoices
                    WHERE invoice_number IN ({placeholders})
                """, tuple(inv_nums))
                nickname_map = dict(cur.fetchall())
                conn.close()

            # Merge payments into invoice "Status" like the PDF:
            # rows structure from your calculator (expected):
            # Invoice rows: (date, "Invoice", invoice#, amount, paid_flag/boolean-or-string, ...)
            # Payment rows: (date, "Payment", invoice#, amount, method, reference, note)
            from collections import defaultdict
            pay_index = defaultdict(list)
            for dt, t, inv, *rest in raw_rows:
                if str(t) == "Payment":
                    # rest = [amount, method, reference, note] per your calculator
                    # We only need: "METHOD REF"
                    try:
                        _, method, ref, *_ = rest
                    except Exception:
                        method, ref = "", ""
                    label = f"{(method or '').strip()} {(ref or '').strip()}".strip()
                    if label:
                        pay_index[inv].append(label)

            # Compose invoice-only export rows (like the PDF table)
            export_rows = []
            for row in raw_rows:
                if str(row[1]) != "Invoice":
                    continue
                dt, _, inv, amt, paid_flag, po_num = row
                date_str = dt.strftime("%m/%d/%Y") if hasattr(dt, "strftime") else str(dt)
                nickname = nickname_map.get(inv) or ""
                amount = float(amt)

                pays = pay_index.get(inv, [])
                if pays:
                    status = f"Paid - {pays[0]}" + (f" (+{len(pays)-1} more)" if len(pays) > 1 else "")
                else:
                    status = "Paid" if str(paid_flag).strip().lower() in {"yes","true","paid","y","1"} else "Unpaid"

                export_rows.append([date_str, inv, po_num or "", nickname, f"{amount:.2f}", status])

            if not export_rows:
                messagebox.showinfo("Export CSV", "No rows to export for this selection.")
                return

            # Ask where to save

            default_name = f"statement_{selected_name.replace(' ', '_')}_{(start_s or 'start')}_to_{(end_s or 'end')}.csv"
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=default_name,
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if not path:
                return

            export_statement_csv(
                selected_name=selected_name,
                start_s=start_s,
                end_s=end_s,
                export_rows=export_rows,
                totals=totals,
                interactive=True,
                user_selected_path=path
            )

            messagebox.showinfo("Export CSV", f"Saved: {path}")

        except Exception as e:
            messagebox.showerror("Export Failed", f"{type(e).__name__}: {e}")

    def prompt_reprint():
        stmt_num = simpledialog.askstring("Reprint Statement", "Enter Statement Number to reprint:")
        if not stmt_num:
            return
        try:
            reprint_statement(stmt_num.strip())
            messagebox.showinfo("Reprint", f"Statement {stmt_num} reprinted successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def reset_selected_customer():
        selected_name = customer_combo.get().strip()
        if not selected_name:
            messagebox.showerror("No Customer", "Please select a customer first.")
            return

        # Safety confirmation
        if not messagebox.askyesno(
            "Confirm Reset",
            f"This will unassign all statement numbers for:\n\n{selected_name}\n\n"
            "Notes on invoices will be preserved.\n\nProceed?"
        ):
            return

        try:
            # Exact match is safest. Use fuzzy_match=True if you like prefix matching (e.g., “Harlestons” vs “Harlestons, LLC”)
            cleared, headers = reset_statements_for_company(
                company_name=selected_name,
                fuzzy_match=False,
                delete_statement_headers=True
            )

            messagebox.showinfo(
                "Reset Complete",
                f"Cleared statement assignment on {cleared} invoice(s)\n"
                f"Removed {headers} old statement header(s)\n\n"
                "Now click ‘Load Statement’ and then ‘Export to PDF’ to re-generate fresh statements."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Reset failed:\n{e}")


    def add_invoice_note():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select one or more invoice rows.")
            return

        invoice_numbers = []
        for item_id in selected_items:
            item = tree.item(item_id)
            row_type = item["values"][1]
            if row_type != "Invoice":
                continue  # skip if it's a Payment row
            invoice_numbers.append((item_id, item["values"][2]))  # (Treeview ID, Invoice #)

        if not invoice_numbers:
            messagebox.showwarning("No Invoices Selected", "Please select one or more invoice rows.")
            return

        # Ask for the note to apply to all
        note = simpledialog.askstring("Add/Edit Note", "Enter the note for selected invoices:")
        if note is None:
            return  # User canceled

        # Update DB
        conn = get_connection()
        cursor = conn.cursor()

        for _, invoice_number in invoice_numbers:
            cursor.execute("""
                INSERT INTO invoice_tracking (invoice_number, notes)
                VALUES (?, ?)
                ON CONFLICT(invoice_number) DO UPDATE SET notes = excluded.notes
            """, (invoice_number, note))

        conn.commit()
        conn.close()

        # Update UI
        for item_id, _ in invoice_numbers:
            tree.set(item_id, column="Notes", value=note)

        messagebox.showinfo("Note Saved", f"Note applied to {len(invoice_numbers)} invoice(s).")

    # optional: a subtle divider before the table
    ttk.Separator(win, orient="horizontal").pack(fill="x", pady=(0, 6))

    # --- TOOLBAR (replace your old stacked buttons with this block) ---
    toolbar = ttk.Frame(win, style="Card.TFrame", padding=(0, 4))
    toolbar.pack(fill="x", pady=(2, 8))

    # left-aligned action buttons
    ttk.Button(toolbar, text="📄 Generate", style="Primary.TButton",
            command=load_statement  # <-- use your existing handler
    ).pack(side="left", padx=(0, 6))

    ttk.Button(toolbar, text="💾 Export to PDF", style="Primary.TButton",
            command=handle_export_pdf  # <-- your handler
    ).pack(side="left", padx=6)

    ttk.Button(toolbar, text="📝 Add/Edit Note", style="Primary.TButton",
            command=add_invoice_note
    ).pack(side="left", padx=6)

    ttk.Button(toolbar, text="📄 Reprint Statement", style="Accent.TButton",
            command=prompt_reprint  # <-- your handler
    ).pack(side="left", padx=6)

    ttk.Button(toolbar, text="💾 Export CSV", style="Accent.TButton",
            command=handle_export_csv  # <-- your handler
    ).pack(side="left", padx=6)

    ttk.Button(toolbar, text="🧹 Reset ",style="Accent.TButton",
            command=reset_selected_customer
    ).pack(side="left", padx=6)

    # right-aligned close
    ttk.Button(toolbar, text="Close", style="Primary.TButton",
            command=win.destroy
    ).pack(side="right", padx=(6, 0))



    
