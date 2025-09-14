# routes/stock_routes.py
# Stock and inventory API routes

from flask import Blueprint, jsonify
from decimal import Decimal
from database import run_query, get_project_id, get_dataset_id, get_table_id
from utils import get_user_filters_string

stock_bp = Blueprint('stock', __name__)

@stock_bp.route("/stock-products")
def stock_products():
    """API endpoint for top 20 products with stock information."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        # Query to get top 20 products by sales with their stock information
        stock_query = f"""
            WITH SalesData AS (
                SELECT 
                    product_barcode,
                    product_name,
                    SUM(quantity) as total_quantity,
                    SUM(subtotal_incl) as total_sales,
                    SUM(ROUND((subtotal_incl / 1.15), 2) - (total_cost)) as total_profit
                FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
                {where_sql}
                    {"AND" if where_sql else "WHERE"} quantity > 0 
                    AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%pos%')
                    AND product_barcode IS NOT NULL
                    AND product_barcode != ''
                GROUP BY product_barcode, product_name
                ORDER BY total_sales DESC
                LIMIT 20
            ),
            StockData AS (
                SELECT 
                    Barcode as barcode,
                    MAX(Product_Name) as product_name,
                    MAX(Category) as category,
                    SUM(Qty_On_Hand) as qty_on_hand,
                    SUM(Reserved_Qty) as reserved_qty,
                    SUM(Available_Qty) as available_qty,
                    AVG(Unit_Cost) as unit_cost,
                    SUM(Total_Cost) as total_cost
                FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
                WHERE Barcode IS NOT NULL
                GROUP BY Barcode
            )
            SELECT 
                s.product_barcode,
                s.product_name,
                CAST(s.total_quantity AS INT64) as total_quantity,
                CAST(s.total_sales AS NUMERIC) as total_sales,
                CAST(s.total_profit AS NUMERIC) as total_profit,
                CAST(COALESCE(st.available_qty, 0) AS INT64) as current_stock,
                st.product_name as stock_product_name,
                st.category as stock_category,
                CAST(st.qty_on_hand AS INT64) as qty_on_hand,
                CAST(st.reserved_qty AS INT64) as reserved_qty,
                CAST(st.available_qty AS INT64) as available_qty,
                CAST(st.unit_cost AS NUMERIC) as unit_cost,
                CAST(st.total_cost AS NUMERIC) as total_cost,
                CASE 
                    WHEN COALESCE(st.available_qty, 0) = 0 THEN 'نفد المخزون'
                    WHEN COALESCE(st.available_qty, 0) < 10 THEN 'مخزون منخفض'
                    WHEN COALESCE(st.available_qty, 0) < 50 THEN 'مخزون متوسط'
                    ELSE 'مخزون جيد'
                END as stock_status,
                CASE 
                    WHEN COALESCE(st.available_qty, 0) = 0 THEN 'stock-low'
                    WHEN COALESCE(st.available_qty, 0) < 10 THEN 'stock-low'
                    WHEN COALESCE(st.available_qty, 0) < 50 THEN 'stock-medium'
                    ELSE 'stock-good'
                END as stock_status_class
            FROM SalesData s
            LEFT JOIN StockData st ON s.product_barcode = st.barcode
            ORDER BY s.total_sales DESC;
        """
        
        results = run_query(stock_query)
        
        products_data = []
        for row in results:
            products_data.append({
                "product_barcode": row.product_barcode or '',
                "product_name": row.product_name,
                "total_quantity": f"{int(row.total_quantity or 0):,}",
                "total_sales": f"{float(row.total_sales or 0):,.2f}",
                "total_profit": f"{float(row.total_profit or 0):,.2f}",
                "current_stock": f"{int(row.current_stock or 0):,}",
                "stock_status": row.stock_status,
                "stock_status_class": row.stock_status_class
            })
        
        return jsonify({"status": "success", "data": products_data})

    except Exception as e:
        print(f"❌ Error in /api/stock-products: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
