import sys
import os
import threading, queue
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.brand_ui import apply_brand, zebra_tree
from tobys_terminal.shared.reprint import reprint_statement
from tobys_terminal.shared.statement_logic import void_statement

DB_NAME = "terminal.db"


def open_statement_register():
    win = tk.Toplevel()
    win.title("Statement Register")
    win.geometry("1100x620")
    apply_brand(win)

    ttk.Label(win, text="Statement Register", style="Header.TLabel").pack(pady=(10, 6))

    # ---- Top controls
    top = ttk.Frame(win)
    top.pack(fill="x", padx=10, pady=(0, 8))

    ttk.Label(top, text="Customer:").pack(side="left", padx=(0, 6))
    customer_combo = ttk.Combobox(top, width=50, state="readonly")
    customer_combo.pack(side="left")

    prog = ttk.Progressbar(top, mode="indeterminate", length=120)
    prog.pack(side="left", padx=8)


    # ==== Helpers (capture globals via default args) ====
    def load_customers():
        conn = get_connection()
        cur = conn.cursor()
        # Same grouping strategy you already use in Statement View
        cur.execute("""
            SELECT DISTINCT c.id, c.first_name, c.last_name, c.company
            FROM customers c
            LEFT JOIN invoices i ON c.id = i.customer_id
            LEFT JOIN payments p ON c.id = p.customer_id
            WHERE i.invoice_number IS NOT NULL OR p.invoice_number IS NOT NULL
        """)
        rows = cur.fetchall()
        conn.close()

        from collections import defaultdict
        company_group = defaultdict(list)
        for cid, first, last, company in rows:
            label = company.strip() if company and company.strip() else f"No Company - {first} {last}"
            company_group[label].append(cid)

        customer_combo['values'] = sorted(company_group.keys())
        return dict(company_group)

    customer_group_map = load_customers()

    import threading, queue
    q = queue.Queue()

    def run_query(ids, _get_connection=get_connection):
        try:
            conn = _get_connection()
            cur = conn.cursor()

            in_placeholders = ",".join("?" for _ in ids)
            like_clause = " OR ".join(
                "(s.customer_ids_text IS NOT NULL AND (',' || s.customer_ids_text || ',') LIKE '%,' || ? || ',%')"
                for _ in ids
            )
            where_clause = f"(s.customer_id IN ({in_placeholders}) OR {like_clause})"
            params = tuple(ids) + tuple(str(x) for x in ids)

            sql = f"""
            WITH pay AS (
              SELECT invoice_number, SUM(amount) AS paid
              FROM payments_clean
              GROUP BY invoice_number
            )
            SELECT
              s.statement_number,
              s.generated_on,
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
            GROUP BY s.statement_number, s.generated_on, s_start, s_end
            ORDER BY s.generated_on DESC
            """
            cur.execute(sql, params)
            rows = cur.fetchall()
            conn.close()

            formatted = []
            for stmt, gen_on, s_date, e_date, cnt, billed, paid in rows:
                billed = billed or 0.0
                paid   = paid   or 0.0
                bal    = billed - paid
                status = "Paid" if abs(bal) < 0.005 else ("Credit" if bal < 0 else "Due")
                period = f"{s_date or '—'} to {e_date or '—'}"
                formatted.append((stmt, gen_on or "", period, cnt or 0,
                                  f"${billed:,.2f}", f"${paid:,.2f}", f"${bal:,.2f}", status))

            CHUNK = 300
            for i in range(0, len(formatted), CHUNK):
                q.put(("chunk", formatted[i:i+CHUNK]))
            q.put(("done", None))
        except Exception as e:
            q.put(("error", e))

    def pump_queue():
        try:
            while True:
                kind, payload = q.get_nowait()
                if kind == "chunk":
                    for row in payload:
                        tree.insert("", "end", values=row)
                elif kind == "done":
                    prog.stop()
                    btn_load.state(["!disabled"])
                    try:
                        zebra_tree(tree)
                    except Exception:
                        pass
                    return
                elif kind == "error":
                    prog.stop()
                    btn_load.state(["!disabled"])
                    messagebox.showerror("Error", str(payload))
                    return
        except queue.Empty:
            pass
        win.after(40, pump_queue)

    # ---- Table
    columns = ("Statement #", "Generated", "Period", "Invoices", "Billed", "Paid", "Balance", "Status")
    tree = ttk.Treeview(win, columns=columns, show="headings", style="Sage.Treeview")
    for c in columns:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor="w")
    tree.column("Period", width=220)
    tree.column("Invoices", width=90, anchor="center")
    tree.column("Billed", width=110, anchor="e")
    tree.column("Paid", width=110, anchor="e")
    tree.column("Balance", width=110, anchor="e")
    tree.pack(fill="both", expand=True, padx=10, pady=(0, 8))



    def load_register_async():
        tree.delete(*tree.get_children())
        name = (customer_combo.get() or "").strip()
        if name not in customer_group_map:
            messagebox.showwarning("Pick a customer", "Please choose a valid customer.")
            return
        ids = list(customer_group_map[name])
        btn_load.state(["disabled"])
        prog.start(12)
        threading.Thread(target=run_query, args=(ids,), daemon=True).start()
        win.after(60, pump_queue)

    # create Load button AFTER the function exists
    btn_load = ttk.Button(top, text="Load", style="Primary.TButton", command=load_register_async)
    btn_load.pack(side="left", padx=8)

    # now safely bind toolbar commands; protect against name shadowing
    try:
        btn_export.configure(command=lambda cb=export_csv: cb())
    except Exception:
        pass
    try:
        btn_reprint.configure(command=lambda cb=reprint_selected: cb(tree))
    except Exception:
        pass



    zebra_tree(tree)

    def void_selected_statement():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select one statement to void.")
            return
        
        stmt = tree.item(sel[0])["values"][0]
        
        # Confirm with user
        confirm = messagebox.askyesno(
            "Confirm Void", 
            f"Are you sure you want to void statement {stmt}?\n\n"
            "This will remove all invoice associations and mark the statement as void.\n"
            "This action cannot be undone."
        )
        
        if not confirm:
            return
        
        try:
            success, message = void_statement(stmt)
            if success:
                messagebox.showinfo("Success", message)
                # Refresh the view to show updated status
                load_register_async()
            else:
                messagebox.showerror("Error", message)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to void statement: {str(e)}")



    def export_csv():
        items = tree.get_children()
        if not items:
            messagebox.showinfo("Export CSV", "Nothing to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            initialfile="statement_register.csv",
                                            filetypes=[("CSV","*.csv"),("All files","*.*")])
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(columns)
            for iid in items:
                w.writerow(tree.item(iid)["values"])
        messagebox.showinfo("Export CSV", f"Saved: {path}")

    def reprint_selected():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select one statement to reprint.")
            return
        stmt = tree.item(sel[0])["values"][0]
        try:
            reprint_statement(stmt)
            messagebox.showinfo("Reprint", f"Statement {stmt} reprinted.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

        # ---- Toolbar
    bar = ttk.Frame(win)
    bar.pack(fill="x", padx=10, pady=(0, 10))

    btn_export = ttk.Button(bar, text="💾 Export CSV", style="Primary.TButton", command=export_csv)
    btn_export.pack(side="left")

    btn_reprint = ttk.Button(bar, text="📄 Reprint Selected", style="Primary.TButton", command=reprint_selected)
    btn_reprint.pack(side="left", padx=8)

    btn_void = ttk.Button(bar, text="🚫 Void Statement", style="Danger.TButton", command=void_selected_statement)
    btn_void.pack(side="left", padx=8)


    ttk.Button(bar, text="Close", style="Primary.TButton", command=win.destroy).pack(side="right")

