# --- System Imports ---
import os, sys, pathlib
from flask import Flask, render_template
from datetime import datetime

# --- Sentry Logging ---
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# --- Local Imports ---
# Import the Config class from your config file
from config import Config 

# --- App Initialization ---
app = Flask(__name__)

# Load all configuration from our Config object
app.config.from_object(Config)

# --- Initialize Sentry (now using the config) ---
if app.config.get('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=app.config['SENTRY_DSN'],
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
        # Set the environment for Sentry to distinguish between dev and prod issues
        environment=app.config.get('FLASK_ENV', 'production') 
    )

# --- Register Blueprints ---
from tobys_terminal.web.routes.auth import auth_bp
from tobys_terminal.web.routes.lori import lori_bp
from tobys_terminal.web.routes.dashboard import dashboard_bp
from tobys_terminal.web.routes.customer_portal import customer_bp
from tobys_terminal.web.routes.harlestons import harlestons_bp
from tobys_terminal.web.routes.imm import imm_bp
from tobys_terminal.web.routes.dataimaging import dataimaging_bp
from tobys_terminal.web.routes.admin import admin_bp

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

# --- Context Processors & Filters 
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

app.jinja_env.filters["dollars"] = lambda x: f"${float(x):,.2f}" if x else "$0.00"


# --- Run Local Dev ---
if __name__ == "__main__":
    app.run()