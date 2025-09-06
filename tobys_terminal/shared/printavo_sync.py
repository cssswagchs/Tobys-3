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

# Import from your project
from tobys_terminal.shared.db import get_connection
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
CSV_DIR = Path("./data_imports")  # Directory for CSV files
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



def import_harlestons_csv(csv_path=None):
    """Import Harlestons orders from CSV file"""
    if csv_path is None:
        csv_path = CSV_DIR / "harlestons_orders.csv"
    
    if not os.path.exists(csv_path):
        log(f"❌ CSV file not found: {csv_path}")
        return False
    
    log(f"Importing Harlestons orders from {csv_path}...")
    conn = get_connection()
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    
    try:
        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Check if this invoice already exists
                invoice_num = row.get("INVOICE #", "").strip()
                if invoice_num:
                    cursor.execute("SELECT id FROM harlestons_orders WHERE invoice_number = ?", (invoice_num,))
                    if cursor.fetchone():
                        skipped += 1
                        continue
                
                cursor.execute("""
                    INSERT INTO harlestons_orders (
                        po_number, location, club_nickname, process, invoice_number, pcs, priority,
                        in_hand_date, status, notes, inside_location, uploaded,
                        logo_file, club_colors, colors_verified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get("PO #", ""),
                    row.get("LOC", ""),
                    row.get("CLUB", ""),
                    row.get("PROCESS", ""),
                    invoice_num,
                    row.get("PCS", ""),
                    row.get("PRIORITY", ""),
                    row.get("IN-HAND DATE", ""),
                    row.get("Status", ""),
                    row.get("NOTES", ""),
                    row.get("Inside", ""),
                    row.get("Uploaded", ""),
                    row.get("LOGO FILE", ""),
                    row.get("CLUB COLORS", ""),
                    row.get("COLORS VERIFIED", "")
                ))
                imported += 1
        
        conn.commit()
        log(f"✅ Harlestons CSV import complete. Imported: {imported}, Skipped: {skipped}")
        return True
    
    except Exception as e:
        log(f"❌ Error importing Harlestons CSV: {str(e)}")
        return False
    
    finally:
        conn.close()

def sync_imm_orders():
    """Sync IMM orders from invoices table"""
    log("Starting IMM order synchronization...")
    
    # Get customer IDs for IMM using our direct function
    customer_ids = get_customer_ids_by_company_name("IMM")
    if not customer_ids:
        log("❌ No IMM customer IDs found.")
        return False
    
    log(f"Found {len(customer_ids)} IMM customer IDs")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get invoices for IMM customers - now including customer_due_date
    placeholders = ','.join(['?'] * len(customer_ids))
    cur.execute(f"""
        SELECT invoice_number, invoice_status, nickname, po_number, customer_due_date
        FROM invoices
        WHERE
            invoice_number IS NOT NULL
            AND TRIM(invoice_number) != ''
            AND customer_id IN ({placeholders})
    """, customer_ids)
    
    rows = cur.fetchall()
    log(f"Found {len(rows)} invoices for IMM customers")
    
    inserted = 0
    updated = 0
    skipped = 0
    
    for row in rows:
        invoice = row[0].strip() if row[0] else ""
        status = row[1] if row[1] else ""
        nickname = row[2] if row[2] else ""
        po = row[3] if row[3] else ""
        due_date = row[4] if len(row) > 4 and row[4] else ""
        
        status_clean = status.strip().lower()
        
        if not invoice:
            skipped += 1
            continue
        
        # Check if status is in excluded list
        if status_clean in {s.lower() for s in IMM_EXCLUDED_STATUSES}:
            log(f"Skipping invoice {invoice} with excluded status: {status}")
            skipped += 1
            continue
        
        cur.execute("SELECT id FROM imm_orders WHERE TRIM(invoice_number) = ?", (invoice,))
        existing = cur.fetchone()
        
        if existing:
            # Update existing order - now including customer_due_date
            # Also update in_hand_date with customer_due_date if available
            if due_date:
                cur.execute("""
                    UPDATE imm_orders
                    SET p_status = ?, customer_due_date = ?, in_hand_date = ?
                    WHERE invoice_number = ?
                """, (status, due_date, due_date, invoice))
            else:
                cur.execute("""
                    UPDATE imm_orders
                    SET p_status = ?
                    WHERE invoice_number = ?
                """, (status, invoice))
            updated += 1
        else:
            # Insert new order - now including customer_due_date
            # Also use customer_due_date as in_hand_date if available
            cur.execute("""
                INSERT INTO imm_orders (
                    invoice_number, p_status, nickname, po_number, status, 
                    customer_due_date, in_hand_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice,
                status,
                nickname or "",
                po or "",
                "Need Review",
                due_date,
                due_date
            ))
            inserted += 1
    
    conn.commit()
    conn.close()
    log(f"✅ IMM sync complete. Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
    return True

def sync_harlestons_orders():
    """Sync Harlestons orders from invoices table"""
    log("Starting Harlestons order synchronization...")
    
    # Get customer IDs for Harlestons using our direct function
    customer_ids = get_customer_ids_by_company_name("Harlestons")
    if not customer_ids:
        log("❌ No Harlestons customer IDs found.")
        return False
    
    log(f"Found {len(customer_ids)} Harlestons customer IDs")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get invoices for Harlestons customers
    placeholders = ','.join(['?'] * len(customer_ids))
    cur.execute(f"""
        SELECT invoice_number, invoice_status, nickname, po_number, customer_due_date
        FROM invoices
        WHERE
            invoice_number IS NOT NULL
            AND TRIM(invoice_number) != ''
            AND customer_id IN ({placeholders})
    """, customer_ids)
    
    rows = cur.fetchall()
    log(f"Found {len(rows)} invoices for Harlestons customers")
    
    inserted = 0
    updated = 0
    skipped = 0
    
    for row in rows:
        invoice = row[0].strip() if row[0] else ""
        status = row[1] if row[1] else ""
        nickname = row[2] if row[2] else ""
        po = row[3] if row[3] else ""
        
        status_clean = status.strip().lower()
        
        if not invoice:
            skipped += 1
            continue
        
        # Check if status is in excluded list
        if status_clean in {s.lower() for s in HARLESTONS_EXCLUDED_STATUSES}:
            log(f"Skipping invoice {invoice} with excluded status: {status}")
            skipped += 1
            continue
        
        cur.execute("SELECT id FROM harlestons_orders WHERE TRIM(invoice_number) = ?", (invoice,))
        existing = cur.fetchone()
        
        if existing:
            cur.execute("""
                UPDATE harlestons_orders
                SET p_status = ?
                WHERE invoice_number = ?
            """, (status, invoice))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO harlestons_orders (
                    invoice_number, p_status, club_nickname, po_number, status
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                invoice,
                status,
                nickname,
                po,
                "Need Review"
            ))
            inserted += 1
    
    conn.commit()
    conn.close()
    log(f"✅ Harlestons sync complete. Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
    return True

def update_terminal_filters():
    """Update the filters in the terminal views to match config settings"""
    log("Updating terminal view filters...")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Convert all excluded statuses to lowercase for case-insensitive comparison
    imm_excluded_statuses_lower = [s.lower() for s in IMM_EXCLUDED_STATUSES]
    imm_excluded_p_statuses_lower = [s.lower() for s in IMM_EXCLUDED_P_STATUSES]
    
    # Update IMM orders that should be hidden - using LOWER() function
    cur.execute("""
    UPDATE imm_orders
    SET status = 'Hidden'
    WHERE 
        LOWER(TRIM(status)) IN ({0})
        OR LOWER(TRIM(p_status)) IN ({1})
    """.format(
        ','.join(['?'] * len(imm_excluded_statuses_lower)),
        ','.join(['?'] * len(imm_excluded_p_statuses_lower))
    ), imm_excluded_statuses_lower + imm_excluded_p_statuses_lower)
    
    imm_updated = cur.rowcount
    log(f"Updated {imm_updated} IMM orders to 'Hidden' status")
    
    # Same for Harlestons
    harlestons_excluded_statuses_lower = [s.lower() for s in HARLESTONS_EXCLUDED_STATUSES]
    harlestons_excluded_p_statuses_lower = [s.lower() for s in HARLESTONS_EXCLUDED_P_STATUSES]
    
    cur.execute("""
        UPDATE harlestons_orders
        SET status = 'Hidden'
        WHERE 
            LOWER(status) IN ({0})
            OR LOWER(p_status) IN ({1})
    """.format(
        ','.join(['?'] * len(harlestons_excluded_statuses_lower)),
        ','.join(['?'] * len(harlestons_excluded_p_statuses_lower))
    ), harlestons_excluded_statuses_lower + harlestons_excluded_p_statuses_lower)
    
    harlestons_updated = cur.rowcount
    log(f"Updated {harlestons_updated} Harlestons orders to 'Hidden' status")
    
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


def sync_all():
    """Run all synchronization processes"""
    log("=== Starting full Printavo synchronization ===")
    
    # Check and create tables
    create_tables()
    
    # Check database structure
    check_database()
    
    # Sync IMM orders
    imm_success = sync_imm_orders()
    
    # Sync Harlestons orders
    harlestons_success = sync_harlestons_orders()
    
    # Import from CSV if files exist
    harlestons_csv = CSV_DIR / "harlestons_orders.csv"
    if os.path.exists(harlestons_csv):
        import_harlestons_csv(harlestons_csv)
    
    # Update terminal filters
    update_terminal_filters()
    
    # Backfill customer due dates
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
