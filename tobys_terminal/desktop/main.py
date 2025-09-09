
# main.py
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading

# Update these imports to use the new package structure
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
from tobys_terminal.shared.db import initialize_db, ensure_views
from tobys_terminal.shared.db import get_connection, ensure_statement_tables, ensure_indexes, ensure_customer_profiles_table
from tobys_terminal.shared.settings import ensure_settings_table
from tobys_terminal.shared.settings import get_setting, set_setting

# Import the new printavo_sync functionality
from tobys_terminal.shared.printavo_sync import sync_all, sync_imm_orders, sync_harlestons_orders, check_database
from tobys_terminal.shared.statement_logic import fix_invoice_tracking_table

def handle_sync_all():
    """Run the full Printavo synchronization process"""
    # Show a progress indicator
    progress_window = tk.Toplevel()
    progress_window.title("Synchronizing with Printavo")
    progress_window.geometry("400x150")
    progress_window.transient()
    progress_window.resizable(False, False)
    
    # Center the window
    progress_window.update_idletasks()
    width = progress_window.winfo_width()
    height = progress_window.winfo_height()
    x = (progress_window.winfo_screenwidth() // 2) - (width // 2)
    y = (progress_window.winfo_screenheight() // 2) - (height // 2)
    progress_window.geometry(f"{width}x{height}+{x}+{y}")
    
    # Add a label
    ttk.Label(progress_window, text="Synchronizing with Printavo...", font=("Arial", 12)).pack(pady=20)
    
    # Add a progress bar
    progress = ttk.Progressbar(progress_window, mode="indeterminate")
    progress.pack(fill="x", padx=20, pady=10)
    progress.start()
    
    # Run sync in a separate thread to keep UI responsive
    def run_sync():
        try:
            result = sync_all()
            progress_window.after(0, lambda: complete_sync(result))
        except Exception as e:
            progress_window.after(0, lambda: complete_sync(False, str(e)))
    
    def complete_sync(success, error_message=None):
        progress.stop()
        progress_window.destroy()
        
        if success:
            messagebox.showinfo("Sync Complete", "Successfully synchronized with Printavo!")
        else:
            error_text = f"Error during synchronization: {error_message}" if error_message else "Synchronization failed."
            messagebox.showerror("Sync Failed", error_text)
    
    # Start the thread
    sync_thread = threading.Thread(target=run_sync)
    sync_thread.daemon = True
    sync_thread.start()

def handle_sync_imm():
    """Sync only IMM orders from Printavo"""
    try:
        sync_imm_orders()
        messagebox.showinfo("Sync Complete", "Successfully synchronized IMM orders from Printavo!")
    except Exception as e:
        messagebox.showerror("Sync Failed", f"Error synchronizing IMM orders: {str(e)}")

def handle_sync_harlestons():
    """Sync only Harlestons orders from Printavo"""
    try:
        sync_harlestons_orders()
        messagebox.showinfo("Sync Complete", "Successfully synchronized Harlestons orders from Printavo!")
    except Exception as e:
        messagebox.showerror("Sync Failed", f"Error synchronizing Harlestons orders: {str(e)}")

def handle_check_database():
    """Run database check and display results"""
    try:
        # Create a text window to display results
        result_window = tk.Toplevel()
        result_window.title("Database Check Results")
        result_window.geometry("600x400")
        
        # Add a text widget with scrollbar
        text_frame = ttk.Frame(result_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        text_widget = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set)
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Redirect output to the text widget
        import io
        import sys
        
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        # Run the check
        check_database()
        
        # Get the output and restore stdout
        output = sys.stdout.getvalue()
        sys.stdout = original_stdout
        
        # Display the output
        text_widget.insert("1.0", output)
        text_widget.config(state="disabled")
        
    except Exception as e:
        messagebox.showerror("Error", f"Error checking database: {str(e)}")

def initialize_database():
    ensure_customer_profiles_table()
    ensure_statement_tables()
    fix_invoice_tracking_table()  # Add this line
    ensure_indexes()
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
        messagebox.showinfo("Oldest Open Invoice", f"Invoice #{invoice_number}\
Date: {invoice_date}")
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
    
    # File menu - replace old import commands with new sync commands
    filem = tk.Menu(menubar, tearoff=False)
    filem.add_command(label="\ud83d\udd04 Sync All Printavo Data", command=handle_sync_all)
    filem.add_command(label="\ud83d\udd04 Sync IMM Orders", command=handle_sync_imm)
    filem.add_command(label="\ud83d\udd04 Sync Harlestons Orders", command=handle_sync_harlestons)
    filem.add_separator()
    filem.add_command(label="\ud83d\udd0d Check Database", command=handle_check_database)
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
        "CSS Billing\
Python + tkinter/ttk\
Fast imports, statements, A/R dashboard."
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
        "Sage's sidekick for invoices, A/R, and statements",
        icon_text="\ud83d\udcbc"
    )
    hdr.pack(fill="x", pady=(0, 8))

    # Main body: left = sidebar buttons, right = info/tips
    body = ttk.Frame(outer, style="Card.TFrame")
    body.pack(fill="both", expand=True)

    # ----- Sidebar
    left = ttk.Frame(body, style="Card.TFrame")
    left.pack(side="left", fill="y", padx=(0, 12))

    # Replace Import section with Printavo Sync section
    grp_sync = ttk.Labelframe(left, text="Printavo Sync", style="Card.TLabelframe")
    grp_sync.pack(fill="x", pady=6)
    ttk.Button(grp_sync, text="\ud83d\udd04 Sync All Data", style="Primary.TButton",
               command=handle_sync_all).pack(fill="x", pady=4)
    ttk.Button(grp_sync, text="\ud83d\udd04 Sync IMM Orders", style="Primary.TButton",
               command=handle_sync_imm).pack(fill="x", pady=4)
    ttk.Button(grp_sync, text="\ud83d\udd04 Sync Harlestons Orders", style="Primary.TButton",
               command=handle_sync_harlestons).pack(fill="x", pady=4)

    grp_views = ttk.Labelframe(left, text="Views", style="Card.TLabelframe")
    grp_views.pack(fill="x", pady=6)
    ttk.Button(grp_views, text="\ud83d\udcc4 Customer Statement", style="Primary.TButton",
               command=open_statement_view).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="\ud83d\udcca A/R Report", style="Primary.TButton",
               command=open_ar_view).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="\ud83d\udd01 Reconcile Payments", style="Primary.TButton",
               command=open_reconcile_view).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="\ud83e\uddee Payment Integrity Checker", style="Primary.TButton",
               command=open_payment_checker).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="\ud83d\udcda Statement Register", style="Primary.TButton",
           command=open_statement_register).pack(fill="x", pady=4)
    ttk.Button(grp_views, text="\ud83d\udcc4 Customer Viewer", style="Primary.TButton",
           command=open_contract_tagger).pack(fill="x", pady=4)
    
    grp_utils = ttk.Labelframe(left, text="Utilities", style="Card.TLabelframe")
    grp_utils.pack(fill="x", pady=6)
    ttk.Button(grp_utils, text="\ud83d\udd53 Oldest Open Invoice", style="Accent.TButton",
               command=show_oldest_open_invoice).pack(fill="x", pady=4)
    ttk.Button(grp_utils, text="\ud83d\udce6 IMM Production",
               command=lambda: open_imm_roster_view("IMM")).pack(pady=4)
    ttk.Button(grp_utils, text="\ud83e\uddf5 Harlestons Production",
               command=lambda: open_harlestons_roster_view("Harlestons")).pack(pady=4)
    ttk.Button(grp_utils, text="\ud83d\udd0d Check Database", style="Accent.TButton",
               command=handle_check_database).pack(fill="x", pady=4)

    ttk.Button(grp_utils, text="Exit", style="Primary.TButton",
               command=root.destroy).pack(fill="x", pady=8)

    # ----- Right side: welcome / tips
    right = ttk.Frame(body, style="Card.TFrame")
    right.pack(side="left", fill="both", expand=True)

    tips = tk.Text(right, height=14, wrap="word", borderwidth=0,
                   bg=root._swag["paper"], fg="black")
    tips.insert("end",
        "Welcome!\
\
"
        "\u2022 Use the Printavo Sync section to synchronize data from Printavo.\
"
        "\u2022 Sync All Data will update customers, orders, and payments.\
"
        "\u2022 Use Views for statements, reconciliation, or A/R aging.\
"
        "\u2022 All actions are keyboard-friendly: Tab/Enter work everywhere.\
"
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
