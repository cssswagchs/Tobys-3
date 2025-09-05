# --- System Imports ---
import os, sys, pathlib
from flask import Flask, render_template, redirect, url_for, session
from collections import defaultdict
import string
from dotenv import load_dotenv
from datetime import datetime
# --- Sentry Logging ---
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="https://70d83f1457688428216a2a6161f852f2@o4509887507136512.ingest.us.sentry.io/4509887667634176",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)

# --- Env and Shared Setup ---
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared')))

# Register filters
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.jinja_env.filters["dollars"] = lambda x: f"${float(x):,.2f}" if x else "$0.00"

# --- Register Blueprints ---
from routes.auth import auth_bp
from routes.lori import lori_bp
from routes.dashboard import dashboard_bp
from routes.customer_portal import customer_bp
from routes.harlestons import harlestons_bp
from routes.imm import imm_bp
from routes.dataimaging import dataimaging_bp
from routes.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(lori_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(harlestons_bp)
app.register_blueprint(imm_bp)
app.register_blueprint(dataimaging_bp)
app.register_blueprint(admin_bp)

# --- Error Pages ---
@app.errorhandler(404)
def not_found_error(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# --- Run Local Dev ---
if __name__ == "__main__":
    app.run(debug=True)