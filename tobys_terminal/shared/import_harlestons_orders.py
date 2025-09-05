import sqlite3
import csv

# Connect to your terminal.db SQLite database
conn = sqlite3.connect("terminal.db")
cursor = conn.cursor()

# Create the table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS harlestons_orders (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number TEXT,
    location TEXT,
    club_nickname TEXT,
    process TEXT,
    invoice_number TEXT,
    pcs INTEGER,
    priority INTEGER,
    in_hand_date TEXT,
    status TEXT,
    notes TEXT,
    inside_location TEXT,
    uploaded TEXT,
    logo_file TEXT,
    club_colors TEXT,
    colors_verified TEXT
)
""")

# Read and insert data from the cleaned CSV
with open("harlestons_cleaned_orders.csv", "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        cursor.execute("""
            INSERT INTO harlestons_orders (
                po_number, location, club_nickname, process, invoice_number, pcs, priority,
                in_hand_date, status, notes, inside_location, uploaded,
                logo_file, club_colors, colors_verified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("PO #"),
            row.get("LOC"),
            row.get("CLUB"),
            row.get("PROCESS"),
            row.get("INVOICE #"),
            row.get("PCS"),
            row.get("PRIORITY"),
            row.get("IN-HAND DATE"),
            row.get("Status"),
            row.get("NOTES"),
            row.get("Inside"),
            row.get("Uploaded"),
            row.get("LOGO FILE"),
            row.get("CLUB COLORS"),
            row.get("COLORS VERIFIED")
        ))

# Commit and close
conn.commit()
conn.close()
print("✅ Import complete. Data added to terminal.db → harlestons_orders table.")
