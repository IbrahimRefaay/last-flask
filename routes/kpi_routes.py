# routes/kpi_routes.py
# KPI and main business metrics API routes

from flask import Blueprint, jsonify
from decimal import Decimal
from collections import OrderedDict
from database import run_query, get_project_id, get_dataset_id, get_table_id
from utils import get_user_filters_string

kpi_bp = Blueprint('kpi', __name__)

@kpi_bp.route("/data")
def main_kpi_data():
    """API endpoint to fetch the main KPI data."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        print(f"🔍 KPI Data Filter: {where_sql}")  # Debug logging
        
        kpi_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
                {where_sql}
            )
            SELECT
                -- ## مجموعة المبيعات ##
                -- 1. إجمالي المبيعات
                CAST(COALESCE(SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END), 0) AS NUMERIC) AS total_sales,
                -- 2. المبيعات بدون خدمات
                CAST(COALESCE(SUM(IF(NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%pos%') AND subtotal_incl IS NOT NULL, subtotal_incl, 0)), 0) AS NUMERIC) AS sales_without_services,

                -- ## مجموعة الأرباح ##
                -- 3. إجمالي الأرباح
                CAST(COALESCE(SUM(CASE WHEN subtotal_incl IS NOT NULL AND total_cost IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) - total_cost ELSE 0 END), 0) AS NUMERIC) AS profit,
                -- 4. هامش الربح
                CAST(COALESCE(SAFE_DIVIDE(
                    SUM(CASE WHEN subtotal_incl IS NOT NULL AND total_cost IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) - total_cost ELSE 0 END),
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) ELSE 0 END)
                ), 0) AS NUMERIC) as profit_margin,

                -- ## مجموعة الفواتير والعملاء ##
                -- 5. عدد الفواتير
                CAST(COALESCE(COUNT(DISTINCT CASE WHEN subtotal_incl IS NOT NULL THEN receipt_number ELSE NULL END), 0) AS INT64) AS invoice_count,
                -- 6. متوسط قيمة الفاتورة
                CAST(COALESCE(SAFE_DIVIDE(
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END), 
                    COUNT(DISTINCT CASE WHEN subtotal_incl IS NOT NULL THEN receipt_number ELSE NULL END)
                ), 0) AS NUMERIC) as avg_invoice_value,
                -- 7. عدد العملاء
                CAST(COALESCE(COUNT(DISTINCT CASE WHEN subtotal_incl IS NOT NULL THEN phone_number ELSE NULL END), 0) AS INT64) AS customer_count,

                -- ## مجموعة القطع ##
                -- 8. عدد القطع المباعة
                CAST(COALESCE(SUM(IF(branch != 'المتجر الالكتروني' AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%pos%') AND subtotal_incl IS NOT NULL, quantity, 0)), 0) AS INT64) AS total_items_sold,

                -- ## مجموعة المرتجعات ##
                -- 9. عدد القطع المرتجعة
                CAST(COALESCE(SUM(IF(quantity < 0 AND branch != 'المتجر الإلكتروني' AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%pos%') AND subtotal_incl IS NOT NULL, ABS(quantity), 0)), 0) AS INT64) AS returned_items_count,
                -- 10. قيمة القطع المرتجعة
                CAST(COALESCE(SUM(IF(quantity < 0 AND branch != 'المتجر الإلكتروني' AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%pos%') AND subtotal_incl IS NOT NULL, ABS(subtotal_incl), 0)), 0) AS NUMERIC) AS returned_items_value,

                -- ## مجموعة الخدمات ##
                -- 11. قيمة الخدمات
                CAST(COALESCE(SUM(IF(
                    quantity > 0 AND
                    branch != 'المتجر الالكتروني' AND
                    (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%') AND
                    (product_name NOT LIKE '%عربون طلب بضاعة%' AND product_name NOT LIKE '%دفع مسبق منتجات البدائع%' AND product_name NOT LIKE '%قسيمة التخفيض%' AND product_name NOT LIKE '%نقاط المكافآت%') AND
                    subtotal_incl IS NOT NULL,
                    subtotal_incl, 0
                )), 0) AS NUMERIC) AS services_value,
                -- 12. مرتجعات الخدمات
                CAST(COALESCE(SUM(IF(
                    quantity < 0 AND
                    branch != 'المتجر الالكتروني' AND
                    (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%') AND
                    (product_name NOT LIKE '%عربون طلب بضاعة%' AND product_name NOT LIKE '%دفع مسبق منتجات البدائع%' AND product_name NOT LIKE '%قسيمة التخفيض%' AND product_name NOT LIKE '%نقاط المكافآت%') AND
                    subtotal_incl IS NOT NULL,
                    ABS(subtotal_incl), 0
                )), 0) AS NUMERIC) AS returned_services_value,

                -- ## Other KPIs (not displayed but might be needed) ##
                CAST(COALESCE(SUM(CASE WHEN subtotal_incl IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) ELSE 0 END), 0) AS NUMERIC) AS net_sales_without_vat,
                CAST(COALESCE(SUM(IF(total_cost > 0 AND subtotal_incl IS NOT NULL, ROUND((subtotal_incl / 1.15), 2), 0)), 0) AS NUMERIC) AS gross_sales_without_vat,
                CAST(COALESCE(SUM(CASE WHEN total_cost IS NOT NULL THEN total_cost ELSE 0 END), 0) AS NUMERIC) AS total_cost_all

            FROM FilteredData
            WHERE subtotal_incl IS NOT NULL;
        """
        
        results = run_query(kpi_query)
        kpis_english = dict(list(results)[0]) if results.total_rows > 0 else {}

        key_mapping = {
            "total_sales": "إجمالي المبيعات",
            "sales_without_services": "المبيعات بدون خدمات",
            "profit": "الربح",
            "profit_margin": "هامش الربح",
            "invoice_count": "عدد الفواتير",
            "customer_count": "عدد العملاء",
            "total_items_sold": "إجمالي القطع المباعة",
            "avg_invoice_value": "متوسط الفاتورة",
            "returned_items_count": "المرتجعات (فروع)",
            "returned_items_value": "قيمة المرتجعات (فروع)",
            "services_value": "قيمة الخدمات",
            "returned_services_value": "مرتجعات الخدمات",
            "net_sales_without_vat": "الإجمالي بدون ضريبة",
            "total_cost_all": "إجمالي التكلفة"
        }

        # The order of the final dictionary is now controlled by the SQL query's SELECT order
        formatted_kpis_arabic = {}
        fields_to_exclude = ['gross_sales_without_vat', 'net_sales_without_vat', 'total_cost_all']

        for key_en, value in kpis_english.items():
            if key_en in fields_to_exclude: continue
            key_ar = key_mapping.get(key_en, key_en)
            if key_ar is None: continue # Skip keys that are not in the mapping

            if key_en == 'profit_margin':
                formatted_kpis_arabic[key_ar] = f"{float(value or 0) * 100:.2f}%"
            elif isinstance(value, (Decimal, float)):
                formatted_kpis_arabic[key_ar] = f"{float(value):,.2f}"
            elif isinstance(value, int):
                formatted_kpis_arabic[key_ar] = f"{value:,}"
            else:
                formatted_kpis_arabic[key_ar] = value
        
        return jsonify({"status": "success", "data": formatted_kpis_arabic})

    except Exception as e:
        print(f"❌ Error in /api/data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
@kpi_bp.route("/services-details")
def services_breakdown():
    """API endpoint for services breakdown details."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        # Add business logic conditions to the universal filter
        if where_sql:
            where_sql += """ AND quantity > 0
                AND (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')
                AND (product_name NOT LIKE '%عربون طلب بضاعة%' AND product_name NOT LIKE '%دفع مسبق منتجات البدائع%' AND product_name NOT LIKE '%قسيمة التخفيض%' AND product_name NOT LIKE '%نقاط المكافآت%')
            """
        else:
            where_sql = """WHERE quantity > 0
                AND (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')
                AND (product_name NOT LIKE '%عربون طلب بضاعة%' AND product_name NOT LIKE '%دفع مسبق منتجات البدائع%' AND product_name NOT LIKE '%قسيمة التخفيض%' AND product_name NOT LIKE '%نقاط المكافآت%')
            """

        services_query = f"""
            SELECT 
                TRIM(LOWER(product_name)) as product_name, 
                CAST(SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) AS NUMERIC) as total_value
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
            {where_sql}
            GROUP BY 1 
            HAVING SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) > 0 
            ORDER BY total_value DESC;
        """
        results = run_query(services_query)
        
        services_data, total_sum = [], 0
        rows = list(results)
        for row in rows: total_sum += (row.total_value or 0)
        for row in rows:
            services_data.append({"product": row.product_name, "total_value": f"{float(row.total_value or 0):,.2f}"})
        if services_data:
            services_data.append({"product": "<strong>الإجمالي</strong>", "total_value": f"<strong>{total_sum:,.2f}</strong>"})
            
        return jsonify({"status": "success", "data": services_data})

    except Exception as e:
        print(f"❌ Error in /api/services-details: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@kpi_bp.route("/sales-details")
def sales_breakdown_by_source():
    """API endpoint for sales breakdown by purchase source."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()

        # Add business logic conditions
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f""" {and_clause} product_category LIKE '% / %'
            AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%pos%' OR product_category LIKE '%بضاعة مخفضة%')
        """

        sales_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` {where_sql}
            ),
            GrandTotals AS (
                SELECT SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as grand_total_sales
                FROM FilteredData
            ),
            GroupedData AS (
                SELECT
                    TRIM(LOWER(SPLIT(product_category, ' / ')[SAFE_OFFSET(1)])) AS purchase_source,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as total_sales,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN quantity ELSE 0 END) AS total_items_sold,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL AND total_cost IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) - total_cost ELSE 0 END) AS profit,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) ELSE 0 END) AS net_sales_without_vat
                FROM FilteredData
                WHERE subtotal_incl IS NOT NULL
                GROUP BY purchase_source
                HAVING SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) > 0
                ORDER BY total_sales DESC
            )
            SELECT
                purchase_source,
                CAST(total_sales AS NUMERIC) as total_sales,
                CAST(total_items_sold AS INT64) as total_items_sold,
                CAST((total_sales / (SELECT grand_total_sales FROM GrandTotals)) * 100 AS NUMERIC) as rate_by_source,
                CAST(SAFE_DIVIDE(profit, net_sales_without_vat) * 100 AS NUMERIC) as profit_margin
            FROM GroupedData
            CROSS JOIN GrandTotals;
        """
        
        results = run_query(sales_query)
        
        sales_data, grand_total_sales, grand_total_items, grand_total_profit, grand_net_sales = [], 0, 0, 0, 0
        rows = list(results)
        
        # Calculate totals including profit and net sales for margin calculation
        for row in rows:
            grand_total_sales += (row.total_sales or 0)
            grand_total_items += (row.total_items_sold or 0)
        
        # Calculate grand profit margin by running a separate query
        profit_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` {where_sql}
            )
            SELECT
                SUM(ROUND((subtotal_incl / 1.15), 2) - total_cost) AS total_profit,
                SUM(ROUND((subtotal_incl / 1.15), 2)) AS total_net_sales
            FROM FilteredData
        """
        profit_results = list(run_query(profit_query))
        if profit_results:
            total_profit = profit_results[0].total_profit or 0
            total_net_sales = profit_results[0].total_net_sales or 0
            grand_profit_margin = (total_profit / total_net_sales * 100) if total_net_sales > 0 else 0
        else:
            grand_profit_margin = 0
        
        for row in rows:
            sales_data.append({
                "purchase_source": row.purchase_source or "غير محدد",
                "total_sales": f"{float(row.total_sales or 0):,.2f}",
                "total_items_sold": f"{int(row.total_items_sold or 0):,}",
                "rate_by_source": f"{float(row.rate_by_source or 0):.2f}%",
                "profit_margin": f"{float(row.profit_margin or 0):.2f}%"
            })
        
        if sales_data:
            sales_data.append({
                "purchase_source": "<strong>الإجمالي</strong>",
                "total_sales": f"<strong>{grand_total_sales:,.2f}</strong>",
                "total_items_sold": f"<strong>{grand_total_items:,}</strong>",
                "rate_by_source": "<strong>100.00%</strong>",
                "profit_margin": f"<strong>{grand_profit_margin:.2f}%</strong>"
            })
        
        return jsonify({"status": "success", "data": sales_data})

    except Exception as e:
        print(f"❌ Error in /api/sales-by-source: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@kpi_bp.route("/branch-sales")
def branch_sales_performance():
    """API endpoint for branch sales performance analysis."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        print(f"🔍 Branch Sales Filter: {where_sql}")  # Debug logging
        
        # Add some basic validation
        if not PROJECT_ID or not DATASET_ID or not TABLE_ID:
            return jsonify({"status": "error", "message": "Database configuration missing"}), 500
        
        branch_sales_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
                {where_sql}
            ),
            GrandTotals AS (
                SELECT 
                    CAST(COALESCE(SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END), 0) AS NUMERIC) as grand_total_sales,
                    CAST(COALESCE(COUNT(CASE WHEN subtotal_incl IS NOT NULL THEN 1 ELSE NULL END), 0) AS INT64) as total_records
                FROM FilteredData
            ),
            BranchData AS (
                SELECT
                    COALESCE(branch, 'غير محدد') as branch,
                    CAST(COALESCE(SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END), 0) AS NUMERIC) as total_sales,
                    CAST(COALESCE(SUM(IF(NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%' OR product_category LIKE '%pos%') AND subtotal_incl IS NOT NULL, quantity, 0)), 0) AS INT64) AS total_items_sold,
                    CAST(COALESCE(COUNT(DISTINCT CASE WHEN subtotal_incl IS NOT NULL THEN receipt_number ELSE NULL END), 0) AS INT64) AS invoice_count,
                    CAST(COALESCE(COUNT(DISTINCT CASE WHEN subtotal_incl IS NOT NULL THEN phone_number ELSE NULL END), 0) AS INT64) AS customer_count
                FROM FilteredData
                GROUP BY COALESCE(branch, 'غير محدد')
                HAVING SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) > 0
            )
            SELECT
                bd.branch,
                bd.total_sales,
                bd.total_items_sold,
                bd.invoice_count,
                bd.customer_count,
                CAST(CASE 
                    WHEN gt.grand_total_sales > 0 THEN (bd.total_sales / gt.grand_total_sales) * 100 
                    ELSE 0 
                END AS NUMERIC) as sales_percentage,
                CAST(CASE 
                    WHEN bd.invoice_count > 0 THEN bd.total_sales / bd.invoice_count 
                    ELSE 0 
                END AS NUMERIC) as avg_invoice_value
            FROM BranchData bd
            CROSS JOIN GrandTotals gt
            WHERE gt.total_records > 0
            ORDER BY bd.total_sales DESC, bd.branch ASC;
        """
        
        results = run_query(branch_sales_query)
        
        if not results:
            return jsonify({"status": "success", "data": []})
        
        branch_data = []
        grand_total_sales, grand_total_items, grand_total_invoices, grand_total_customers = 0, 0, 0, 0
        rows = list(results)
        
        # Calculate totals first
        for row in rows:
            grand_total_sales += float(row.total_sales or 0)
            grand_total_items += int(row.total_items_sold or 0)
            grand_total_invoices += int(row.invoice_count or 0)
            grand_total_customers += int(row.customer_count or 0)
        
        # Format data for display
        for row in rows:
            branch_data.append({
                "branch": row.branch or "غير محدد",
                "total_sales": f"{float(row.total_sales or 0):,.2f}",
                "total_items_sold": f"{int(row.total_items_sold or 0):,}",
                "invoice_count": f"{int(row.invoice_count or 0):,}",
                "customer_count": f"{int(row.customer_count or 0):,}",
                "sales_percentage": f"{float(row.sales_percentage or 0):.2f}%",
                "avg_invoice_value": f"{float(row.avg_invoice_value or 0):,.2f}"
            })
        
        # Add totals row
        if branch_data and grand_total_sales > 0:
            avg_total_invoice = grand_total_sales / grand_total_invoices if grand_total_invoices > 0 else 0
            branch_data.append({
                "branch": "<strong>الإجمالي</strong>",
                "total_sales": f"<strong>{grand_total_sales:,.2f}</strong>",
                "total_items_sold": f"<strong>{grand_total_items:,}</strong>",
                "invoice_count": f"<strong>{grand_total_invoices:,}</strong>",
                "customer_count": f"<strong>{grand_total_customers:,}</strong>",
                "sales_percentage": "<strong>100.00%</strong>",
                "avg_invoice_value": f"<strong>{avg_total_invoice:,.2f}</strong>"
            })
        
        return jsonify({"status": "success", "data": branch_data})

    except Exception as e:
        print(f"❌ Error in /api/branch-sales: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"خطأ في تحميل بيانات الفروع: {str(e)}"}), 500

@kpi_bp.route("/debug-totals")
def debug_totals():
    """Debug endpoint to verify data consistency between KPI cards and branch table."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        debug_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` {where_sql}
            )
            SELECT
                -- Total from all records
                CAST(SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) AS NUMERIC) as total_all_records,
                
                -- Total excluding negative subtotals
                CAST(SUM(CASE WHEN subtotal_incl IS NOT NULL AND subtotal_incl > 0 THEN subtotal_incl ELSE 0 END) AS NUMERIC) as total_positive_only,
                
                -- Count of records
                COUNT(*) as total_record_count,
                COUNT(CASE WHEN subtotal_incl IS NOT NULL THEN 1 ELSE NULL END) as records_with_subtotal,
                COUNT(CASE WHEN subtotal_incl IS NOT NULL AND subtotal_incl > 0 THEN 1 ELSE NULL END) as records_positive_subtotal,
                
                -- Branch breakdown
                COUNT(DISTINCT branch) as unique_branches,
                
                -- Test sum by branch
                CAST(SUM(CASE WHEN subtotal_incl IS NOT NULL AND branch IS NOT NULL THEN subtotal_incl ELSE 0 END) AS NUMERIC) as total_with_branch
                
            FROM FilteredData;
        """
        
        results = run_query(debug_query)
        debug_data = dict(list(results)[0]) if results.total_rows > 0 else {}
        
        return jsonify({
            "status": "success", 
            "filter_used": where_sql,
            "debug_data": debug_data
        })

    except Exception as e:
        print(f"❌ Error in debug endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
