"""
IMM Order Import Functionality
Allows importing IMM orders from PDF or CSV files
"""

import os
import pandas as pd
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.date_util import parse_date_input


def parse_imm_orders_file(file_path):
    """
    Parse IMM orders from a PDF or CSV file.
    Returns a list of dictionaries with order information.
    """
    import pandas as pd
    import os
    import re
    
    orders = []
    
    # Determine file type
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.pdf':
        # Parse PDF using pdfplumber (no Java dependency)
        try:
            import pdfplumber
            
            with pdfplumber.open(file_path) as pdf:
                text_content = ""
                for page in pdf.pages:
                    text_content += page.extract_text() + "\n"
                
                # Process the extracted text
                lines = text_content.split('\n')
                headers = None
                
                # Find header line
                for i, line in enumerate(lines):
                    if "PO" in line and "PROJECT NAME" in line and "IN HANDS DATE" in line:
                        headers = line
                        break
                
                if not headers:
                    # Try alternative header detection
                    for i, line in enumerate(lines):
                        if re.search(r'PO.*CLIENT.*PROJECT.*IN HANDS', line, re.IGNORECASE):
                            headers = line
                            break
                
                if headers:
                    # Process data lines
                    current_order = {}
                    for line in lines[lines.index(headers) + 1:]:
                        # Skip empty lines
                        if not line.strip():
                            continue
                            
                        # Check if line starts with a PO number (usually numeric)
                        if re.match(r'^\d{5,}', line.strip()):
                            # Save previous order if exists
                            if current_order and 'po_number' in current_order:
                                orders.append(current_order)
                            
                            # Start new order
                            parts = line.split()
                            po_number = parts[0]
                            
                            # Extract project name (everything between PO and date)
                            project_name = ""
                            date_index = -1
                            
                            # Look for date pattern in the line
                            date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', line)
                            if date_match:
                                date_index = line.index(date_match.group(0))
                                project_name = line[len(po_number):date_index].strip()
                                in_hand_date = date_match.group(0)
                            else:
                                project_name = " ".join(parts[1:])
                                in_hand_date = ""
                            
                            # Check for "YES" in the line for firm date
                            firm_date = "Yes" if "YES" in line.upper() else "No"
                            
                            # Extract notes (anything after the date and YES/NO)
                            notes = ""
                            if date_index > 0:
                                notes_part = line[date_index + 10:].strip()  # 10 is length of date MM/DD/YYYY
                                if "YES" in notes_part.upper() or "NO" in notes_part.upper():
                                    notes = notes_part[3:].strip()  # Skip YES/NO
                                else:
                                    notes = notes_part
                            
                            current_order = {
                                'po_number': po_number,
                                'nickname': project_name,
                                'in_hand_date': in_hand_date,
                                'firm_date': firm_date,
                                'notes': notes,
                                'status': 'Need Review',
                                'p_status': ''
                            }
                
                # Add the last order if exists
                if current_order and 'po_number' in current_order:
                    orders.append(current_order)
                    
        except Exception as e:
            print(f"Error parsing PDF: {e}")
            import traceback
            traceback.print_exc()
            return []
            
    elif file_ext == '.csv':
        # Parse CSV using pandas
        try:
            df = pd.read_csv(file_path)
            
            # Clean up column names
            df.columns = [col.strip().upper() for col in df.columns]
            
            # Map columns to our database fields
            for _, row in df.iterrows():
                # Try different possible column names
                po_col = next((col for col in df.columns if 'PO' in col), None)
                project_col = next((col for col in df.columns if 'PROJECT' in col or 'NAME' in col), None)
                date_col = next((col for col in df.columns if 'DATE' in col or 'HAND' in col), None)
                firm_col = next((col for col in df.columns if 'FIRM' in col), None)
                notes_col = next((col for col in df.columns if 'NOTE' in col), None)
                p_status_col = next((col for col in df.columns if 'P_STATUS' in col or 'P-STATUS' in col or 'PSTATUS' in col), None)
                
                order = {
                    'po_number': str(row.get(po_col, '')) if po_col else '',
                    'nickname': str(row.get(project_col, '')) if project_col else '',
                    'in_hand_date': row.get(date_col, None) if date_col else None,
                    'firm_date': 'Yes' if firm_col and str(row.get(firm_col, '')).strip().upper() == 'YES' else 'No',
                    'notes': str(row.get(notes_col, '')) if notes_col else '',
                    'status': 'Need Review',
                    'p_status': str(row.get(p_status_col, '')) if p_status_col else ''
                }
                orders.append(order)
        except Exception as e:
            print(f"Error parsing CSV: {e}")
            import traceback
            traceback.print_exc()
            return []

    
    return orders


def import_imm_orders(orders):
    """
    Import IMM orders into the database.
    Updates existing orders if PO number matches, otherwise creates new orders.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    inserted = 0
    updated = 0
    skipped = 0
    
    for order in orders:
        po_number = order.get('po_number', '').strip()
        if not po_number:
            skipped += 1
            continue
        
        # Format the in_hand_date if it exists
        in_hand_date = order.get('in_hand_date')
        if in_hand_date:
            parsed_date = parse_date_input(str(in_hand_date))
            in_hand_date = parsed_date if parsed_date else None
        
        # Check if order with this PO number already exists
        cur.execute("SELECT id, status FROM imm_orders WHERE po_number = ?", (po_number,))
        existing = cur.fetchone()
        
        if existing:
            # Update existing order, preserving status
            order_id, current_status = existing
            
            # Build update query
            set_clauses = []
            values = []
            
            # Only update fields that are provided
            if 'nickname' in order and order['nickname']:
                set_clauses.append("nickname = ?")
                values.append(order['nickname'])
                
            if in_hand_date:
                set_clauses.append("in_hand_date = ?")
                values.append(in_hand_date)
                
            if 'firm_date' in order:
                set_clauses.append("firm_date = ?")
                values.append(order['firm_date'])
                
            if 'notes' in order and order['notes']:
                set_clauses.append("notes = ?")
                values.append(order['notes'])
            
            # Add p_status update if provided
            if 'p_status' in order and order['p_status']:
                set_clauses.append("p_status = ?")
                values.append(order['p_status'])
            
            if set_clauses:
                query = f"UPDATE imm_orders SET {', '.join(set_clauses)} WHERE id = ?"
                values.append(order_id)
                cur.execute(query, values)
                updated += 1
        else:
            # Insert new order
            cur.execute("""
                INSERT INTO imm_orders (
                    po_number, nickname, in_hand_date, firm_date, 
                    status, notes, p_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                po_number,
                order.get('nickname', ''),
                in_hand_date,
                order.get('firm_date', 'No'),
                'Need Review',  # Default status
                order.get('notes', ''),
                order.get('p_status', '')  # Use provided p_status or empty string
            ))
            inserted += 1
    
    conn.commit()
    conn.close()
    
    return {
        'inserted': inserted,
        'updated': updated,
        'skipped': skipped
    }
def import_imm_orders(orders):
    """
    Import IMM orders into the database.
    Updates existing orders if PO number matches, otherwise creates new orders.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    inserted = 0
    updated = 0
    skipped = 0
    
    for order in orders:
        po_number = order.get('po_number', '').strip()
        if not po_number:
            skipped += 1
            continue
        
        # Format the in_hand_date if it exists
        in_hand_date = order.get('in_hand_date')
        if in_hand_date:
            parsed_date = parse_date_input(str(in_hand_date))
            in_hand_date = parsed_date if parsed_date else None
        
        # Check if order with this PO number already exists
        cur.execute("SELECT id, status FROM imm_orders WHERE po_number = ?", (po_number,))
        existing = cur.fetchone()
        
        if existing:
            # Update existing order, preserving status
            order_id, current_status = existing
            
            # Build update query
            set_clauses = []
            values = []
            
            # Only update fields that are provided
            if 'nickname' in order and order['nickname']:
                set_clauses.append("nickname = ?")
                values.append(order['nickname'])
                
            if in_hand_date:
                set_clauses.append("in_hand_date = ?")
                values.append(in_hand_date)
                
            if 'firm_date' in order:
                set_clauses.append("firm_date = ?")
                values.append(order['firm_date'])
                
            if 'notes' in order and order['notes']:
                set_clauses.append("notes = ?")
                values.append(order['notes'])
            
            # Add p_status update if provided
            if 'p_status' in order and order['p_status']:
                set_clauses.append("p_status = ?")
                values.append(order['p_status'])
            
            if set_clauses:
                query = f"UPDATE imm_orders SET {', '.join(set_clauses)} WHERE id = ?"
                values.append(order_id)
                cur.execute(query, values)
                updated += 1
        else:
            # Insert new order
            cur.execute("""
                INSERT INTO imm_orders (
                    po_number, nickname, in_hand_date, firm_date, 
                    status, notes, p_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                po_number,
                order.get('nickname', ''),
                in_hand_date,
                order.get('firm_date', 'No'),
                'Need Review',  # Default status
                order.get('notes', ''),
                order.get('p_status', '')  # Use provided p_status or empty string
            ))
            inserted += 1
    
    conn.commit()
    conn.close()
    
    return {
        'inserted': inserted,
        'updated': updated,
        'skipped': skipped
    }



def open_imm_import_window(refresh_callback=None):
    """
    Open a window to import IMM orders from a file.
    
    refresh_callback: Optional function to call after import to refresh the main view
    """
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import os
    
    win = tk.Toplevel()
    win.title("Import IMM Orders")
    win.geometry("800x500")
    win.resizable(True, True)
    
    # Header
    header = ttk.Label(win, text="Import IMM Orders", font=("Arial", 14, "bold"))
    header.pack(pady=10)
    
    # Instructions
    instructions = ttk.Label(win, text="Select a PDF or CSV file containing IMM orders.\n"
                            "For best results with PDF files, ensure the file has a clear structure.")
    instructions.pack(pady=5)
    
    # File selection frame
    file_frame = ttk.Frame(win)
    file_frame.pack(fill="x", padx=20, pady=10)
    
    ttk.Label(file_frame, text="Select File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    file_path_var = tk.StringVar()
    file_entry = ttk.Entry(file_frame, textvariable=file_path_var, width=50)
    file_entry.grid(row=0, column=1, padx=5, pady=5)
    
    def browse_file():
        file_types = [
            ("All Supported Files", "*.pdf;*.csv"),
            ("PDF Files", "*.pdf"),
            ("CSV Files", "*.csv"),
            ("All Files", "*.*")
        ]
        file_path = filedialog.askopenfilename(filetypes=file_types)
        if file_path:
            file_path_var.set(file_path)
            # Auto-preview when file is selected
            preview_file()
    
    browse_btn = ttk.Button(file_frame, text="Browse...", command=browse_file)
    browse_btn.grid(row=0, column=2, padx=5, pady=5)
    
    # Preview frame
    preview_frame = ttk.LabelFrame(win, text="Preview")
    preview_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
   # Create treeview for preview
    tree = ttk.Treeview(preview_frame, columns=("po", "project", "in_hand", "firm", "notes", "p_status"), show="headings")
    tree.heading("po", text="PO #")
    tree.heading("project", text="Project Name")
    tree.heading("in_hand", text="In Hands Date")
    tree.heading("firm", text="Firm")
    tree.heading("notes", text="Notes")
    tree.heading("p_status", text="P-Status")

    tree.column("po", width=80)
    tree.column("project", width=200)
    tree.column("in_hand", width=100)
    tree.column("firm", width=50)
    tree.column("notes", width=150)
    tree.column("p_status", width=100)

    
    # Add scrollbars
    vsb = ttk.Scrollbar(preview_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(preview_frame, orient="horizontal", command=tree.xview)
    
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    
    vsb.pack(side='right', fill='y')
    hsb.pack(side='bottom', fill='x')
    tree.pack(fill="both", expand=True)
    
    # Status label
    status_var = tk.StringVar()
    status_label = ttk.Label(win, textvariable=status_var, font=("Arial", 10))
    status_label.pack(pady=5)
    
    def preview_file():
        file_path = file_path_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid file.")
            return
        
        # Clear existing items
        tree.delete(*tree.get_children())
        
        # Parse the file
        try:
            status_var.set("Parsing file... Please wait.")
            win.update()  # Update the UI to show the status
            
            orders = parse_imm_orders_file(file_path)
            
            if not orders:
                status_var.set("No orders found in the file.")
                return
            
            # Display orders in the treeview
            for order in orders:
                tree.insert("", "end", values=(
                    order.get('po_number', ''),
                    order.get('nickname', ''),
                    order.get('in_hand_date', ''),
                    order.get('firm_date', ''),
                    order.get('notes', ''),
                    order.get('p_status', '')
                ))
            
            status_var.set(f"Found {len(orders)} orders in the file.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            status_var.set(f"Error parsing file: {str(e)}")
            messagebox.showerror("Error", f"Failed to parse file: {str(e)}")
    
    def import_orders():
        file_path = file_path_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid file.")
            return
        
        # Parse the file
        try:
            status_var.set("Parsing file... Please wait.")
            win.update()  # Update the UI to show the status
            
            orders = parse_imm_orders_file(file_path)
            
            if not orders:
                messagebox.showinfo("Info", "No orders found in the file.")
                return
            
            # Confirm import
            if not messagebox.askyesno("Confirm Import", f"Import {len(orders)} orders?"):
                return
            
            # Import orders
            status_var.set("Importing orders... Please wait.")
            win.update()  # Update the UI to show the status
            
            result = import_imm_orders(orders)
            
            # Show result
            messagebox.showinfo("Import Complete", 
                               f"Import completed:\n"
                               f"- {result['inserted']} new orders added\n"
                               f"- {result['updated']} existing orders updated\n"
                               f"- {result['skipped']} orders skipped")
            
            # Refresh the main view if callback provided
            if refresh_callback:
                refresh_callback()
                
            status_var.set(f"Import complete. {result['inserted']} added, {result['updated']} updated.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            status_var.set(f"Error during import: {str(e)}")
            messagebox.showerror("Error", f"Import failed: {str(e)}")
    
    # Button frame
    btn_frame = ttk.Frame(win)
    btn_frame.pack(pady=10)
    
    preview_btn = ttk.Button(btn_frame, text="Preview", command=preview_file)
    preview_btn.pack(side="left", padx=5)
    
    import_btn = ttk.Button(btn_frame, text="Import", command=import_orders)
    import_btn.pack(side="left", padx=5)
    
    close_btn = ttk.Button(btn_frame, text="Close", command=win.destroy)
    close_btn.pack(side="left", padx=5)
    
    # CSV template help
    def show_csv_template():
        template_info = """CSV Template Format:
        
    PO,PROJECT NAME,IN HANDS DATE,FIRM?,IMM NOTES,P_STATUS
    20252380,Citadel Basketball Embroidery,8/20/2025,YES,Sample note,In Progress
    20252410,Vector Force Development,8/27/2025,NO,Another note,Not Started
        
    Save your PDF as CSV or create a new CSV file with these columns.
    The P_STATUS column is optional but will be used if provided."""
        
        messagebox.showinfo("CSV Template", template_info)

    
    help_btn = ttk.Button(btn_frame, text="CSV Template", command=show_csv_template)
    help_btn.pack(side="left", padx=5)
    
    win.focus_set()
