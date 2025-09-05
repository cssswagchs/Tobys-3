import csv
import sys
import os

# Import directly from the package
from tobys_terminal.shared.db import get_connection

# Update the path to use package resources
from importlib import resources
import tobys_terminal.shared.data

def import_payments():
    # Get the path to the data file using package resources
    try:
        # For Python 3.9+
        with resources.files(tobys_terminal.shared.data).joinpath('payments.csv').open('r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            process_payments(reader)
    except AttributeError:
        # Fallback for older Python versions
        with resources.open_text(tobys_terminal.shared.data, 'payments.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            process_payments(reader)

def process_payments(reader):
    conn = get_connection()
    cursor = conn.cursor()
    imported = 0

    for row in reader:
        try:
            amount = float(row["Amount"])
            if amount < 0:
                continue  # Skip expenses
            cursor.execute("""
                INSERT OR IGNORE INTO payments_clean (
                    invoice_number,
                    amount,
                    transaction_date,
                    payment_method,
                    reference,
                    customer_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                row["Invoice #"].strip(),
                float(row["Amount"]),
                row["Transaction Date"].strip(),
                row.get("Category", "").strip(),
                row.get("Name", "").strip(),
                int(row["Customer ID"] or 0)
            ))

            imported += 1
        except Exception as e:
            print("❌ Error importing row:")
            print(f"  Row: {row}")
            print(f"  Error: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Imported {imported} payments.")
