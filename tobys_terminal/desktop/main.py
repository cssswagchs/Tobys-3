# main.py
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
# test 
# Update these imports to use the new package structure
from tobys_terminal.desktop.importers.customers_import import import_customers
from tobys_terminal.desktop.importers.orders_import import import_orders
from tobys_terminal.desktop.importers.payments_import import import_payments
from tobys_terminal.desktop.gui.statement_view import open_statement_view
from tobys_terminal.desktop.gui.reconcile_view import open_reconcile_view
from tobys_terminal.desktop.gui.ar_view import open_ar_view
from tobys_terminal.desktop.gui.payment_checker_view import open_payment_checker
from tobys_terminal.shared.brand_ui import apply_brand, make_header
from tobys_terminal.desktop.gui.statement_register_view import open_statement_register
from tobys_terminal.desktop.gui.customer_view import open_contract_tagger
from tobys_terminal.desktop.gui.imm_roster_view import open_imm_roster_view
from tobys_terminal.desktop.gui.harlestons_roster_view import open_harlestons_roster_view

# Shared imports
from tobys_terminal.shared.customer_utils import get_company_label
from tobys_terminal.shared.import_printavo_orders import sync_printavo_orders_for_harlestons
from tobys_terminal.shared.db import initialize_db, ensure_views
from tobys_terminal.shared.db import get_connection, ensure_statement_tables, ensure_indexes, ensure_customer_profiles_table
from tobys_terminal.shared.settings import ensure_settings_table
from tobys_terminal.shared.settings import get_setting, set_setting

def handle_import_customers():
    import_customers()
    messagebox.showinfo("Import Complete", "Customers imported successfully!")

def handle_import_orders():
    import_orders()
    messagebox.showinfo("Import Complete", "Orders imported successfully!")

def handle_import_payments():
    import_payments()
    messagebox.showinfo("Import Complete", "Payments imported successfully!")

def initialize_database():
    ensure_customer_profiles_table()
    # other `ensure_*` things here

def show_oldest_open_invoice():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT invoice_date, invoice_number
        FROM invoices
        WHERE LOWER(TRIM(paid)) NOT IN ('yes', 'true', 'paid')
           OR paid IS NULL
        ORDER BY invoice_date ASC
        LIMIT 1
    """)
    result = cursor.fetchone()
    conn.close()

    if result:
        invoice_date, invoice_number = result
        messagebox.showinfo("Oldest Open Invoice", f"Invoice #{invoice_number}\nDate: {invoice_date}")
    else:
        messagebox.showinfo("No Open Invoices", "All invoices are marked as paid.")


def main():
    initialize_db()
    ensure_views()
    ensure_statement_tables()
    ensure_indexes()
    ensure_customer_profiles_table()
    ensure_settings_table()  # Add this line


    root = tk.Tk()
    root.title("Toby's Terminal - CSS Billing")
    root.geometry("860x800")
    root.minsize(760, 500)

    apply_brand(root, large_title=True)  # Sage vibe


    # ----- menu bar
    menubar = tk.Menu(root)
    filem = tk.Menu(menubar, tearoff=False)
    filem.add_command(label="Import Customers…", command=handle_import_customers)
    filem.add_command(label="Import Orders…", command=handle_import_orders)
    filem.add_command(label="Import Payments…", command=handle_import_payments)
    filem.add_separator()
    filem.add_command(label="Exit", command=root.destroy)
    menubar.add_cascade(label="File", menu=filem)

    viewm = tk.Menu(menubar, tearoff=False)
    viewm.add_command(label="Customer Statement", command=open_statement_view)
    viewm.add_command(label="A/R Report", command=open_ar_view)
    viewm.add_command(label="Payment Reconciliation", command=open_reconcile_view)
    viewm.add_command(label="Payment Integrity Checker", command=open_payment_checker)
    viewm.add_command(label="Customer View", command=open_contract_tagger)

    menubar.add_cascade(label="Views", menu=viewm)

    helpm = tk.Menu(menubar, tearoff=False)
    helpm.add_command(label="About", command=lambda: messagebox.showinfo(
        "About",
        "CSS Billing\nPython + tkinter/ttk\nFast imports, statements, A/R dashboard."
    ))
    menubar.add_cascade(label="Help", menu=helpm)

    root.config(menu=menubar)

    # ----- layout frames
    outer = ttk.Frame(root, style="Card.TFrame", padding=12)
    outer.pack(fill="both", expand=True)

    # Header across the top
    hdr = make_header(
        outer,
        "Toby's Terminal - CSS Billing",
        "Sage’s sidekick for invoices, A/R, and statements",
        icon_text="💼"
    )
    hdr.pack(fill="x", pady=(0, 8))

    # Main body: left = sidebar buttons, right = info/tips
    body = ttk.Frame(outer, style="Card.TFrame")
    body.pack(fill="both", expand=True)

    # ----- Sidebar
    left = ttk.Frame(body, style="Card.TFrame")
    left.pack(side="left", fill="y", padx=(0, 12))

    grp_import = ttk.Labelframe(left, text="Import", style="Card.TLabelframe")
    grp_import.pack(fill="x", pady=6)
    ttk.Button(grp_import, text="📥 Import Customers", style="Primary.TButton",
               command=handle_import_customers).pack(fill="x", pady=4)
    ttk.Button(grp_import, text="📥 Import Orders", style="Primary.TButton",
               command=handle_import_orders).pack(fill="x", pady=4)
    ttk.Button(grp_import, text="📥 Import Payments", style="Primary.TButton",
               command=handle_import_payments).pack(fill="x", pady=4)

    grp_views = ttk.Labelframe(left, text="Views", style="Card.TLabelframe")
    grp_views.pack(fill="x", pady=6)
    ttk.Button(grp_views, text="📄 Customer Statement", style="Primary.TButton",
               command=open_statement_view).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="📊 A/R Report", style="Primary.TButton",
               command=open_ar_view).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="🔁 Reconcile Payments", style="Primary.TButton",
               command=open_reconcile_view).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="🧮 Payment Integrity Checker", style="Primary.TButton",
               command=open_payment_checker).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="📚 Statement Register", style="Primary.TButton",
           command=open_statement_register).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="📄 Customer Viewer", style="Primary.TButton",
           command=open_contract_tagger).pack(fill="x", pady=4)
    grp_utils = ttk.Labelframe(left, text="Utilities", style="Card.TLabelframe")
    grp_utils.pack(fill="x", pady=6)
    ttk.Button(grp_utils, text="🕓 Oldest Open Invoice", style="Accent.TButton",
               command=show_oldest_open_invoice).pack(fill="x", pady=4)
    ttk.Button(grp_utils, text="📦 IMM Production",
               command=lambda: open_imm_roster_view("IMM")).pack(pady=4)
    ttk.Button(grp_utils, text="🧵 Harlestons Production",
               command=lambda: open_harlestons_roster_view("Harlestons")).pack(pady=4)

    ttk.Button(grp_utils, text="Exit", style="Primary.TButton",
               command=root.destroy).pack(fill="x", pady=8)

    # ----- Right side: welcome / tips
    right = ttk.Frame(body, style="Card.TFrame")
    right.pack(side="left", fill="both", expand=True)

    tips = tk.Text(right, height=14, wrap="word", borderwidth=0,
                   bg=root._swag["paper"], fg="black")
    tips.insert("end",
        "Welcome!\n\n"
        "• Use the Import section to load CSVs from Printavo.\n"
        "• Use Views for statements, reconciliation, or A/R aging.\n"
        "• Keep CSV column names consistent between exports.\n"
        "• All actions are keyboard-friendly: Tab/Enter work everywhere.\n"
    )
    tips.configure(state="disabled")
    tips.pack(fill="both", expand=True, pady=4)

    def open_settings_view():
        settings_window = tk.Toplevel()
        settings_window.title("Application Settings")
        settings_window.geometry("600x400")
        
        # Create tabs for different setting categories
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # General settings tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        
        # Add settings controls
        ttk.Label(general_frame, text="Company Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        company_name_var = tk.StringVar(value=get_setting('company_name', ''))
        ttk.Entry(general_frame, textvariable=company_name_var, width=40).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Save button
        ttk.Button(settings_window, text="Save Settings", command=lambda: save_settings(
            company_name=company_name_var.get()
        )).pack(pady=10)
        
    def save_settings(**kwargs):
        for key, value in kwargs.items():
            set_setting(key, value)
        messagebox.showinfo("Settings", "Settings saved successfully!")




    root.mainloop()

if __name__ == "__main__":
    main()
