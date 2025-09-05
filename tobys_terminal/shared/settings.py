# tobys_terminal/shared/settings.py
import json
from tobys_terminal.shared.db import get_connection

def ensure_settings_table():
    """Create the settings table if it doesn't exist"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            value_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    """
    Get a setting value by key, returning default if not found.
    Automatically converts to the appropriate Python type.
    """
    ensure_settings_table()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value, value_type FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return default
    
    value, value_type = row
    
    # Convert to appropriate type
    if value_type == 'int':
        return int(value)
    elif value_type == 'float':
        return float(value)
    elif value_type == 'bool':
        return value.lower() in ('true', '1', 'yes')
    elif value_type == 'json':
        return json.loads(value)
    else:  # Default to string
        return value

def set_setting(key, value):
    """
    from tobys_terminal.shared.settings import get_setting, set_setting

    # Store a simple string
    set_setting('company_name', 'CSS Embroidery & Print')

    # Store a number
    set_setting('invoice_start_number', 1000)

    # Store a boolean
    set_setting('dark_mode_enabled', False)

    # Store complex data
    set_setting('recent_customers', ['Customer A', 'Customer B', 'Customer C'])

    # Retrieve settings with defaults
    company_name = get_setting('company_name', 'Default Company')
    invoice_start = get_setting('invoice_start_number', 1)
    dark_mode = get_setting('dark_mode_enabled', False)
    recent = get_setting('recent_customers', [])

    """
    ensure_settings_table()
    
    # Determine value type
    if isinstance(value, int):
        value_type = 'int'
    elif isinstance(value, float):
        value_type = 'float'
    elif isinstance(value, bool):
        value_type = 'bool'
        value = str(value).lower()
    elif isinstance(value, (dict, list, tuple)):
        value_type = 'json'
        value = json.dumps(value)
    else:
        value_type = 'str'
        value = str(value)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value, value_type, updated_at) 
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (key, value, value_type))
    conn.commit()
    conn.close()

def get_all_settings():
    """
    Get all settings as a dictionary.
    """
    ensure_settings_table()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value, value_type FROM settings")
    rows = cursor.fetchall()
    conn.close()
    
    settings = {}
    for key, value, value_type in rows:
        if value_type == 'int':
            settings[key] = int(value)
        elif value_type == 'float':
            settings[key] = float(value)
        elif value_type == 'bool':
            settings[key] = value.lower() in ('true', '1', 'yes')
        elif value_type == 'json':
            settings[key] = json.loads(value)
        else:
            settings[key] = value
    
    return settings

def delete_setting(key):
    """
    Delete a setting by key.
    """
    ensure_settings_table()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
    conn.commit()
    conn.close()

