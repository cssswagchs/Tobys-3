import tkinter as tk
import os, sys
import sqlite3
from tkinter import ttk, messagebox
from tobys_terminal.shared.css_swag_colors import (FOREST_GREEN, PALM_GREEN, CORAL_ORANGE, COCONUT_CREAM, TAN_SAND, PALM_BARK)
from tobys_terminal.shared.order_utils import add_order, update_db
from tobys_terminal.shared.date_util import create_date_picker, parse_date_input, create_calendar_entry
from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.reprint import save_field_value
_active_editor = {"widget": None}

try:
    from config import HARLESTONS_EXCLUDED_STATUSES, HARLESTONS_EXCLUDED_P_STATUSES
except ImportError:
    pass

COL_META = {
    "po_number":        {"type": "entry", "db": "po_number"},
    "invoice_number":   {"type": "entry", "db": "invoice_number"},
    "club_nickname":    {"type": "entry", "db": "club_nickname"},
    "location":         {"type": "combo", "options": ["HAR", "CSS", "OTW"], "db": "location"},
    "in_hand_date":     {"type": "entry_date", "db": "in_hand_date"},
    "pcs":              {"type": "entry", "db": "pcs"},
    "process":          {"type": "combo", "options": ["EMB", "DTF"], "db": "process"},
    "logo_file":        {"type": "entry", "db": "logo_file"},
    "club_colors":      {"type": "toggle_yes_no", "db": "club_colors"},
    "colors_verified":  {"type": "toggle_yes_no", "db": "colors_verified"},
    "status":           {"type": "combo", "options": ["Pending", "In Progress", "Complete"], "db": "status"},
    "p_status":         {"type": "combo", "options": ["Unset", "Reviewed", "Confirmed"], "db": "p_status"},
}

def destroy_active_editor():
    if _active_editor["widget"]:
        try:
            _active_editor["widget"].destroy()
        except:
            pass
        _active_editor["widget"] = None

def open_harlestons_roster_view(company_name):
    def refresh_tree():
        for row in tree.get_children():
            tree.delete(row)
        load_orders()

    def load_orders():
        conn = get_connection()
        conn.row_factory = sqlite3.Row  # optional, but helpful
        cur = conn.cursor()
        cur.execute("""
            SELECT id, po_number, invoice_number, club_nickname, location, process, pcs,
                status, in_hand_date, priority, notes, inside_location, uploaded,
                p_status, logo_file, club_colors, colors_verified
            FROM harlestons_orders
            WHERE
                status != 'Hidden'
                AND TRIM(LOWER(p_status)) NOT IN ('done', 'template', 'done done', 'complete', 'cancelled', 'archived', 'shipped',
                    'picked up', 'harlestons -- invoiced', 'harlestons -- no order pending',
                    'harlestons -- picked up', 'harlestons-need sewout')
            ORDER BY in_hand_date ASC
        """)

        rows = cur.fetchall()
        conn.close()
        for i, row in enumerate(rows):
            values = [row[col] for col in cols]  # or just `row` if you skip the row_factory
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            tree.insert("", "end", iid=str(row["id"]), values=values, tags=(tag,))




    def on_double_click(event):
        item_id = tree.focus()
        col = tree.identify_column(event.x)
        col_index = int(col[1:]) - 1
        if col_index < 1:
            return

        x, y, w, h = tree.bbox(item_id, col)
        value = tree.item(item_id)['values'][col_index]
        field = cols[col_index]
        order_id = tree.item(item_id)['values'][0]

        if field in toggle_fields:
            current = str(value)
            new_value = "No" if current == "Yes" else "Yes"
            save_field_value("harlestons_orders", field, new_value, order_id)
            refresh_tree()
            return

        entry = ttk.Entry(tree)
        entry.place(x=x, y=y, width=w, height=h)


        entry.insert(0, value)
        entry.focus()

        def save_edit(event):
            new_val = entry.get()
            save_field_value("harlestons_orders", field, new_val, order_id)
            entry.destroy()
            refresh_tree()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", lambda e: entry.destroy())

    win = tk.Toplevel()
    win.title(f"Harlestons Production – {company_name}")
    win.geometry("1600x800")
    win.grab_set()

    # Global Notes
    notes_frame = ttk.Frame(win)
    notes_frame.pack(fill="x", padx=10, pady=(10, 0))
    ttk.Label(notes_frame, text="Global Notes:", font=("Arial", 10, "bold")).pack(anchor="w")
    notes_entry = tk.Text(notes_frame, height=3, wrap="word")
    notes_entry.pack(fill="x", expand=True, pady=4)

    def load_notes():
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT value FROM notes WHERE key = ?", ('harlestons_global_notes',))
        row = cur.fetchone()
        conn.close()
        if row:
            notes_entry.delete("1.0", tk.END)
            notes_entry.insert("1.0", row["value"])

    def save_notes():
        value = notes_entry.get("1.0", tk.END).strip()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO notes (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value
        """, ('harlestons_global_notes', value))
        conn.commit()
        conn.close()
        messagebox.showinfo("Saved", "Global notes updated.")

    ttk.Button(notes_frame, text="💾 Save Notes", command=save_notes).pack(anchor="e", pady=(0, 5))
    load_notes()

    # Table Setup
    cols = [
        "id", "po_number", "invoice_number", "club_nickname", "location", "process", "pcs",
        "status", "in_hand_date", "priority", "notes", "inside_location", "uploaded",
        "p_status", "logo_file", "club_colors", "colors_verified"
    ]

    headers = [
        "ID", "PO #", "Invoice #", "Club", "Loc", "Process", "PCS",
        "Status", "Due Date", "Priority", "Notes", "Inside", "Uploaded",
        "P-Status", "Logo File", "Club Colors", "Colors Verified"
    ]

    toggle_fields = {"inside_location", "uploaded", "club_colors", "colors_verified"}

    tree = ttk.Treeview(win, columns=cols, show="headings", height=30)
    for col, header in zip(cols, headers):
        tree.heading(col, text=header)
        tree.column(col, width=100, anchor="center")
        tree.column("id", width=0, stretch=False)
        tree.heading("id", text="")  # No label shown

    tree.tag_configure('oddrow', background=COCONUT_CREAM)
    tree.tag_configure('evenrow', background=TAN_SAND)
    tree.bind("<Double-1>", on_double_click)

    add_frame = ttk.LabelFrame(win, text="➕ Add New Harlestons Order")
    add_frame.pack(fill="x", padx=10, pady=(10, 0))

    add_fields = [
        "po_number", "invoice_number", "club_nickname", "location",
        "in_hand_date", "pcs", "process", "logo_file",
        "club_colors", "colors_verified"
    ]

    dropdown_fields = {
        "location": ["CSS", "HAR", "OTW"],
        "process": ["EMB", "DTF"],
    }

    add_entries = {}

    add_entries = {}

    toggle_fields = ["inside_location", "uploaded", "club_colors", "colors_verified"]
    dropdown_fields = {
        "location": ["CSS", "IMM", "Other"],
        "process": ["EMB", "DTF", "HTV"]
    }

    # Create toggle handler outside loop
    def toggle_button(btn, field):
        new_val = "No" if btn["text"] == "Yes" else "Yes"
        btn.config(text=new_val)
        add_entries[field] = new_val

    for field in add_fields:
        ttk.Label(add_frame, text=field).pack(side="left", padx=2)

        if field in toggle_fields:
            btn = ttk.Button(add_frame, text="No")  # default to "No"
            btn.config(command=lambda b=btn, f=field: toggle_button(b, f))
            btn.pack(side="left", padx=2)
            add_entries[field] = "No"  # Track the value separately

        elif field in dropdown_fields:
            combo = ttk.Combobox(add_frame, values=dropdown_fields[field], width=12, state="readonly")
            combo.set(dropdown_fields[field][0])  # default to first option
            combo.pack(side="left", padx=2)
            add_entries[field] = combo

        elif field == "in_hand_date":
            cal = create_date_picker(add_frame)
            cal.pack(side="left", padx=2)
            add_entries[field] = cal


        else:
            ent = ttk.Entry(add_frame, width=12)
            ent.pack(side="left", padx=2)
            add_entries[field] = ent

    # Submit button
    def submit_new_harl_order():
        from tkinter import messagebox

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

        # Insert into DB
        try:
            add_order("harlestons_orders", field_map)
            refresh_tree()
            messagebox.showinfo("Success", "Order added!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not add order:\n{e}")
            return

        # Clear inputs
        for field, widget in add_entries.items():
            if isinstance(widget, str):
                add_entries[field] = "No"  # Reset toggle fields to "No"
            elif isinstance(widget, ttk.Combobox):
                widget.set(widget["values"][0])  # Reset to first value
            else:
                widget.delete(0, tk.END)


    ttk.Button(add_frame, text="➕ Add", command=submit_new_harl_order).pack(side="left", padx=10)

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
            entry = create_calendar_entry(tree.master, on_commit=commit)
            if curr_val:
                try:
                    entry.set_date(curr_val)
                except:
                    pass
            entry.place(in_=tree, x=x, y=y, width=w, height=h)

            entry.focus_set()
            _active_editor["widget"] = entry

        elif meta["type"].startswith("entry"):
            entry = ttk.Entry(tree.master)
            entry.insert(0, curr_val or "")
            entry.place(in_=tree, x=x, y=y, width=w, height=h)

            entry.focus_set()

            def save_entry(_):
                new_val = entry.get()
                if meta["type"] == "entry_date":
                    parsed = parse_date_input(new_val)
                    if parsed is None:
                        messagebox.showerror("Invalid date", "Please enter date as MM/DD/YYYY or YYYY-MM-DD.")
                        entry.focus_set()
                        return
                    new_val = parsed
                commit(new_val)

            entry.bind("<Return>", save_entry)
            entry.bind("<KP_Enter>", save_entry)
            entry.bind("<Escape>", lambda *_: destroy_active_editor())
            _active_editor["widget"] = entry

        elif meta["type"] == "combo":
            combo = ttk.Combobox(tree.master, values=meta["options"])
            combo.set(curr_val)
            combo.place(x=x, y=y, width=w, height=h)
            combo.focus_set()
            combo.bind("<Return>", lambda _: commit(combo.get()))
            combo.bind("<KP_Enter>", lambda _: commit(combo.get()))
            combo.bind("<FocusOut>", lambda _: commit(combo.get()))
            _active_editor["widget"] = combo

    tree.bind("<Double-1>", start_inline_edit)








    tree.pack(fill="both", expand=True, padx=10, pady=10)







    # Controls
    btn_frame = ttk.Frame(win)
    btn_frame.pack(fill="x", padx=10, pady=(0, 10))
    ttk.Button(btn_frame, text="🔁 Refresh", command=refresh_tree).pack(side="left")

    refresh_tree()
