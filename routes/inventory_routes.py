# routes/inventory_routes.py
# This file contains the route for the inventory history dashboard page.

from flask import Blueprint, render_template, jsonify
# Assuming you have a central place for your BigQuery logic, like in the example
from database import run_query, get_project_id, get_dataset_id
from cache import cache_query
from performance_monitor import performance_monitor

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route("/inventory")
def inventory_dashboard():
    """
    Lightweight route that only loads filter data for dropdowns.
    Main inventory data is loaded asynchronously via API.
    """
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        INVENTORY_TABLE_ID = "inventory_levels_history"

        # Lightweight query to get only unique products and locations for filters
        query = f"""
            SELECT DISTINCT 
                product_name, 
                product_barcode, 
                location_name
            FROM `{PROJECT_ID}.{DATASET_ID}.{INVENTORY_TABLE_ID}`
            WHERE snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
            AND product_name IS NOT NULL 
            AND product_barcode IS NOT NULL
            AND location_name IS NOT NULL
            ORDER BY product_name, location_name
            LIMIT 500
        """
        results = run_query(query)
        
        # Process unique products and locations
        products_dict = {}
        locations_set = set()
        
        for row in results:
            if row['product_barcode'] and row['product_name']:
                products_dict[row['product_barcode']] = {
                    'product_barcode': row['product_barcode'],
                    'product_name': row['product_name']
                }
            if row['location_name']:
                locations_set.add(row['location_name'])
        
        unique_products = list(products_dict.values())
        unique_locations = sorted(list(locations_set))
        
        return render_template(
            "inventory_dashboard.html", 
            products=unique_products,
            locations=unique_locations
        )

    except Exception as e:
        print(f"❌ Error in /inventory route: {e}")
        return render_template(
            "inventory_dashboard.html", 
            products=[], 
            locations=[]
        )

@inventory_bp.route("/api/inventory/history")
@performance_monitor('inventory_history_api')
def inventory_history_api():
    """
    API endpoint to serve large inventory history dataset asynchronously.
    This decouples heavy data transfer from initial page load.
    """
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        INVENTORY_TABLE_ID = "inventory_levels_history"

        # The original heavy query for 90-day inventory history
        query = f"""
            SELECT 
                FORMAT_DATE('%Y-%m-%d', snapshot_date) as snapshot_date, 
                product_name, 
                product_barcode, 
                location_name, 
                on_hand_quantity,
                reserved_quantity,
                available_quantity
            FROM `{PROJECT_ID}.{DATASET_ID}.{INVENTORY_TABLE_ID}`
            WHERE snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
            ORDER BY snapshot_date DESC, product_name
            LIMIT 50000
        """
        results = run_query(query)
        
        stock_history = [dict(row) for row in results]
        
        return jsonify({
            'status': 'success',
            'data': stock_history,
            'total_records': len(stock_history)
        })

    except Exception as e:
        print(f"❌ Error in /api/inventory/history: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'data': []
        }), 500

@inventory_bp.route("/api/inventory/filtered")
@performance_monitor('inventory_filtered_api')
def inventory_filtered_api():
    """
    API endpoint for filtered inventory data based on product/location.
    """
    try:
        from flask import request
        
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        INVENTORY_TABLE_ID = "inventory_levels_history"
        
        # Get filter parameters
        product_barcode = request.args.get('product_barcode', '')
        location_name = request.args.get('location_name', '')
        days = int(request.args.get('days', 30))
        
        # Build dynamic WHERE clause
        where_conditions = [f"snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)"]
        
        if product_barcode:
            where_conditions.append(f"product_barcode = '{product_barcode}'")
        if location_name:
            where_conditions.append(f"location_name = '{location_name}'")
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
            SELECT 
                FORMAT_DATE('%Y-%m-%d', snapshot_date) as snapshot_date, 
                product_name, 
                product_barcode, 
                location_name, 
                on_hand_quantity,
                reserved_quantity,
                available_quantity
            FROM `{PROJECT_ID}.{DATASET_ID}.{INVENTORY_TABLE_ID}`
            WHERE {where_clause}
            ORDER BY snapshot_date DESC, product_name
            LIMIT 10000
        """
        results = run_query(query)
        
        filtered_data = [dict(row) for row in results]
        
        return jsonify({
            'status': 'success',
            'data': filtered_data,
            'total_records': len(filtered_data),
            'filters': {
                'product_barcode': product_barcode,
                'location_name': location_name,
                'days': days
            }
        })

    except Exception as e:
        print(f"❌ Error in /api/inventory/filtered: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'data': []
        }), 500
