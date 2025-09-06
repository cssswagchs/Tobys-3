
import tkinter as tk
import sys, os
from tkinter import ttk, messagebox, filedialog
import sqlite3


from tobys_terminal.shared.db import get_connection, get_contract_type, set_contract_type, get_customer_status, set_customer_status
from tobys_terminal.shared.brand_ui import apply_brand, make_header, zebra_tree

def open_contract_tagger():
    """
    Open the Customer View / Contract Tagger window.
    This view allows users to view customer information and tag them with contract types.
    """
    win = tk.Toplevel()
    win.title("Customer Viewer")
    win.geometry("1200x800")
    win.grab_set()
    
    apply_brand(win)
    
    # Header
    header = make_header(
        win,
        "Customer Viewer / Contract Tagger",
        "View customer information and tag them with contract types",
        icon_text="\ud83d\udc65"
    )
    header.pack(fill="x", pady=(0, 10))
    
    # Main content frame
    content_frame = ttk.Frame(win)
    content_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    # Left side - Controls and filters
    controls_frame = ttk.LabelFrame(content_frame, text="Filters")
    controls_frame.pack(side="left", fill="y", padx=(0, 10), pady=5)
    
    # Search by name or company
    ttk.Label(controls_frame, text="Search:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    
    search_var = tk.StringVar()
    search_entry = ttk.Entry(controls_frame, textvariable=search_var, width=20)
    search_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
    
    ttk.Button(
        controls_frame, 
        text="Search", 
        command=lambda: search_customers(
            customers_tree, 
            search_var.get()
        )
    ).grid(row=0, column=2, padx=5, pady=5)
    
    # Filter by contract type
    ttk.Label(controls_frame, text="Contract Type:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    
    contract_options = ["All", "Contract", "Direct", "Retail", "Untagged"]
    contract_var = tk.StringVar(value=contract_options[0])
    
    contract_dropdown = ttk.Combobox(controls_frame, textvariable=contract_var, values=contract_options, width=15)
    contract_dropdown.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
    
    # Filter by status
    ttk.Label(controls_frame, text="Status:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    
    status_options = ["All", "Active", "Inactive", "Untagged"]
    status_var = tk.StringVar(value=status_options[0])
    
    status_dropdown = ttk.Combobox(controls_frame, textvariable=status_var, values=status_options, width=15)
    status_dropdown.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
    
    # Apply filters button
    ttk.Button(
        controls_frame, 
        text="Apply Filters", 
        style="Primary.TButton",
        command=lambda: load_customers(
            customers_tree, 
            contract_var.get(),
            status_var.get(),
            search_var.get()
        )
    ).grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=10)
    
    # Refresh button
    ttk.Button(
        controls_frame, 
        text="Refresh", 
        command=lambda: load_customers(
            customers_tree, 
            contract_var.get(),
            status_var.get(),
            search_var.get()
        )
    ).grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
    
    # Export button
    ttk.Button(
        controls_frame, 
        text="Export to CSV", 
        command=lambda: export_to_csv(customers_tree)
    ).grid(row=5, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
    
    # Batch tagging section
    batch_frame = ttk.LabelFrame(controls_frame, text="Batch Actions")
    batch_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=5, pady=10)
    
    ttk.Label(batch_frame, text="Set Selected To:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    
    # Contract type batch actions
    ttk.Label(batch_frame, text="Contract Type:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    
    batch_contract_var = tk.StringVar()
    batch_contract_dropdown = ttk.Combobox(batch_frame, textvariable=batch_contract_var, values=["Contract", "Direct", "Retail"], width=15)
    batch_contract_dropdown.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
    
    ttk.Button(
        batch_frame, 
        text="Apply", 
        command=lambda: batch_set_contract_type(
            customers_tree, 
            batch_contract_var.get()
        )
    ).grid(row=1, column=2, padx=5, pady=5)
    
    # Status batch actions
    ttk.Label(batch_frame, text="Status:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    
    batch_status_var = tk.StringVar()
    batch_status_dropdown = ttk.Combobox(batch_frame, textvariable=batch_status_var, values=["Active", "Inactive"], width=15)
    batch_status_dropdown.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
    
    ttk.Button(
        batch_frame, 
        text="Apply", 
        command=lambda: batch_set_status(
            customers_tree, 
            batch_status_var.get()
        )
    ).grid(row=2, column=2, padx=5, pady=5)
    
    # Right side - Customers list
    customers_frame = ttk.LabelFrame(content_frame, text="Customers")
    customers_frame.pack(side="left", fill="both", expand=True, pady=5)
    
    # Create treeview for customers
    columns = ("id", "company", "name", "email", "phone", "contract_type", "status")
    customers_tree = ttk.Treeview(customers_frame, columns=columns, show="headings", style="Sage.Treeview")
    
    # Define column headings
    customers_tree.heading("id", text="ID")
    customers_tree.heading("company", text="Company")
    customers_tree.heading("name", text="Contact Name")
    customers_tree.heading("email", text="Email")
    customers_tree.heading("phone", text="Phone")
    customers_tree.heading("contract_type", text="Contract Type")
    customers_tree.heading("status", text="Status")
    
    # Define column widths
    customers_tree.column("id", width=50)
    customers_tree.column("company", width=200)
    customers_tree.column("name", width=150)
    customers_tree.column("email", width=200)
    customers_tree.column("phone", width=120)
    customers_tree.column("contract_type", width=100)
    customers_tree.column("status", width=80)
    
    # Add scrollbar
    scrollbar = ttk.Scrollbar(customers_frame, orient="vertical", command=customers_tree.yview)
    customers_tree.configure(yscrollcommand=scrollbar.set)
    
    # Pack the treeview and scrollbar
    scrollbar.pack(side="right", fill="y")
    customers_tree.pack(side="left", fill="both", expand=True)
    
    # Add double-click event to edit customer
    customers_tree.bind("<Double-1>", lambda event: edit_customer(customers_tree))
    
    # Add right-click menu
    create_context_menu(customers_tree)
    
    # Bottom buttons
    button_frame = ttk.Frame(win)
    button_frame.pack(fill="x", padx=10, pady=10)
    
    ttk.Button(
        button_frame, 
        text="Edit Selected", 
        command=lambda: edit_customer(customers_tree)
    ).pack(side="left", padx=5)
    
    ttk.Button(
        button_frame, 
        text="View Invoices", 
        command=lambda: view_customer_invoices(customers_tree)
    ).pack(side="left", padx=5)
    
    ttk.Button(button_frame, text="Close", command=win.destroy).pack(side="right", padx=5)
    
    # Initial load of customers
    load_customers(customers_tree, contract_var.get(), status_var.get(), "")
    
    # Apply zebra striping to the treeview
    zebra_tree(customers_tree)

def create_context_menu(tree):
    """
    Create a right-click context menu for the treeview.
    """
    menu = tk.Menu(tree, tearoff=0)
    menu.add_command(label="Edit Customer", command=lambda: edit_customer(tree))
    menu.add_command(label="View Invoices", command=lambda: view_customer_invoices(tree))
    menu.add_separator()
    
    # Contract type submenu
    contract_menu = tk.Menu(menu, tearoff=0)
    contract_menu.add_command(label="Contract", command=lambda: set_selected_contract_type(tree, "Contract"))
    contract_menu.add_command(label="Direct", command=lambda: set_selected_contract_type(tree, "Direct"))
    contract_menu.add_command(label="Retail", command=lambda: set_selected_contract_type(tree, "Retail"))
    menu.add_cascade(label="Set Contract Type", menu=contract_menu)
    
    # Status submenu
    status_menu = tk.Menu(menu, tearoff=0)
    status_menu.add_command(label="Active", command=lambda: set_selected_status(tree, "Active"))
    status_menu.add_command(label="Inactive", command=lambda: set_selected_status(tree, "Inactive"))
    menu.add_cascade(label="Set Status", menu=status_menu)
    
    # Bind right-click to show menu
    tree.bind("<Button-3>", lambda event: show_context_menu(event, menu))

def show_context_menu(event, menu):
    """
    Show the context menu at the mouse position.
    """
    menu.post(event.x_root, event.y_root)

def load_customers(tree, contract_filter, status_filter, search_term):
    """
    Load customers based on the selected filter options.
    """
    # Clear existing items
    for item in tree.get_children():
        tree.delete(item)
    
    try:
        # Get connection to database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Base query
        query = """
        SELECT 
            c.id,
            c.company,
            c.first_name || ' ' || c.last_name as name,
            c.email,
            c.phone,
            cp.contract_type,
            cp.status
        FROM customers c
        LEFT JOIN customer_profiles cp ON c.company = cp.company
        """
        
        # Apply filters
        where_clauses = []
        params = []
        
        if contract_filter == "Contract":
            where_clauses.append("cp.contract_type = 'Contract'")
        elif contract_filter == "Direct":
            where_clauses.append("cp.contract_type = 'Direct'")
        elif contract_filter == "Retail":
            where_clauses.append("cp.contract_type = 'Retail'")
        elif contract_filter == "Untagged":
            where_clauses.append("cp.contract_type IS NULL")
        
        if status_filter == "Active":
            where_clauses.append("cp.status = 'Active'")
        elif status_filter == "Inactive":
            where_clauses.append("cp.status = 'Inactive'")
        elif status_filter == "Untagged":
            where_clauses.append("cp.status IS NULL")
        
        if search_term:
            where_clauses.append("(c.company LIKE ? OR c.first_name LIKE ? OR c.last_name LIKE ? OR c.email LIKE ?)")
            search_param = f"%{search_term}%"
            params.extend([search_param, search_param, search_param, search_param])
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Order by company
        query += " ORDER BY c.company"
        
        cursor.execute(query, params)
        customers = cursor.fetchall()
        conn.close()
        
        # Insert into treeview
        for customer in customers:
            cust_id, company, name, email, phone, contract_type, status = customer
            
            tree.insert("", "end", values=(
                cust_id,
                company or "N/A",
                name or "N/A",
                email or "N/A",
                phone or "N/A",
                contract_type or "Untagged",
                status or "Untagged"
            ))
        
        # Apply zebra striping
        zebra_tree(tree)
        
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Error loading customers: {str(e)}")

def search_customers(tree, search_term):
    """
    Search for customers by name, company, or email.
    """
    if not search_term:
        messagebox.showinfo("Search", "Please enter a search term.")
        return
    
    # Get current filters from the parent window
    parent = tree.master.master  # Navigate up to the main frame
    
    # Find the contract and status filter variables
    contract_var = None
    status_var = None
    
    for child in parent.winfo_children():
        if isinstance(child, ttk.LabelFrame) and child.cget("text") == "Filters":
            for grandchild in child.winfo_children():
                if isinstance(grandchild, ttk.Combobox):
                    if "contract" in str(grandchild).lower():
                        contract_var = grandchild.get()
                    elif "status" in str(grandchild).lower():
                        status_var = grandchild.get()
    
    # Use default values if not found
    contract_filter = contract_var or "All"
    status_filter = status_var or "All"
    
    # Load customers with the search term
    load_customers(tree, contract_filter, status_filter, search_term)

def edit_customer(tree):
    """
    Edit the selected customer.
    """
    # Get selected item
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showinfo("Selection", "Please select a customer to edit.")
        return
    
    # Get customer details
    values = tree.item(selected_items[0], "values")
    cust_id, company, name, email, phone, contract_type, status = values
    
    # Create dialog
    dialog = tk.Toplevel()
    dialog.title("Edit Customer")
    dialog.geometry("500x500")
    dialog.grab_set()
    
    apply_brand(dialog)
    
    # Header
    ttk.Label(dialog, text="Edit Customer", font=("Arial", 16, "bold")).pack(pady=10)
    
    # Customer details form
    form_frame = ttk.Frame(dialog, padding=10)
    form_frame.pack(fill="both", expand=True)
    
    # Company
    ttk.Label(form_frame, text="Company:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    company_var = tk.StringVar(value=company)
    company_entry = ttk.Entry(form_frame, textvariable=company_var, width=30)
    company_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
    
    # Name
    ttk.Label(form_frame, text="Contact Name:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    name_var = tk.StringVar(value=name)
    name_entry = ttk.Entry(form_frame, textvariable=name_var, width=30)
    name_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
    
    # Email
    ttk.Label(form_frame, text="Email:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    email_var = tk.StringVar(value=email)
    email_entry = ttk.Entry(form_frame, textvariable=email_var, width=30)
    email_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
    
    # Phone
    ttk.Label(form_frame, text="Phone:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
    phone_var = tk.StringVar(value=phone)
    phone_entry = ttk.Entry(form_frame, textvariable=phone_var, width=30)
    phone_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
    
    # Contract Type
    ttk.Label(form_frame, text="Contract Type:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
    contract_var = tk.StringVar(value=contract_type)
    contract_dropdown = ttk.Combobox(form_frame, textvariable=contract_var, values=["Contract", "Direct", "Retail", "Untagged"], width=15)
    contract_dropdown.grid(row=4, column=1, sticky="ew", padx=5, pady=5)
    
    # Status
    ttk.Label(form_frame, text="Status:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
    status_var = tk.StringVar(value=status)
    status_dropdown = ttk.Combobox(form_frame, textvariable=status_var, values=["Active", "Inactive", "Untagged"], width=15)
    status_dropdown.grid(row=5, column=1, sticky="ew", padx=5, pady=5)
    
    # Address information
    ttk.Label(form_frame, text="Billing Address:").grid(row=6, column=0, sticky="w", padx=5, pady=5)
    
    # Get address from database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        billing_address1, 
        billing_address2, 
        billing_city, 
        billing_state, 
        billing_zip
    FROM customers
    WHERE id = ?
    """, (cust_id,))
    
    address_data = cursor.fetchone()
    conn.close()
    
    if address_data:
        address1, address2, city, state, zip_code = address_data
    else:
        address1, address2, city, state, zip_code = "", "", "", "", ""
    
    # Address fields
    address_frame = ttk.Frame(form_frame)
    address_frame.grid(row=6, column=1, sticky="ew", padx=5, pady=5)
    
    address1_var = tk.StringVar(value=address1 or "")
    address1_entry = ttk.Entry(address_frame, textvariable=address1_var, width=30)
    address1_entry.pack(fill="x", pady=2)
    
    address2_var = tk.StringVar(value=address2 or "")
    address2_entry = ttk.Entry(address_frame, textvariable=address2_var, width=30)
    address2_entry.pack(fill="x", pady=2)
    
    city_state_frame = ttk.Frame(address_frame)
    city_state_frame.pack(fill="x", pady=2)
    
    city_var = tk.StringVar(value=city or "")
    city_entry = ttk.Entry(city_state_frame, textvariable=city_var, width=15)
    city_entry.pack(side="left", padx=(0, 5))
    
    state_var = tk.StringVar(value=state or "")
    state_entry = ttk.Entry(city_state_frame, textvariable=state_var, width=5)
    state_entry.pack(side="left", padx=(0, 5))
    
    zip_var = tk.StringVar(value=zip_code or "")
    zip_entry = ttk.Entry(city_state_frame, textvariable=zip_var, width=10)
    zip_entry.pack(side="left")
    
    # Notes section
    ttk.Label(form_frame, text="Notes:").grid(row=7, column=0, sticky="w", padx=5, pady=5)
    notes_text = tk.Text(form_frame, height=5, width=30)
    notes_text.grid(row=7, column=1, sticky="ew", padx=5, pady=5)
    
    # Button frame
    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill="x", padx=10, pady=10)
    
    ttk.Button(
        button_frame, 
        text="Save Changes", 
        style="Primary.TButton",
        command=lambda: save_customer_changes(
            dialog,
            tree,
            selected_items[0],
            cust_id,
            company_var.get(),
            name_var.get(),
            email_var.get(),
            phone_var.get(),
            contract_var.get(),
            status_var.get(),
            address1_var.get(),
            address2_var.get(),
            city_var.get(),
            state_var.get(),
            zip_var.get(),
            notes_text.get("1.0", "end-1c")
        )
    ).pack(side="left", padx=5)
    
    ttk.Button(
        button_frame, 
        text="Cancel", 
        command=dialog.destroy
    ).pack(side="right", padx=5)

def save_customer_changes(dialog, tree, item_id, cust_id, company, name, email, phone, contract_type, status, address1, address2, city, state, zip_code, notes):
    """
    Save changes to a customer.
    """
    try:
        # Parse name into first and last
        name_parts = name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Get connection to database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update customer in database
        cursor.execute("""
        UPDATE customers
        SET company = ?, first_name = ?, last_name = ?, email = ?, phone = ?,
            billing_address1 = ?, billing_address2 = ?, billing_city = ?, billing_state = ?, billing_zip = ?
        WHERE id = ?
        """, (company, first_name, last_name, email, phone, address1, address2, city, state, zip_code, cust_id))
        
        # Update contract type and status
        if contract_type == "Untagged":
            contract_type = None
        
        if status == "Untagged":
            status = None
        
        # Use the set_contract_type and set_customer_status functions
        set_contract_type(company, contract_type)
        set_customer_status(company, status)
        
        # Save notes if provided
        if notes:
            cursor.execute("""
            INSERT OR REPLACE INTO notes (key, value)
            VALUES (?, ?)
            """, (f"customer_{cust_id}_notes", notes))
        
        conn.commit()
        conn.close()
        
        # Update treeview
        tree.item(item_id, values=(
            cust_id,
            company,
            name,
            email,
            phone,
            contract_type or "Untagged",
            status or "Untagged"
        ))
        
        # Close dialog
        dialog.destroy()
        
        messagebox.showinfo("Success", "Customer updated successfully.")
        
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Error updating customer: {str(e)}")

def view_customer_invoices(tree):
    """
    View invoices for the selected customer.
    """
    # Get selected item
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showinfo("Selection", "Please select a customer to view invoices.")
        return
    
    # Get customer details
    values = tree.item(selected_items[0], "values")
    cust_id, company, name, email, phone, contract_type, status = values
    
    # Create dialog
    dialog = tk.Toplevel()
    dialog.title(f"Invoices for {company}")
    dialog.geometry("900x600")
    dialog.grab_set()
    
    apply_brand(dialog)
    
    # Header
    header = make_header(
        dialog,
        f"Invoices for {company}",
        f"Contact: {name} | {email} | {phone}",
        icon_text="\ud83d\udccb"
    )
    header.pack(fill="x", pady=(0, 10))
    
    # Main content frame
    content_frame = ttk.Frame(dialog)
    content_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    # Create treeview for invoices
    columns = ("date", "invoice", "amount", "paid", "status", "po_number")
    invoices_tree = ttk.Treeview(content_frame, columns=columns, show="headings", style="Sage.Treeview")
    
    # Define column headings
    invoices_tree.heading("date", text="Date")
    invoices_tree.heading("invoice", text="Invoice #")
    invoices_tree.heading("amount", text="Amount")
    invoices_tree.heading("paid", text="Paid")
    invoices_tree.heading("status", text="Status")
    invoices_tree.heading("po_number", text="PO Number")
    
    # Define column widths
    invoices_tree.column("date", width=100)
    invoices_tree.column("invoice", width=100)
    invoices_tree.column("amount", width=100, anchor="e")
    invoices_tree.column("paid", width=100, anchor="center")
    invoices_tree.column("status", width=150)
    invoices_tree.column("po_number", width=150)
    
    # Add scrollbar
    scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=invoices_tree.yview)
    invoices_tree.configure(yscrollcommand=scrollbar.set)
    
    # Pack the treeview and scrollbar
    scrollbar.pack(side="right", fill="y")
    invoices_tree.pack(side="left", fill="both", expand=True)
    
    # Load invoice data
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query for invoices
        cursor.execute("""
        SELECT 
            i.invoice_date, 
            i.invoice_number, 
            i.total, 
            CASE 
                WHEN LOWER(TRIM(i.paid)) IN ('yes', 'true', 'paid') THEN 'Yes' 
                ELSE 'No' 
            END as paid,
            i.invoice_status,
            i.po_number
        FROM invoices i
        WHERE i.customer_id = ?
        ORDER BY i.invoice_date DESC
        """, (cust_id,))
        
        invoices = cursor.fetchall()
        conn.close()
        
        # Insert into treeview
        for invoice in invoices:
            date, invoice_num, amount, paid, status, po_number = invoice
            
            # Format amount
            amount = float(amount) if amount else 0
            
            invoices_tree.insert("", "end", values=(
                date,
                invoice_num,
                f"${amount:.2f}",
                paid,
                status or "N/A",
                po_number or "N/A"
            ))
        
        # Apply zebra striping
        zebra_tree(invoices_tree)
        
        # Summary frame at the bottom
        summary_frame = ttk.Frame(dialog)
        summary_frame.pack(fill="x", padx=10, pady=10)
        
        # Calculate totals
        total_invoiced = sum(float(i[2] or 0) for i in invoices)
        total_paid = sum(float(i[2] or 0) for i in invoices if i[3] == "Yes")
        total_outstanding = total_invoiced - total_paid
        
        # Summary labels
        ttk.Label(summary_frame, text="Total Invoiced:").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(summary_frame, text=f"${total_invoiced:.2f}").grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(summary_frame, text="Total Paid:").grid(row=0, column=2, sticky="w", padx=5)
        ttk.Label(summary_frame, text=f"${total_paid:.2f}").grid(row=0, column=3, sticky="w", padx=5)
        
        ttk.Label(summary_frame, text="Outstanding:").grid(row=0, column=4, sticky="w", padx=5)
        ttk.Label(summary_frame, text=f"${total_outstanding:.2f}", style="Bold.TLabel").grid(row=0, column=5, sticky="w", padx=5)
        
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Error loading invoices: {str(e)}")
    
    # Button frame
    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill="x", padx=10, pady=10)
    
    ttk.Button(
        button_frame, 
        text="Generate Statement", 
        command=lambda: generate_statement_for_customer(cust_id, company)
    ).pack(side="left", padx=5)
    
    ttk.Button(
        button_frame, 
        text="Close", 
        command=dialog.destroy
    ).pack(side="right", padx=5)

def generate_statement_for_customer(customer_id, company_name):
    """
    Generate a statement for the selected customer.
    """
    # This would typically open the statement view with the customer pre-selected
    messagebox.showinfo("Generate Statement", f"Statement generation for {company_name} will be implemented soon.")

def set_selected_contract_type(tree, contract_type):
    """
    Set the contract type for the selected customer.
    """
    # Get selected item
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showinfo("Selection", "Please select a customer to set contract type.")
        return
    
    try:
        # Update each selected customer
        for item_id in selected_items:
            values = tree.item(item_id, "values")
            cust_id, company, name, email, phone, old_contract_type, status = values
            
            # Update contract type in database
            set_contract_type(company, contract_type)
            
            # Update treeview
            values = list(values)
            values[5] = contract_type
            tree.item(item_id, values=values)
        
        messagebox.showinfo("Success", f"Contract type set to {contract_type} for {len(selected_items)} customer(s).")
        
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Error setting contract type: {str(e)}")

def set_selected_status(tree, status):
    """
    Set the status for the selected customer.
    """
    # Get selected item
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showinfo("Selection", "Please select a customer to set status.")
        return
    
    try:
        # Update each selected customer
        for item_id in selected_items:
            values = tree.item(item_id, "values")
            cust_id, company, name, email, phone, contract_type, old_status = values
            
            # Update status in database
            set_customer_status(company, status)
            
            # Update treeview
            values = list(values)
            values[6] = status
            tree.item(item_id, values=values)
        
        messagebox.showinfo("Success", f"Status set to {status} for {len(selected_items)} customer(s).")
        
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Error setting status: {str(e)}")

def batch_set_contract_type(tree, contract_type):
    """
    Set the contract type for all selected customers.
    """
    if not contract_type:
        messagebox.showinfo("Input Required", "Please select a contract type.")
        return
    
    # Get selected items
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showinfo("Selection", "Please select customers to update.")
        return
    
    # Confirm action
    if not messagebox.askyesno("Confirm", f"Set contract type to {contract_type} for {len(selected_items)} customer(s)?"):
        return
    
    # Update contract type
    set_selected_contract_type(tree, contract_type)

def batch_set_status(tree, status):
    """
    Set the status for all selected customers.
    """
    if not status:
        messagebox.showinfo("Input Required", "Please select a status.")
        return
    
    # Get selected items
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showinfo("Selection", "Please select customers to update.")
        return
    
    # Confirm action
    if not messagebox.askyesno("Confirm", f"Set status to {status} for {len(selected_items)} customer(s)?"):
        return
    
    # Update status
    set_selected_status(tree, status)

def export_to_csv(tree):
    """
    Export the customers list to a CSV file.
    """
    # Get the file path to save the CSV
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")],
        title="Save Customers As"
    )
    
    if not file_path:
        return
    
    try:
        # Open file for writing
        with open(file_path, "w", newline="") as f:
            # Write header
            f.write("ID,Company,Contact Name,Email,Phone,Contract Type,Status\
")
            
            # Write data
            for item_id in tree.get_children():
                values = tree.item(item_id, "values")
                # Clean up values and format as CSV
                cleaned_values = [str(v).replace(",", " ") for v in values]
                f.write(",".join(cleaned_values) + "\
")
        
        messagebox.showinfo("Export Complete", f"Customers exported to {file_path}")
        
    except Exception as e:
        messagebox.showerror("Export Error", f"Error exporting customers: {str(e)}")
