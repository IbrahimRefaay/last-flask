# routes/services_routes.py
# Services analysis routes

from flask import Blueprint, jsonify, render_template
from decimal import Decimal
from database import run_query, get_project_id, get_dataset_id, get_table_id
from utils import get_user_filters_string

services_bp = Blueprint('services', __name__)

@services_bp.route("/services")
def services_page():
    """صفحة تحليل الخدمات."""
    return render_template('services.html')

@services_bp.route("/api/services-branches")
def get_services_branches():
    """API endpoint to get available branches from services data."""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        branches_query = f"""
            SELECT DISTINCT branch
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            WHERE (product_category LIKE '%خدمات%' OR product_category LIKE '%pos%')
                AND product_name NOT LIKE '%عربون طلب بضاعة%'
                AND product_name NOT LIKE '%دفع مسبق منتجات البدائع%'
                AND product_name NOT LIKE '%عربون%'
                AND product_name NOT LIKE '%دفع مسبق%'
                AND branch IS NOT NULL
                AND branch != ''
            ORDER BY branch
        """
        
        result = run_query(branches_query)
        branches = [row.branch for row in result if row.branch]
        
        return jsonify({
            'status': 'success',
            'branches': branches
        })
        
    except Exception as e:
        print(f"❌ Error getting branches: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@services_bp.route("/api/services-data")
def services_data():
    """API endpoint to fetch services data excluding specific services."""
    try:
        # طباعة الفلاتر للتأكد من وصولها
        from flask import request
        print(f"🔍 Services Data - Request args: {dict(request.args)}")
        
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        print(f"🔍 Services Data Filter SQL: {where_sql}")
        
        # استعلام للحصول على بيانات الخدمات (باستثناء عربون طلب بضاعة ودفع مسبق منتجات البدائع)
        services_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
                {where_sql}
            ),
            ServicesData AS (
                SELECT 
                    product_name,
                    product_category,
                    branch,
                    SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END) as total_quantity,
                    SUM(CASE WHEN quantity > 0 THEN subtotal_incl ELSE 0 END) as total_amount,
                    COUNT(DISTINCT receipt_number) as receipt_count
                FROM FilteredData
                WHERE (product_category LIKE '%خدمات%' OR product_category LIKE '%pos%')
                    AND product_name NOT LIKE '%عربون طلب بضاعة%'
                    AND product_name NOT LIKE '%دفع مسبق منتجات البدائع%'
                    AND product_name NOT LIKE '%عربون%'
                    AND product_name NOT LIKE '%دفع مسبق%'
                    AND subtotal_incl IS NOT NULL
                    AND quantity > 0
                GROUP BY product_name, product_category, branch
            )
            SELECT 
                product_name,
                product_category,
                branch,
                total_quantity,
                CAST(total_amount AS NUMERIC) as total_amount,
                receipt_count
            FROM ServicesData
            ORDER BY total_amount DESC
        """
        
        services_result = run_query(services_query)
        
        # تحويل النتائج إلى قائمة
        services_list = []
        total_services_amount = Decimal('0')
        total_services_quantity = 0
        total_receipts = 0
        
        for row in services_result:
            service_data = {
                'product_name': row.product_name or 'غير محدد',
                'product_category': row.product_category or 'غير محدد',
                'branch': row.branch or 'غير محدد',
                'total_quantity': int(row.total_quantity) if row.total_quantity else 0,
                'total_amount': float(row.total_amount) if row.total_amount else 0.0,
                'receipt_count': int(row.receipt_count) if row.receipt_count else 0
            }
            
            services_list.append(service_data)
            total_services_amount += Decimal(str(service_data['total_amount']))
            total_services_quantity += service_data['total_quantity']
            total_receipts += service_data['receipt_count']
        
        return jsonify({
            'status': 'success',
            'services': services_list,
            'summary': {
                'total_amount': float(total_services_amount),
                'total_quantity': total_services_quantity,
                'total_receipts': total_receipts,
                'services_count': len(services_list)
            }
        })
        
    except Exception as e:
        print(f"❌ Error in services data: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@services_bp.route("/api/services-returns")
def services_returns():
    """API endpoint to fetch services returns data."""
    try:
        # طباعة الفلاتر للتأكد من وصولها
        from flask import request
        print(f"🔍 Services Returns - Request args: {dict(request.args)}")
        
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        print(f"🔍 Services Returns Filter SQL: {where_sql}")
        
        # استعلام للحصول على بيانات مرتجعات الخدمات
        returns_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
                {where_sql}
            ),
            ServicesReturns AS (
                SELECT 
                    product_name,
                    product_category,
                    branch,
                    SUM(CASE WHEN quantity < 0 THEN ABS(quantity) ELSE 0 END) as returned_quantity,
                    SUM(CASE WHEN quantity < 0 THEN ABS(subtotal_incl) ELSE 0 END) as returned_amount,
                    COUNT(DISTINCT CASE WHEN quantity < 0 THEN receipt_number END) as return_receipts
                FROM FilteredData
                WHERE (product_category LIKE '%خدمات%' OR product_category LIKE '%pos%')
                    AND product_name NOT LIKE '%عربون طلب بضاعة%'
                    AND product_name NOT LIKE '%دفع مسبق منتجات البدائع%'
                    AND product_name NOT LIKE '%عربون%'
                    AND product_name NOT LIKE '%دفع مسبق%'
                    AND subtotal_incl IS NOT NULL
                    AND quantity < 0
                GROUP BY product_name, product_category, branch
            )
            SELECT 
                product_name,
                product_category,
                branch,
                returned_quantity,
                CAST(returned_amount AS NUMERIC) as returned_amount,
                return_receipts
            FROM ServicesReturns
            WHERE returned_quantity > 0
            ORDER BY returned_amount DESC
        """
        
        returns_result = run_query(returns_query)
        
        # تحويل النتائج إلى قائمة
        returns_list = []
        total_returns_amount = Decimal('0')
        total_returns_quantity = 0
        total_return_receipts = 0
        
        for row in returns_result:
            return_data = {
                'product_name': row.product_name or 'غير محدد',
                'product_category': row.product_category or 'غير محدد',
                'branch': row.branch or 'غير محدد',
                'returned_quantity': int(row.returned_quantity) if row.returned_quantity else 0,
                'returned_amount': float(row.returned_amount) if row.returned_amount else 0.0,
                'return_receipts': int(row.return_receipts) if row.return_receipts else 0
            }
            
            returns_list.append(return_data)
            total_returns_amount += Decimal(str(return_data['returned_amount']))
            total_returns_quantity += return_data['returned_quantity']
            total_return_receipts += return_data['return_receipts']
        
        return jsonify({
            'status': 'success',
            'returns': returns_list,
            'summary': {
                'total_returned_amount': float(total_returns_amount),
                'total_returned_quantity': total_returns_quantity,
                'total_return_receipts': total_return_receipts,
                'returned_services_count': len(returns_list)
            }
        })
        
    except Exception as e:
        print(f"❌ Error in services returns: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
