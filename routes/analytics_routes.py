# routes/analytics_routes.py
# Business analytics and category analysis API routes

from flask import Blueprint, jsonify, render_template
from decimal import Decimal
from collections import OrderedDict
from database import run_query, get_project_id, get_dataset_id, get_table_id
from utils import get_user_filters_string

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route("/branch-profits")
def branch_profit_analysis():
    """API endpoint for branch profit analysis."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()

        branch_profits_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` {where_sql}
            ),
            GrandTotals AS (
                SELECT SUM(CASE WHEN subtotal_incl IS NOT NULL AND total_cost IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) - total_cost ELSE 0 END) as grand_total_profit
                FROM FilteredData
            ),
            BranchData AS (
                SELECT
                    COALESCE(branch, 'غير محدد') as branch,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL AND total_cost IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) - total_cost ELSE 0 END) AS profit,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) ELSE 0 END) AS net_sales_without_vat
                FROM FilteredData
                GROUP BY COALESCE(branch, 'غير محدد')
                HAVING SUM(CASE WHEN subtotal_incl IS NOT NULL AND total_cost IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) - total_cost ELSE 0 END) > 0
            )
            SELECT
                bd.branch,
                CAST(bd.profit AS NUMERIC) as profit,
                CAST(CASE 
                    WHEN gt.grand_total_profit > 0 THEN (bd.profit / gt.grand_total_profit) * 100 
                    ELSE 0 
                END AS NUMERIC) as profit_percentage,
                CAST(CASE 
                    WHEN bd.net_sales_without_vat > 0 THEN (bd.profit / bd.net_sales_without_vat) * 100 
                    ELSE 0 
                END AS NUMERIC) as profit_margin
            FROM BranchData bd
            CROSS JOIN GrandTotals gt
            ORDER BY bd.profit DESC, bd.branch ASC;
        """
        
        results = run_query(branch_profits_query)
        
        branch_data = []
        grand_total_profit, grand_total_sales = 0, 0
        rows = list(results)
        
        # Calculate totals for proper profit margin calculation
        for row in rows:
            grand_total_profit += (row.profit or 0)
        
        # Calculate grand profit margin by running a separate query
        margin_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` {where_sql}
            )
            SELECT
                SUM(ROUND((subtotal_incl / 1.15), 2) - total_cost) AS total_profit,
                SUM(ROUND((subtotal_incl / 1.15), 2)) AS total_net_sales
            FROM FilteredData
        """
        margin_results = list(run_query(margin_query))
        if margin_results:
            total_profit = margin_results[0].total_profit or 0
            total_net_sales = margin_results[0].total_net_sales or 0
            grand_profit_margin = (total_profit / total_net_sales * 100) if total_net_sales > 0 else 0
        else:
            grand_profit_margin = 0
        
        for row in rows:
            branch_data.append({
                "branch": row.branch or "غير محدد",
                "profit": f"{float(row.profit or 0):,.2f}",
                "profit_percentage": f"{float(row.profit_percentage or 0):.2f}%",
                "profit_margin": f"{float(row.profit_margin or 0):.2f}%"
            })
        
        if branch_data:
            branch_data.append({
                "branch": "<strong>الإجمالي</strong>",
                "profit": f"<strong>{grand_total_profit:,.2f}</strong>",
                "profit_percentage": "<strong>100.00%</strong>",
                "profit_margin": f"<strong>{grand_profit_margin:.2f}%</strong>"
            })
        
        return jsonify({"status": "success", "data": branch_data})

    except Exception as e:
        print(f"❌ Error in /api/branch-profit-analysis: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@analytics_bp.route("/top-categories")
def top_performing_categories():
    """API endpoint for top performing categories by sales."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f""" {and_clause} product_category LIKE '% / %'
            AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')
        """

        top_categories_query = f"""
            WITH BaseData AS (
                SELECT
                    SPLIT(product_category, ' / ')[SAFE_OFFSET(0)] AS category_name,
                    SPLIT(product_category, ' / ')[SAFE_OFFSET(1)] AS purchase_source,
                    subtotal_incl,
                    quantity,
                    total_cost
                FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
                {where_sql}
            ),
            GroupedBySource AS (
                SELECT
                    category_name,
                    purchase_source,
                    SUM(subtotal_incl) as total_sales,
                    SUM(quantity) as total_items_sold,
                    SUM(ROUND((subtotal_incl / 1.15), 2) - total_cost) as profit
                FROM BaseData
                GROUP BY category_name, purchase_source
            ),
            CategoryTotals AS (
                SELECT
                    category_name,
                    SUM(total_sales) as category_total_sales,
                    SUM(total_items_sold) as category_total_items,
                    SUM(profit) as category_total_profit,
                    DENSE_RANK() OVER (ORDER BY SUM(total_sales) DESC) as rnk
                FROM GroupedBySource
                GROUP BY category_name
            ),
            TopCategories AS (
                SELECT *
                FROM CategoryTotals
                WHERE rnk <= 5
            )
            SELECT
                g.category_name,
                g.purchase_source,
                g.total_sales,
                g.total_items_sold,
                g.profit,
                SAFE_DIVIDE(g.total_sales, tc.category_total_sales) * 100 as rate_within_category,
                tc.category_total_sales,
                tc.category_total_items,
                tc.category_total_profit
            FROM GroupedBySource g
            INNER JOIN TopCategories tc ON g.category_name = tc.category_name
            ORDER BY tc.category_total_sales DESC, g.total_sales DESC;
        """
        results = run_query(top_categories_query)
        
        grouped_data = OrderedDict()
        for row in results:
            cat_name = row.category_name or "غير محدد"
            if cat_name not in grouped_data:
                grouped_data[cat_name] = {
                    "category_name": cat_name,
                    "sources": [],
                    "category_total_sales": row.category_total_sales or 0,
                    "category_total_items": row.category_total_items or 0,
                    "category_total_profit": row.category_total_profit or 0,
                }
            
            grouped_data[cat_name]["sources"].append({
                "purchase_source": row.purchase_source or "غير محدد",
                "total_sales": f"{float(row.total_sales or 0):,.2f}",
                "total_items_sold": f"{int(row.total_items_sold or 0):,}",
                "rate_within_category": f"{float(row.rate_within_category or 0):.2f}%",
                "profit": f"{float(row.profit or 0):,.2f}",
            })
            
        return jsonify({"status": "success", "data": list(grouped_data.values())})

    except Exception as e:
        print(f"❌ Error in /api/top-categories-by-sales: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@analytics_bp.route("/top-categories-by-profit")
def top_profitable_categories():
    """API endpoint for top categories by profit margin."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f""" {and_clause} product_category LIKE '% / %'
            AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%')
        """

        top_categories_query = f"""
            WITH BaseData AS (
                SELECT
                    SPLIT(product_category, ' / ')[SAFE_OFFSET(0)] AS category_name,
                    SPLIT(product_category, ' / ')[SAFE_OFFSET(1)] AS purchase_source,
                    subtotal_incl,
                    quantity,
                    total_cost
                FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
                {where_sql}
            ),
            GroupedBySource AS (
                SELECT
                    category_name,
                    purchase_source,
                    SUM(subtotal_incl) as total_sales,
                    SUM(quantity) as total_items_sold,
                    SUM(ROUND((subtotal_incl / 1.15), 2) - total_cost) as profit,
                    SUM(ROUND((subtotal_incl / 1.15), 2)) AS net_sales_without_vat
                FROM BaseData
                GROUP BY category_name, purchase_source
            ),
            CategoryTotals AS (
                SELECT
                    category_name,
                    SUM(total_sales) as category_total_sales,
                    SUM(total_items_sold) as category_total_items,
                    SUM(profit) as category_total_profit,
                    DENSE_RANK() OVER (ORDER BY SUM(profit) DESC) as rnk
                FROM GroupedBySource
                GROUP BY category_name
            ),
            TopCategories AS (
                SELECT *
                FROM CategoryTotals
                WHERE rnk <= 5
            )
            SELECT
                g.category_name,
                g.purchase_source,
                g.total_sales,
                g.total_items_sold,
                g.profit,
                g.net_sales_without_vat,
                SAFE_DIVIDE(g.profit, g.net_sales_without_vat) * 100 as profit_margin,
                tc.category_total_sales,
                tc.category_total_items,
                tc.category_total_profit
            FROM GroupedBySource g
            INNER JOIN TopCategories tc ON g.category_name = tc.category_name
            ORDER BY tc.category_total_profit DESC, g.profit DESC;
        """
        results = run_query(top_categories_query)
        
        grouped_data = OrderedDict()
        for row in results:
            cat_name = row.category_name or "غير محدد"
            if cat_name not in grouped_data:
                grouped_data[cat_name] = {
                    "category_name": cat_name,
                    "sources": [],
                    "category_total_sales": row.category_total_sales or 0,
                    "category_total_items": row.category_total_items or 0,
                    "category_total_profit": row.category_total_profit or 0,
                }
            
            grouped_data[cat_name]["sources"].append({
                "purchase_source": row.purchase_source or "غير محدد",
                "profit": f"{float(row.profit or 0):,.2f}",
                "profit_margin": f"{float(row.profit_margin or 0):.2f}%",
                "total_items_sold": f"{int(row.total_items_sold or 0):,}",
                "total_sales": f"{float(row.total_sales or 0):,.2f}",
            })
            
        return jsonify({"status": "success", "data": list(grouped_data.values())})

    except Exception as e:
        print(f"❌ Error in /api/top-categories-by-profit: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@analytics_bp.route("/top-10-categories")
def top_10_categories_subtotal_quantity():
    """API endpoint for top 10 categories by subtotal and quantity."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        print(f"🔍 Top 10 Categories Filter: {where_sql}")  # Debug logging
        
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f""" {and_clause} product_category LIKE '% / %'
            AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%' OR product_category LIKE '%pos%')
            AND subtotal_incl IS NOT NULL
        """

        top_categories_query = f"""
            WITH FilteredData AS (
                SELECT
                    TRIM(SPLIT(product_category, ' / ')[SAFE_OFFSET(0)]) AS category_name,
                    TRIM(SPLIT(product_category, ' / ')[SAFE_OFFSET(1)]) AS purchase_source,
                    subtotal_incl,
                    quantity,
                    total_cost
                FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
                {where_sql}
            ),
            CategoryTotals AS (
                SELECT
                    category_name,
                    CAST(SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) AS NUMERIC) as total_subtotal,
                    CAST(SUM(CASE WHEN quantity IS NOT NULL THEN quantity ELSE 0 END) AS INT64) as total_quantity,
                    CAST(COUNT(DISTINCT purchase_source) AS INT64) as source_count,
                    CAST(SUM(CASE WHEN subtotal_incl IS NOT NULL AND total_cost IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) - total_cost ELSE 0 END) AS NUMERIC) AS total_profit
                FROM FilteredData
                WHERE category_name IS NOT NULL AND category_name != ''
                GROUP BY category_name
                HAVING total_subtotal > 0
                ORDER BY total_subtotal DESC, total_quantity DESC
                LIMIT 10
            )
            SELECT
                category_name,
                total_subtotal,
                total_quantity,
                source_count,
                total_profit,
                CAST(CASE 
                    WHEN total_subtotal > 0 THEN (total_profit / (total_subtotal / 1.15)) * 100 
                    ELSE 0 
                END AS NUMERIC) as profit_margin
            FROM CategoryTotals
            ORDER BY total_subtotal DESC, total_quantity DESC;
        """
        
        results = run_query(top_categories_query)
        
        if not results:
            return jsonify({"status": "success", "data": []})
        
        categories_data = []
        grand_total_subtotal = 0
        grand_total_quantity = 0
        grand_total_profit = 0
        rows = list(results)
        
        # Calculate totals
        for row in rows:
            grand_total_subtotal += float(row.total_subtotal or 0)
            grand_total_quantity += int(row.total_quantity or 0)
            grand_total_profit += float(row.total_profit or 0)
        
        # Format data for display
        for row in rows:
            categories_data.append({
                "category_name": row.category_name or "غير محدد",
                "total_subtotal": f"{float(row.total_subtotal or 0):,.2f}",
                "total_quantity": f"{int(row.total_quantity or 0):,}",
                "source_count": f"{int(row.source_count or 0):,}",
                "total_profit": f"{float(row.total_profit or 0):,.2f}",
                "profit_margin": f"{float(row.profit_margin or 0):.2f}%"
            })
        
        # Add totals row
        if categories_data and grand_total_subtotal > 0:
            avg_profit_margin = (grand_total_profit / (grand_total_subtotal / 1.15) * 100) if grand_total_subtotal > 0 else 0
            categories_data.append({
                "category_name": "<strong>الإجمالي</strong>",
                "total_subtotal": f"<strong>{grand_total_subtotal:,.2f}</strong>",
                "total_quantity": f"<strong>{grand_total_quantity:,}</strong>",
                "source_count": "<strong>-</strong>",
                "total_profit": f"<strong>{grand_total_profit:,.2f}</strong>",
                "profit_margin": f"<strong>{avg_profit_margin:.2f}%</strong>"
            })
        
        return jsonify({"status": "success", "data": categories_data})

    except Exception as e:
        print(f"❌ Error in /api/top-10-categories: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"خطأ في تحميل أهم 10 فئات: {str(e)}"}), 500

@analytics_bp.route("/top-15-customers")
def top_15_customers():
    """API endpoint for top 15 customers with name, phone, branch, subtotal, quantity, and receipt count."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        print(f"🔍 Top 15 Customers Filter: {where_sql}")  # Debug logging
        
        top_customers_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
                {where_sql}
            ),
            CustomerData AS (
                SELECT
                    COALESCE(TRIM(customer_name), 'غير محدد') as customer_name,
                    COALESCE(TRIM(phone_number), 'غير محدد') as phone_number,
                    COALESCE(TRIM(branch), 'غير محدد') as branch,
                    CAST(SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) AS NUMERIC) as total_subtotal,
                    CAST(SUM(CASE WHEN subtotal_incl IS NOT NULL AND NOT (product_category LIKE '%خدمات%' OR product_category LIKE '%خدمات وخصومات%' OR product_category LIKE '%pos%') THEN quantity ELSE 0 END) AS INT64) as total_quantity,
                    CAST(COUNT(DISTINCT CASE WHEN subtotal_incl IS NOT NULL THEN receipt_number ELSE NULL END) AS INT64) as receipt_count,
                    CAST(SUM(CASE WHEN subtotal_incl IS NOT NULL AND total_cost IS NOT NULL THEN ROUND((subtotal_incl / 1.15), 2) - total_cost ELSE 0 END) AS NUMERIC) AS total_profit,
                    CAST(COUNT(DISTINCT DATE(order_date)) AS INT64) as visit_days
                FROM FilteredData
                WHERE subtotal_incl IS NOT NULL
                  AND phone_number IS NOT NULL 
                  AND phone_number != ''
                  AND phone_number != 'NULL'
                GROUP BY 
                    COALESCE(TRIM(customer_name), 'غير محدد'),
                    COALESCE(TRIM(phone_number), 'غير محدد'),
                    COALESCE(TRIM(branch), 'غير محدد')
                HAVING total_subtotal > 0
                ORDER BY total_subtotal DESC, total_quantity DESC
                LIMIT 15
            )
            SELECT
                customer_name,
                phone_number,
                branch,
                total_subtotal,
                total_quantity,
                receipt_count,
                total_profit,
                visit_days,
                CAST(CASE 
                    WHEN receipt_count > 0 THEN total_subtotal / receipt_count 
                    ELSE 0 
                END AS NUMERIC) as avg_receipt_value,
                CAST(CASE 
                    WHEN total_subtotal > 0 THEN (total_profit / (total_subtotal / 1.15)) * 100 
                    ELSE 0 
                END AS NUMERIC) as profit_margin
            FROM CustomerData
            ORDER BY total_subtotal DESC, total_quantity DESC;
        """
        
        results = run_query(top_customers_query)
        
        if not results:
            return jsonify({"status": "success", "data": []})
        
        customers_data = []
        grand_total_subtotal = 0
        grand_total_quantity = 0
        grand_total_receipts = 0
        grand_total_profit = 0
        rows = list(results)
        
        # Calculate totals
        for row in rows:
            grand_total_subtotal += float(row.total_subtotal or 0)
            grand_total_quantity += int(row.total_quantity or 0)
            grand_total_receipts += int(row.receipt_count or 0)
            grand_total_profit += float(row.total_profit or 0)
        
        # Format data for display
        for row in rows:
            customers_data.append({
                "customer_name": row.customer_name or "غير محدد",
                "phone_number": row.phone_number or "غير محدد",
                "branch": row.branch or "غير محدد",
                "total_subtotal": f"{float(row.total_subtotal or 0):,.2f}",
                "total_quantity": f"{int(row.total_quantity or 0):,}",
                "receipt_count": f"{int(row.receipt_count or 0):,}",
                "total_profit": f"{float(row.total_profit or 0):,.2f}",
                "visit_days": f"{int(row.visit_days or 0):,}",
                "avg_receipt_value": f"{float(row.avg_receipt_value or 0):,.2f}",
                "profit_margin": f"{float(row.profit_margin or 0):.2f}%"
            })
        
        # Add totals row
        if customers_data and grand_total_subtotal > 0:
            avg_receipt_value_total = grand_total_subtotal / grand_total_receipts if grand_total_receipts > 0 else 0
            avg_profit_margin = (grand_total_profit / (grand_total_subtotal / 1.15) * 100) if grand_total_subtotal > 0 else 0
            
            customers_data.append({
                "customer_name": "<strong>الإجمالي</strong>",
                "phone_number": "<strong>-</strong>",
                "branch": "<strong>جميع الفروع</strong>",
                "total_subtotal": f"<strong>{grand_total_subtotal:,.2f}</strong>",
                "total_quantity": f"<strong>{grand_total_quantity:,}</strong>",
                "receipt_count": f"<strong>{grand_total_receipts:,}</strong>",
                "total_profit": f"<strong>{grand_total_profit:,.2f}</strong>",
                "visit_days": "<strong>-</strong>",
                "avg_receipt_value": f"<strong>{avg_receipt_value_total:,.2f}</strong>",
                "profit_margin": f"<strong>{avg_profit_margin:.2f}%</strong>"
            })
        
        return jsonify({"status": "success", "data": customers_data})

    except Exception as e:
        print(f"❌ Error in /api/top-15-customers: {e}")
        import traceback
        traceback.print_exc()
@analytics_bp.route("/customer-invoices/<phone_number>")
def customer_invoices(phone_number):
    """API endpoint for customer invoices details."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        print(f"🔍 Customer Invoices Filter: {where_sql}, Phone: {phone_number}")  # Debug logging
        
        # Add customer phone filter
        if where_sql:
            where_sql += f" AND phone_number = '{phone_number.replace('\'', '\'\'')}'"
        else:
            where_sql = f"WHERE phone_number = '{phone_number.replace('\'', '\'\'')}'"
        
        print(f"🔍 Final where clause: {where_sql}")  # Debug logging
        
        customer_invoices_query = f"""
            WITH FilteredData AS (
                SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
                {where_sql}
            ),
            CustomerInfo AS (
                SELECT 
                    COALESCE(customer_name, 'غير محدد') as customer_name,
                    phone_number,
                    COUNT(DISTINCT receipt_number) as total_invoices,
                    SUM(CASE WHEN subtotal_incl IS NOT NULL THEN subtotal_incl ELSE 0 END) as total_amount,
                    COUNT(*) as total_items
                FROM FilteredData
                GROUP BY customer_name, phone_number
            ),
            InvoiceDetails AS (
                SELECT
                    ci.customer_name,
                    ci.phone_number,
                    ci.total_invoices,
                    ci.total_amount,
                    ci.total_items,
                    fd.receipt_number,
                    fd.order_date,
                    fd.product_name,
                    fd.product_barcode,
                    fd.product_category,
                    fd.branch,
                    fd.quantity,
                    fd.subtotal_incl,
                    fd.total_cost,
                    CASE WHEN fd.subtotal_incl IS NOT NULL AND fd.total_cost IS NOT NULL 
                         THEN ROUND((fd.subtotal_incl / 1.15), 2) - fd.total_cost 
                         ELSE 0 END as profit
                FROM FilteredData fd
                CROSS JOIN CustomerInfo ci
                WHERE fd.subtotal_incl IS NOT NULL
                ORDER BY fd.order_date DESC, fd.receipt_number DESC
            )
            SELECT * FROM InvoiceDetails;
        """
        
        print(f"🔍 Executing query for phone: {phone_number}")  # Debug logging
        results = run_query(customer_invoices_query)
        
        if not results:
            print(f"❌ No results returned from BigQuery for phone: {phone_number}")
            return jsonify({"status": "error", "message": "لا توجد فواتير لهذا العميل"}), 404
        
        rows = list(results)
        print(f"🔍 Found {len(rows)} rows for phone: {phone_number}")  # Debug logging
        
        if not rows:
            print(f"❌ Empty rows list for phone: {phone_number}")
            return jsonify({"status": "error", "message": "لا توجد فواتير لهذا العميل"}), 404
        
        # Get customer info from first row
        customer_info = {
            "customer_name": rows[0].customer_name or "غير محدد",
            "phone_number": rows[0].phone_number or "غير محدد",
            "total_invoices": int(rows[0].total_invoices or 0),
            "total_amount": float(rows[0].total_amount or 0),
            "total_items": int(rows[0].total_items or 0)
        }
        
        print(f"🔍 Customer info: {customer_info}")  # Debug logging
        
        # Format invoice details
        invoices_data = []
        current_receipt = None
        current_invoice = None
        
        for row in rows:
            receipt_num = row.receipt_number
            
            if current_receipt != receipt_num:
                # Save previous invoice if exists
                if current_invoice:
                    invoices_data.append(current_invoice)
                
                # Start new invoice
                current_receipt = receipt_num
                current_invoice = {
                    "receipt_number": receipt_num,
                    "order_date": row.order_date.strftime('%Y-%m-%d %H:%M:%S') if row.order_date else "غير محدد",
                    "branch": row.branch or "غير محدد",
                    "items": [],
                    "invoice_total": 0,
                    "invoice_profit": 0
                }
            
            # Add item to current invoice
            if current_invoice:
                current_invoice["items"].append({
                    "product_name": row.product_name or "غير محدد",
                    "product_barcode": row.product_barcode or "غير محدد",
                    "product_category": row.product_category or "غير محدد",
                    "quantity": int(row.quantity or 0),
                    "subtotal_incl": float(row.subtotal_incl or 0),
                    "profit": float(row.profit or 0)
                })
                current_invoice["invoice_total"] += float(row.subtotal_incl or 0)
                current_invoice["invoice_profit"] += float(row.profit or 0)
        
        # Add last invoice
        if current_invoice:
            invoices_data.append(current_invoice)
        
        # Sort invoices by date (most recent first)
        invoices_data.sort(key=lambda x: x["order_date"], reverse=True)
        
        print(f"🔍 Returning {len(invoices_data)} invoices for phone: {phone_number}")  # Debug logging
        
        return jsonify({
            "status": "success",
            "customer_info": customer_info,
            "invoices": invoices_data
        })

    except Exception as e:
        print(f"❌ Error in /api/customer-invoices/{phone_number}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"خطأ في تحميل فواتير العميل: {str(e)}"}), 500
