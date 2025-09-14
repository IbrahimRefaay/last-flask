from flask import Flask, render_template
from routes.dashboard_routes import dashboard_bp
from routes.kpi_routes import kpi_bp
from routes.analytics_routes import analytics_bp
from routes.seller_routes import seller_bp
from routes.returns_routes import returns_bp
from routes.products_routes import products_bp
from routes.inventory_routes import inventory_bp
from routes.admin_routes import admin_bp
from routes.stock_routes import stock_bp
from routes.inventory_dashboard_routes import inventory_dashboard_bp
from routes.services_routes import services_bp
from routes.debug_routes import debug_bp
from routes.customers_routes import customers_bp
from database import init_bigquery_client

app = Flask(__name__)

# Initialize BigQuery client
init_bigquery_client()

# Register blueprints with descriptive names and /api prefix

app.register_blueprint(dashboard_bp)
app.register_blueprint(kpi_bp, url_prefix='/api')
app.register_blueprint(analytics_bp, url_prefix='/api')
app.register_blueprint(seller_bp, url_prefix='/api')
app.register_blueprint(returns_bp, url_prefix='/api')
app.register_blueprint(stock_bp, url_prefix='/api')
app.register_blueprint(inventory_dashboard_bp)
app.register_blueprint(products_bp)
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(services_bp)
app.register_blueprint(debug_bp, url_prefix='/debug')
app.register_blueprint(customers_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
