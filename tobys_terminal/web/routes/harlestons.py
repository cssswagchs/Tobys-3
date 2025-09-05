# routes/harlestons.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from tobys_terminal.shared.auth_utils import get_db_connection, requires_permission
harlestons_bp = Blueprint('harlestons', __name__, url_prefix='/harlestons')

try:
    from config import HARLESTONS_EXCLUDED_STATUSES, HARLESTONS_EXCLUDED_P_STATUSES
except ImportError:
    pass  # Add a pass statement to handle the empty except block

# routes/harlestons.py
@harlestons_bp.route('/')
@requires_permission('view_production')
def terminal():
    # Check if user has admin permissions
    is_admin = 'admin' in session.get('role', '') or session.get('role') == 'admin'
    # Get filter parameters
    status_filter = request.args.get('status', '')
    process_filter = request.args.get('process', '')
    location_filter = request.args.get('location', '')
    search_query = request.args.get('search', '')
    
    # Base query
    query = """
        SELECT * FROM harlestons_orders
        WHERE 
            status != 'Hidden'
            AND TRIM(LOWER(p_status)) NOT IN ('done', 'template', 'done done', 'complete', 'cancelled', 'archived', 'shipped',
                'picked up', 'harlestons -- invoiced', 'harlestons -- no order pending',
                'harlestons -- picked up', 'harlestons-need sewout')
    """
    params = []
    
    # Apply filters if provided
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
        
    if process_filter:
        query += " AND process = ?"
        params.append(process_filter)
        
    if location_filter:
        query += " AND location = ?"
        params.append(location_filter)
        
    if search_query:
        query += """ AND (
            LOWER(po_number) LIKE ? OR 
            LOWER(club_nickname) LIKE ? OR 
            LOWER(notes) LIKE ?
        )"""
        search_term = f"%{search_query.lower()}%"
        params.extend([search_term, search_term, search_term])
    
    # Add ordering
    query += """
        ORDER BY 
        CASE priority
            WHEN 'High' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 3
            ELSE 4
        END,
        in_hand_date ASC
    """
    
    conn = get_db_connection()
    orders = conn.execute(query, params).fetchall()
    
    # Get filter options for dropdowns
    status_options = conn.execute(
        "SELECT DISTINCT status FROM harlestons_orders WHERE status IS NOT NULL ORDER BY status"
    ).fetchall()
    
    process_options = conn.execute(
        "SELECT DISTINCT process FROM harlestons_orders WHERE process IS NOT NULL ORDER BY process"
    ).fetchall()
    
    location_options = conn.execute(
        "SELECT DISTINCT location FROM harlestons_orders WHERE location IS NOT NULL ORDER BY location"
    ).fetchall()
    
    global_notes = conn.execute("SELECT value FROM notes WHERE key = 'harlestons_global_notes'").fetchone()
    
    # Check if user has edit permissions
    can_edit = 'manage_production' in session.get('permissions', [])
    
    conn.close()
    
    return render_template(
        'harlestons.html', 
        orders=orders, 
        global_notes=global_notes['value'] if global_notes else '',
        can_edit=can_edit,
        is_admin=is_admin,  # Pass admin status to template
        status_options=status_options,
        process_options=process_options,
        location_options=location_options,
        current_filters={
            'status': status_filter,
            'process': process_filter,
            'location': location_filter,
            'search': search_query
        }
    )


@harlestons_bp.route('/harlestons')
@requires_permission('view_production')
def view_orders():
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM harlestons_orders ORDER BY id').fetchall()
    note = conn.execute('SELECT value FROM notes WHERE key = ?', ('harlestons_global_notes',)).fetchone()
    
    # Check if user has edit permissions
    can_edit = 'manage_production' in requires_permission(session.get('user_id'))
    
    conn.close()
    global_note = note['value'] if note else ''
    return render_template('harlestons.html', orders=orders, global_notes=global_note, can_edit=can_edit)

@harlestons_bp.route('/save_notes', methods=['POST'])
@requires_permission('manage_production')
def save_notes():
    note_text = request.form.get('global_notes')
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO notes (key, value) VALUES (?, ?)',
                 ('harlestons_global_notes', note_text))
    conn.commit()
    conn.close()
    return redirect(url_for('harlestons.terminal'))

@harlestons_bp.route('/update_orders', methods=['POST'])
@requires_permission('manage_production')
def update_orders():
    conn = get_db_connection()
    updated_ids = set()
    
    # Check if user has admin permissions
    is_admin = 'admin' in session.get('role', '') or session.get('role') == 'admin'

    for key in request.form:
        if "_" in key:
            prefix, id_str = key.split("_", 1)
            order_id = id_str

            # Skip if we've already updated this order_id
            if order_id in updated_ids:
                continue

            # Grab all fields for this order
            po_number      = request.form.get(f'po_number_{order_id}')
            invoice_number = request.form.get(f'invoice_number_{order_id}')
            club_nickname  = request.form.get(f'club_nickname_{order_id}')
            location       = request.form.get(f'location_{order_id}')
            process        = request.form.get(f'process_{order_id}')
            pcs            = request.form.get(f'pcs_{order_id}')
            status         = request.form.get(f'status_{order_id}')
            notes          = request.form.get(f'notes_{order_id}')
            in_hands       = request.form.get(f'in_hands_{order_id}')
            priority       = request.form.get(f'priority_{order_id}')
            uploaded       = request.form.get(f'uploaded_{order_id}')
            inside_location = request.form.get(f'inside_{order_id}', 'No')
            
            # Only get p_status if user is admin
            if is_admin:
                p_status = request.form.get(f'p_status_{order_id}')
                
                # Update with p_status for admin users
                conn.execute('''
                    UPDATE harlestons_orders
                    SET po_number = ?, invoice_number = ?, club_nickname = ?, location = ?, 
                        process = ?, pcs = ?, status = ?, p_status = ?, notes = ?, 
                        in_hand_date = ?, priority = ?, uploaded = ?, inside_location = ?
                    WHERE id = ?
                ''', (
                    po_number, invoice_number, club_nickname, location,
                    process, pcs, status, p_status, notes,
                    in_hands, priority, uploaded, inside_location,
                    order_id
                ))
            else:
                # Update without p_status for non-admin users
                conn.execute('''
                    UPDATE harlestons_orders
                    SET po_number = ?, invoice_number = ?, club_nickname = ?, location = ?, 
                        process = ?, pcs = ?, status = ?, notes = ?, 
                        in_hand_date = ?, priority = ?, uploaded = ?, inside_location = ?
                    WHERE id = ?
                ''', (
                    po_number, invoice_number, club_nickname, location,
                    process, pcs, status, notes,
                    in_hands, priority, uploaded, inside_location,
                    order_id
                ))

            updated_ids.add(order_id)

    conn.commit()
    conn.close()
    return redirect(url_for('harlestons.terminal'))

@harlestons_bp.route('/home')
def landing_page():
    # Check if user has Harlestons access
    if session.get("company") != "Harlestons" and session.get("role") != "admin":
        flash("You do not have access to Harlestons", "error")
        return redirect(url_for("auth.login"))
        
    # Get user permissions for the template
    user_permissions = requires_permission(session.get('user_id'))
    
    return render_template(
        "harlestons_landing.html",
        user_permissions=user_permissions
    )
