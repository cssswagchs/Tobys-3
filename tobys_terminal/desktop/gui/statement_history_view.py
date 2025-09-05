import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import re
import sys
import subprocess
from datetime import datetime

from tobys_terminal.desktop.gui.customer_statement_creator import open_customer_statement_creator
from tobys_terminal.shared.db import get_connection, generate_statement_number 

def open_statement_history_view(preselect=None):
    win = tk.Toplevel()
    win.title(f"{preselect or 'Customer'} – Statement History")
    win.geometry("800x500")
    win.grab_set()
    ttk.Label(win, text=f"Statement History for {preselect or 'N/A'}", font=("Arial", 14, "bold")).pack(pady=10)

    # Statement list
    tree_frame = ttk.Frame(win)
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    tree = ttk.Treeview(tree_frame, columns=("number", "range", "date"), show="headings")
    tree.heading("number", text="Statement #")
    tree.heading("range", text="Date Range")
    tree.heading("date", text="Generated On")
    tree.column("number", width=120, anchor="center")
    tree.column("range", width=200, anchor="center")
    tree.column("date", width=150, anchor="center")

    # 🖱️ Double-click to open PDF
    def on_double_click(event):
        selected = tree.focus()
        if not selected:
            return
        values = tree.item(selected, "values")
        if not values:
            return

        statement_number, date_range, _ = values
        company_folder = preselect.strip().replace(" ", "_")

        exports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'exports', 'statements', company_folder))
        
        for fname in os.listdir(exports_dir):
            if fname.startswith(statement_number):
                pdf_path = os.path.join(exports_dir, fname)
                try:
                    subprocess.Popen(["start", "", pdf_path], shell=True)  # Windows-friendly
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open PDF:\n\n{e}")
                return

        messagebox.showwarning("Not Found", f"No PDF found for statement {statement_number}.")

    # ✅ Bind after tree is fully defined
    tree.bind("<Double-1>", on_double_click)

    tree.pack(fill="both", expand=True)



    def load_statements():
        tree.delete(*tree.get_children())

        if not preselect:
            return

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT statement_number, start_date, end_date, generated_on
            FROM statement_tracking
            WHERE company_label = ?
            ORDER BY generated_on DESC
        """, (preselect,))
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            num, start, end, gen = row
            tree.insert("", "end", values=(
                num,
                f"{start or '–'} to {end or '–'}",
                gen
            ))

    # Action buttons
    btn_frame = ttk.Frame(win)
    btn_frame.pack(pady=10)

    


    ttk.Button(btn_frame, text="➕ Generate New Statement", command=lambda: open_customer_statement_creator(preselect)).pack(side="left", padx=5)

    ttk.Button(btn_frame, text="🔄 Refresh", command=load_statements).pack(side="left", padx=5)

    # Load on start
    load_statements()
