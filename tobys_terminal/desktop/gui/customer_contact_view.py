import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from tobys_terminal.shared.customer_utils import get_customer_ids_by_company
from tobys_terminal.shared.db import get_connection
from tobys_terminal.desktop.gui.statement_view import open_statement_view
from tobys_terminal.desktop.gui.statement_register_view import open_statement_register
from tobys_terminal.desktop.gui.statement_history_view import open_statement_history_view
from tobys_terminal.desktop.gui.production_roster import open_production_roster
def open_customer_contact_view(preselect=None):
    win = tk.Toplevel()
    win.title("Customer Contact Viewer")
    win.geometry("720x500")

    ttk.Label(win, text="Customer Portal", font=("Arial", 14, "bold")).pack(pady=10)

    # Fetch customer list from the customers table
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT company FROM customers WHERE company IS NOT NULL ORDER BY company")
    customer_names = [row[0] for row in cur.fetchall()]
    conn.close()

    selected_customer = tk.StringVar(value=preselect if preselect else "")

    contract_type = tk.StringVar()
    customer_status = tk.StringVar()
    contact_name = tk.StringVar()
    contact_email = tk.StringVar()
    contact_phone = tk.StringVar()
    billing_address = tk.StringVar()
    verified = tk.BooleanVar()

    # Dropdown to select customer
    form_frame = ttk.Frame(win)
    form_frame.pack(padx=20, pady=10, fill="x")

    ttk.Label(form_frame, text="Select Customer:").grid(row=0, column=0, sticky="w")
    customer_dropdown = ttk.Combobox(form_frame, textvariable=selected_customer, values=customer_names, width=50)
    customer_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    def load_customer_data(*args):
        name = selected_customer.get().strip()
        if not name:
            return

        ids = get_customer_ids_by_company(name)
        primary_id = ids[0] if ids else None

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT contact_name, contact_email, contact_phone, billing_address, verified,
                contract_type, status
            FROM customer_profiles WHERE company = ?
        """, (name,))
        row = cur.fetchone()

        if row:
            contact_name.set(row[0] or "")
            contact_email.set(row[1] or "")
            contact_phone.set(row[2] or "")
            billing_address.set(row[3] or "")
            contract_type.set(row[5] or "")
            customer_status.set(row[6] or "")
            verified.set(row[4] == "Yes")

        elif primary_id:
            cur.execute("""
                SELECT first_name, last_name, email, phone, address_1, address_2, city, state, zip
                FROM customers WHERE id = ?
            """, (primary_id,))
            cust = cur.fetchone()
            if cust:
                first, last, email, phone, addr1, addr2, city, state, zip_code = cust
                contact_name.set(f"{first or ''} {last or ''}".strip())
                contact_email.set(email or "")
                contact_phone.set(phone or "")

                address_parts = [addr1, addr2, city, state, zip_code]
                billing_address.set(", ".join(part for part in address_parts if part))
            else:
                contact_name.set("")
                contact_email.set("")
                contact_phone.set("")
                billing_address.set("")
            verified.set(False)
        else:
            contact_name.set("")
            contact_email.set("")
            contact_phone.set("")
            billing_address.set("")
            verified.set(False)

        conn.close()

    customer_dropdown.bind("<<ComboboxSelected>>", load_customer_data)

    # Contact fields
    fields = [
        ("Contact Name:", contact_name),
        ("Email:", contact_email),
        ("Phone:", contact_phone),
        ("Billing Address:", billing_address),
    ]
    for i, (label, var) in enumerate(fields, start=1):
        ttk.Label(form_frame, text=label).grid(row=i, column=0, sticky="w")
        ttk.Entry(form_frame, textvariable=var, width=50).grid(row=i, column=1, padx=5, pady=2, sticky="w")

    # Contract Type dropdown
    ttk.Label(form_frame, text="Contract Type:").grid(row=6, column=0, sticky="w")
    contract_combo = ttk.Combobox(form_frame, textvariable=contract_type, state="readonly", values=["", "Contract", "Direct"], width=47)
    contract_combo.grid(row=6, column=1, padx=5, pady=2, sticky="w")

    # Status dropdown
    ttk.Label(form_frame, text="Status:").grid(row=7, column=0, sticky="w")
    status_combo = ttk.Combobox(form_frame, textvariable=customer_status, state="readonly", values=["", "Active", "Inactive"], width=47)
    status_combo.grid(row=7, column=1, padx=5, pady=2, sticky="w")


    ttk.Checkbutton(form_frame, text="Verified", variable=verified).grid(row=5, column=1, sticky="w", padx=5, pady=5)

    def save_customer_data():
        name = selected_customer.get().strip()
        if not name:
            messagebox.showwarning("Missing Customer", "Please select a customer first.")
            return

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT company FROM customer_profiles WHERE company = ?", (name,))
        exists = cur.fetchone()

        if exists:
            cur.execute("""
                UPDATE customer_profiles
                SET contact_name = ?, contact_email = ?, contact_phone = ?, billing_address = ?, contract_type = ?, status = ?, verified = ?
                WHERE company = ?
            """, (
                contact_name.get().strip(),
                contact_email.get().strip(),
                contact_phone.get().strip(),
                billing_address.get().strip(),
                contract_type.get().strip(),
                customer_status.get().strip(),
                "Yes" if verified.get() else "No",
                name
            ))
        else:
            cur.execute("""
                INSERT INTO customer_profiles (company, contact_name, contact_email, contact_phone, billing_address, contract_type, status, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                contact_name.get().strip(),
                contact_email.get().strip(),
                contact_phone.get().strip(),
                billing_address.get().strip(),
                contract_type.get().strip(),
                customer_status.get().strip(),
                "Yes" if verified.get() else "No"
            ))

        conn.commit()
        conn.close()
        messagebox.showinfo("Saved", f"Contact info saved for {name}.")

    if preselect:
        load_customer_data()


    # Horizontal button layout
    button_frame = ttk.Frame(win)
    button_frame.pack(pady=10)

    ttk.Button(button_frame, text="📋 View Production", command=lambda: open_production_roster(preselect)).pack(side="left", padx=5)
    ttk.Button(button_frame, text="💾 Save Contact Info", command=save_customer_data).pack(side="left", padx=5)
    ttk.Button(button_frame, text="📖 Statements & History", command=lambda: open_statement_history_view(preselect=selected_customer.get())).pack(side="left", padx=5)