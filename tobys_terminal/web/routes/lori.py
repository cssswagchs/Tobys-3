# 📁 routes/lori.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from tobys_terminal.shared.auth_utils import get_db_connection, requires_permission

lori_bp = Blueprint('lori', __name__, url_prefix='/lori')

@lori_bp.route('/dashboard')
def lori_dashboard():
    """Lori's custom dashboard"""
    # Get Lori's notes from the database
    conn = get_db_connection()
    notes = conn.execute("SELECT value FROM notes WHERE key = 'lori_notes'").fetchone()
    conn.close()
    
    return render_template('lori_dashboard.html', notes=notes['value'] if notes else '')

@lori_bp.route('/save_notes', methods=['POST'])
def save_notes():
    """Save Lori's notes"""
    notes = request.form.get('notes', '')
    
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO notes (key, value) VALUES (?, ?)", 
                ('lori_notes', notes))
    conn.commit()
    conn.close()
    
    flash("Notes saved successfully!", "success")
    return redirect(url_for('lori.lori_dashboard'))