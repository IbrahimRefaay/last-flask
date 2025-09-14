# routes/debug_routes.py
# Debug routes for testing customer data

from flask import Blueprint, jsonify
from database import run_query, get_project_id, get_dataset_id, get_table_id

debug_bp = Blueprint('debug', __name__)

@debug_bp.route("/debug/customer-sample")
def debug_customer_sample():
    """Debug endpoint to see sample customer data."""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        sample_query = f"""
            SELECT 
                customer_name,
                phone_number,
                receipt_number,
                order_date,
                product_name,
                product_barcode,
                product_category,
                branch,
                quantity,
                subtotal_incl
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            WHERE phone_number IS NOT NULL 
              AND phone_number != ''
              AND phone_number != 'NULL'
              AND subtotal_incl IS NOT NULL
            ORDER BY order_date DESC
            LIMIT 10;
        """
        
        results = run_query(sample_query)
        
        if not results:
            return jsonify({"status": "error", "message": "No data found"}), 404
        
        sample_data = []
        for row in results:
            sample_data.append({
                "customer_name": row.customer_name,
                "phone_number": row.phone_number,
                "receipt_number": row.receipt_number,
                "order_date": row.order_date.isoformat() if row.order_date else None,
                "product_name": row.product_name,
                "product_barcode": row.product_barcode,
                "product_category": row.product_category,
                "branch": row.branch,
                "quantity": int(row.quantity or 0),
                "subtotal_incl": float(row.subtotal_incl or 0)
            })
        
        return jsonify({"status": "success", "data": sample_data})

    except Exception as e:
        print(f"❌ Error in debug sample: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@debug_bp.route("/debug/table-schema")
def debug_table_schema():
    """Debug endpoint to see table schema."""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        schema_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{TABLE_ID}'
            ORDER BY ordinal_position;
        """
        
        results = run_query(schema_query)
        
        if not results:
            return jsonify({"status": "error", "message": "No schema found"}), 404
        
        schema_data = []
        for row in results:
            schema_data.append({
                "column_name": row.column_name,
                "data_type": row.data_type,
                "is_nullable": row.is_nullable
            })
        
        return jsonify({"status": "success", "data": schema_data})

    except Exception as e:
        print(f"❌ Error in debug schema: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
