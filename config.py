# config.py
import os
import sys
from pathlib import Path
from datetime import datetime

# Determine if we're running from a frozen executable (like PyInstaller)
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    PROJECT_ROOT = Path(sys.executable).parent.absolute()
else:
    # Running in normal Python environment
    # Get the directory containing config.py (project root)
    PROJECT_ROOT = Path(__file__).parent.absolute()

# Base paths
DATA_DIR = PROJECT_ROOT / "tobys_terminal" / "shared" / "data"
ASSETS_DIR = PROJECT_ROOT / "tobys_terminal" / "shared" / "assets"
EXPORTS_DIR = PROJECT_ROOT / "tobys_terminal" / "shared" / "exports"

# Database path - use root level database
DB_PATH = os.environ.get('TOBYS_TERMINAL_DB')
if not DB_PATH:
    # Default to project root
    DB_PATH = PROJECT_ROOT / "terminal.db"
else:
    DB_PATH = Path(DB_PATH)

# Create necessary directories
LOG_DIR = PROJECT_ROOT / "logs"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Application settings
APP_NAME = "Toby's Terminal - CSS Billing"
APP_VERSION = "1.0.0"
APP_AUTHOR = "CSS Billing"

# Database settings
DB_CONNECTION_TIMEOUT = 5

# Logging settings
LOG_FILE = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# UI settings
UI_THEME = "sage"  # Your custom theme name
UI_FONT = ("Arial", 10)
UI_HEADER_FONT = ("Arial", 16, "bold")

# PDF export settings
PDF_EXPORT_DIR = EXPORTS_DIR
os.makedirs(PDF_EXPORT_DIR, exist_ok=True)

# Default date format
DATE_FORMAT = "%Y-%m-%d"
DATE_DISPLAY_FORMAT = "%m/%d/%Y"

# Status options
STATUS = (
    "Pending", 
    "In Progress", 
    "Complete", 
    "Need Sewout", 
    "Need Paperwork",
    "Need Product",
    "Need Files",
    "Need Approval",
    "Issue",
    "Inline-EMB",
    "Inline-DTF",
    "Inline-PAT",
    "Done Done"
)

# Production status options
P_STATUS = (
    "Complete and Ready for Pickup",
    "EMB - Flats - Inline",
    "EMB - Hats - Inline",
    "EMB - Need Sewout",
    "File Sent for Approval",
    "Picked Up",
    "Print DTF",
    "Waiting Product Only",
    "HARLESTONS -- EMB INLINE",
    "HARLESTONS -- FILE SENT FOR APPROVAL",
    "HARLESTONS -- NO ORDER PENDING",
    "HARLESTONS -- ON DECK",
    "HARLESTONS -- PICKED UP",
    "HARLESTONS -- WAITING ON PRODUCT",
    "HARLESTONS-NEED SEWOUT",
    "Heatpress",
    "Need Customer Supplied File",
    "SEWING - Need Product or Patches"
)

# Function to get database connection path
def get_db_path():
    """Get the path to the database file"""
    return os.path.join(os.path.dirname(__file__), 'terminal.db')

# Statuses to exclude from production terminals
EXCLUDED_STATUSES = {
    'done', 'cancelled', 'archived', 
    'done done', 'shipped', 'picked up'
}

# P-Statuses to exclude from production terminals
EXCLUDED_P_STATUSES = {
    'done', 'template', 'DONE DONE', 'complete', 'cancelled', 'archived', 'shipped',
    'picked up', 'harlestons -- invoiced', 'harlestons -- no order pending',
    'harlestons -- picked up'
}

# Customer IDs for main customers
IMM_CUSTOMER_ID = 4246724
HARLESTONS_CUSTOMER_ID = 5005118

# Lists of customer IDs for each company
IMM_CUSTOMER_IDS = [4246724]  # Add any additional IMM-related customer IDs here
HARLESTONS_CUSTOMER_IDS = [5005118]  # Add any additional Harlestons-related customer IDs here


# New filters for financial views - more permissive
FINANCIAL_EXCLUDED_STATUSES = {
    'cancelled', 'archived'  # Only exclude truly cancelled orders
}

FINANCIAL_EXCLUDED_P_STATUSES = {
    'cancelled', 'archived'  # Only exclude truly cancelled orders
}

# Company-specific versions
HARLESTONS_EXCLUDED_STATUSES = EXCLUDED_STATUSES
HARLESTONS_EXCLUDED_P_STATUSES = EXCLUDED_P_STATUSES | {
    'harlestons -- invoiced', 'harlestons -- no order pending',
    'harlestons -- picked up'
}
IMM_EXCLUDED_STATUSES = EXCLUDED_STATUSES
IMM_EXCLUDED_P_STATUSES = EXCLUDED_P_STATUSES

# Financial versions
HARLESTONS_FINANCIAL_EXCLUDED_STATUSES = FINANCIAL_EXCLUDED_STATUSES
HARLESTONS_FINANCIAL_EXCLUDED_P_STATUSES = FINANCIAL_EXCLUDED_P_STATUSES
IMM_FINANCIAL_EXCLUDED_STATUSES = FINANCIAL_EXCLUDED_STATUSES
IMM_FINANCIAL_EXCLUDED_P_STATUSES = FINANCIAL_EXCLUDED_P_STATUSES


# Field type definitions for formatting
FIELD_TYPES = {
    'invoice_number': 'invoice',
    'po_number': 'po',
    'pcs': 'numeric',
    'in_hand_date': 'date',
    'customer_due_date': 'date',
    'firm_date': 'boolean',  # Yes/No field
    'club_colors': 'boolean',
    'colors_verified': 'boolean',
    'inside_location': 'boolean',
    'uploaded': 'boolean',
}
# Invoice number formatting
def format_invoice_number(invoice_num, for_display=True):
    """
    Format invoice numbers consistently throughout the application.
    
    Args:
        invoice_num: The invoice number to format (can be int, float, or string)
        for_display (bool): If True, formats for UI display; if False, formats for database storage
        
    Returns:
        str: Formatted invoice number
    """
    if invoice_num is None or invoice_num == "":
        return ""
        
    try:
        # Convert to integer to remove decimal part
        num = int(float(invoice_num))
        return str(num)
    except (ValueError, TypeError):
        # If it's not a valid number, return as-is
        return str(invoice_num)

# Function to clean display values
def clean_display_value(value, field_type):
    """
    Clean up values for display based on their field type.
    
    Args:
        value: The value to clean
        field_type (str): The type of field ('invoice', 'po', 'numeric', 'date', 'boolean', etc.)
        
    Returns:
        The cleaned value ready for display
    """
    if value is None or value == "":
        return ""
        
    if field_type in ['invoice', 'po', 'numeric']:
        try:
            return str(int(float(value)))
        except (ValueError, TypeError):
            return str(value)
            
    if field_type == 'date' and value:
        try:
            # Convert from database format to display format
            date_obj = datetime.strptime(str(value), DATE_FORMAT)
            return date_obj.strftime(DATE_DISPLAY_FORMAT)
        except (ValueError, TypeError):
            return value
    
    if field_type == 'boolean':
        # Handle yes/no fields
        if isinstance(value, bool):
            return "Yes" if value else "No"
        elif isinstance(value, (int, float)):
            return "Yes" if value else "No"
        elif isinstance(value, str):
            value = value.lower().strip()
            if value in ('yes', 'y', 'true', '1'):
                return "Yes"
            elif value in ('no', 'n', 'false', '0'):
                return "No"
            return value.capitalize()  # Just capitalize existing string values
            
    return value
