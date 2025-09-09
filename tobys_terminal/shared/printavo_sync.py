"""
printavo_sync.py - Unified system for Printavo order synchronization

This file handles all Printavo-related imports and synchronization:
1. Importing orders from CSV files
2. Syncing IMM orders from invoices
3. Syncing Harlestons orders from invoices
4. Providing diagnostic tools for troubleshooting

Usage:
- Run directly: python printavo_sync.py
- Import functions: from printavo_sync import sync_all, sync_imm, sync_harlestons
"""

import csv
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd
# Import from your project
import config
from tobys_terminal.shared.db import get_connection
from config import PROJECT_ROOT
# Import status filters from config
try:
    from config import (
        EXCLUDED_STATUSES, EXCLUDED_P_STATUSES,
        HARLESTONS_EXCLUDED_STATUSES, HARLESTONS_EXCLUDED_P_STATUSES,
        IMM_EXCLUDED_STATUSES, IMM_EXCLUDED_P_STATUSES
    )
except ImportError:
    # Default filters if not in config
    EXCLUDED_STATUSES = {
        'done', 'complete', 'cancelled', 'archived', 
        'done done', 'shipped', 'picked up'
    }
    EXCLUDED_P_STATUSES = {
        'done', 'template', 'done done', 'complete', 'cancelled', 'archived', 'shipped',
        'picked up', 'harlestons -- invoiced', 'harlestons -- no order pending',
        'harlestons -- picked up', 'harlestons-need sewout'
    }
    HARLESTONS_EXCLUDED_STATUSES = EXCLUDED_STATUSES
    HARLESTONS_EXCLUDED_P_STATUSES = EXCLUDED_P_STATUSES
    IMM_EXCLUDED_STATUSES = EXCLUDED_STATUSES
    IMM_EXCLUDED_P_STATUSES = EXCLUDED_P_STATUSES

# Constants
CSV_DIR = PROJECT_ROOT / "data_imports"
LOG_DIR = Path("./logs")  # Directory for logs

# Ensure directories exist
CSV_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Set up logging
log_file = LOG_DIR / f"printavo_sync_{datetime.now().strftime('%Y%m%d')}.log"

def log(message):
    """Write message to log file and print to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")

# Direct implementation to get customer IDs by company name
def get_customer_ids_by_company_name(company_name):
    """Get customer IDs for a specific company name"""
    # First try to use the config file constants
    try:
        from config import IMM_CUSTOMER_IDS, HARLESTONS_CUSTOMER_IDS
        
        if company_name.lower() == "imm":
            log(f"Using configured IMM customer IDs: {IMM_CUSTOMER_IDS}")
            return IMM_CUSTOMER_IDS
        elif company_name.lower() == "harlestons":
            log(f"Using configured Harlestons customer IDs: {HARLESTONS_CUSTOMER_IDS}")
            return HARLESTONS_CUSTOMER_IDS
    except ImportError:
        log("Customer IDs not found in config, falling back to database search")
    
    # Fall back to database search if config doesn't have the IDs
    conn = get_connection()
    cur = conn.cursor()
    
    # Direct query to get customer IDs by company
    cur.execute("""
        SELECT id FROM customers 
        WHERE LOWER(company) LIKE ?
    """, (f"%{company_name.lower()}%",))
    
    customer_ids = [row[0] for row in cur.fetchall()]
    conn.close()
    
    log(f"Found {len(customer_ids)} customer IDs for {company_name}")
    return customer_ids

def check_orders_by_customer_id(customer_id):
    """Check orders directly by customer ID"""
    log(f"Checking orders for customer ID: {customer_id}")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Check invoices
    cur.execute("SELECT COUNT(*) FROM invoices WHERE customer_id = ?", (customer_id,))
    invoice_count = cur.fetchone()[0]
    log(f"Found {invoice_count} invoices for customer ID {customer_id}")
    
    # Sample some invoices
    cur.execute("""
        SELECT invoice_number, invoice_status, po_number 
        FROM invoices 
        WHERE customer_id = ? 
        ORDER BY invoice_number DESC
        LIMIT 5
    """, (customer_id,))
    
    sample_invoices = cur.fetchall()
    if sample_invoices:
        log("Sample invoices:")
        for inv in sample_invoices:
            log(f"  Invoice: {inv[0]}, Status: {inv[1]}, PO: {inv[2]}")
    
    # Check for specific PO/invoice
    cur.execute("""
        SELECT invoice_number, invoice_status, po_number, customer_due_date
        FROM invoices
        WHERE customer_id = ? AND (po_number = ? OR invoice_number = ?)
    """, (customer_id, "20252546", "31288"))
    
    target = cur.fetchone()
    if target:
        log(f"Found target order: Invoice={target[0]}, Status={target[1]}, PO={target[2]}, Due Date={target[3]}")
    else:
        log("Target order not found for this customer ID")
    
    conn.close()



def check_database():
    """Check database tables and structure"""
    log("Checking database structure...")
    conn = get_connection()
    cur = conn.cursor()
    
    # Check if tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    log(f"Tables in database: {', '.join(tables)}")
    
    # Check structure of key tables
    for table in ['invoices', 'imm_orders', 'harlestons_orders', 'customers']:
        if table in tables:
            cur.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cur.fetchall()]
            log(f"Columns in {table}: {', '.join(columns)}")
            
            # Count records
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            log(f"Records in {table}: {count}")
        else:
            log(f"⚠️ Table {table} does not exist!")
    
    conn.close()
    log("Database check complete.")

def create_tables():
    """Create necessary tables if they don't exist"""
    log("Creating/checking required tables...")
    conn = get_connection()
    cur = conn.cursor()
    
    # Check if customer_due_date column exists in imm_orders
    cur.execute("PRAGMA table_info(imm_orders)")
    columns = [row[1] for row in cur.fetchall()]
    
    if "customer_due_date" not in columns:
        log("Adding customer_due_date column to imm_orders table")
        cur.execute("ALTER TABLE imm_orders ADD COLUMN customer_due_date TEXT")
    
    # Check if customer_due_date column exists in harlestons_orders
    cur.execute("PRAGMA table_info(harlestons_orders)")
    columns = [row[1] for row in cur.fetchall()]
    
    if "customer_due_date" not in columns:
        log("Adding customer_due_date column to harlestons_orders table")
        cur.execute("ALTER TABLE harlestons_orders ADD COLUMN customer_due_date TEXT")
    
    # Create tables if they don't exist (existing code)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS harlestons_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_number TEXT,
        location TEXT,
        club_nickname TEXT,
        process TEXT,
        invoice_number TEXT,
        pcs INTEGER,
        priority TEXT,
        in_hand_date TEXT,
        customer_due_date TEXT,
        status TEXT,
        p_status TEXT,
        notes TEXT,
        inside_location TEXT,
        uploaded TEXT,
        logo_file TEXT,
        club_colors TEXT,
        colors_verified TEXT
    )
    """)
    
    cur.execute("PRAGMA table_info(invoices)")
    columns = [col[1] for col in cur.fetchall()]
    if "customer_due_date" not in columns:
        print("Adding customer_due_date column to invoices table")
        cur.execute("ALTER TABLE invoices ADD COLUMN customer_due_date TEXT")
        conn.commit()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS imm_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_number TEXT,
        nickname TEXT,
        in_hand_date TEXT,
        customer_due_date TEXT,
        firm_date TEXT,
        invoice_number TEXT,
        process TEXT,
        status TEXT,
        p_status TEXT,
        notes TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    log("Tables created/checked successfully.")

def import_master_orders_from_csv(csv_path):
    """
    Imports the master orders.csv file into the 'invoices' table.
    This is the primary function for getting Printavo data into the system.
    It updates existing records and inserts new ones (UPSERT).
    """
    log(f"Starting master import from {csv_path}...")
    
    try:
        # Specify dtype for columns that might be mixed to avoid warnings
        dtype_spec = {'PO #': str, 'Invoice #': str}
        df = pd.read_csv(csv_path, dtype=dtype_spec)
        log(f"Successfully read {len(df)} rows from master CSV.")
    except Exception as e:
        log(f"❌ Failed to read master CSV file: {e}")
        return

    conn = get_connection()
    cur = conn.cursor()
    
    processed = 0
    skipped = 0

    # Ensure the invoices table has a UNIQUE index on invoice_number for UPSERT to work
    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices (invoice_number);")
    except sqlite3.OperationalError as e:
        log(f"Could not create unique index, it might already exist: {e}")

    for index, row in df.iterrows():
        try:
            invoice_num = str(row.get('Invoice #', '')).strip()
            if not invoice_num:
                skipped += 1
                continue

            # Prepare data for insertion/update
            data = {
                'invoice_number': invoice_num,
                'customer_id': int(row.get('Customer Id', 0)) if pd.notna(row.get('Customer Id')) else None,
                'invoice_date': pd.to_datetime(row.get('Invoice Date')).strftime('%Y-%m-%d') if pd.notna(row.get('Invoice Date')) else None,
                'po_number': str(row.get('PO #', '')).strip(),
                'total': float(row.get('Total', 0.0)) if pd.notna(row.get('Total')) else 0.0,
                'amount_paid': float(row.get('Amount Paid', 0.0)) if pd.notna(row.get('Amount Paid')) else 0.0,
                'amount_outstanding': float(row.get('Amount Outstanding', 0.0)) if pd.notna(row.get('Amount Outstanding')) else 0.0,
                'paid': bool(row.get('Paid?', False)),
                'invoice_status': str(row.get('Invoice Status', '')).strip(),
                'nickname': str(row.get('Nickname', '')).strip(),
                'customer_due_date': pd.to_datetime(row.get('Customer Due Date')).strftime('%Y-%m-%d') if pd.notna(row.get('Customer Due Date')) else None
            }

            # Using INSERT ... ON CONFLICT (UPSERT) for efficiency
            cur.execute("""
                INSERT INTO invoices (
                    invoice_number, customer_id, invoice_date, po_number, total, 
                    amount_paid, amount_outstanding, paid, invoice_status, nickname, 
                    customer_due_date
                ) VALUES (
                    :invoice_number, :customer_id, :invoice_date, :po_number, :total, 
                    :amount_paid, :amount_outstanding, :paid, :invoice_status, :nickname, 
                    :customer_due_date
                )
                ON CONFLICT(invoice_number) DO UPDATE SET
                    customer_id = excluded.customer_id,
                    invoice_date = excluded.invoice_date,
                    po_number = excluded.po_number,
                    total = excluded.total,
                    amount_paid = excluded.amount_paid,
                    amount_outstanding = excluded.amount_outstanding,
                    paid = excluded.paid,
                    invoice_status = excluded.invoice_status,
                    nickname = excluded.nickname,
                    customer_due_date = excluded.customer_due_date;
            """, data)
            processed += 1

        except Exception as e:
            log(f"❌ Error processing row {index} (Invoice: {row.get('Invoice #', 'N/A')}): {e}")
            skipped += 1

    conn.commit()
    conn.close()

    log(f"✅ Master import complete. Processed: {processed}, Skipped: {skipped}")

def import_payments_from_csv(csv_path):
    """
    Imports payment data from Printavo payments CSV export.
    """
    log(f"Starting payment import from {csv_path}...")
    
    try:
        # Specify dtype for columns that might be mixed to avoid warnings
        dtype_spec = {'Invoice #': str, 'Payment Transaction ID': str}
        df = pd.read_csv(csv_path, dtype=dtype_spec)
        log(f"Successfully read {len(df)} rows from payments CSV.")
    except Exception as e:
        log(f"❌ Failed to read payments CSV file: {e}")
        return

    conn = get_connection()
    cur = conn.cursor()
    
    processed = 0
    skipped = 0
    duplicates = 0

    # Create payments_clean table if it doesn't exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments_clean (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_date TEXT,
        amount REAL,
        invoice_number TEXT,
        payment_method TEXT,
        reference TEXT,
        customer_id INTEGER
    )
    """)
    
    # Create index for faster lookups
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_invoice_number ON payments_clean (invoice_number);")
    except sqlite3.OperationalError as e:
        log(f"Could not create index, it might already exist: {e}")

    for index, row in df.iterrows():
        try:
            invoice_num = str(row.get('Invoice #', '')).strip()
            if not invoice_num:
                skipped += 1
                continue

            amount = float(row.get('Amount', 0))
            if amount < 0:
                log(f"Skipping negative amount payment: {invoice_num}, ${amount}")
                skipped += 1
                continue

            # Get payment method and reference
            payment_method = str(row.get('Category', '')).strip()
            reference = str(row.get('Name', '')).strip()
            
            # Get transaction date
            tx_date = pd.to_datetime(row.get('Transaction Date')).strftime('%Y-%m-%d') if pd.notna(row.get('Transaction Date')) else None
            
            # Get customer ID
            customer_id = int(row.get('Customer ID', 0)) if pd.notna(row.get('Customer ID')) else None
            
            # Check if payment already exists
            cur.execute("""
                SELECT id FROM payments_clean 
                WHERE invoice_number = ? AND transaction_date = ? AND amount = ?
            """, (invoice_num, tx_date, amount))
            
            existing = cur.fetchone()
            if existing:
                # Payment already exists, update the reference if needed
                cur.execute("""
                    UPDATE payments_clean 
                    SET payment_method = ?, reference = ?
                    WHERE invoice_number = ? AND transaction_date = ? AND amount = ?
                """, (payment_method, reference, invoice_num, tx_date, amount))
                duplicates += 1
                continue
            
            # Insert new payment
            cur.execute("""
                INSERT INTO payments_clean (
                    transaction_date, amount, invoice_number, payment_method, reference, customer_id
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (tx_date, amount, invoice_num, payment_method, reference, customer_id))
            
            processed += 1

        except Exception as e:
            log(f"❌ Error processing payment row {index} (Invoice: {row.get('Invoice #', 'N/A')}): {e}")
            skipped += 1

    conn.commit()
    conn.close()

    log(f"✅ Payment import complete. Processed: {processed}, Updated: {duplicates}, Skipped: {skipped}")


def import_customers_from_csv(csv_path):
    """
    Imports customer data from Printavo customers CSV export.
    """
    log(f"Starting customer import from {csv_path}...")
    
    try:
        # Specify dtype for columns that might be mixed to avoid warnings
        dtype_spec = {'Customer ID': str}
        df = pd.read_csv(csv_path, dtype=dtype_spec)
        log(f"Successfully read {len(df)} rows from customers CSV.")
    except Exception as e:
        log(f"❌ Failed to read customers CSV file: {e}")
        return

    conn = get_connection()
    cur = conn.cursor()
    
    processed = 0
    skipped = 0

    for index, row in df.iterrows():
        try:
            customer_id = int(row.get('Customer ID', 0)) if pd.notna(row.get('Customer ID')) else 0
            if customer_id == 0:
                skipped += 1
                continue
                
            cur.execute("""
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
                customer_id,
                str(row.get("First Name", "")).strip(),
                str(row.get("Last Name", "")).strip(),
                str(row.get("Company", "")).strip(),
                str(row.get("Email", "")).strip(),
                str(row.get("Phone", "")).strip(),
                str(row.get("Billing Address - Address 1", "")).strip(),
                str(row.get("Billing Address - Address 2", "")).strip(),
                str(row.get("Billing Address - City", "")).strip(),
                str(row.get("Billing Address - State", "")).strip(),
                str(row.get("Billing Address - Zip", "")).strip(),
                str(row.get("Billing Address - Country", "")).strip(),
                str(row.get("Shipping Address - Address 1", "")).strip(),
                str(row.get("Shipping Address - Address 2", "")).strip(),
                str(row.get("Shipping Address - City", "")).strip(),
                str(row.get("Shipping Address - State", "")).strip(),
                str(row.get("Shipping Address - Zip", "")).strip(),
                str(row.get("Shipping Address - Country", "")).strip(),
                str(row.get("Tax Exempt?", "")).strip(),
                str(row.get("Tax Resale No", "")).strip(),
                str(row.get("Created", "")).strip(),
                str(row.get("Default Payment Term", "")).strip(),
                int(row.get("Default Payment Term Days", 0)) if pd.notna(row.get("Default Payment Term Days")) else 0
            ))
            processed += 1
            
        except Exception as e:
            log(f"❌ Error processing customer row {index} (ID: {row.get('Customer ID', 'N/A')}): {e}")
            skipped += 1

    conn.commit()
    conn.close()

    log(f"✅ Customer import complete. Processed: {processed}, Skipped: {skipped}")






def sync_imm_orders():
    """
    Syncs data from the main 'invoices' table to the 'imm_orders' table.
    It will INSERT new orders and UPDATE existing ones.
    """
    log("Starting IMM order synchronization...")
    conn = get_connection()
    cur = conn.cursor()

    try:
        imm_ids = tuple(config.IMM_CUSTOMER_IDS)
        placeholders = ','.join('?' for _ in imm_ids)
        
        cur.execute(f"""
            SELECT invoice_number, po_number, nickname, customer_due_date, invoice_status
            FROM invoices
            WHERE customer_id IN ({placeholders})
        """, imm_ids)
        
        invoices_to_sync = cur.fetchall()
        log(f"Found {len(invoices_to_sync)} invoices for IMM customers")

        inserted = 0
        updated = 0
        skipped = 0

        for inv_num, po_num, nickname, due_date, status in invoices_to_sync:
            if not po_num:
                skipped += 1
                continue

            # Check if the order already exists in imm_orders
            cur.execute("SELECT id FROM imm_orders WHERE po_number = ?", (po_num,))
            existing_order = cur.fetchone()

            if existing_order:
                # UPDATE existing order
                cur.execute("""
                    UPDATE imm_orders SET
                        nickname = ?,
                        invoice_number = ?,
                        p_status = ?,
                        customer_due_date = ?
                    WHERE po_number = ?
                """, (nickname, inv_num, status, due_date, po_num))
                updated += 1
            else:
                # INSERT new order
                cur.execute("""
                    INSERT INTO imm_orders (po_number, nickname, invoice_number, p_status, customer_due_date, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (po_num, nickname, inv_num, status, due_date, "New")) # Default status to "New"
                inserted += 1
        
        conn.commit()
        log(f"✅ IMM sync complete. Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
        return True

    except Exception as e:
        log(f"❌ ERROR in IMM order synchronization: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()




def sync_harlestons_orders():
    """
    Syncs data from the main 'invoices' table to the 'harlestons_orders' table.
    It will INSERT new orders and UPDATE existing ones.
    """
    log("Starting Harlestons order synchronization...")
    conn = get_connection()
    cur = conn.cursor()

    try:
        harlestons_ids = tuple(config.HARLESTONS_CUSTOMER_IDS)
        placeholders = ','.join('?' for _ in harlestons_ids)

        cur.execute(f"""
            SELECT invoice_number, po_number, nickname, customer_due_date, invoice_status
            FROM invoices
            WHERE customer_id IN ({placeholders})
        """, harlestons_ids)
        
        invoices_to_sync = cur.fetchall()
        log(f"Found {len(invoices_to_sync)} invoices for Harlestons customers")

        inserted = 0
        updated = 0
        skipped = 0

        for inv_num, po_num, nickname, due_date, status in invoices_to_sync:
            if not po_num:
                skipped += 1
                continue

            # Check if the order already exists in harlestons_orders
            cur.execute("SELECT id FROM harlestons_orders WHERE po_number = ?", (po_num,))
            existing_order = cur.fetchone()

            if existing_order:
                # UPDATE existing order
                cur.execute("""
                    UPDATE harlestons_orders SET
                        club_nickname = ?,
                        invoice_number = ?,
                        p_status = ?,
                        customer_due_date = ?
                    WHERE po_number = ?
                """, (nickname, inv_num, status, due_date, po_num))
                updated += 1
            else:
                # INSERT new order
                cur.execute("""
                    INSERT INTO harlestons_orders (po_number, club_nickname, invoice_number, p_status, customer_due_date, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (po_num, nickname, inv_num, status, due_date, "New")) # Default status to "New"
                inserted += 1

        conn.commit()
        log(f"✅ Harlestons sync complete. Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
        return True

    except Exception as e:
        log(f"❌ ERROR in Harlestons order synchronization: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    return True

def update_terminal_filters():
    """Update terminal view filters - only affect orders with default status"""
    log("Updating terminal view filters...")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Convert all excluded statuses to lowercase for case-insensitive comparison
    imm_excluded_statuses_lower = [s.lower() for s in IMM_EXCLUDED_STATUSES]
    imm_excluded_p_statuses_lower = [s.lower() for s in IMM_EXCLUDED_P_STATUSES]
    
    # Only update orders with the default "Need Review" status
    cur.execute("""
    UPDATE imm_orders
    SET status = 'Hidden'
    WHERE 
        status = 'Need Review' AND (
            LOWER(TRIM(p_status)) IN ({0})
        )
    """.format(
        ','.join(['?'] * len(imm_excluded_p_statuses_lower))
    ), imm_excluded_p_statuses_lower)
    
    imm_updated = cur.rowcount
    log(f"Updated {imm_updated} IMM orders to 'Hidden' status (preserving manual changes)")
    
    # Same for Harlestons
    harlestons_excluded_p_statuses_lower = [s.lower() for s in HARLESTONS_EXCLUDED_P_STATUSES]
    
    cur.execute("""
        UPDATE harlestons_orders
        SET status = 'Hidden'
        WHERE 
            status = 'Need Review' AND (
                LOWER(TRIM(p_status)) IN ({0})
            )
    """.format(
        ','.join(['?'] * len(harlestons_excluded_p_statuses_lower))
    ), harlestons_excluded_p_statuses_lower)
    
    harlestons_updated = cur.rowcount
    log(f"Updated {harlestons_updated} Harlestons orders to 'Hidden' status (preserving manual changes)")
    
    conn.commit()
    conn.close()
    
    return imm_updated + harlestons_updated




def backfill_customer_due_dates():
    """Backfill customer_due_date from invoices table for existing orders"""
    log("Backfilling customer due dates...")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Backfill IMM orders
    cur.execute("""
        UPDATE imm_orders
        SET customer_due_date = (
            SELECT customer_due_date
            FROM invoices
            WHERE invoices.invoice_number = imm_orders.invoice_number
        ),
        in_hand_date = COALESCE(
            (SELECT customer_due_date
             FROM invoices
             WHERE invoices.invoice_number = imm_orders.invoice_number),
            in_hand_date
        )
        WHERE customer_due_date IS NULL
        AND EXISTS (
            SELECT 1
            FROM invoices
            WHERE invoices.invoice_number = imm_orders.invoice_number
            AND invoices.customer_due_date IS NOT NULL
        )
    """)
    
    imm_updated = cur.rowcount
    log(f"Updated {imm_updated} IMM orders with customer due dates")
    
    # Backfill Harlestons orders
    cur.execute("""
        UPDATE harlestons_orders
        SET customer_due_date = (
            SELECT customer_due_date
            FROM invoices
            WHERE invoices.invoice_number = harlestons_orders.invoice_number
        ),
        in_hand_date = COALESCE(
            (SELECT customer_due_date
             FROM invoices
             WHERE invoices.invoice_number = harlestons_orders.invoice_number),
            in_hand_date
        )
        WHERE customer_due_date IS NULL
        AND EXISTS (
            SELECT 1
            FROM invoices
            WHERE invoices.invoice_number = harlestons_orders.invoice_number
            AND invoices.customer_due_date IS NOT NULL
        )
    """)
    
    harlestons_updated = cur.rowcount
    log(f"Updated {harlestons_updated} Harlestons orders with customer due dates")
    
    conn.commit()
    conn.close()
    
    return imm_updated + harlestons_updated

def find_duplicates():
    """Find and report duplicate PO numbers in the terminal tables."""
    log("Checking for duplicate PO numbers...")
    conn = get_connection()
    cur = conn.cursor()
    
    # Check IMM duplicates
    cur.execute("""
        SELECT po_number, COUNT(*) as count
        FROM imm_orders
        GROUP BY po_number
        HAVING COUNT(*) > 1
    """)
    imm_duplicates = cur.fetchall()
    
    if imm_duplicates:
        log(f"Found {len(imm_duplicates)} duplicate PO numbers in IMM orders:")
        for po, count in imm_duplicates:
            log(f"  - PO: {po} appears {count} times")
            
            # Show details of each duplicate
            cur.execute("SELECT id, po_number, nickname, invoice_number FROM imm_orders WHERE po_number = ?", (po,))
            details = cur.fetchall()
            for d in details:
                log(f"    * ID: {d[0]}, PO: {d[1]}, Nickname: {d[2]}, Invoice: {d[3]}")
    else:
        log("No duplicates found in IMM orders.")
    
    # Check Harlestons duplicates
    cur.execute("""
        SELECT po_number, COUNT(*) as count
        FROM harlestons_orders
        GROUP BY po_number
        HAVING COUNT(*) > 1
    """)
    harlestons_duplicates = cur.fetchall()
    
    if harlestons_duplicates:
        log(f"Found {len(harlestons_duplicates)} duplicate PO numbers in Harlestons orders:")
        for po, count in harlestons_duplicates:
            log(f"  - PO: {po} appears {count} times")
            
            # Show details of each duplicate
            cur.execute("SELECT id, po_number, club_nickname, invoice_number FROM harlestons_orders WHERE po_number = ?", (po,))
            details = cur.fetchall()
            for d in details:
                log(f"    * ID: {d[0]}, PO: {d[1]}, Nickname: {d[2]}, Invoice: {d[3]}")
    else:
        log("No duplicates found in Harlestons orders.")
    
    conn.close()

def clean_duplicates():
    """Remove duplicate entries from terminal tables, keeping the most recent one."""
    log("Cleaning up duplicate PO numbers...")
    conn = get_connection()
    cur = conn.cursor()
    
    # Clean IMM duplicates
    cur.execute("""
        DELETE FROM imm_orders 
        WHERE id NOT IN (
            SELECT MAX(id) 
            FROM imm_orders 
            GROUP BY po_number
        )
    """)
    imm_deleted = cur.rowcount
    log(f"Removed {imm_deleted} duplicate IMM orders")
    
    # Clean Harlestons duplicates
    cur.execute("""
        DELETE FROM harlestons_orders 
        WHERE id NOT IN (
            SELECT MAX(id) 
            FROM harlestons_orders 
            GROUP BY po_number
        )
    """)
    harlestons_deleted = cur.rowcount
    log(f"Removed {harlestons_deleted} duplicate Harlestons orders")
    
    conn.commit()
    conn.close()
    
    return imm_deleted + harlestons_deleted



def sync_all():
    """Run all synchronization processes in the correct order."""
    log("=== Starting full Printavo synchronization ===")
    
    # STEP 1A: Import customers
    customers_csv_path = CSV_DIR / "customers.csv"
    if customers_csv_path.exists():
        log("Found customers.csv, importing to 'customers' table...")
        import_customers_from_csv(customers_csv_path)
    else:
        log(f"⚠️ Customers CSV not found at '{customers_csv_path}'.")
    
    # STEP 1B: Import the master CSV into the 'invoices' table.
    orders_csv_path = CSV_DIR / "orders.csv"
    if orders_csv_path.exists():
        log("Found orders.csv, importing to 'invoices' table...")
        import_master_orders_from_csv(orders_csv_path)
    else:
        log(f"⚠️ Orders CSV not found at '{orders_csv_path}'.")
        log("Sync will only run on existing data in the 'invoices' table.")
    
    # STEP 1C: Import payments CSV
    payments_csv_path = CSV_DIR / "payments.csv"
    if payments_csv_path.exists():
        log("Found payments.csv, importing to 'payments_clean' table...")
        import_payments_from_csv(payments_csv_path)
    else:
        log(f"⚠️ Payments CSV not found at '{payments_csv_path}'.")
        
    # Check and create tables if needed
    create_tables()
    
    # Check database structure (optional, good for diagnostics)
    check_database()
    
    # STEP 2: Sync IMM orders from the now-updated 'invoices' table
    imm_success = sync_imm_orders()
    
    # STEP 3: Sync Harlestons orders from the now-updated 'invoices' table
    harlestons_success = sync_harlestons_orders()
    
    # STEP 4: Find and report any duplicates
    find_duplicates()
    
    # STEP 5: Clean up any duplicates
    cleaned = clean_duplicates()
    if cleaned > 0:
        log(f"✅ Removed {cleaned} duplicate entries")
        # Run find_duplicates again to verify cleanup
        find_duplicates()
    
    # STEP 6: Update terminal filters based on the latest statuses
    update_terminal_filters()
    
    # STEP 7: Backfill any missing customer due dates
    backfill_customer_due_dates()
    
    log("=== Printavo synchronization complete ===")
    return imm_success and harlestons_success




def add_sync_buttons_to_terminals():
    """
    Instructions for adding sync buttons to terminals
    
    This function doesn't actually do anything - it's just documentation
    for how to add sync buttons to your terminals.
    """
    log("""
    === How to Add Sync Buttons to Terminals ===
    
    1. For Harlestons Web Terminal (harlestons.py):
    
    @harlestons_bp.route('/sync_printavo', methods=['POST'])
    @requires_permission('manage_production')
    def sync_printavo():
        from printavo_sync import sync_harlestons_orders
        
        try:
            sync_harlestons_orders()
            flash("✅ Successfully synchronized orders from Printavo!", "success")
        except Exception as e:
            flash(f"❌ Error synchronizing orders: {str(e)}", "error")
        
        return redirect(url_for('harlestons.terminal'))
    
    2. For IMM Web Terminal (imm.py):
    
    @imm_bp.route('/sync_printavo', methods=['POST'])
    @requires_permission('manage_production')
    def sync_printavo():
        from printavo_sync import sync_imm_orders
        
        try:
            sync_imm_orders()
            flash("✅ Successfully synchronized orders from Printavo!", "success")
        except Exception as e:
            flash(f"❌ Error synchronizing orders: {str(e)}", "error")
        
        return redirect(url_for('imm.terminal'))
    
    3. Add buttons to HTML templates:
    
    {% if is_admin %}
    <form method="POST" action="{{ url_for('harlestons.sync_printavo') }}" class="mb-4">
      <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
        🔄 Sync Orders from Printavo
      </button>
    </form>
    {% endif %}
    
    4. For Tkinter terminals, add these imports and buttons:
    
    from printavo_sync import sync_harlestons_orders  # or sync_imm_orders
    
    ttk.Button(btn_frame, text="🔄 Sync from Printavo", command=lambda: sync_and_refresh()).pack(side="left", padx=6)
    
    def sync_and_refresh():
        try:
            sync_harlestons_orders()  # or sync_imm_orders()
            messagebox.showinfo("Success", "Successfully synchronized orders from Printavo!")
            refresh_tree()  # or load_imm_orders()
        except Exception as e:
            messagebox.showerror("Error", f"Error synchronizing orders: {str(e)}")
    """)

def update_terminal_queries():
    """
    Instructions for updating terminal queries
    
    This function doesn't actually do anything - it's just documentation
    for how to update your terminal queries.
    """
    log("""
    === How to Update Terminal Queries ===
    
    1. For Harlestons Web Terminal (harlestons.py):
    
    query = '''
        SELECT * FROM harlestons_orders
        WHERE 
            status != 'Hidden'
            AND LOWER(status) NOT IN ('cancelled', 'archived')
    '''
    
    2. For IMM Web Terminal (imm.py):
    
    query = '''
        SELECT * FROM imm_orders
        WHERE 
            status != 'Hidden'
            AND LOWER(status) NOT IN ('cancelled', 'archived')
    '''
    
    3. For Harlestons Tkinter Terminal (harlestons_roster_view.py):
    
    cur.execute('''
        SELECT id, po_number, invoice_number, club_nickname, location, process, pcs,
            status, in_hand_date, priority, notes, inside_location, uploaded,
            p_status, logo_file, club_colors, colors_verified
        FROM harlestons_orders
        WHERE
            status != 'Hidden'
            AND LOWER(status) NOT IN ('cancelled', 'archived')
        ORDER BY in_hand_date ASC
    ''')
    
    4. For IMM Tkinter Terminal (imm_roster_view.py):
    
    cur.execute('''
        SELECT id, po_number, nickname, in_hand_date, firm_date,
            invoice_number, process, status, p_status, notes
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
            in_hand_date ASC
    ''')
    """)
def fix_done_done_status():
    """Directly fix 'Done Done' status entries"""
    log("Fixing 'Done Done' status entries...")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Fix IMM orders
    cur.execute("UPDATE imm_orders SET status = 'Hidden' WHERE LOWER(p_status) LIKE '%done done%'")
    imm_updated = cur.rowcount
    log(f"Updated {imm_updated} IMM 'Done Done' orders to 'Hidden'")
    
    # Fix Harlestons orders
    cur.execute("UPDATE harlestons_orders SET status = 'Hidden' WHERE LOWER(p_status) LIKE '%done done%'")
    harlestons_updated = cur.rowcount
    log(f"Updated {harlestons_updated} Harlestons 'Done Done' orders to 'Hidden'")
    
    conn.commit()
    conn.close()


    
    return imm_updated + harlestons_updated


if __name__ == "__main__":
    # When run directly, perform full synchronization
    sync_all()
    
    # Show instructions for updating terminal queries
    update_terminal_queries()
    
    # Uncomment to show instructions for adding buttons
    # add_sync_buttons_to_terminals()
