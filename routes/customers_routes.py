from flask import Blueprint, render_template, jsonify, request
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import run_query, get_project_id, get_dataset_id
import logging

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/customers-analytics')
def customers_analytics():
    """صفحة تحليل العملاء الشاملة"""
    return render_template('customers_analytics.html')

@customers_bp.route('/api/branches')
def get_branches():
    """جلب قائمة الفروع المتاحة"""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        branches_query = f"""
            SELECT 
                CASE 
                    WHEN delivery_address IS NULL OR delivery_address = '' THEN 'غير محدد'
                    WHEN LOWER(delivery_address) LIKE '%الرياض%' THEN 'الرياض'
                    WHEN LOWER(delivery_address) LIKE '%جدة%' THEN 'جدة'
                    WHEN LOWER(delivery_address) LIKE '%الدمام%' THEN 'الدمام'
                    WHEN LOWER(delivery_address) LIKE '%مكة%' THEN 'مكة المكرمة'
                    WHEN LOWER(delivery_address) LIKE '%المدينة%' THEN 'المدينة المنورة'
                    WHEN LOWER(delivery_address) LIKE '%الطائف%' THEN 'الطائف'
                    WHEN LOWER(delivery_address) LIKE '%الخبر%' THEN 'الخبر'
                    WHEN LOWER(delivery_address) LIKE '%القطيف%' THEN 'القطيف'
                    WHEN LOWER(delivery_address) LIKE '%الأحساء%' THEN 'الأحساء'
                    WHEN LOWER(delivery_address) LIKE '%أبها%' THEN 'أبها'
                    WHEN LOWER(delivery_address) LIKE '%تبوك%' THEN 'تبوك'
                    WHEN LOWER(delivery_address) LIKE '%جازان%' THEN 'جازان'
                    WHEN LOWER(delivery_address) LIKE '%نجران%' THEN 'نجران'
                    WHEN LOWER(delivery_address) LIKE '%حائل%' THEN 'حائل'
                    WHEN LOWER(delivery_address) LIKE '%القصيم%' THEN 'القصيم'
                    ELSE 'أخرى'
                END as branch_name,
                COUNT(*) as order_count
            FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
            WHERE phone_number NOT IN ('0555555555', '0500000000', 'رفض العميل', '0000000000', '1111111111')
            AND subtotal_incl > 0
            GROUP BY branch_name
            HAVING order_count > 5
            ORDER BY order_count DESC
        """
        
        results = run_query(branches_query)
        
        branches_data = []
        for row in results:
            branches_data.append({
                "name": row.branch_name or 'غير محدد',
                "order_count": int(row.order_count or 0)
            })
            
        return jsonify({"status": "success", "data": branches_data})
        
    except Exception as e:
        print(f"❌ Error in get branches: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@customers_bp.route('/api/customers-overview')
def customers_overview():
    """إحصائيات عامة عن العملاء"""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # استقبال الفلاتر
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        branch = request.args.get('branch')
        
        # بناء شروط WHERE
        where_conditions = [
            "customer_name IS NOT NULL",
            "customer_name != ''",
            "subtotal_incl > 0",
            "phone_number NOT IN ('0555555555', '0500000000', 'رفض العميل', '0000000000', '1111111111')"
        ]
        
        if start_date:
            where_conditions.append(f"order_date >= '{start_date}'")
        if end_date:
            where_conditions.append(f"order_date <= '{end_date}'")
        if branch:
            where_conditions.append(f"delivery_address LIKE '%{branch}%'")
        
        where_clause = " AND ".join(where_conditions)
        
        overview_query = f"""
            SELECT 
                COUNT(DISTINCT customer_name) as total_customers,
                COUNT(*) as total_orders,
                SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as total_revenue,
                AVG(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as avg_order_value,
                MIN(order_date) as first_order_date,
                MAX(order_date) as last_order_date
            FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
            WHERE {where_clause}
        """
        
        results = list(run_query(overview_query))
        
        if results:
            row = results[0]
            total_customers = int(row.total_customers or 0)
            total_orders = int(row.total_orders or 0)
            total_revenue = float(row.total_revenue or 0)
            
            data = {
                "total_customers": total_customers,
                "total_orders": total_orders,
                "total_revenue": f"{total_revenue:,.2f}",
                "avg_order_value": f"{float(row.avg_order_value or 0):,.2f}",
                "avg_customer_value": f"{total_revenue / max(total_customers, 1):,.2f}",
                "avg_orders_per_customer": f"{total_orders / max(total_customers, 1):,.1f}",
                "first_order_date": str(row.first_order_date) if row.first_order_date else 'غير محدد',
                "last_order_date": str(row.last_order_date) if row.last_order_date else 'غير محدد'
            }
        else:
            data = {
                "total_customers": 0,
                "total_orders": 0,
                "total_revenue": "0.00",
                "avg_order_value": "0.00",
                "avg_customer_value": "0.00",
                "avg_orders_per_customer": "0.0",
                "first_order_date": 'غير محدد',
                "last_order_date": 'غير محدد'
            }
            
        return jsonify({"status": "success", "data": data})
        
    except Exception as e:
        print(f"❌ Error in customers overview: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@customers_bp.route('/api/top-customers-by-revenue')
def top_customers_by_revenue():
    """أكبر العملاء من ناحية الإيرادات"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit
        
        # استقبال الفلاتر
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        branch = request.args.get('branch')
        
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # بناء شروط WHERE
        where_conditions = [
            "phone_number IS NOT NULL",
            "phone_number != ''",
            "subtotal_incl > 0",
            "phone_number NOT IN ('0555555555', '0500000000', 'رفض العميل', '0000000000', '1111111111')"
        ]
        
        if start_date:
            where_conditions.append(f"order_date >= '{start_date}'")
        if end_date:
            where_conditions.append(f"order_date <= '{end_date}'")
        if branch:
            where_conditions.append(f"delivery_address LIKE '%{branch}%'")
        
        where_clause = " AND ".join(where_conditions)
        
        # العدد الكلي
        count_query = f"""
            SELECT COUNT(DISTINCT phone_number) as total_count
            FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
            WHERE {where_clause}
        """
        
        count_result = list(run_query(count_query))
        total_count = count_result[0].total_count if count_result else 0
        total_pages = (total_count + limit - 1) // limit
        
        revenue_query = f"""
            WITH CustomerRevenue AS (
                SELECT 
                    phone_number,
                    customer_name,
                    COALESCE(delivery_address, 'غير محدد') as delivery_address,
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as total_revenue,
                    AVG(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as avg_order_value,
                    MIN(order_date) as first_order,
                    MAX(order_date) as last_order,
                    COUNT(DISTINCT DATE(order_date)) as active_days
                FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
                WHERE {where_clause}
                GROUP BY phone_number, customer_name, delivery_address
            ),
            TotalRevenue AS (
                SELECT SUM(total_revenue) as grand_total
                FROM CustomerRevenue
            )
            SELECT 
                cr.phone_number,
                cr.customer_name,
                cr.delivery_address,
                cr.total_orders,
                cr.total_revenue,
                cr.avg_order_value,
                cr.first_order,
                cr.last_order,
                cr.active_days,
                ROUND((cr.total_revenue / tr.grand_total) * 100, 2) as revenue_percentage
            FROM CustomerRevenue cr
            CROSS JOIN TotalRevenue tr
            ORDER BY cr.total_revenue DESC
            LIMIT {limit} OFFSET {offset}
        """
        
        results = run_query(revenue_query)
        
        customers_data = []
        for row in results:
            customers_data.append({
                "phone_number": row.phone_number or 'غير محدد',
                "customer_name": row.customer_name or 'غير محدد',
                "delivery_address": row.delivery_address or 'غير محدد',
                "total_orders": int(row.total_orders or 0),
                "total_revenue": f"{float(row.total_revenue or 0):,.2f}",
                "avg_order_value": f"{float(row.avg_order_value or 0):,.2f}",
                "first_order": str(row.first_order) if row.first_order else 'غير محدد',
                "last_order": str(row.last_order) if row.last_order else 'غير محدد',
                "active_days": int(row.active_days or 0),
                "revenue_percentage": float(row.revenue_percentage or 0)
            })
            
        return jsonify({
            "status": "success", 
            "data": customers_data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": limit
            }
        })
        
    except Exception as e:
        print(f"❌ Error in top customers by revenue: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@customers_bp.route('/api/top-customers-by-frequency')
def top_customers_by_frequency():
    """أكثر العملاء تكراراً في الطلبات"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit
        
        # استقبال الفلاتر
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        branch = request.args.get('branch')
        
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # بناء شروط WHERE
        where_conditions = [
            "phone_number IS NOT NULL",
            "phone_number != ''",
            "subtotal_incl > 0",
            "phone_number NOT IN ('0555555555', '0500000000', 'رفض العميل', '0000000000', '1111111111')"
        ]
        
        if start_date:
            where_conditions.append(f"order_date >= '{start_date}'")
        if end_date:
            where_conditions.append(f"order_date <= '{end_date}'")
        if branch:
            where_conditions.append(f"delivery_address LIKE '%{branch}%'")
        
        where_clause = " AND ".join(where_conditions)
        
        frequency_query = f"""
            WITH CustomerFrequency AS (
                SELECT 
                    phone_number,
                    customer_name,
                    COUNT(*) as order_frequency,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as total_spent,
                    AVG(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as avg_order_value,
                    COUNT(DISTINCT DATE(order_date)) as unique_shopping_days,
                    MIN(order_date) as first_order,
                    MAX(order_date) as last_order,
                    DATE_DIFF(MAX(order_date), MIN(order_date), DAY) as customer_lifetime_days
                FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
                WHERE {where_clause}
                GROUP BY phone_number, customer_name
            )
            SELECT 
                phone_number,
                customer_name,
                order_frequency,
                total_spent,
                avg_order_value,
                unique_shopping_days,
                first_order,
                last_order,
                customer_lifetime_days,
                CASE 
                    WHEN customer_lifetime_days > 0 THEN ROUND(order_frequency / customer_lifetime_days * 30, 2)
                    ELSE 0 
                END as monthly_order_rate
            FROM CustomerFrequency
            ORDER BY order_frequency DESC
            LIMIT {limit} OFFSET {offset}
        """
        
        results = run_query(frequency_query)
        
        customers_data = []
        for row in results:
            customers_data.append({
                "phone_number": row.phone_number or 'غير محدد',
                "customer_name": row.customer_name or 'غير محدد',
                "order_frequency": int(row.order_frequency or 0),
                "total_spent": f"{float(row.total_spent or 0):,.2f}",
                "avg_order_value": f"{float(row.avg_order_value or 0):,.2f}",
                "unique_shopping_days": int(row.unique_shopping_days or 0),
                "first_order": str(row.first_order) if row.first_order else 'غير محدد',
                "last_order": str(row.last_order) if row.last_order else 'غير محدد',
                "customer_lifetime_days": int(row.customer_lifetime_days or 0),
                "monthly_order_rate": float(row.monthly_order_rate or 0)
            })
            
        return jsonify({"status": "success", "data": customers_data})
        
    except Exception as e:
        print(f"❌ Error in top customers by frequency: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@customers_bp.route('/api/customers-by-city')
def customers_by_city():
    """توزيع العملاء حسب المدن (إذا كان هناك عمود للمدينة)"""
    try:
        # استقبال الفلاتر
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        branch = request.args.get('branch')
        
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # بناء شروط WHERE
        where_conditions = [
            "customer_name IS NOT NULL",
            "customer_name != ''",
            "subtotal_incl > 0",
            "phone_number NOT IN ('0555555555', '0500000000', 'رفض العميل', '0000000000', '1111111111')"
        ]
        
        if start_date:
            where_conditions.append(f"order_date >= '{start_date}'")
        if end_date:
            where_conditions.append(f"order_date <= '{end_date}'")
        if branch:
            where_conditions.append(f"delivery_address LIKE '%{branch}%'")
        
        where_clause = " AND ".join(where_conditions)
        
        # نحاول أولاً معرفة إذا كان هناك عمود للمدينة أو العنوان
        city_query = f"""
            WITH CustomerCities AS (
                SELECT 
                    CASE 
                        WHEN delivery_address IS NULL OR delivery_address = '' THEN 'غير محدد'
                        WHEN LOWER(delivery_address) LIKE '%الرياض%' THEN 'الرياض'
                        WHEN LOWER(delivery_address) LIKE '%جدة%' THEN 'جدة'
                        WHEN LOWER(delivery_address) LIKE '%الدمام%' THEN 'الدمام'
                        WHEN LOWER(delivery_address) LIKE '%مكة%' THEN 'مكة المكرمة'
                        WHEN LOWER(delivery_address) LIKE '%المدينة%' THEN 'المدينة المنورة'
                        WHEN LOWER(delivery_address) LIKE '%الطائف%' THEN 'الطائف'
                        WHEN LOWER(delivery_address) LIKE '%الخبر%' THEN 'الخبر'
                        WHEN LOWER(delivery_address) LIKE '%القطيف%' THEN 'القطيف'
                        WHEN LOWER(delivery_address) LIKE '%الأحساء%' OR LOWER(delivery_address) LIKE '%احساء%' THEN 'الأحساء'
                        WHEN LOWER(delivery_address) LIKE '%أبها%' THEN 'أبها'
                        WHEN LOWER(delivery_address) LIKE '%تبوك%' THEN 'تبوك'
                        WHEN LOWER(delivery_address) LIKE '%جازان%' THEN 'جازان'
                        WHEN LOWER(delivery_address) LIKE '%نجران%' THEN 'نجران'
                        WHEN LOWER(delivery_address) LIKE '%حائل%' THEN 'حائل'
                        WHEN LOWER(delivery_address) LIKE '%القصيم%' OR LOWER(delivery_address) LIKE '%بريدة%' THEN 'القصيم'
                        ELSE SUBSTR(delivery_address, 1, 50)  -- First 50 characters for other addresses
                    END as city,
                    customer_name,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as total_revenue,
                    COUNT(*) as total_orders
                FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
                WHERE {where_clause}
                GROUP BY city, customer_name
            )
            SELECT 
                city,
                COUNT(DISTINCT customer_name) as customer_count,
                SUM(total_revenue) as city_revenue,
                SUM(total_orders) as city_orders,
                AVG(total_revenue) as avg_customer_value
            FROM CustomerCities
            GROUP BY city
            ORDER BY city_revenue DESC
            LIMIT 15
        """
        
        try:
            results = run_query(city_query)
            
            cities_data = []
            for row in results:
                cities_data.append({
                    "city": row.city or 'غير محدد',
                    "customer_count": int(row.customer_count or 0),
                    "city_revenue": f"{float(row.city_revenue or 0):,.2f}",
                    "city_orders": int(row.city_orders or 0),
                    "avg_customer_value": f"{float(row.avg_customer_value or 0):,.2f}"
                })
                
            return jsonify({"status": "success", "data": cities_data})
            
        except Exception as inner_e:
            # إذا فشل الاستعلام، نرجع بيانات افتراضية
            print(f"City query failed: {inner_e}")
            return jsonify({
                "status": "success", 
                "data": [{"city": "الرياض", "customer_count": 0, "city_revenue": "0.00", "city_orders": 0, "avg_customer_value": "0.00"}],
                "note": "بيانات المدن غير متوفرة"
            })
        
    except Exception as e:
        print(f"❌ Error in customers by city: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@customers_bp.route('/api/monthly-customer-trends')
def monthly_customer_trends():
    """اتجاهات العملاء الشهرية"""
    try:
        # استقبال الفلاتر
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        branch = request.args.get('branch')
        
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        
        # بناء شروط WHERE
        where_conditions = [
            "customer_name IS NOT NULL",
            "customer_name != ''",
            "subtotal_incl > 0",
            "phone_number NOT IN ('0555555555', '0500000000', 'رفض العميل', '0000000000', '1111111111')"
        ]
        
        # إضافة فلتر التاريخ الافتراضي (آخر 12 شهر) أو المخصص
        if start_date:
            where_conditions.append(f"order_date >= '{start_date}'")
        else:
            where_conditions.append("order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)")
            
        if end_date:
            where_conditions.append(f"order_date <= '{end_date}'")
        if branch:
            where_conditions.append(f"delivery_address LIKE '%{branch}%'")
        
        where_clause = " AND ".join(where_conditions)
        
        trends_query = f"""
            WITH MonthlyStats AS (
                SELECT 
                    EXTRACT(YEAR FROM order_date) as year,
                    EXTRACT(MONTH FROM order_date) as month,
                    COUNT(DISTINCT customer_name) as unique_customers,
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as total_revenue
                FROM `{PROJECT_ID}.{DATASET_ID}.pos_order_lines`
                WHERE {where_clause}
                GROUP BY year, month
            )
            SELECT 
                CONCAT(year, '-', LPAD(CAST(month AS STRING), 2, '0')) as month_year,
                unique_customers,
                total_orders,
                total_revenue,
                ROUND(total_revenue / unique_customers, 2) as avg_revenue_per_customer
            FROM MonthlyStats
            ORDER BY year, month
        """
        
        results = run_query(trends_query)
        
        trends_data = []
        for row in results:
            trends_data.append({
                "month_year": row.month_year,
                "unique_customers": int(row.unique_customers or 0),
                "total_orders": int(row.total_orders or 0),
                "total_revenue": f"{float(row.total_revenue or 0):,.2f}",
                "avg_revenue_per_customer": f"{float(row.avg_revenue_per_customer or 0):,.2f}"
            })
            
        return jsonify({"status": "success", "data": trends_data})
        
    except Exception as e:
        print(f"❌ Error in monthly customer trends: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
