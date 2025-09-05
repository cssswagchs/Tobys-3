import os

from tobys_terminal.shared.db import get_connection

def add_order(table: str, fields: dict):
    conn = get_connection()
    cur = conn.cursor()

    keys = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    values = list(fields.values())

    cur.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", values)
    conn.commit()
    conn.close()

import sqlite3
from tkinter import messagebox

def update_db(order_id, field, value, db_path="shared/terminal.db", table="harlestons_orders"):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(f"UPDATE {table} SET {field} = ? WHERE id = ?", (value, order_id))
        conn.commit()
        conn.close()
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to update record: {e}")
