import os, io, csv, sys
import sqlite3

from flask import Blueprint, render_template
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared')))

dataimaging_bp = Blueprint("dataimaging", __name__, url_prefix="/dataimaging")

def get_db_connection():
    conn = sqlite3.connect('terminal.db')
    conn.row_factory = sqlite3.Row
    return conn

@dataimaging_bp.route("/")
def terminal():
    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM dataimaging_orders").fetchall()
    conn.close()
    return render_template("dataimaging.html", orders=orders)
