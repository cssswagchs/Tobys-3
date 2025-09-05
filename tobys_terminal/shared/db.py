import sqlite3
import os

# tobys_terminal/shared/db.py
import sqlite3

# Import from the root config
from config import get_db_path

def get_connection():
    """Get a connection to the database"""
    db_path = get_db_path()
    return sqlite3.connect(db_path)


def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create customers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        company TEXT,
        email TEXT,
        phone TEXT,
        billing_address1 TEXT,
        billing_address2 TEXT,
        billing_city TEXT,
        billing_state TEXT,
        billing_zip TEXT,
        billing_country TEXT,
        shipping_address1 TEXT,
        shipping_address2 TEXT,
        shipping_city TEXT,
        shipping_state TEXT,
        shipping_zip TEXT,
        shipping_country TEXT,
        tax_exempt TEXT,
        tax_resale_no TEXT,
        created_at TEXT,
        default_payment_term TEXT,
        default_payment_term_days INTEGER
    )
    """)

    # Create invoices table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE,
        customer_id INTEGER,
        invoice_date TEXT,
        po_number TEXT,
        total REAL,
        amount_paid REAL,
        amount_outstanding REAL,
        paid TEXT,
        invoice_status TEXT,
        sales_tax REAL,
        shipping REAL,
        convenience_fee REAL,
        customer_due_date TEXT,
        billing_address1 TEXT,
        billing_address2 TEXT,
        billing_city TEXT,
        billing_state TEXT,
        billing_zip TEXT,
        billing_country TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    # Create payments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY,
        transaction_date TEXT,
        amount REAL,
        invoice_number TEXT,
        payment_processor TEXT,
        payment_transaction_id TEXT,
        customer_id INTEGER,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (invoice_number) REFERENCES invoices(invoice_number)
    )
    """)


    conn.commit()
    conn.close()

    ensure_customer_profiles_table()

def ensure_views():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY,
        transaction_date TEXT,
        amount REAL,
        invoice_number TEXT,
        payment_method TEXT,        -- added
        reference TEXT,             -- added
        customer_id INTEGER,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (invoice_number) REFERENCES invoices(invoice_number)
    )
    """)

    conn.commit()
    conn.close()

def ensure_statement_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Table to assign statement numbers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS statement_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            statement_number TEXT UNIQUE,
            customer_id INTEGER,
            generated_on TEXT,
            start_date TEXT,
            end_date TEXT
        )
    """)
    # Add optional columns if they don’t exist yet
    try:
        cursor.execute("ALTER TABLE statement_tracking ADD COLUMN company_label TEXT")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE statement_tracking ADD COLUMN customer_ids_text TEXT")
    except Exception:
        pass


    # Table to track which invoices were included in which statement
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_tracking (
            invoice_number TEXT PRIMARY KEY,
            statement_number TEXT,
            tagged_on TEXT
        )
    """)

    conn.commit()
    conn.close()
 # Create customer_profiles table
def ensure_customer_profiles_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_profiles (
            company TEXT PRIMARY KEY,
            contract_type TEXT CHECK(contract_type IN ('Contract', 'Direct', 'Retail') OR contract_type IS NULL),
            status TEXT,
            contact_name TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            billing_address TEXT,
            verified TEXT
        )
    """)

    try:
        cursor.execute("ALTER TABLE customer_profiles ADD COLUMN status TEXT CHECK (status IN ('Active', 'Inactive') OR status IS NULL)")
    except:
        pass

    conn.commit()
    conn.close()

def ensure_company_profiles_table():
    """Create a table to store normalized company information"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            normalized_name TEXT NOT NULL,
            parent_company_id INTEGER NULL,
            is_active BOOLEAN DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_company_id) REFERENCES company_profiles(id)
        )
    """)
    
    # Create index for faster lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_normalized_name ON company_profiles(normalized_name)")
    conn.commit()
    conn.close()


def ensure_customer_company_mapping():
    """Create a table to map customers to companies"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_company_mapping (
            customer_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            is_primary BOOLEAN DEFAULT 1,
            role TEXT,
            PRIMARY KEY (customer_id, company_id),
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (company_id) REFERENCES company_profiles(id)
        )
    """)
    conn.commit()
    conn.close()


def generate_statement_number(customer_id, start_date, end_date, company_label=None, customer_ids_list=None):

    conn = get_connection()
    cursor = conn.cursor()
    # Accept a list/tuple of IDs, but keep single int for the FK column
    ids_text = None
    primary_id = customer_id
    if isinstance(customer_id, (list, tuple)):
        ids_text = ",".join(str(x) for x in customer_id)
        primary_id = customer_id[0] if customer_id else None

    if customer_ids_list and not ids_text:
        ids_text = ",".join(str(x) for x in customer_ids_list)


    cursor.execute("""
        INSERT INTO statement_tracking (statement_number, customer_id, generated_on, start_date, end_date, company_label, customer_ids_text)
        VALUES (?, ?, DATE('now'), ?, ?, ?, ?)
    """, ("TEMP", primary_id, start_date, end_date, company_label, ids_text))


    row_id = cursor.lastrowid
    statement_number = f"S{row_id:05d}"

    cursor.execute("UPDATE statement_tracking SET statement_number = ? WHERE id = ?", (statement_number, row_id))
    conn.commit()
    conn.close()

    return statement_number


# utils/db.py or wherever your DB helpers live
from typing import Tuple, List, Optional

def get_statement_meta(statement_number: str):
    """
    Returns (customer_id, start_date, end_date) for a statement_number.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT customer_id, start_date, end_date
        FROM statement_tracking
        WHERE statement_number = ?
    """, (statement_number,))
    row = cur.fetchone()
    conn.close()
    return (row[0], row[1], row[2]) if row else None


def get_statement_invoices(statement_number: str):
    """
    Returns the list of invoice_numbers included in a statement.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT invoice_number
        FROM invoice_tracking
        WHERE statement_number = ?
        ORDER BY invoice_number
    """, (statement_number,))
    nums = [r[0] for r in cur.fetchall()]
    conn.close()
    return nums

# utils/db.py (or your db module)
def ensure_indexes():
    conn = get_connection()
    cur = conn.cursor()
    stmts = [
        "CREATE INDEX IF NOT EXISTS idx_invoices_customer   ON invoices(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_number     ON invoices(invoice_number)",
        "CREATE INDEX IF NOT EXISTS idx_payments_invoice    ON payments(invoice_number)",
        "CREATE INDEX IF NOT EXISTS idx_payments_customer   ON payments(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_payment_tracking_inv ON payment_tracking(invoice_number)",
    ]
    for sql in stmts:
        try:
            cur.execute(sql)
        except Exception:
            pass
    conn.commit()
    conn.close()


def get_contract_type(company: str) -> str | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT contract_type FROM customer_profiles WHERE company = ?", (company,))
    row = cur.fetchone()
    return row[0] if row else None

def set_contract_type(company: str, value: str | None) -> None:
    if value not in (None, "Contract", "Retail", "Direct"):
        raise ValueError("Invalid contract_type value.")
    conn = get_connection()
    cur = conn.cursor()
    if value is None:
        cur.execute("DELETE FROM customer_profiles WHERE company = ?", (company,))
    else:
        cur.execute("""
            INSERT INTO customer_profiles (company, contract_type)
            VALUES (?, ?)
            ON CONFLICT(company) DO UPDATE SET contract_type=excluded.contract_type
        """, (company, value))
    conn.commit()

def get_customer_status(company: str) -> str | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM customer_profiles WHERE company = ?", (company,))
    row = cur.fetchone()
    return row[0] if row else None

def set_customer_status(company: str, value: str | None) -> None:
    if value not in (None, "Active", "Inactive"):
        raise ValueError("Invalid status value.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO customer_profiles (company, status)
        VALUES (?, ?)
        ON CONFLICT(company) DO UPDATE SET status=excluded.status
    """, (company, value))
    conn.commit()
