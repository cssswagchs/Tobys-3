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
    """Return the database path, creating parent directories if needed"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return str(DB_PATH)

# Statuses to exclude from production terminals
EXCLUDED_STATUSES = {
    'done', 'cancelled', 'archived', 
    'done done', 'shipped', 'picked up'
}

# P-Statuses to exclude from production terminals
EXCLUDED_P_STATUSES = {
    'done', 'template', 'DONE DONE', 'complete', 'cancelled', 'archived', 'shipped',
    'picked up', 'harlestons -- invoiced', 'harlestons -- no order pending',
    'harlestons -- picked up', 'harlestons-need sewout'
}

# Harlestons-specific exclusions
HARLESTONS_EXCLUDED_STATUSES = EXCLUDED_STATUSES
HARLESTONS_EXCLUDED_P_STATUSES = EXCLUDED_P_STATUSES | {
    'harlestons -- invoiced', 'harlestons -- no order pending',
    'harlestons -- picked up', 'harlestons-need sewout'
}

# IMM-specific exclusions
IMM_EXCLUDED_STATUSES = EXCLUDED_STATUSES
IMM_EXCLUDED_P_STATUSES = EXCLUDED_P_STATUSES
