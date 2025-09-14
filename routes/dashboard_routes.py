# routes/dashboard_routes.py
# Main dashboard routes for the Flask application

from flask import Blueprint, render_template

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route("/")
def dashboard():
    """Renders the main dashboard page."""
    return render_template("index.html")

@dashboard_bp.route("/customer/<phone_number>")
def customer_invoices_page(phone_number):
    """Page to display customer invoices."""
    return render_template('customer_invoices.html')
