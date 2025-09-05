# routes/auth.py
from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from tobys_terminal.shared.auth_utils import get_db_connection, get_user_permissions

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login"""
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        # Get user from database with role information
        conn = get_db_connection()
        
        # First, get the user's basic info and role name
        query = """
        SELECT u.id, u.username, u.password, u.company, r.name as role_name
        FROM portal_users u
        JOIN user_roles r ON u.role_id = r.id
        WHERE LOWER(u.username) = LOWER(?)
        """
        
        user = conn.execute(query, (username,)).fetchone()
        
        # Simple password check
        if user and user['password'] == password:
            # Get user permissions
            permissions = get_user_permissions(user['id'])
            
            # Store user info in session
            session["user_id"] = user['id']
            session["username"] = username
            session["company"] = user['company']
            session["role"] = user['role_name']
            session["permissions"] = permissions
            
            # Special case for Lori - check by username
            if username.lower() == "lori":
                return redirect(url_for("lori.lori_dashboard"))
                
            # Redirect based on role and company
            if user['role_name'] == "admin":
                return redirect(url_for("admin.dashboard"))
            
            # Employee roles - send directly to their respective terminals
            elif user['role_name'] == "harlestons_employee":
                return redirect(url_for("harlestons.terminal"))
            elif user['role_name'] == "imm_employee":
                return redirect(url_for("imm.terminal"))
                
            # Special case for Harlestons owner
            elif user['role_name'] == "harlestons_owner":
                return redirect(url_for("harlestons.landing_page"))
                
            # Customer landing pages
            elif user['company'] and user['company'].lower() == "harlestons":
                return redirect(url_for("harlestons.landing_page"))
            elif user['company'] and user['company'].lower() == "imm promotionals":
                return redirect(url_for("imm.landing_page"))
            else:
                # Default to customer portal
                return redirect(url_for("customer.customer_portal", company=user['company']))

        conn.close()
        flash("Invalid username or password", "error")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    """Handle user logout"""
    session.clear()
    return redirect(url_for("auth.login"))
