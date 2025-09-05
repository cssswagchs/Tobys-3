import tkinter as tk
import sys
import os
from tkinter import ttk, messagebox
from tobys_terminal.shared.db import (
    get_connection,
    get_contract_type,
    set_contract_type,
    get_customer_status,
    set_customer_status
)
from tobys_terminal.shared.customer_utils import get_grouped_customers
from tobys_terminal.desktop.gui.customer_contact_view import open_customer_contact_view
def open_contract_tagger():
    win = tk.Toplevel()
    win.title("Customer Tag Manager")
    win.geometry("720x500")

    ttk.Label(win, text="Customer Overview", font=("Arial", 14, "bold")).pack(pady=10)

    filter_frame = ttk.Frame(win)
    filter_frame.pack()

    ttk.Label(filter_frame, text="Show:").pack(side="left", padx=(0, 6))

    filter_var = tk.StringVar(value="Active")  # Default

    filter_dropdown = ttk.Combobox(filter_frame, textvariable=filter_var, state="readonly", width=15)
    filter_dropdown["values"] = ["All", "Active", "Inactive", "Untagged"]

    filter_dropdown.pack(side="left")

    def refresh_tree():
        tree.delete(*tree.get_children())
        customer_dict, sorted_companies = get_grouped_customers()

        selected_filter = filter_var.get()

        for company in sorted_companies:
            status = get_customer_status(company) or ""
            contract = get_contract_type(company) or ""

            if selected_filter == "Inactive" and status != "Inactive":
                continue
            if selected_filter == "Active" and status != "Active":
                continue
            if selected_filter == "Untagged" and status:
                continue  # skip if status is filled

            tree.insert("", "end", iid=company, values=(company, contract, status))


    filter_dropdown.bind("<<ComboboxSelected>>", lambda e: refresh_tree())

    def on_customer_double_click(event):
        selected_item = tree.focus()
        if selected_item:
            company_name = tree.item(selected_item)["values"][0]
            open_customer_contact_view(preselect=company_name)


    # Treeview setup
    frame = ttk.Frame(win)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    tree = ttk.Treeview(frame, columns=("company", "contract", "status"), show="headings", selectmode="extended")
    tree.heading("company", text="Customer")
    tree.heading("contract", text="Contract Type")
    tree.heading("status", text="Status")
    tree.column("company", width=360)
    tree.column("contract", width=120, anchor="center")
    tree.column("status", width=100, anchor="center")
    tree.bind("<Double-1>", on_customer_double_click)
    tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    # Load companies using shared utility
    customer_dict, sorted_companies = get_grouped_customers()

    refresh_tree()



    # Update contract tag
    def update_contract_tag(value):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select one or more customers.")
            return
        for company in selected:
            set_contract_type(company, value)
            tree.set(company, column="contract", value=value or "")
        status_var.set(f"✅ Updated {len(selected)} companies to Contract Type: {value or 'None'}")

    # Update status tag
    def update_status_tag(value):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select one or more customers.")
            return
        for company in selected:
            set_customer_status(company, value)
            tree.set(company, column="status", value=value or "")
        status_var.set(f"✅ Updated {len(selected)} customers to Status: {value or 'None'}")

    # Auto-tag logic
    def auto_tag_inactive():
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.company
            FROM customers c
            JOIN invoices i ON c.id = i.customer_id
            GROUP BY c.company
            HAVING SUM(i.total - IFNULL(i.amount_paid, 0)) = 0
               AND MAX(i.invoice_date) < '2024-01-01'
        """)
        results = cur.fetchall()
        conn.close()

        count = 0
        for row in results:
            company = row[0]
            set_customer_status(company, "Inactive")
            if tree.exists(company):
                tree.set(company, column="status", value="Inactive")
            count += 1
        messagebox.showinfo("Auto-Tag Complete", f"Tagged {count} companies as Inactive.")
        status_var.set(f"🧹 Auto-tagged {count} companies as Inactive")

    # Buttons
    btn_frame = ttk.Frame(win)
    btn_frame.pack(pady=10)

    ttk.Button(btn_frame, text="Set as Contract", command=lambda: update_contract_tag("Contract")).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Set as Retail", command=lambda: update_contract_tag("Retail")).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Set as Direct", command=lambda: update_contract_tag("Direct")).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Clear Type", command=lambda: update_contract_tag(None)).pack(side="left", padx=5)

    ttk.Separator(win, orient="horizontal").pack(fill="x", padx=10, pady=5)

    status_btn_frame = ttk.Frame(win)
    status_btn_frame.pack()

    ttk.Button(status_btn_frame, text="Mark as Active", command=lambda: update_status_tag("Active")).pack(side="left", padx=5)
    ttk.Button(status_btn_frame, text="Mark as Inactive", command=lambda: update_status_tag("Inactive")).pack(side="left", padx=5)
    ttk.Button(status_btn_frame, text="Clear Status", command=lambda: update_status_tag(None)).pack(side="left", padx=5)

    ttk.Button(win, text="🧹 Auto-Tag Inactive (0 Balance + Old)", command=auto_tag_inactive).pack(pady=10)

    # Status label
    status_var = tk.StringVar()
    ttk.Label(win, textvariable=status_var, foreground="green").pack(pady=5)
