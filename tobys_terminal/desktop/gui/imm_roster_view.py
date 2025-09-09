import tkinter as tk
import sys, os
from tkinter import ttk, messagebox
from datetime import datetime
from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.css_swag_colors import (FOREST_GREEN, PALM_GREEN, CORAL_ORANGE, COCONUT_CREAM, TAN_SAND, PALM_BARK)
from tobys_terminal.shared.pdf_export import generate_imm_production_pdf
from tobys_terminal.shared.order_utils import add_order
from tobys_terminal.shared.date_util import create_date_picker, parse_date_input, safe_set_date
from tobys_terminal.shared.settings import get_setting, set_setting
from tobys_terminal.shared.imm_import import open_imm_import_window

try:
    from config import IMM_EXCLUDED_STATUSES, IMM_EXCLUDED_P_STATUSES
except ImportError:
    pass

COL_META = {
        "po":      {"db": "po_number",   "type": "entry"},
        "project": {"db": "nickname",    "type": "entry"},
        "in_hand": {"db": "in_hand_date","type": "entry_date"},
        "firm":    {"db": "firm_date",   "type": "toggle_yes_no"},
        "invoice": {"db": "invoice_number","type": "entry"},
        "process": {"db": "process",     "type": "combo", "options": ["", "DTF", "EMB", "PAT", "MIX"]},
        "status":  {"db": "status",      "type": "combo", "options": [
            "", "Need Paperwork", "Need Product", "Need Files", "Need Sewout",
            "Need Approval", "Issue", "Inline-EMB", "Inline-DTF", "Inline-PAT",
            "Complete", "Done Done"]},
        "p_status": {"db": "p_status",   "type": "combo", "options": [
            "", "Not Started", "In Progress", "Completed", "On Hold"
        ]},
        "notes": {"db": "notes", "type": "entry"}
    }

def open_imm_roster_view(company_name):
    win = tk.Toplevel()
    win.title(f"IMM Production – {company_name}")
    win.geometry("1500x700")
    win.grab_set()

    ttk.Label(win, text=f"📦 IMM Production Terminal", font=("Arial", 16, "bold")).pack(pady=10)

    # --- Global Notes Section ---
    notes_frame = ttk.Frame(win)
    notes_frame.pack(fill="x", padx=10, pady=(10, 0))

    ttk.Label(notes_frame, text="Global Notes:", font=("Arial", 10, "bold")).pack(anchor="w")
    notes_var = tk.StringVar()
    notes_entry = tk.Text(notes_frame, height=3, wrap="word")
    notes_entry.pack(fill="x", expand=True, pady=4)
    
    frame = ttk.Frame(win)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    tree = ttk.Treeview(frame, columns=(
        "po", "project", "in_hand", "firm", "invoice", "process", "status", "p_status", "notes"
    ), show="headings")
    style = ttk.Style()
    style.configure("Treeview", rowheight=26)
    style.map("Treeview")  # Clears hover colors for consistency

    tree.tag_configure("evenrow", background=COCONUT_CREAM)  # light gray
    tree.tag_configure("oddrow", background=TAN_SAND)   # white
    tree.tag_configure("highlight", background=PALM_GREEN)  # Highlight for newly matched rows

    headers = [
        ("po", "PO #", 60),
        ("project", "Project Name", 220),
        ("in_hand", "In Hands Date", 100),
        ("firm", "Firm Date", 70),
        ("invoice", "Invoice #", 70),
        ("process", "Process", 70),
        ("status", "Status", 140),
        ("p_status", "P-Status", 220),
        ("notes", "Notes", 260)
    ]

    for key, label, width in headers:
        tree.heading(key, text=label, command=lambda _key=key: sort_by(_key))
        tree.column(key, width=width)

    # Add vertical scrollbar
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    vsb.pack(side='right', fill='y')
    tree.configure(yscrollcommand=vsb.set)

    # Add horizontal scrollbar
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    hsb.pack(side='bottom', fill='x')
    tree.configure(xscrollcommand=hsb.set)

    add_frame = ttk.LabelFrame(win, text="➕ Add New Order")
    add_frame.pack(fill="x", padx=10, pady=6)

    add_entries = {}

    for key, meta in COL_META.items():
        if key == "firm":
            continue  # toggle field, not needed in add

        lbl = ttk.Label(add_frame, text=meta.get("db", key))
        lbl.pack(side="left", padx=3)

        # 👇 Swap entry for date picker if it's a date field
        if meta.get("type") == "entry_date":
            ent = create_date_picker(add_frame, width=12)
        elif meta.get("type") == "combo":
            ent = ttk.Combobox(add_frame, values=meta.get("options", []), width=14)
        else:
            ent = ttk.Entry(add_frame, width=14)

        ent.pack(side="left", padx=3)
        add_entries[key] = ent

    def submit_new_order():
        field_map = {}
        for key, meta in COL_META.items():
            if key == "firm":
                field_map[meta["db"]] = "No"
            elif key in add_entries:
                val = add_entries[key].get().strip()
                if meta["type"] == "entry_date" and val:
                    parsed = parse_date_input(val)
                    if not parsed:
                        messagebox.showerror("Error", f"Invalid date: {val}")
                        return
                    val = parsed
                field_map[meta["db"]] = val
        
        # Check if an order with this PO number already exists
        po_number = field_map.get("po_number", "").strip()
        if po_number:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM imm_orders WHERE po_number = ?", (po_number,))
            existing = cur.fetchone()
            conn.close()
            
            if existing:
                if messagebox.askyesno("PO Already Exists", 
                                      f"An order with PO #{po_number} already exists. Update it?"):
                    # Update existing order
                    order_id = existing[0]
                    conn = get_connection()
                    cur = conn.cursor()
                    
                    # Build update query
                    set_clauses = []
                    values = []
                    for db_field, value in field_map.items():
                        if value:  # Only update non-empty fields
                            set_clauses.append(f"{db_field} = ?")
                            values.append(value)
                    
                    if set_clauses:
                        query = f"UPDATE imm_orders SET {', '.join(set_clauses)} WHERE id = ?"
                        values.append(order_id)
                        cur.execute(query, values)
                        conn.commit()
                        conn.close()
                        messagebox.showinfo("Success", f"Order with PO #{po_number} updated!")
                    else:
                        conn.close()
                        messagebox.showinfo("No Changes", "No fields to update.")
                else:
                    return  # User chose not to update
            else:
                # Add new order
                add_order("imm_orders", field_map)
                messagebox.showinfo("Success", f"New order with PO #{po_number} added!")
        else:
            # No PO number provided, just add the order
            add_order("imm_orders", field_map)
            messagebox.showinfo("Success", "New order added!")
            
        load_imm_orders()
        load_global_notes()
        for e in add_entries.values():
            if hasattr(e, 'delete'):
                e.delete(0, tk.END)
            elif hasattr(e, 'set'):
                e.set('')

    ttk.Button(add_frame, text="➕ Add", command=submit_new_order).pack(side="left", padx=10)

    tree.pack(fill="both", expand=True)

    def load_global_notes():
        """Load global notes from settings"""
        notes_text = get_setting('imm_notes', '')
        notes_entry.delete("1.0", "end")  # Clear existing text
        notes_entry.insert("1.0", notes_text)

    def save_global_notes():
        """Save global notes to settings"""
        notes_text = notes_entry.get("1.0", "end-1c")  # Get text without trailing newline
        set_setting('imm_notes', notes_text)
        messagebox.showinfo("Notes Saved", "Global notes have been saved.")

    save_btn = ttk.Button(notes_frame, text="💾 Save Notes", command=save_global_notes)
    save_btn.pack(anchor="e", pady=(0, 5))
    
    load_global_notes()

    def sort_by(col_key, reverse=False):
        data = [(tree.set(child, col_key), child) for child in tree.get_children('')]

        # Try to sort as date, number, or fallback to string
        def try_cast(val):
            # Handle empty values - they should sort to the bottom in ascending order
            if not val or val.strip() == "":
                # Return a "maximum" value for ascending sort (will be at the bottom)
                # For descending sort, this will be reversed later
                if col_key == "in_hand":
                    return datetime.max  # Latest possible date for empty dates
                return float('inf') if col_key in ["invoice", "po"] else "zzzzz"  # For text, sort after all letters
            
            # For dates, try to parse
            if col_key == "in_hand":
                try:
                    # Try MM/DD/YYYY format first
                    return datetime.strptime(val, "%m/%d/%Y")
                except ValueError:
                    try:
                        # Then try YYYY-MM-DD format
                        return datetime.strptime(val, "%Y-%m-%d")
                    except ValueError:
                        # If it's not a valid date, treat it as text
                        return val.lower()
            
            # For numeric columns
            if col_key in ["invoice", "po"]:
                try:
                    return float(val)
                except ValueError:
                    return val.lower()
            
            # Default case: sort as text
            return val.lower()

        # Sort the data
        data.sort(key=lambda t: try_cast(t[0]), reverse=reverse)

        for index, (val, item) in enumerate(data):
            tree.move(item, '', index)

        # Re-apply row striping
        for i, item in enumerate(tree.get_children('')):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            tree.item(item, tags=(tag,))

        # Toggle sort direction next time
        tree.heading(col_key, command=lambda: sort_by(col_key, not reverse))


    def load_imm_orders():
        tree.delete(*tree.get_children())
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, po_number, nickname, in_hand_date, firm_date,
                invoice_number, process, status, p_status, notes, customer_due_date
            FROM imm_orders
            WHERE
                status != 'Hidden'
                AND LOWER(status) NOT IN ('cancelled', 'archived', 'done done')
            ORDER BY
                CASE status
                    WHEN 'Complete and Ready for Pickup' THEN 1
                    WHEN 'Inline-EMB' THEN 2
                    WHEN 'Inline-DTF' THEN 3
                    WHEN 'Inline-PAT' THEN 4
                    WHEN 'Waiting Product' THEN 5
                    WHEN 'Need Sewout' THEN 6
                    WHEN 'Need File' THEN 7
                    WHEN 'Need Order' THEN 8
                    ELSE 9
                END,
                COALESCE(customer_due_date, in_hand_date) ASC
        """)

        rows = cur.fetchall()
        conn.close()
        
        for i, row in enumerate(rows):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            row = list(row)
            
            # Use customer_due_date for display if available
            if row[10]:  # customer_due_date is at index 10
                row[3] = row[10]  # Replace in_hand_date with customer_due_date
            
            # Format in_hand_date (index 3) from YYYY-MM-DD to MM/DD/YYYY
            if row[3]:  # Only if date exists
                try:
                    row[3] = datetime.strptime(row[3], "%Y-%m-%d").strftime("%m/%d/%Y")
                except ValueError:
                    pass  # Leave it as-is if invalid
            
            tree.insert("", "end", iid=row[0], values=row[1:10], tags=(tag,))
        # Add this line to sort by in_hand date initially
        sort_by("in_hand")

    # --- Inline edit support ---

    def update_db(order_id: int, field: str, value: str):
        # Only allow columns from COL_META
        valid_columns = [meta["db"] for meta in COL_META.values()]
        if field not in valid_columns:
            print(f"Skipping invalid field: {field}")
            return

        conn = get_connection()
        cur = conn.cursor()
        print(f"Updating order {order_id} field '{field}' to value: {value}")

        cur.execute(f"UPDATE imm_orders SET {field} = ? WHERE id = ?", (value, order_id))
        conn.commit()
        conn.close()
        load_imm_orders()

    _active_editor = {"widget": None}

    def destroy_active_editor():
        w = _active_editor.get("widget")
        if w and w.winfo_exists():
            w.destroy()
        _active_editor["widget"] = None

    def start_inline_edit(event):
        destroy_active_editor()

        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = tree.identify_row(event.y)
        col_id = tree.identify_column(event.x)
        if not row_id or not col_id:
            return

        cols = ["po", "project", "in_hand", "firm", "invoice", "process", "status", "p_status", "notes"]
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except:
            return
        if col_index < 0 or col_index >= len(cols):
            return
        col_key = cols[col_index]
        meta = COL_META.get(col_key)
        if not meta:
            return

        if meta["type"] == "toggle_yes_no":
            current = tree.set(row_id, col_key).strip() or "No"
            new_val = "No" if current.lower().startswith("y") else "Yes"
            update_db(int(row_id), meta["db"], new_val)
            return

        bbox = tree.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        curr_val = tree.set(row_id, col_key).strip()

        def commit(val):
            destroy_active_editor()
            update_db(int(row_id), meta["db"], val)

        # Start editing
        editor = None

        if meta["type"] == "entry_date":
            editor = create_date_picker(tree.master, width=12)
            try:
                parsed_date = parse_date_input(curr_val)
                if parsed_date:
                    editor.set_date(parsed_date)
            except:
                pass  # leave it alone if not valid

            def save_date(_):
                val = editor.get()
                if val:
                    parsed = parse_date_input(val)
                    if parsed is None:
                        messagebox.showerror("Invalid date", "Please enter a valid date.")
                        editor.focus_set()
                        return
                    val = parsed
                commit(val)

            editor.bind("<Return>", save_date)
            editor.bind("<KP_Enter>", save_date)
            editor.bind("<Escape>", lambda *_: destroy_active_editor())
            editor.place(x=x, y=y, width=w, height=h)
            editor.focus_set()

        elif meta["type"] == "combo":
            editor = ttk.Combobox(tree.master, values=meta["options"])
            editor.set(curr_val)
            editor.place(x=x, y=y, width=w, height=h)
            editor.focus_set()
            editor.bind("<Return>", lambda _: commit(editor.get()))
            editor.bind("<KP_Enter>", lambda _: commit(editor.get()))
            editor.bind("<FocusOut>", lambda _: commit(editor.get()))

        else:
            editor = ttk.Entry(tree.master)
            editor.insert(0, curr_val)
            editor.place(x=x, y=y, width=w, height=h)
            editor.focus_set()

            def save_entry(_):
                commit(editor.get().strip())

            editor.bind("<Return>", save_entry)
            editor.bind("<KP_Enter>", save_entry)
            editor.bind("<Escape>", lambda *_: destroy_active_editor())

        _active_editor["widget"] = editor

    tree.bind("<Double-1>", start_inline_edit)

    button_frame = ttk.Frame(win)
    button_frame.pack(pady=10)

    def sync_with_printavo():
        """Sync orders from Printavo"""
        try:
            # Show a progress indicator
            progress_window = tk.Toplevel(win)
            progress_window.title("Synchronizing with Printavo")
            progress_window.geometry("400x150")
            progress_window.transient(win)
            progress_window.resizable(False, False)
            
            # Center the window
            progress_window.update_idletasks()
            width = progress_window.winfo_width()
            height = progress_window.winfo_height()
            x = (progress_window.winfo_screenwidth() // 2) - (width // 2)
            y = (progress_window.winfo_screenheight() // 2) - (height // 2)
            progress_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # Add a label
            ttk.Label(progress_window, text="Synchronizing IMM orders from Printavo...", 
                     font=("Arial", 12)).pack(pady=20)
            
            # Add a progress bar
            progress = ttk.Progressbar(progress_window, mode="indeterminate")
            progress.pack(fill="x", padx=20, pady=10)
            progress.start()
            
            # Run sync in a separate thread to keep UI responsive
            def run_sync():
                try:
                    from tobys_terminal.shared.printavo_sync import sync_imm_orders
                    result = sync_imm_orders()
                    progress_window.after(0, lambda: complete_sync(result))
                except Exception as e:
                    progress_window.after(0, lambda: complete_sync(False, str(e)))
            
            def complete_sync(success, error_message=None):
                progress.stop()
                progress_window.destroy()
                
                if success:
                    messagebox.showinfo("Sync Complete", "Successfully synchronized IMM orders from Printavo!")
                    load_imm_orders()  # Refresh the view
                else:
                    error_text = f"Error during synchronization: {error_message}" if error_message else "Synchronization failed."
                    messagebox.showerror("Sync Failed", error_text)
            
            # Start the thread
            import threading
            sync_thread = threading.Thread(target=run_sync)
            sync_thread.daemon = True
            sync_thread.start()
            
        except ImportError:
            messagebox.showerror("Module Not Found", 
                               "The printavo_sync module is not available. Please make sure it's installed.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    ttk.Button(button_frame, text="🔄 Sync from Printavo", command=sync_with_printavo).pack(side="left", padx=6)
    ttk.Button(button_frame, text="📥 Import Orders", command=open_imm_import_window).pack(side="left", padx=6)
    ttk.Button(button_frame, text="🔄 Refresh", command=load_imm_orders).pack(side="left", padx=6)
    ttk.Button(button_frame, text="Close", command=win.destroy).pack(side="right", padx=6)

    def print_pdf(mode):
        try:
            path = generate_imm_production_pdf(mode=mode)
            messagebox.showinfo("PDF Created", f"{mode.upper()} PDF created:\n\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Something went wrong:\n{e}")

    ttk.Button(button_frame, text="📄 Print Full IMM", command=lambda: print_pdf("full")).pack(side="left", padx=6)
    ttk.Button(button_frame, text="📄 Print Inline-EMB", command=lambda: print_pdf("emb")).pack(side="left", padx=6)
    ttk.Button(button_frame, text="📄 Print Inline-DTF", command=lambda: print_pdf("dtf")).pack(side="left", padx=6)

    def delete_selected_order():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an order to delete.")
            return
        order_id = selected[0]
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete PO #{tree.set(order_id, 'po')}?"):
            return
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM imm_orders WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        load_imm_orders()

    ttk.Button(button_frame, text="🗑️ Delete", command=delete_selected_order).pack(side="left", padx=6)

    load_imm_orders()