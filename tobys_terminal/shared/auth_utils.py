# tobys_terminal/shared/auth_utils.py
import sqlite3
from functools import wraps
from flask import session, redirect, url_for, flash, current_app

def get_db_connection():
    """Create and return a database connection with row factory"""
    from config import get_db_path
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def get_user_permissions(user_id):
    """Get all permissions for a user based on their role"""
    query = """
    SELECT p.name 
    FROM permissions p
    JOIN role_permissions rp ON p.id = rp.permission_id
    JOIN user_roles r ON rp.role_id = r.id
    JOIN portal_users u ON u.role_id = r.id
    WHERE u.id = ?
    
    UNION
    
    SELECT p.name
    FROM permissions p
    JOIN user_permissions up ON p.id = up.permission_id
    WHERE up.user_id = ?
    """
    
    conn = get_db_connection()
    permissions = conn.execute(query, (user_id, user_id)).fetchall()
    conn.close()
    
    return [p['name'] for p in permissions]

def requires_permission(permission=None):
    """Decorator to check if user has required permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
                
            # Admin can access everything
            if session.get('role') == 'admin':
                return f(*args, **kwargs)
                
            # Check specific permission if needed
            if permission and permission not in session.get('permissions', []):
                flash(f'You need {permission} permission to access this feature', 'error')
                return redirect(url_for('dashboard.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_company_permission(company=None, permission=None):
    """Decorator to check if user has permission for a specific company"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
                
            # Admin can access everything
            if session.get('role') == 'admin':
                return f(*args, **kwargs)
                
            # Check company match if specified
            if company and session.get('company') != company:
                flash(f'You do not have access to {company}', 'error')
                return redirect(url_for('dashboard.index'))
                
            # Check specific permission if needed
            if permission and permission not in session.get('permissions', []):
                flash(f'You need {permission} permission to access this feature', 'error')
                return redirect(url_for('dashboard.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
