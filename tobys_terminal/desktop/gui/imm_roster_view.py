import tkinter as tk
import sys, os
from tkinter import ttk, messagebox
from datetime import datetime
from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.css_swag_colors import (FOREST_GREEN, PALM_GREEN, CORAL_ORANGE, COCONUT_CREAM, TAN_SAND, PALM_BARK)
from tobys_terminal.shared.pdf_export import generate_imm_production_pdf
from tobys_terminal.shared.order_utils import add_order
from tobys_terminal.shared.date_util import create_date_picker, parse_date_input
from tobys_terminal.shared.settings import get_setting, set_setting

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

    headers = [
        ("po", "PO #", 80),
        ("project", "Project Name", 180),
        ("in_hand", "In Hands Date", 110),
        ("firm", "Firm Date", 90),
        ("invoice", "Invoice #", 80),
        ("process", "Process", 80),
        ("status", "Status", 220),
        ("p_status", "P-Status", 220),
        ("notes", "Notes", 300)
    ]

    for key, label, width in headers:
        tree.heading(key, text=label, command=lambda _key=key: sort_by(_key))

        tree.column(key, width=width)

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
        add_order("imm_orders", field_map)
        load_imm_orders()
        load_global_notes()
        for e in add_entries.values():
            e.delete(0, tk.END)

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
        save_btn = ttk.Button(notes_frame, text="💾 Save Notes", command=save_global_notes)
        save_btn.pack(anchor="e", pady=(0, 5))

    load_global_notes()





    def sort_by(col_key, reverse=False):
        data = [(tree.set(child, col_key), child) for child in tree.get_children('')]

        # Try to sort as date, number, or fallback to string
        def try_cast(val):
            from datetime import datetime
            try:
                return datetime.strptime(val, "%m/%d/%Y")  # for in_hand
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
                AND LOWER(status) NOT IN ('cancelled', 'archived')
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


    def parse_date_input(s: str) -> str | None:
        """Accepts MM/DD/YYYY or YYYY-MM-DD and returns normalized YYYY-MM-DD string, or None if invalid"""
        import datetime
        s = s.strip()
        if not s:
            return ""
        for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                dt = datetime.datetime.strptime(s, fmt)
                return dt.strftime("%Y-%m-%d")  # Save in standard format
            except ValueError:
                continue
        return None


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

        cols = ["po", "project", "in_hand", "firm", "invoice", "process", "status", "notes"]  # adjust for Harlestons if needed
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
