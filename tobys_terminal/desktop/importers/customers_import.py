import csv
import os
import sys

# Import directly from the package
from tobys_terminal.shared.db import get_connection

# Update the path to use package resources
from importlib import resources
import tobys_terminal.shared.data


def import_customers():
    # Get the path to the data file using package resources
    try:
        # For Python 3.9+
        with resources.files(tobys_terminal.shared.data).joinpath('customers.csv').open('r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            process_customers(reader)
    except AttributeError:
        # Fallback for older Python versions
        with resources.open_text(tobys_terminal.shared.data, 'customers.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            process_customers(reader)

def process_customers(reader):
    conn = get_connection()
    cursor = conn.cursor()
    imported = 0

    for row in reader:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO customers (
                        id, first_name, last_name, company, email, phone,
                        billing_address1, billing_address2, billing_city, billing_state,
                        billing_zip, billing_country,
                        shipping_address1, shipping_address2, shipping_city, shipping_state,
                        shipping_zip, shipping_country,
                        tax_exempt, tax_resale_no, created_at,
                        default_payment_term, default_payment_term_days
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(row["Customer ID"] or 0),
                    row["First Name"].strip(),
                    row["Last Name"].strip(),
                    row["Company"].strip(),
                    row["Email"].strip(),
                    row["Phone"].strip(),
                    row["Billing Address - Address 1"].strip(),
                    row["Billing Address - Address 2"].strip(),
                    row["Billing Address - City"].strip(),
                    row["Billing Address - State"].strip(),
                    row["Billing Address - Zip"].strip(),
                    row["Billing Address - Country"].strip(),
                    row["Shipping Address - Address 1"].strip(),
                    row["Shipping Address - Address 2"].strip(),
                    row["Shipping Address - City"].strip(),
                    row["Shipping Address - State"].strip(),
                    row["Shipping Address - Zip"].strip(),
                    row["Shipping Address - Country"].strip(),
                    row["Tax Exempt?"].strip(),
                    row["Tax Resale No"].strip(),
                    row["Created"].strip(),
                    row["Default Payment Term"].strip(),
                    int(row["Default Payment Term Days"] or 0)
                ))
                imported += 1
            except Exception as e:
                print(f"Error importing customer ID {row.get('Customer ID')}: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Imported {imported} customers.")
