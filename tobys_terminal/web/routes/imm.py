# routes/imm.py
from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from tobys_terminal.shared.auth_utils import get_db_connection, requires_permission

imm_bp = Blueprint('imm', __name__, url_prefix='/imm')
try:
    from config import IMM_EXCLUDED_STATUSES, IMM_EXCLUDED_P_STATUSES
except ImportError:
    pass
# routes/imm.py
@imm_bp.route('/')
@requires_permission('view_production')
def terminal():
    # Get filter parameters
    status_filter = request.args.get('status', '')
    process_filter = request.args.get('process', '')
    firm_date_filter = request.args.get('firm_date', '')
    search_query = request.args.get('search', '')
    
    # Check if user has admin permissions
    is_admin = 'admin' in session.get('role', '') or session.get('role') == 'admin'
    
    # Base query
    query = """
        SELECT * FROM imm_orders
        WHERE 
            status != 'Hidden'
            AND TRIM(LOWER(p_status)) NOT IN ('done', 'complete', 'cancelled', 'archived', 'done done')
    """
    params = []
    
    # Apply filters if provided
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
        
    if process_filter:
        query += " AND process = ?"
        params.append(process_filter)
        
    if firm_date_filter:
        query += " AND firm_date = ?"
        params.append(firm_date_filter)
        
    if search_query:
        query += """ AND (
            LOWER(po_number) LIKE ? OR 
            LOWER(nickname) LIKE ? OR 
            LOWER(notes) LIKE ? OR
            LOWER(invoice_number) LIKE ?
        )"""
        search_term = f"%{search_query.lower()}%"
        params.extend([search_term, search_term, search_term, search_term])
    
    # Add ordering by customer_due_date if available
    query += """
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
        COALESCE(customer_due_date, in_hand_date) ASC
    """
    
    conn = get_db_connection()
    orders = conn.execute(query, params).fetchall()
    
    # Get filter options for dropdowns
    status_options = conn.execute(
        "SELECT DISTINCT status FROM imm_orders WHERE status IS NOT NULL ORDER BY status"
    ).fetchall()
    
    process_options = conn.execute(
        "SELECT DISTINCT process FROM imm_orders WHERE process IS NOT NULL ORDER BY process"
    ).fetchall()
    
    # If admin, get p_status options
    p_status_options = []
    if is_admin:
        p_status_options = conn.execute(
            "SELECT DISTINCT p_status FROM imm_orders WHERE p_status IS NOT NULL ORDER BY p_status"
        ).fetchall()
    
    # Check if user has edit permissions
    can_edit = 'manage_production' in session.get('permissions', [])
    
    conn.close()
    
    return render_template(
        'imm.html', 
        orders=orders, 
        can_edit=can_edit,
        is_admin=is_admin,  # Pass admin status to template
        status_options=status_options,
        process_options=process_options,
        p_status_options=p_status_options if is_admin else [],  # Only pass if admin
        current_filters={
            'status': status_filter,
            'process': process_filter,
            'firm_date': firm_date_filter,
            'search': search_query
        }
    )

@imm_bp.route('/update_orders', methods=['POST'])
@requires_permission('manage_production')
def update_orders():
    """Update IMM orders (requires manage_production permission)"""
    conn = get_db_connection()
    updated_ids = set()
    
    # Check if user has admin permissions
    is_admin = 'admin' in session.get('role', '') or session.get('role') == 'admin'

    for key in request.form:
        if "_" in key:
            prefix, id_str = key.split("_", 1)
            order_id = id_str
            if order_id in updated_ids:
                continue

            # Get common fields for all users
            po_number      = request.form.get(f'po_number_{order_id}')
            project_name   = request.form.get(f'project_name_{order_id}')
            in_hands       = request.form.get(f'in_hands_{order_id}')
            firm_date      = request.form.get(f'firm_date_{order_id}', 'No')
            invoice_number = request.form.get(f'invoice_number_{order_id}')
            process        = request.form.get(f'process_{order_id}')
            status         = request.form.get(f'status_{order_id}')
            notes          = request.form.get(f'notes_{order_id}')
            
            # Only admin users can update p_status
            if is_admin:
                p_status = request.form.get(f'p_status_{order_id}')
                
                # Update with p_status for admin users
                conn.execute('''
                    UPDATE imm_orders
                    SET po_number = ?, nickname = ?, in_hand_date = ?, firm_date = ?, 
                        invoice_number = ?, process = ?, status = ?, p_status = ?, notes = ?
                    WHERE id = ?
                ''', (
                    po_number, project_name, in_hands, firm_date, 
                    invoice_number, process, status, p_status, notes, order_id
                ))
            else:
                # Update without changing p_status for non-admin users
                conn.execute('''
                    UPDATE imm_orders
                    SET po_number = ?, nickname = ?, in_hand_date = ?, firm_date = ?, 
                        invoice_number = ?, process = ?, status = ?, notes = ?
                    WHERE id = ?
                ''', (
                    po_number, project_name, in_hands, firm_date, 
                    invoice_number, process, status, notes, order_id
                ))

            updated_ids.add(order_id)

    conn.commit()
    conn.close()
    flash("✅ Orders updated successfully!", "success")
    return redirect(url_for('imm.terminal'))

@imm_bp.route('/new', methods=['GET', 'POST'])
@requires_permission('manage_production')
def new_order():
    """Add a new IMM order (requires manage_production permission)"""
    if request.method == 'POST':
        po_number = request.form.get('po_number')
        nickname = request.form.get('nickname')
        in_hand_date = request.form.get('in_hand_date') or ''
        firm_date = 'Yes' if request.form.get('firm_date') == 'Yes' else 'No'
        invoice_number = request.form.get('invoice_number').strip() or None
        process = request.form.get('process') or ''
        status = request.form.get('status') or ''
        notes = request.form.get('notes') or ''

        conn = get_db_connection()
        cur = conn.cursor()

        # Check for duplicate invoice number
        if invoice_number:
            existing = cur.execute("""
                SELECT id FROM imm_orders WHERE invoice_number = ?
            """, (invoice_number,)).fetchone()

            if existing:
                conn.close()
                flash(f"⚠️ Invoice #{invoice_number} already exists!", "error")
                return redirect(url_for('imm.new_order'))

        # Insert the new order
        cur.execute("""
            INSERT INTO imm_orders (
                po_number, nickname, in_hand_date, firm_date,
                invoice_number, process, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (po_number, nickname, in_hand_date, firm_date,
              invoice_number, process, status, notes))
        conn.commit()
        conn.close()

        flash("✅ New IMM order added!", "success")
        return redirect(url_for('imm.terminal'))

    return render_template('imm_new.html')

@imm_bp.route('/report')
@requires_permission('view_production')
def generate_report():
    """Generate a PDF report of IMM orders by status"""
    status = request.args.get('status', '')
    # Report generation logic here
    flash("Report generation coming soon!", "info")
    return redirect(url_for('imm.terminal'))

@imm_bp.route('/home')
def landing_page():
    """IMM landing page with access to billing and production"""
    # Check if user has IMM access
    if session.get("company") != "IMM Promotionals" and session.get("role") != "admin":
        flash("Unauthorized", "error")
        return redirect(url_for("auth.login"))
        
    # Get user permissions for the template
    user_permissions = session.get('permissions', [])
    
    return render_template("imm_landing.html", user_permissions=user_permissions)
