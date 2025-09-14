# routes/inventory_dashboard_routes.py
# Comprehensive Inventory Management Dashboard Routes

from flask import Blueprint, jsonify, request, render_template
from decimal import Decimal
from datetime import datetime, timedelta
import subprocess
import os
import threading
from database import run_query, get_project_id, get_dataset_id

inventory_dashboard_bp = Blueprint('inventory_dashboard', __name__)

@inventory_dashboard_bp.route('/inventory-dashboard')
def inventory_dashboard():
    """Main inventory dashboard page."""
    return render_template('inventory_dashboard.html')

@inventory_dashboard_bp.route('/api/trigger-stock-update', methods=['POST'])
def trigger_stock_update():
    """Trigger stock update from GitHub repository."""
    try:
        # التحقق من وجود مفتاح أمان
        auth_header = request.headers.get('Authorization', '')
        expected_token = os.environ.get('STOCK_UPDATE_TOKEN', 'your-secret-token')
        
        # دعم لكل من Bearer token والتوكن المباشر
        provided_token = ''
        if auth_header.startswith('Bearer '):
            provided_token = auth_header.replace('Bearer ', '')
        else:
            provided_token = auth_header
        
        if provided_token != expected_token:
            return jsonify({
                "status": "error", 
                "message": "Unauthorized access"
            }), 401
        
        # الحصول على معلومات الطلب
        request_data = request.get_json() or {}
        source = request_data.get('source', 'manual')
        
        # تشغيل سكريبت تحديث المخزون في background
        def run_stock_update():
            try:
                # تشغيل سكريبت تحديث المخزون
                script_path = os.path.join(os.path.dirname(__file__), '..', 'data-push', 'inventory.py')
                result = subprocess.run([
                    'python', script_path
                ], capture_output=True, text=True, timeout=300)  # 5 دقائق timeout
                
                print(f"✅ Stock update completed. Return code: {result.returncode}")
                if result.stdout:
                    print(f"📊 Output: {result.stdout}")
                if result.stderr:
                    print(f"⚠️ Errors: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print("⏰ Stock update timed out after 5 minutes")
            except Exception as e:
                print(f"❌ Error running stock update: {e}")
        
        # تشغيل في thread منفصل حتى لا يتوقف الـ API
        update_thread = threading.Thread(target=run_stock_update)
        update_thread.start()
        
        return jsonify({
            "status": "success", 
            "message": "Stock update triggered successfully",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error triggering stock update: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/inventory-kpis')
def inventory_kpis():
    """Get inventory KPIs."""
    try:
        date_filter = request.args.get('date')
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # Base query for current stock data
        date_condition = ""
        if date_filter:
            # If specific date provided, try to get historical data
            date_condition = f"AND DATE(snapshot_date) = '{date_filter}'" if 'historical_inventory' in str(date_filter) else ""
        
        kpi_query = f"""
            SELECT 
                COUNT(DISTINCT Barcode) as total_products,
                SUM(Available_Qty) as total_quantity,
                SUM(Available_Qty * Unit_Cost) as total_value,
                COUNT(CASE WHEN Available_Qty < 10 THEN 1 END) as low_stock_count
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
            WHERE Barcode IS NOT NULL
            AND (Category IS NULL OR (Category LIKE '% / %' AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')))
            {date_condition}
        """
        
        result = list(run_query(kpi_query))
        
        if result:
            kpi_data = result[0]
            return jsonify({
                "status": "success",
                "data": {
                    "total_products": int(kpi_data.total_products or 0),
                    "total_quantity": int(kpi_data.total_quantity or 0),
                    "total_value": f"{float(kpi_data.total_value or 0):,.2f}",
                    "low_stock_count": int(kpi_data.low_stock_count or 0)
                }
            })
        else:
            return jsonify({
                "status": "success",
                "data": {
                    "total_products": 0,
                    "total_quantity": 0,
                    "total_value": "0.00",
                    "low_stock_count": 0
                }
            })
            
    except Exception as e:
        print(f"❌ Error in /api/inventory-kpis: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/inventory-by-category')
def inventory_by_category():
    """Get inventory distribution by category."""
    try:
        date_filter = request.args.get('date')
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        category_query = f"""
            WITH CategoryStats AS (
                SELECT 
                    TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(1)]) AS purchase_source,
                    COUNT(DISTINCT Barcode) as products_count,
                    SUM(Available_Qty) as total_quantity,
                    SUM(Available_Qty * Unit_Cost) as total_value
                FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
                WHERE Barcode IS NOT NULL
                AND Category IS NOT NULL
                AND Category LIKE '% / %'
                AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')
                GROUP BY TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(1)])
            ),
            TotalValue AS (
                SELECT SUM(total_value) as grand_total
                FROM CategoryStats
            )
            SELECT 
                cs.purchase_source as category,
                cs.products_count,
                cs.total_quantity,
                cs.total_value,
                ROUND((cs.total_value / tv.grand_total) * 100, 2) as percentage
            FROM CategoryStats cs
            CROSS JOIN TotalValue tv
            WHERE cs.purchase_source IS NOT NULL AND cs.purchase_source != ''
            ORDER BY cs.total_value DESC
            LIMIT 10
        """
        
        results = run_query(category_query)
        
        category_data = []
        for row in results:
            category_data.append({
                "category": row.category or 'غير محدد',
                "products_count": int(row.products_count or 0),
                "total_quantity": int(row.total_quantity or 0),
                "total_value": float(row.total_value or 0),
                "percentage": float(row.percentage or 0)
            })
            
        return jsonify({"status": "success", "data": category_data})
        
    except Exception as e:
        print(f"❌ Error in /api/inventory-by-category: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/inventory-by-main-category')
def inventory_by_main_category():
    """Get inventory distribution by main category (first part of split)."""
    try:
        date_filter = request.args.get('date')
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        main_category_query = f"""
            WITH MainCategoryStats AS (
                SELECT 
                    TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(0)]) AS main_category,
                    COUNT(DISTINCT Barcode) as products_count,
                    SUM(Available_Qty) as total_quantity,
                    SUM(Available_Qty * Unit_Cost) as total_value
                FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
                WHERE Barcode IS NOT NULL
                AND Category IS NOT NULL
                AND Category LIKE '% / %'
                AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')
                GROUP BY TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(0)])
            ),
            TotalValue AS (
                SELECT SUM(total_value) as grand_total
                FROM MainCategoryStats
            )
            SELECT 
                cs.main_category as category,
                cs.products_count,
                cs.total_quantity,
                cs.total_value,
                ROUND((cs.total_value / tv.grand_total) * 100, 2) as percentage
            FROM MainCategoryStats cs
            CROSS JOIN TotalValue tv
            WHERE cs.main_category IS NOT NULL AND cs.main_category != ''
            ORDER BY cs.total_value DESC
            LIMIT 10
        """
        
        results = run_query(main_category_query)
        
        category_data = []
        for row in results:
            category_data.append({
                "category": row.category or 'غير محدد',
                "products_count": int(row.products_count or 0),
                "total_quantity": int(row.total_quantity or 0),
                "total_value": float(row.total_value or 0),
                "percentage": float(row.percentage or 0)
            })
            
        return jsonify({"status": "success", "data": category_data})
        
    except Exception as e:
        print(f"❌ Error in /api/inventory-by-main-category: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/top-value-products')
def top_value_products():
    """Get top products by inventory value."""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        top_value_query = f"""
            SELECT 
                Product_Name as product_name,
                Barcode,
                Available_Qty as quantity,
                (Available_Qty * Unit_Cost) as value,
                CASE 
                    WHEN Available_Qty = 0 THEN 'نفد المخزون'
                    WHEN Available_Qty < 10 THEN 'مخزون منخفض'
                    WHEN Available_Qty < 50 THEN 'مخزون متوسط'
                    ELSE 'مخزون جيد'
                END as stock_status,
                CASE 
                    WHEN Available_Qty = 0 THEN 'stock-low'
                    WHEN Available_Qty < 10 THEN 'stock-low'
                    WHEN Available_Qty < 50 THEN 'stock-medium'
                    ELSE 'stock-good'
                END as stock_status_class
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
            WHERE Available_Qty > 0
            AND Unit_Cost > 0
            AND (Category IS NULL OR (Category LIKE '% / %' AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')))
            ORDER BY (Available_Qty * Unit_Cost) DESC
            LIMIT 50
        """
        
        results = run_query(top_value_query)
        
        products_data = []
        for row in results:
            products_data.append({
                "product_name": row.product_name,
                "barcode": row.Barcode,
                "quantity": int(row.quantity or 0),
                "value": float(row.value or 0),
                "stock_status": row.stock_status,
                "stock_status_class": row.stock_status_class
            })
            
        return jsonify({"status": "success", "data": products_data})
        
    except Exception as e:
        print(f"❌ Error in /api/top-value-products: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/stock-alerts')
def stock_alerts():
    """Get stock alerts - alias for low-stock-alerts."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # Query للحصول على العدد الكلي
        count_query = f"""
            SELECT COUNT(*) as total_count
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
            WHERE Available_Qty < 10
            AND Barcode IS NOT NULL
            AND (Category IS NULL OR (Category LIKE '% / %' AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')))
        """
        
        count_result = list(run_query(count_query))
        total_count = count_result[0].total_count if count_result else 0
        total_pages = (total_count + limit - 1) // limit
        
        alerts_query = f"""
            SELECT 
                Product_Name as product_name,
                Barcode as barcode,
                Available_Qty as qty_available,
                Unit_Cost,
                (Available_Qty * Unit_Cost) as value,
                Category as full_category,
                TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(0)]) as main_category
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
            WHERE Available_Qty < 10
            AND Barcode IS NOT NULL
            AND (Category IS NULL OR (Category LIKE '% / %' AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')))
            ORDER BY Available_Qty ASC, (Available_Qty * Unit_Cost) DESC
            LIMIT {limit} OFFSET {offset}
        """
        
        results = run_query(alerts_query)
        
        alerts_data = []
        for row in results:
            alerts_data.append({
                "product_name": row.product_name,
                "barcode": row.barcode,
                "qty_available": int(row.qty_available or 0),
                "unit_cost": float(row.Unit_Cost or 0),
                "value": float(row.value or 0),
                "category": row.full_category,
                "main_category": row.main_category
            })
            
        return jsonify({
            "status": "success", 
            "data": alerts_data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit
            }
        })
        
    except Exception as e:
        print(f"❌ Error in /api/stock-alerts: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/main-categories')
def main_categories():
    """Get main categories - alias for inventory-by-main-category."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # Query للحصول على العدد الكلي
        count_query = f"""
            SELECT COUNT(DISTINCT TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(0)])) as total_count
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
            WHERE Barcode IS NOT NULL
            AND Category IS NOT NULL
            AND Category LIKE '% / %'
            AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')
            AND TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(0)]) IS NOT NULL 
            AND TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(0)]) != ''
        """
        
        count_result = list(run_query(count_query))
        total_count = count_result[0].total_count if count_result else 0
        total_pages = (total_count + limit - 1) // limit
        
        main_category_query = f"""
            WITH MainCategoryStats AS (
                SELECT 
                    TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(0)]) AS main_category,
                    COUNT(DISTINCT Barcode) as product_count,
                    SUM(Available_Qty) as total_quantity,
                    SUM(Available_Qty * Unit_Cost) as total_value
                FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
                WHERE Barcode IS NOT NULL
                AND Category IS NOT NULL
                AND Category LIKE '% / %'
                AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')
                GROUP BY TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(0)])
            ),
            TotalValue AS (
                SELECT SUM(total_value) as grand_total
                FROM MainCategoryStats
            )
            SELECT 
                cs.main_category,
                cs.product_count,
                cs.total_quantity,
                cs.total_value,
                ROUND((cs.total_value / tv.grand_total) * 100, 2) as percentage
            FROM MainCategoryStats cs
            CROSS JOIN TotalValue tv
            WHERE cs.main_category IS NOT NULL AND cs.main_category != ''
            ORDER BY cs.total_value DESC
            LIMIT {limit} OFFSET {offset}
        """
        
        results = run_query(main_category_query)
        
        category_data = []
        for row in results:
            category_data.append({
                "main_category": row.main_category or 'غير محدد',
                "product_count": int(row.product_count or 0),
                "total_quantity": int(row.total_quantity or 0),
                "total_value": f"{float(row.total_value or 0):,.2f}",
                "percentage": float(row.percentage or 0)
            })
            
        return jsonify({
            "status": "success", 
            "data": category_data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit
            }
        })
        
    except Exception as e:
        print(f"❌ Error in /api/main-categories: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/purchase-sources')
def purchase_sources():
    """Get purchase sources - alias for inventory-by-category."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # Query للحصول على العدد الكلي
        count_query = f"""
            SELECT COUNT(DISTINCT TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(1)])) as total_count
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
            WHERE Barcode IS NOT NULL
            AND Category IS NOT NULL
            AND Category LIKE '% / %'
            AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')
            AND TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(1)]) IS NOT NULL 
            AND TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(1)]) != ''
        """
        
        count_result = list(run_query(count_query))
        total_count = count_result[0].total_count if count_result else 0
        total_pages = (total_count + limit - 1) // limit
        
        category_query = f"""
            WITH CategoryStats AS (
                SELECT 
                    TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(1)]) AS purchase_source,
                    COUNT(DISTINCT Barcode) as product_count,
                    SUM(Available_Qty) as total_quantity,
                    SUM(Available_Qty * Unit_Cost) as total_value,
                    AVG(Unit_Cost) as avg_price
                FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
                WHERE Barcode IS NOT NULL
                AND Category IS NOT NULL
                AND Category LIKE '% / %'
                AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')
                GROUP BY TRIM(SPLIT(Category, ' / ')[SAFE_OFFSET(1)])
            ),
            TotalValue AS (
                SELECT SUM(total_value) as grand_total
                FROM CategoryStats
            )
            SELECT 
                cs.purchase_source,
                cs.product_count,
                cs.total_quantity,
                cs.total_value,
                cs.avg_price,
                ROUND((cs.total_value / tv.grand_total) * 100, 2) as percentage
            FROM CategoryStats cs
            CROSS JOIN TotalValue tv
            WHERE cs.purchase_source IS NOT NULL AND cs.purchase_source != ''
            ORDER BY cs.total_value DESC
            LIMIT {limit} OFFSET {offset}
        """
        
        results = run_query(category_query)
        
        category_data = []
        for row in results:
            category_data.append({
                "purchase_source": row.purchase_source or 'غير محدد',
                "product_count": int(row.product_count or 0),
                "total_quantity": int(row.total_quantity or 0),
                "total_value": f"{float(row.total_value or 0):,.2f}",
                "avg_price": f"{float(row.avg_price or 0):,.2f}",
                "percentage": float(row.percentage or 0)
            })
            
        return jsonify({
            "status": "success", 
            "data": category_data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit
            }
        })
        
    except Exception as e:
        print(f"❌ Error in /api/purchase-sources: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/low-stock-alerts')
def low_stock_alerts():
    """Get low stock alerts."""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        alerts_query = f"""
            SELECT 
                Product_Name as product_name,
                Barcode as barcode,
                Available_Qty as quantity,
                Unit_Cost,
                (Available_Qty * Unit_Cost) as value
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
            WHERE Available_Qty < 10
            AND Barcode IS NOT NULL
            AND (Category IS NULL OR (Category LIKE '% / %' AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')))
            ORDER BY Available_Qty ASC, (Available_Qty * Unit_Cost) DESC
            LIMIT 50
        """
        
        results = run_query(alerts_query)
        
        alerts_data = []
        for row in results:
            alerts_data.append({
                "product_name": row.product_name,
                "barcode": row.barcode,
                "quantity": int(row.quantity or 0),
                "unit_cost": float(row.Unit_Cost or 0),
                "value": float(row.value or 0)
            })
            
        return jsonify({"status": "success", "data": alerts_data})
        
    except Exception as e:
        print(f"❌ Error in /api/low-stock-alerts: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/stagnant-stock')
def stagnant_stock():
    """Get stagnant stock (products with no recent sales)."""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # Get products that haven't sold in the last 30 days
        stagnant_query = f"""
            WITH RecentSales AS (
                SELECT DISTINCT product_barcode
                FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
                WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                AND product_barcode IS NOT NULL
                AND product_category LIKE '% / %'
                AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')
            ),
            LastSales AS (
                SELECT 
                    product_barcode,
                    MAX(DATE(order_date)) as last_sale_date
                FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
                WHERE product_barcode IS NOT NULL
                AND product_category LIKE '% / %'
                AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')
                GROUP BY product_barcode
            )
            SELECT 
                s.Product_Name as product_name,
                s.Barcode as barcode,
                s.Available_Qty as quantity,
                ls.last_sale_date,
                CASE 
                    WHEN ls.last_sale_date IS NULL THEN 999
                    ELSE DATE_DIFF(CURRENT_DATE(), ls.last_sale_date, DAY)
                END as days_stagnant
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data` s
            LEFT JOIN RecentSales rs ON s.Barcode = rs.product_barcode
            LEFT JOIN LastSales ls ON s.Barcode = ls.product_barcode
            WHERE rs.product_barcode IS NULL
            AND s.Available_Qty > 0
            AND (s.Category IS NULL OR (s.Category LIKE '% / %' 
                AND NOT (s.Category LIKE '%خدمات%' OR s.Category LIKE '%خدمات وخصومات%')
                AND NOT (s.Category LIKE '%منوع%')
                AND NOT (s.Category LIKE '%ادوات تغليف%')
                AND NOT (s.Category LIKE '%ورد%')
                AND NOT (s.Category LIKE '%بوكيه ورد%')
                AND NOT (s.Category LIKE '%اشجار زينة%')))
            ORDER BY days_stagnant DESC, s.Available_Qty DESC
            LIMIT 50
        """
        
        results = run_query(stagnant_query)
        
        stagnant_data = []
        for row in results:
            stagnant_data.append({
                "product_name": row.product_name,
                "barcode": row.barcode,
                "quantity": int(row.quantity or 0),
                "last_sale_date": str(row.last_sale_date) if row.last_sale_date else None,
                "days_stagnant": int(row.days_stagnant or 0)
            })
            
        return jsonify({"status": "success", "data": stagnant_data})
        
    except Exception as e:
        print(f"❌ Error in /api/stagnant-stock: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/bestselling-with-stock')
def bestselling_with_stock():
    """Get best selling products with current stock levels."""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        bestselling_query = f"""
            WITH SalesData AS (
                SELECT 
                    product_barcode,
                    product_name,
                    SUM(quantity) as total_quantity,
                    SUM(subtotal_incl) as total_sales
                FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
                WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                AND product_barcode IS NOT NULL
                AND quantity > 0
                AND product_category LIKE '% / %'
                AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')
                GROUP BY product_barcode, product_name
                ORDER BY total_sales DESC
                LIMIT 50
            )
            SELECT 
                sd.product_name,
                sd.product_barcode,
                sd.total_quantity,
                sd.total_sales,
                COALESCE(st.Available_Qty, 0) as current_stock,
                CASE 
                    WHEN COALESCE(st.Available_Qty, 0) = 0 THEN 'نفد المخزون'
                    WHEN COALESCE(st.Available_Qty, 0) < 10 THEN 'مخزون منخفض'
                    WHEN COALESCE(st.Available_Qty, 0) < 50 THEN 'مخزون متوسط'
                    ELSE 'مخزون جيد'
                END as stock_status,
                CASE 
                    WHEN COALESCE(st.Available_Qty, 0) = 0 THEN 'stock-low'
                    WHEN COALESCE(st.Available_Qty, 0) < 10 THEN 'stock-low'
                    WHEN COALESCE(st.Available_Qty, 0) < 50 THEN 'stock-medium'
                    ELSE 'stock-good'
                END as stock_status_class
            FROM SalesData sd
            LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.stock_data` st ON sd.product_barcode = st.Barcode
            WHERE (st.Category IS NULL OR (st.Category LIKE '% / %' AND NOT (st.Category LIKE '%خدمات%' OR st.Category LIKE '%خدمات وخصومات%')))
            ORDER BY sd.total_sales DESC
        """
        
        results = run_query(bestselling_query)
        
        products_data = []
        for row in results:
            products_data.append({
                "product_name": row.product_name,
                "product_barcode": row.product_barcode,
                "total_sales": f"{float(row.total_sales or 0):,.2f}",
                "current_stock": f"{int(row.current_stock or 0):,}",
                "stock_status": row.stock_status,
                "stock_status_class": row.stock_status_class
            })
            
        return jsonify({"status": "success", "data": products_data})
        
    except Exception as e:
        print(f"❌ Error in /api/bestselling-with-stock: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/profitable-with-stock-simple')
def profitable_with_stock_simple():
    """Get most profitable products with current stock levels - simplified version."""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # Simplified query focusing on revenue only
        simple_query = f"""
            SELECT 
                product_name,
                product_barcode,
                SUM(subtotal_incl) as total_revenue,
                SUM(quantity) as total_quantity_sold,
                COUNT(*) as transaction_count
            FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
            WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            AND product_barcode IS NOT NULL
            AND quantity > 0
            AND subtotal_incl > 0
            AND product_category LIKE '% / %'
            AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')
            GROUP BY product_barcode, product_name
            HAVING total_revenue > 100
            ORDER BY total_revenue DESC
            LIMIT 50
        """
        
        results = run_query(simple_query)
        
        products_data = []
        for row in results:
            products_data.append({
                "product_name": row.product_name,
                "product_barcode": row.product_barcode,
                "total_revenue": f"{float(row.total_revenue or 0):,.2f}",
                "total_quantity_sold": f"{int(row.total_quantity_sold or 0):,}",
                "transaction_count": int(row.transaction_count or 0)
            })
            
        return jsonify({
            "status": "success", 
            "data": products_data,
            "count": len(products_data)
        })
        
    except Exception as e:
        print(f"❌ Error in /api/profitable-with-stock-simple: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/search-product')
def search_product():
    """Search for product by barcode in stock_data table."""
    try:
        barcode = request.args.get('barcode', '').strip()
        if not barcode:
            return jsonify({"status": "error", "message": "Barcode parameter is required"}), 400
            
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # Search for exact barcode match first
        search_query = f"""
            SELECT 
                Product_Name as product_name,
                Barcode as barcode,
                Category as category,
                Qty_On_Hand as qty_on_hand,
                Reserved_Qty as reserved_qty,
                Available_Qty as available_qty,
                Unit_Cost as unit_cost,
                (Available_Qty * Unit_Cost) as total_value,
                CURRENT_TIMESTAMP() as last_updated,
                CASE 
                    WHEN Available_Qty = 0 THEN 'نفد المخزون'
                    WHEN Available_Qty < 10 THEN 'مخزون منخفض'
                    WHEN Available_Qty < 50 THEN 'مخزون متوسط'
                    ELSE 'مخزون جيد'
                END as stock_status,
                CASE 
                    WHEN Available_Qty = 0 THEN 'stock-out'
                    WHEN Available_Qty < 10 THEN 'stock-low'
                    WHEN Available_Qty < 50 THEN 'stock-medium'
                    ELSE 'stock-good'
                END as stock_status_class
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
            WHERE Barcode = '{barcode}'
            LIMIT 1
        """
        
        results = list(run_query(search_query))
        
        if results:
            product = results[0]
            product_data = {
                "product_name": product.product_name,
                "barcode": product.barcode,
                "category": product.category or 'غير محدد',
                "qty_on_hand": int(product.qty_on_hand or 0),
                "reserved_qty": int(product.reserved_qty or 0),
                "available_qty": int(product.available_qty or 0),
                "unit_cost": float(product.unit_cost or 0),
                "total_value": float(product.total_value or 0),
                "last_updated": str(product.last_updated) if product.last_updated else 'غير محدد',
                "stock_status": product.stock_status,
                "stock_status_class": product.stock_status_class
            }
            return jsonify({"status": "success", "data": product_data})
        else:
            # If exact match not found, try partial search
            partial_search_query = f"""
                SELECT 
                    Product_Name as product_name,
                    Barcode as barcode,
                    Category as category,
                    Qty_On_Hand as qty_on_hand,
                    Reserved_Qty as reserved_qty,
                    Available_Qty as available_qty,
                    Unit_Cost as unit_cost,
                    (Available_Qty * Unit_Cost) as total_value,
                    CURRENT_TIMESTAMP() as last_updated,
                    CASE 
                        WHEN Available_Qty = 0 THEN 'نفد المخزون'
                        WHEN Available_Qty < 10 THEN 'مخزون منخفض'
                        WHEN Available_Qty < 50 THEN 'مخزون متوسط'
                        ELSE 'مخزون جيد'
                    END as stock_status,
                    CASE 
                        WHEN Available_Qty = 0 THEN 'stock-out'
                        WHEN Available_Qty < 10 THEN 'stock-low'
                        WHEN Available_Qty < 50 THEN 'stock-medium'
                        ELSE 'stock-good'
                    END as stock_status_class
                FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
                WHERE Barcode LIKE '%{barcode}%' 
                OR Product_Name LIKE '%{barcode}%'
                LIMIT 10
            """
            
            partial_results = list(run_query(partial_search_query))
            
            if partial_results:
                products_data = []
                for product in partial_results:
                    products_data.append({
                        "product_name": product.product_name,
                        "barcode": product.barcode,
                        "category": product.category or 'غير محدد',
                        "qty_on_hand": int(product.qty_on_hand or 0),
                        "reserved_qty": int(product.reserved_qty or 0),
                        "available_qty": int(product.available_qty or 0),
                        "unit_cost": float(product.unit_cost or 0),
                        "total_value": float(product.total_value or 0),
                        "last_updated": str(product.last_updated) if product.last_updated else 'غير محدد',
                        "stock_status": product.stock_status,
                        "stock_status_class": product.stock_status_class
                    })
                return jsonify({"status": "success", "data": products_data, "multiple": True})
            else:
                return jsonify({"status": "error", "message": "لم يتم العثور على منتج بهذا الباركود"}), 404
        
    except Exception as e:
        print(f"❌ Error in /api/search-product: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@inventory_dashboard_bp.route('/api/historical-stock')
def historical_stock():
    """Get historical stock data for a specific date."""
    try:
        date_filter = request.args.get('date')
        if not date_filter:
            return jsonify({"status": "error", "message": "Date parameter is required"}), 400
            
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # Try to get historical data first
        historical_query = f"""
            SELECT 
                product_name,
                product_barcode as barcode,
                Category as category,
                on_hand_quantity as qty_on_hand,
                reserved_quantity as reserved_qty,
                available_quantity as available_qty
            FROM `{PROJECT_ID}.{DATASET_ID}.historical_inventory`
            WHERE DATE(snapshot_date) = '{date_filter}'
            AND (Category IS NULL OR (Category LIKE '% / %' AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')))
            ORDER BY product_name
            LIMIT 100
        """
        
        try:
            results = run_query(historical_query)
            historical_data = []
            for row in results:
                historical_data.append({
                    "product_name": row.product_name,
                    "barcode": row.barcode,
                    "category": row.category,
                    "qty_on_hand": int(row.qty_on_hand or 0),
                    "reserved_qty": int(row.reserved_qty or 0),
                    "available_qty": int(row.available_qty or 0)
                })
                
            if historical_data:
                return jsonify({"status": "success", "data": historical_data})
        except Exception as e:
            print(f"Historical query failed: {e}")
        
        # Fallback to current stock data if historical not available
        current_query = f"""
            SELECT 
                Product_Name as product_name,
                Barcode as barcode,
                Category as category,
                Qty_On_Hand as qty_on_hand,
                Reserved_Qty as reserved_qty,
                Available_Qty as available_qty
            FROM `{PROJECT_ID}.{DATASET_ID}.stock_data`
            WHERE Barcode IS NOT NULL
            AND (Category IS NULL OR (Category LIKE '% / %' AND NOT (Category LIKE '%خدمات%' OR Category LIKE '%خدمات وخصومات%')))
            ORDER BY Product_Name
            LIMIT 100
        """
        
        results = run_query(current_query)
        stock_data = []
        for row in results:
            stock_data.append({
                "product_name": row.product_name,
                "barcode": row.barcode,
                "category": row.category or 'غير محدد',
                "qty_on_hand": int(row.qty_on_hand or 0),
                "reserved_qty": int(row.reserved_qty or 0),
                "available_qty": int(row.available_qty or 0)
            })
            
        return jsonify({"status": "success", "data": stock_data, "note": "عرض البيانات الحالية - لا توجد بيانات تاريخية للتاريخ المحدد"})
        
    except Exception as e:
        print(f"❌ Error in /api/historical-stock: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
