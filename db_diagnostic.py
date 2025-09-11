# db_diagnostic.py
import os
import sys
import sqlite3
from pathlib import Path

def check_db_access():
    print("=== Database Access Diagnostic ===")
    
    # 1. Check current working directory
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    
    # 2. Try to import from config
    try:
        sys.path.insert(0, cwd)  # Ensure current directory is in path
        from config import get_db_path, PROJECT_ROOT
        
        print(f"Project root from config: {PROJECT_ROOT}")
        db_path = get_db_path()
        print(f"Database path from config: {db_path}")
        
        # Check if the file exists
        if os.path.exists(db_path):
            print(f"✓ Database file exists at: {db_path}")
            
            # Check permissions
            if os.access(db_path, os.R_OK):
                print(f"✓ Read permission OK")
            else:
                print(f"✗ No read permission on database file")
                
            if os.access(db_path, os.W_OK):
                print(f"✓ Write permission OK")
            else:
                print(f"✗ No write permission on database file")
                
            # Check if file is locked
            try:
                conn = sqlite3.connect(db_path, timeout=1)
                print(f"✓ Successfully connected to database")
                conn.close()
            except sqlite3.OperationalError as e:
                print(f"✗ Failed to connect to database: {e}")
                if "locked" in str(e).lower():
                    print("  Database may be locked by another process")
        else:
            print(f"✗ Database file does not exist at: {db_path}")
            
            # Check if the directory exists and is writable
            db_dir = os.path.dirname(db_path)
            if os.path.exists(db_dir):
                print(f"✓ Directory exists: {db_dir}")
                if os.access(db_dir, os.W_OK):
                    print(f"✓ Directory is writable")
                else:
                    print(f"✗ No write permission on directory")
            else:
                print(f"✗ Directory does not exist: {db_dir}")
    
    except ImportError as e:
        print(f"✗ Failed to import from config: {e}")
    
    # 3. Check for database in common locations
    common_locations = [
        os.path.join(cwd, "terminal.db"),
        os.path.join(os.path.dirname(cwd), "terminal.db"),
        os.path.join(os.path.dirname(os.path.dirname(cwd)), "terminal.db")
    ]
    
    print("\nChecking common locations:")
    for loc in common_locations:
        if os.path.exists(loc):
            print(f"✓ Found database at: {loc}")
        else:
            print(f"✗ No database at: {loc}")

if __name__ == "__main__":
    check_db_access()
