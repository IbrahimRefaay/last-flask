# routes/seller_routes.py
# Employee performance and product analysis API routes

from flask import Blueprint, jsonify
from decimal import Decimal
from collections import OrderedDict
from database import run_query, get_project_id, get_dataset_id, get_table_id
from utils import get_user_filters_string

seller_bp = Blueprint('seller', __name__)

@seller_bp.route("/top-sellers")
def top_performing_sellers():
    """API endpoint for top performing sellers by branch."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f" {and_clause} branch != 'المتجر الإلكتروني'"

        top_sellers_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` {where_sql}
            ),
            BranchTotals AS (
                SELECT
                    branch,
                    SUM(subtotal_incl) as total_branch_sales
                FROM FilteredData
                GROUP BY branch
            ),
            SellerMetrics AS (
                SELECT
                    branch,
                    employee_name,
                    SUM(subtotal_incl) as total_sales,
                    SUM(IF(NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%' OR product_category LIKE '%pos%'), quantity, 0)) as total_items_sold,
                    COUNT(DISTINCT receipt_number) as invoice_count,
                    SUM(ROUND((subtotal_incl / 1.15), 2) - total_cost) AS profit,
                    SUM(ROUND((subtotal_incl / 1.15), 2)) AS net_sales_without_vat,
                    COUNT(DISTINCT DATE(order_date)) as work_days,
                    RANK() OVER (PARTITION BY branch ORDER BY SUM(subtotal_incl) DESC) as seller_rank
                FROM FilteredData
                WHERE employee_name IS NOT NULL
                GROUP BY branch, employee_name
            )
            SELECT
                s.branch,
                s.employee_name,
                s.total_sales,
                s.total_items_sold,
                s.invoice_count,
                s.profit,
                s.work_days,
                SAFE_DIVIDE(s.total_sales, s.invoice_count) as avg_invoice_value,
                SAFE_DIVIDE(s.profit, s.net_sales_without_vat) * 100 as profit_margin,
                SAFE_DIVIDE(s.total_sales, bt.total_branch_sales) * 100 as sales_percentage_in_branch
            FROM SellerMetrics s
            JOIN BranchTotals bt ON s.branch = bt.branch
            WHERE s.seller_rank = 1
            ORDER BY s.total_sales DESC;
        """
        results = run_query(top_sellers_query)
        
        sellers_data = []
        for row in results:
            sellers_data.append({
                "employee_name": row.employee_name or "غير محدد",
                "branch": row.branch or "غير محدد",
                "total_sales": f"{float(row.total_sales or 0):,.2f}",
                "sales_percentage_in_branch": f"{float(row.sales_percentage_in_branch or 0):.2f}%",
                "total_items_sold": f"{int(row.total_items_sold or 0):,}",
                "invoice_count": f"{int(row.invoice_count or 0):,}",
                "avg_invoice_value": f"{float(row.avg_invoice_value or 0):,.2f}",
                "profit": f"{float(row.profit or 0):,.2f}",
                "profit_margin": f"{float(row.profit_margin or 0):.2f}%",
                "work_days": f"{int(row.work_days or 0):,}",
            })
            
        return jsonify({"status": "success", "data": sellers_data})

    except Exception as e:
        print(f"❌ Error in /api/top-performers: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@seller_bp.route("/top-10-sellers")
def top_10_sales_performers():
    """API endpoint for top 10 sales performers overall."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f" {and_clause} branch != 'المتجر الإلكتروني'"

        top_10_sellers_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` {where_sql}
            ),
            BranchTotals AS (
                SELECT
                    branch,
                    SUM(subtotal_incl) as total_branch_sales
                FROM FilteredData
                GROUP BY branch
            ),
            SellerMetrics AS (
                SELECT
                    branch,
                    employee_name,
                    SUM(subtotal_incl) as total_sales,
                    SUM(IF(NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%' OR product_category LIKE '%pos%'), quantity, 0)) as total_items_sold,
                    COUNT(DISTINCT receipt_number) as invoice_count,
                    SUM(ROUND((subtotal_incl / 1.15), 2) - total_cost) AS profit,
                    SUM(ROUND((subtotal_incl / 1.15), 2)) AS net_sales_without_vat,
                    COUNT(DISTINCT DATE(order_date)) as work_days
                FROM FilteredData
                WHERE employee_name IS NOT NULL
                GROUP BY branch, employee_name
            )
            SELECT
                s.branch,
                s.employee_name,
                s.total_sales,
                s.total_items_sold,
                s.invoice_count,
                s.profit,
                s.work_days,
                SAFE_DIVIDE(s.total_sales, s.invoice_count) as avg_invoice_value,
                SAFE_DIVIDE(s.profit, s.net_sales_without_vat) * 100 as profit_margin,
                SAFE_DIVIDE(s.total_sales, bt.total_branch_sales) * 100 as sales_percentage_in_branch
            FROM SellerMetrics s
            JOIN BranchTotals bt ON s.branch = bt.branch
            ORDER BY s.total_sales DESC
            LIMIT 10;
        """
        results = run_query(top_10_sellers_query)
        
        sellers_data = []
        for row in results:
            sellers_data.append({
                "employee_name": row.employee_name or "غير محدد",
                "branch": row.branch or "غير محدد",
                "total_sales": f"{float(row.total_sales or 0):,.2f}",
                "sales_percentage_in_branch": f"{float(row.sales_percentage_in_branch or 0):.2f}%",
                "total_items_sold": f"{int(row.total_items_sold or 0):,}",
                "invoice_count": f"{int(row.invoice_count or 0):,}",
                "avg_invoice_value": f"{float(row.avg_invoice_value or 0):,.2f}",
                "profit": f"{float(row.profit or 0):,.2f}",
                "profit_margin": f"{float(row.profit_margin or 0):.2f}%",
                "work_days": f"{int(row.work_days or 0):,}",
            })
            
        return jsonify({"status": "success", "data": sellers_data})

    except Exception as e:
        print(f"❌ Error in /api/top-10-performers: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@seller_bp.route("/top_products_by_sales_value")
def top_products_by_sales_value():
    """API endpoint for best selling products by sales value."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f" {and_clause} NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')"

        query = f"""
            SELECT
                product_barcode,
                product_name,
                SUM(quantity) as total_quantity,
                SUM(subtotal_incl) as total_sales
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            {where_sql}
            GROUP BY product_barcode, product_name
            ORDER BY total_sales DESC
            LIMIT 10;
        """
        results = run_query(query)
        data = [
            {
                "product_barcode": row.product_barcode,
                "product_name": row.product_name,
                "total_quantity": f"{int(row.total_quantity or 0):,}",
                "total_sales": f"{float(row.total_sales or 0):,.2f}"
            } for row in results
        ]
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        print(f"❌ Error in /api/best-selling-products-by-value: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@seller_bp.route("/top_products_by_quantity")
def top_products_by_quantity_sold():
    """API endpoint for best selling products by quantity."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f" {and_clause} NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')"

        query = f"""
            SELECT
                product_barcode,
                product_name,
                SUM(quantity) as total_quantity,
                SUM(subtotal_incl) as total_sales
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            {where_sql}
            GROUP BY product_barcode, product_name
            ORDER BY total_quantity DESC
            LIMIT 10;
        """
        results = run_query(query)
        data = [
            {
                "product_barcode": row.product_barcode,
                "product_name": row.product_name,
                "total_quantity": f"{int(row.total_quantity or 0):,}",
                "total_sales": f"{float(row.total_sales or 0):,.2f}"
            } for row in results
        ]
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        print(f"❌ Error in /api/best-selling-products-by-quantity: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@seller_bp.route("/top_products_by_profit")
def top_products_by_profit_margin():
    """API endpoint for most profitable products."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        query = f"""
            SELECT
                product_barcode,
                ANY_VALUE(product_name) as product_name,
                SUM(ROUND(IF(total_cost > 0, (subtotal_incl / 1.15) - total_cost, 0), 2)) as total_profit,
                SUM(quantity) as total_quantity
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            {where_sql}
            GROUP BY
                product_barcode
            ORDER BY
                total_profit DESC
            LIMIT 10;
        """
        results = run_query(query)
        data = [
            {
                "product_barcode": row.product_barcode,
                "product_name": row.product_name,
                "total_quantity": f"{int(row.total_quantity or 0):,}",
                "total_profit": f"{float(row.total_profit or 0):,.2f}"
            } for row in results
        ]
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        print(f"❌ Error in /api/most-profitable-products: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
