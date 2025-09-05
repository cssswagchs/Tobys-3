import csv
import os
# Import directly from the package
from tobys_terminal.shared.db import get_connection

# Update the path to use package resources
from importlib import resources
import tobys_terminal.shared.data

def import_orders():
    # Get the path to the data file using package resources
    try:
        # For Python 3.9+
        with resources.files(tobys_terminal.shared.data).joinpath('orders.csv').open('r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            process_orders(reader)
    except AttributeError:
        # Fallback for older Python versions
        with resources.open_text(tobys_terminal.shared.data, 'orders.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            process_orders(reader)

def process_orders(reader):
    conn = get_connection()
    cursor = conn.cursor()
    imported = 0

    for row in reader:
        try:
            # Extract and normalize values
            total = float(row["Total"] or 0)
            amount_paid = float(row["Amount Paid"] or 0)
            amount_outstanding = float(row["Amount Outstanding"] or 0)
            paid_raw = row["Paid?"].strip().lower()

            # Normalize paid status
            paid_flag = "yes" if paid_raw in {"yes", "true", "1", "y", "paid"} else "no"

            # 🧠 Auto-mark as paid if total is zero
            if total == 0.0:
                paid_flag = "yes"

            cursor.execute("""
                INSERT OR REPLACE INTO invoices (
                    invoice_number,
                    customer_id,
                    invoice_date,
                    po_number,
                    total,
                    amount_paid,
                    amount_outstanding,
                    paid,
                    invoice_status,
                    sales_tax,
                    shipping,
                    convenience_fee,
                    billing_address1,
                    billing_address2,
                    billing_city,
                    billing_state,
                    billing_zip,
                    billing_country,
                    nickname
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["Invoice #"].strip(),
                int(row["Customer Id"] or 0),
                row["Invoice Date"].strip(),
                row["PO #"].strip(),
                total,
                amount_paid,
                amount_outstanding,
                paid_flag,
                row["Invoice Status"].strip(),
                float(row["Sales Tax"] or 0),
                float(row["Shipping"] or 0),
                float(row["Convenience Fee"] or 0),
                row["Billing Address 1"].strip(),
                row["Billing Address 2"].strip(),
                row["Billing City"].strip(),
                row["Billing State"].strip(),
                row["Billing Zip"].strip(),
                row["Billing Country"].strip(),
                row.get("Nickname", "").strip()
            ))
            imported += 1
        except Exception as e:
            print(f"❌ Error importing invoice {row.get('Invoice #')}: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Imported {imported} orders.")
