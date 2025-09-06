import tkinter as tk
import os, sys
import sqlite3
from tkinter import ttk, messagebox
from datetime import datetime
import threading
from tobys_terminal.shared.css_swag_colors import (FOREST_GREEN, PALM_GREEN, CORAL_ORANGE, COCONUT_CREAM, TAN_SAND, PALM_BARK)
from tobys_terminal.shared.order_utils import add_order
from tobys_terminal.shared.date_util import create_date_picker, parse_date_input, safe_set_date
from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.settings import get_setting, set_setting

try:
    from config import HARLESTONS_EXCLUDED_STATUSES, HARLESTONS_EXCLUDED_P_STATUSES
except ImportError:
    pass

COL_META = {
    "po_number":        {"type": "entry", "db": "po_number", "width": 100, "label": "PO #"},
    "invoice_number":   {"type": "entry", "db": "invoice_number", "width": 100, "label": "Invoice #"},
    "club_nickname":    {"type": "entry", "db": "club_nickname", "width": 150, "label": "Club"},
    "location":         {"type": "combo", "options": ["HAR", "CSS", "OTW"], "db": "location", "width": 80, "label": "Loc"},
    "process":          {"type": "combo", "options": ["EMB", "DTF"], "db": "process", "width": 80, "label": "Process"},
    "pcs":              {"type": "entry", "db": "pcs", "width": 60, "label": "PCS"},
    "in_hand_date":     {"type": "entry_date", "db": "in_hand_date", "width": 110, "label": "Due Date"},
    "priority":         {"type": "combo", "options": ["High", "Medium", "Low"], "db": "priority", "width": 80, "label": "Priority"},
    "status":           {"type": "combo", "options": ["Pending", "In Progress", "Complete", "Need Sewout", "Need Paperwork", "Need Product", "Need Files", "Need Approval"], "db": "status", "width": 120, "label": "Status"},
    "p_status":         {"type": "combo", "options": ["Unset", "Reviewed", "Confirmed", "In Production", "Complete"], "db": "p_status", "width": 120, "label": "P-Status"},
    "notes":            {"type": "entry", "db": "notes", "width": 200, "label": "Notes"},
    "inside_location":  {"type": "toggle_yes_no", "db": "inside_location", "width": 80, "label": "Inside"},
    "uploaded":         {"type": "toggle_yes_no", "db": "uploaded", "width": 80, "label": "Uploaded"},
    "logo_file":        {"type": "entry", "db": "logo_file", "width": 150, "label": "Logo File"},
    "club_colors":      {"type": "toggle_yes_no", "db": "club_colors", "width": 100, "label": "Club Colors"},
    "colors_verified":  {"type": "toggle_yes_no", "db": "colors_verified", "width": 120, "label": "Colors Verified"},
}

def open_harlestons_roster_view(company_name):
    win = tk.Toplevel()
    win.title(f"Harlestons Production – {company_name}")
    win.geometry("1600x800")
    win.grab_set()
    
    # Active editor tracking
    _active_editor = {"widget": None}
    
    def destroy_active_editor():
        if _active_editor["widget"]:
            try:
                _active_editor["widget"].destroy()
            except:
                pass
            _active_editor["widget"] = None

    # Header
    ttk.Label(win, text=f"🧵 Harlestons Production Terminal", font=("Arial", 16, "bold")).pack(pady=10)

    # Global Notes
    notes_frame = ttk.Frame(win)
    notes_frame.pack(fill="x", padx=10, pady=(10, 0))
    ttk.Label(notes_frame, text="Global Notes:", font=("Arial", 10, "bold")).pack(anchor="w")
    notes_entry = tk.Text(notes_frame, height=3, wrap="word")
    notes_entry.pack(fill="x", expand=True, pady=4)

    def load_notes():
        """Load global notes from settings"""
        notes_text = get_setting('harlestons_notes', '')
        notes_entry.delete("1.0", tk.END)
        notes_entry.insert("1.0", notes_text)

    def save_notes():
        """Save global notes to settings"""
        value = notes_entry.get("1.0", tk.END).strip()
        set_setting('harlestons_notes', value)
        messagebox.showinfo("Saved", "Global notes updated.")

    ttk.Button(notes_frame, text="💾 Save Notes", command=save_notes).pack(anchor="e", pady=(0, 5))
    load_notes()

    # Main frame for treeview
    main_frame = ttk.Frame(win)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Create columns list from COL_META
    cols = list(COL_META.keys())
    
    # Create headers list from COL_META
    headers = [meta["label"] for meta in COL_META.values()]
    
    # Create treeview
    tree = ttk.Treeview(main_frame, columns=cols, show="headings", height=30)
    
    # Configure columns
    for col, meta in COL_META.items():
        tree.heading(col, text=meta["label"])
        tree.column(col, width=meta["width"], anchor="center")
    
    # Style configuration
    style = ttk.Style()
    style.configure("Treeview", rowheight=26)
    style.map("Treeview")  # Clears hover colors for consistency
    
    # Row styling
    tree.tag_configure('oddrow', background=COCONUT_CREAM)
    tree.tag_configure('evenrow', background=TAN_SAND)
    tree.tag_configure('highlight', background=PALM_GREEN)  # For newly matched rows
    
    # Add vertical scrollbar
    vsb = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
    vsb.pack(side='right', fill='y')
    tree.configure(yscrollcommand=vsb.set)
    
    # Add horizontal scrollbar
    hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=tree.xview)
    hsb.pack(side='bottom', fill='x')
    tree.configure(xscrollcommand=hsb.set)
    
    tree.pack(fill="both", expand=True)

    # Add New Order Frame
    add_frame = ttk.LabelFrame(win, text="➕ Add New Harlestons Order")
    add_frame.pack(fill="x", padx=10, pady=(10, 0))

    # Fields to include in the add form
    add_fields = [
        "po_number", "invoice_number", "club_nickname", "location",
        "in_hand_date", "pcs", "process", "logo_file",
        "club_colors", "colors_verified"
    ]

    add_entries = {}

    # Create toggle handler
    def toggle_button(btn, field):
        new_val = "No" if btn["text"] == "Yes" else "Yes"
        btn.config(text=new_val)
        add_entries[field] = new_val

    # Create add form fields
    for field in add_fields:
        meta = COL_META[field]
        ttk.Label(add_frame, text=meta["label"]).pack(side="left", padx=2)

        if meta["type"] == "toggle_yes_no":
            btn = ttk.Button(add_frame, text="No")  # default to "No"
            btn.config(command=lambda b=btn, f=field: toggle_button(b, f))
            btn.pack(side="left", padx=2)
            add_entries[field] = "No"  # Track the value separately

        elif meta["type"] == "combo":
            combo = ttk.Combobox(add_frame, values=meta["options"], width=12, state="readonly")
            combo.set(meta["options"][0] if meta["options"] else "")  # default to first option
            combo.pack(side="left", padx=2)
            add_entries[field] = combo

        elif meta["type"] == "entry_date":
            cal = create_date_picker(add_frame)
            cal.pack(side="left", padx=2)
            add_entries[field] = cal

        else:
            ent = ttk.Entry(add_frame, width=12)
            ent.pack(side="left", padx=2)
            add_entries[field] = ent

    # Submit function
    def submit_new_order():
        field_map = {}

        for field, widget in add_entries.items():
            # Handle toggle button fields stored as strings
            if isinstance(widget, str):
                val = widget
            # Handle entry and combobox widgets
            else:
                val = widget.get().strip()

            # Special case for date parsing
            if field == "in_hand_date" and val:
                parsed = parse_date_input(val)
                if not parsed:
                    messagebox.showerror("Invalid Date", f"Couldn't understand date: {val}")
                    return
                val = parsed

            field_map[field] = val

        # Set default statuses
        field_map["status"] = "Pending"
        field_map["p_status"] = "Unset"
        
        # Check if an order with this PO number already exists
        po_number = field_map.get("po_number", "").strip()
        if po_number:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM harlestons_orders WHERE po_number = ?", (po_number,))
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
                        query = f"UPDATE harlestons_orders SET {', '.join(set_clauses)} WHERE id = ?"
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
                add_order("harlestons_orders", field_map)
                messagebox.showinfo("Success", f"New order with PO #{po_number} added!")
        else:
            # No PO number provided, just add the order
            add_order("harlestons_orders", field_map)
            messagebox.showinfo("Success", "New order added!")

        # Refresh the view
        refresh_tree()

        # Clear inputs
        for field, widget in add_entries.items():
            if isinstance(widget, str):
                add_entries[field] = "No"  # Reset toggle fields to "No"
                # Find and update the button
                for child in add_frame.winfo_children():
                    if isinstance(child, ttk.Button) and child.cget("text") in ["Yes", "No"]:
                        if field in ["club_colors", "colors_verified"] and child.cget("text") == "Yes":
                            child.config(text="No")
            elif isinstance(widget, ttk.Combobox):
                widget.set(widget["values"][0] if widget["values"] else "")  # Reset to first value
            elif hasattr(widget, 'delete'):
                widget.delete(0, tk.END)
            elif hasattr(widget, 'set'):
                widget.set('')

    ttk.Button(add_frame, text="➕ Add", command=submit_new_order).pack(side="left", padx=10)

    # Refresh function
    def refresh_tree():
        for row in tree.get_children():
            tree.delete(row)
        load_orders()

    # Load orders function
    def load_orders():
        conn = get_connection()
        conn.row_factory = sqlite3.Row  # optional, but helpful
        cur = conn.cursor()
        
        # Build the query dynamically from COL_META
        columns = ", ".join([f"{meta['db']}" for meta in COL_META.values()])
        
        cur.execute(f"""
            SELECT id, {columns}
            FROM harlestons_orders
            WHERE
                status != 'Hidden'
                AND TRIM(LOWER(p_status)) NOT IN (
                    'done', 'template', 'done done', 'complete', 'cancelled', 'archived', 'shipped',
                    'picked up', 'harlestons -- invoiced', 'harlestons -- no order pending',
                    'harlestons -- picked up', 'harlestons-need sewout'
                )
            ORDER BY in_hand_date ASC
        """)

        rows = cur.fetchall()
        conn.close()
        
        for i, row in enumerate(rows):
            # Format date fields for display
            values = []
            for col in cols:
                value = row[col] if col in row.keys() else ""
                
                # Format date if it's a date field
                if col == "in_hand_date" and value:
                    try:
                        value = datetime.strptime(value, "%Y-%m-%d").strftime("%m/%d/%Y")
                    except ValueError:
                        pass  # Leave as is if not valid
                
                values.append(value)
            
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            tree.insert("", "end", iid=str(row["id"]), values=values, tags=(tag,))

    # Inline editing
    def update_db(order_id, field, value):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(f"UPDATE harlestons_orders SET {field} = ? WHERE id = ?", (value, order_id))
            conn.commit()
            conn.close()
            refresh_tree()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update record: {e}")

    def start_inline_edit(event):
        destroy_active_editor()

        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = tree.identify_row(event.y)
        col_id = tree.identify_column(event.x)
        if not row_id or not col_id:
            return

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
        curr_val = tree.set(row_id, col_key)

        def commit(val):
            destroy_active_editor()
            update_db(int(row_id), meta["db"], val)

        editor = None
        if meta["type"] == "entry_date":
            editor = create_date_picker(tree.master)
            if curr_val:
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

    # Button frame
    btn_frame = ttk.Frame(win)
    btn_frame.pack(fill="x", padx=10, pady=(0, 10))
    
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
            ttk.Label(progress_window, text="Synchronizing Harlestons orders from Printavo...", 
                     font=("Arial", 12)).pack(pady=20)
            
            # Add a progress bar
            progress = ttk.Progressbar(progress_window, mode="indeterminate")
            progress.pack(fill="x", padx=20, pady=10)
            progress.start()
            
            # Run sync in a separate thread to keep UI responsive
            def run_sync():
                try:
                    from tobys_terminal.shared.printavo_sync import sync_harlestons_orders
                    result = sync_harlestons_orders()
                    progress_window.after(0, lambda: complete_sync(result))
                except Exception as e:
                    progress_window.after(0, lambda: complete_sync(False, str(e)))
            
            def complete_sync(success, error_message=None):
                progress.stop()
                progress_window.destroy()
                
                if success:
                    messagebox.showinfo("Sync Complete", "Successfully synchronized Harlestons orders from Printavo!")
                    refresh_tree()  # Refresh the view
                else:
                    error_text = f"Error during synchronization: {error_message}" if error_message else "Synchronization failed."
                    messagebox.showerror("Sync Failed", error_text)
            
            # Start the thread
            sync_thread = threading.Thread(target=run_sync)
            sync_thread.daemon = True
            sync_thread.start()
            
        except ImportError:
            messagebox.showerror("Module Not Found", 
                               "The printavo_sync module is not available. Please make sure it's installed.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    ttk.Button(btn_frame, text="🔄 Sync from Printavo", command=sync_with_printavo).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="🔄 Refresh", command=refresh_tree).pack(side="left", padx=6)
    
    def delete_selected_order():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an order to delete.")
            return
        
        order_id = selected[0]
        po_number = tree.item(order_id, "values")[cols.index("po_number")]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete order with PO #{po_number}?"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM harlestons_orders WHERE id = ?", (order_id,))
            conn.commit()
            conn.close()
            refresh_tree()
            messagebox.showinfo("Success", f"Order with PO #{po_number} has been deleted.")
    
    ttk.Button(btn_frame, text="🗑️ Delete", command=delete_selected_order).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Close", command=win.destroy).pack(side="right", padx=6)

    # Export to PDF button
    def export_to_pdf():
        try:
            from tobys_terminal.shared.pdf_export import generate_harlestons_production_pdf
            path = generate_harlestons_production_pdf()
            messagebox.showinfo("PDF Created", f"Harlestons production PDF created:\n\n{path}")
        except ImportError:
            messagebox.showerror("Module Not Found", "PDF export functionality is not available.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create PDF: {e}")
    
    ttk.Button(btn_frame, text="📄 Export to PDF", command=export_to_pdf).pack(side="left", padx=6)

    # Sort function
    def sort_by(col_key, reverse=False):
        col_index = cols.index(col_key)
        data = [(tree.set(child, col_key), child) for child in tree.get_children('')]

        # Try to sort as date, number, or fallback to string
        def try_cast(val):
            from datetime import datetime
            try:
                return datetime.strptime(val, "%m/%d/%Y")  # for in_hand_date
            except:
                try:
                    return float(val)
                except:
                    return val.lower()

        data.sort(key=lambda t: try_cast(t[0]), reverse=reverse)

        for index, (val, item) in enumerate(data):
            tree.move(item, '', index)

        # Re-apply row striping
        for i, item in enumerate(tree.get_children('')):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            tree.item(item, tags=(tag,))

        # Toggle sort direction next time
        tree.heading(col_key, command=lambda: sort_by(col_key, not reverse))

    # Configure column headings for sorting
    for col in cols:
        tree.heading(col, text=COL_META[col]["label"], command=lambda c=col: sort_by(c))

    # Load orders on startup
    refresh_tree()