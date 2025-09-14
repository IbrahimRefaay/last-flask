# routes/returns_routes.py
# Returns analysis and reference data API routes

from flask import Blueprint, jsonify
from decimal import Decimal
from collections import OrderedDict
from database import run_query, get_project_id, get_dataset_id, get_table_id
from utils import get_user_filters_string

returns_bp = Blueprint('returns', __name__)

@returns_bp.route("/top_categories_by_returns")
def categories_with_highest_returns():
    """API endpoint for categories with highest return rates."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f""" {and_clause} quantity < 0
            AND branch != 'المتجر الإلكتروني'
            AND SPLIT(product_category, ' / ')[SAFE_OFFSET(1)] NOT LIKE '%خدمات%'
        """

        query = f"""
            SELECT
                SPLIT(product_category, ' / ')[SAFE_OFFSET(0)] AS category_name,
                SUM(ABS(IF(quantity < 0, quantity, 0))) as returned_quantity,
                SUM(ABS(IF(quantity < 0, subtotal_incl, 0))) as returned_value
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            {where_sql}
            GROUP BY category_name
            HAVING returned_value > 0
            ORDER BY returned_value DESC
            LIMIT 5;
        """
        results = run_query(query)
        data = []
        total_qty = 0
        total_val = 0
        for row in results:
            total_qty += row.returned_quantity or 0
            total_val += row.returned_value or 0
            data.append({
                "category_name": row.category_name,
                "returned_quantity": f"{int(row.returned_quantity or 0):,}",
                "returned_value": f"{float(row.returned_value or 0):,.2f}"
            })
        
        if data:
            data.append({
                "category_name": "<strong>الإجمالي</strong>",
                "returned_quantity": f"<strong>{int(total_qty):,}</strong>",
                "returned_value": f"<strong>{float(total_val):,.2f}</strong>"
            })

        return jsonify({"status": "success", "data": data})
    except Exception as e:
        print(f"❌ Error in /api/categories-with-highest-returns: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@returns_bp.route("/top_sellers_by_returns")
def employees_with_highest_returns():
    """API endpoint for employees with highest return rates."""
    try:
        where_sql = get_user_filters_string()
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        and_clause = "AND " if where_sql else "WHERE "
        where_sql += f""" {and_clause} quantity < 0
            AND employee_name IS NOT NULL
            AND branch != 'المتجر الإلكتروني'
            AND SPLIT(product_category, ' / ')[SAFE_OFFSET(1)] NOT LIKE '%خدمات%'
        """

        query = f"""
            SELECT
                branch,
                employee_name,
                SUM(ABS(IF(quantity < 0, quantity, 0))) as returned_quantity,
                SUM(ABS(IF(quantity < 0, subtotal_incl, 0))) as returned_value
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            {where_sql}
            GROUP BY branch, employee_name
            HAVING returned_value > 0
            ORDER BY returned_value DESC
            LIMIT 5;
        """
        results = run_query(query)
        data = []
        total_qty = 0
        total_val = 0
        for row in results:
            total_qty += row.returned_quantity or 0
            total_val += row.returned_value or 0
            data.append({
                "branch": row.branch,
                "employee_name": row.employee_name,
                "returned_quantity": f"{int(row.returned_quantity or 0):,}",
                "returned_value": f"{float(row.returned_value or 0):,.2f}"
            })
        
        if data:
            data.append({
                "branch": "<strong>الإجمالي</strong>",
                "employee_name": "",
                "returned_quantity": f"<strong>{int(total_qty):,}</strong>",
                "returned_value": f"<strong>{float(total_val):,.2f}</strong>"
            })

        return jsonify({"status": "success", "data": data})
    except Exception as e:
        print(f"❌ Error in /api/employees-with-highest-returns: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@returns_bp.route("/get-branches")
def available_branches():
    """Get all available branches for filtering."""
    try:
        PROJECT_ID = get_project_id()
        DATASET_ID = get_dataset_id()
        TABLE_ID = get_table_id()
        
        query = f"""
            SELECT DISTINCT branch
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            WHERE branch IS NOT NULL
            ORDER BY branch;
        """
        results = run_query(query)
        branches = [row.branch for row in results]
        return jsonify({"status": "success", "data": branches})
    except Exception as e:
        print(f"❌ Error in /api/branch-list: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
