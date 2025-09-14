from flask import Blueprint, render_template, jsonify, request
import database
from cache import clear_cache
from performance_monitor import get_performance_report, clear_metrics

products_bp = Blueprint('products', __name__)

# API لجلب كل snapshot_date المتاحة
@products_bp.route('/api/products/inventory-dates')
def inventory_dates_api():
    try:
        dates = database.get_all_inventory_dates()
        return jsonify({'dates': dates})
    except Exception as e:
        print(f"Error getting inventory dates: {e}")
        return jsonify({'dates': []})
from flask import Blueprint, render_template, jsonify, request
import database
from cache import clear_cache
from performance_monitor import get_performance_report, clear_metrics

products_bp = Blueprint('products', __name__)

@products_bp.route('/products')
def products_page():
    """Main products page - loads quickly with basic data only"""
    try:
        # Get date filter from query parameter, default to yesterday (latest day with data)
        date_filter = request.args.get('date_filter', 'yesterday')
        
        # Load initial data with date filter
        top_products = database.get_top_10_products(date_filter)
        
        # Get available date ranges for the filter dropdown
        latest_date = database.get_latest_inventory_date()
        
        return render_template('products.html', 
                               top_products=top_products,
                               current_filter=date_filter,
                               latest_date=latest_date)
    except Exception as e:
        print(f"Error in products page: {e}")
        return render_template('products.html', 
                               top_products=[],
                               current_filter='yesterday',
                               latest_date=None)

@products_bp.route('/api/products/category')
def products_by_category_api():
    """API endpoint for products by category - loaded on demand"""
    try:
        date_filter = request.args.get('date_filter', 'yesterday')
        top_products_by_category = database.get_top_10_products_by_category(date_filter)
        return jsonify(top_products_by_category)
    except Exception as e:
        print(f"Error getting products by category: {e}")
        return jsonify([])

@products_bp.route('/api/products/inventory')
def products_inventory_api():
    """API endpoint for product inventory info - loaded on demand"""
    try:
        # Get barcodes from query parameter
        barcodes_param = request.args.get('barcodes', '')
        snapshot_date = request.args.get('snapshot_date', None)  # Optional specific date
        
        if not barcodes_param:
            return jsonify([])
        
        barcodes = barcodes_param.split(',')[:10]  # Limit to 10 for performance
        products_info = database.get_products_info(barcodes, snapshot_date)
        
        # Create warning products
        warning_products = []
        for info in products_info:
            qty = info.get('Qty On Hand', info.get('on_hand_quantity', 0))
            if qty and float(qty) < 10:
                warning_products.append({
                    'name': info.get('Product Name', info.get('product_name', '')),
                    'barcode': info.get('Barcode', info.get('product_barcode', '')),
                    'quantity': qty,
                    'snapshot_date': info.get('snapshot_date', 'N/A')
                })
        
        return jsonify({
            'products_info': products_info,
            'warning_products': warning_products
        })
    except Exception as e:
        print(f"Error getting products inventory: {e}")
        return jsonify({'products_info': [], 'warning_products': []})

@products_bp.route('/api/products/stock-history')
def products_stock_history_api():
    """API endpoint for stock history - loaded on demand"""
    try:
        # Get parameters from query
        barcodes_param = request.args.get('barcodes', '')
        days = int(request.args.get('days', 30))
        end_date = request.args.get('end_date', None)
        
        if not barcodes_param:
            return jsonify([])
        
        barcodes = barcodes_param.split(',')[:5]  # Limit to 5 for performance
        stock_history = database.get_products_stock_history(barcodes, days, end_date)
        return jsonify(stock_history)
    except Exception as e:
        print(f"Error getting stock history: {e}")
        return jsonify([])

@products_bp.route('/api/clear-cache')
def clear_cache_api():
    """Clear all cached data"""
    clear_cache()
    return jsonify({'status': 'Cache cleared successfully'})

@products_bp.route('/api/performance-report')
def performance_report():
    """Get performance metrics"""
    report = get_performance_report()
    return jsonify(report)

@products_bp.route('/api/clear-metrics')
def clear_metrics_api():
    """Clear performance metrics"""
    clear_metrics()
    return jsonify({'status': 'Performance metrics cleared'})

@products_bp.route('/api/products/refresh')
def refresh_products_data():
    """Refresh products data with new date filter"""
    try:
        date_filter = request.args.get('date_filter', 'yesterday')
        top_products = database.get_top_10_products(date_filter)
        return jsonify({
            'top_products': top_products,
            'current_filter': date_filter
        })
    except Exception as e:
        print(f"Error refreshing products data: {e}")
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/latest-date')
def get_latest_date_api():
    """Get the latest available inventory date"""
    try:
        latest_date = database.get_latest_inventory_date()
        return jsonify({
            'latest_date': str(latest_date) if latest_date else None
        })
    except Exception as e:
        print(f"Error getting latest date: {e}")
        return jsonify({'error': str(e)}), 500
