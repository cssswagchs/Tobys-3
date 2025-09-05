# routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from tobys_terminal.shared.auth_utils import get_db_connection, requires_permission
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@requires_permission('manage_users')  # Only true admins should access this
def dashboard():
    """Admin dashboard with system overview"""
    conn = get_db_connection()
    
    # Get system statistics
    stats = {
        'users': conn.execute("SELECT COUNT(*) as count FROM portal_users").fetchone()['count'],
        'harlestons_orders': conn.execute("SELECT COUNT(*) as count FROM harlestons_orders").fetchone()['count'],
        'imm_orders': conn.execute("SELECT COUNT(*) as count FROM imm_orders").fetchone()['count'],
        'active_harlestons': conn.execute(
            "SELECT COUNT(*) as count FROM harlestons_orders WHERE LOWER(status) NOT IN ('done', 'complete', 'done done', 'cancelled', 'archived')"
        ).fetchone()['count'],
        'active_imm': conn.execute(
            "SELECT COUNT(*) as count FROM imm_orders WHERE LOWER(status) NOT IN ('done', 'complete', 'cancelled', 'archived', 'done done')"
        ).fetchone()['count'],
    }
    
    # Get recent activity
    recent_harlestons = conn.execute("""
        SELECT * FROM harlestons_orders 
        ORDER BY id DESC LIMIT 5
    """).fetchall()
    
    recent_imm = conn.execute("""
        SELECT * FROM imm_orders 
        ORDER BY id DESC LIMIT 5
    """).fetchall()
    
    # Get user list for management
    users = conn.execute("""
        SELECT u.id, u.username, u.company, r.name as role_name
        FROM portal_users u
        JOIN user_roles r ON u.role_id = r.id
        ORDER BY u.username
    """).fetchall()
    
    conn.close()
    
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_harlestons=recent_harlestons,
        recent_imm=recent_imm,
        users=users
    )

@admin_bp.route('/users')
@requires_permission('manage_users')
def manage_users():
    """User management interface"""
    conn = get_db_connection()
    
    users = conn.execute("""
        SELECT u.id, u.username, u.company, r.name as role_name, r.id as role_id
        FROM portal_users u
        JOIN user_roles r ON u.role_id = r.id
        ORDER BY u.username
    """).fetchall()
    
    roles = conn.execute("SELECT * FROM user_roles ORDER BY name").fetchall()
    
    conn.close()
    
    return render_template('admin/users.html', users=users, roles=roles)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@requires_permission('manage_users')
def edit_user(user_id):
    """Edit a user's details"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        username = request.form.get('username')
        company = request.form.get('company')
        role_id = request.form.get('role_id')
        password = request.form.get('password')
        
        # Update user details
        if password and password.strip():
            conn.execute("""
                UPDATE portal_users
                SET username = ?, company = ?, role_id = ?, password = ?
                WHERE id = ?
            """, (username, company, role_id, password, user_id))
        else:
            conn.execute("""
                UPDATE portal_users
                SET username = ?, company = ?, role_id = ?
                WHERE id = ?
            """, (username, company, role_id, user_id))
        
        conn.commit()
        flash("User updated successfully!", "success")
        return redirect(url_for('admin.manage_users'))
    
    # Get user data for the form
    user = conn.execute("SELECT * FROM portal_users WHERE id = ?", (user_id,)).fetchone()
    roles = conn.execute("SELECT * FROM user_roles ORDER BY name").fetchall()
    
    conn.close()
    
    if not user:
        flash("User not found", "error")
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/edit_user.html', user=user, roles=roles)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@requires_permission('manage_users')
def new_user():
    """Create a new user"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        company = request.form.get('company')
        role_id = request.form.get('role_id')
        
        conn = get_db_connection()
        
        # Check if username already exists
        existing = conn.execute("SELECT id FROM portal_users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash("Username already exists", "error")
            roles = conn.execute("SELECT * FROM user_roles ORDER BY name").fetchall()
            conn.close()
            return render_template('admin/new_user.html', roles=roles)
        
        # Create new user
        conn.execute("""
            INSERT INTO portal_users (username, password, company, role_id)
            VALUES (?, ?, ?, ?)
        """, (username, password, company, role_id))
        
        conn.commit()
        conn.close()
        
        flash("User created successfully!", "success")
        return redirect(url_for('admin.manage_users'))
    
    conn = get_db_connection()
    roles = conn.execute("SELECT * FROM user_roles ORDER BY name").fetchall()
    conn.close()
    
    return render_template('admin/new_user.html', roles=roles)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@requires_permission('manage_users')
def delete_user(user_id):
    """Delete a user"""
    conn = get_db_connection()
    conn.execute("DELETE FROM portal_users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User deleted successfully!", "success")
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/system')
@requires_permission('manage_users')
def system_info():
    """System information and maintenance"""
    conn = get_db_connection()
    
    # Get database tables and counts
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_stats = {}
    
    for table in tables:
        table_name = table['name']
        if table_name.startswith('sqlite_'):
            continue
            
        count = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()['count']
        table_stats[table_name] = count
    
    conn.close()
    
    return render_template('admin/system.html', table_stats=table_stats)

@admin_bp.route('/notes', methods=['GET', 'POST'])
@requires_permission('manage_users')
def admin_notes():
    """Admin personal notes"""
    if request.method == 'POST':
        notes = request.form.get('notes', '')
        
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO notes (key, value) VALUES (?, ?)", 
                    ('admin_notes', notes))
        conn.commit()
        conn.close()
        
        flash("Notes saved successfully!", "success")
        return redirect(url_for('admin.admin_notes'))
    
    conn = get_db_connection()
    notes = conn.execute("SELECT value FROM notes WHERE key = 'admin_notes'").fetchone()
    conn.close()
    
    return render_template('admin/notes.html', notes=notes['value'] if notes else '')
