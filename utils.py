# utils.py
# Helper functions and utilities

from flask import request
from datetime import datetime, date, time, timedelta
import calendar

def get_date_range_strings():
    """
    Parses date filters and returns formatted date strings for SQL queries.
    Handles all filter types with proper priority and validation.
    Business Day: Starts at 21:00 on the previous calendar day and ends at 20:59 on the current day.
    """
    # Get all possible filter parameters
    single_day = request.args.get('single_day')
    start_day = request.args.get('start_day')
    end_day = request.args.get('end_day')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_type = request.args.get('filter')
    month_param = request.args.get('month')
    today = date.today()
    
    start_sql_str, end_sql_str = None, None

    try:
        # Priority 1: Full date range (most specific)
        if start_date and end_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Validate date range
            if start_date_obj > end_date_obj:
                start_date_obj, end_date_obj = end_date_obj, start_date_obj
            
            business_start_dt = datetime.combine(start_date_obj, time(21, 0, 0)) - timedelta(days=1)
            business_end_dt = datetime.combine(end_date_obj, time(20, 59, 59))
            
            start_sql_str = business_start_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_sql_str = business_end_dt.strftime('%Y-%m-%d %H:%M:%S')

        # Priority 2: Month-specific filters
        elif month_param:
            year, month = map(int, month_param.split('-'))
            
            # Validate month
            if month < 1 or month > 12:
                raise ValueError("Invalid month")
            
            if filter_type == 'day_in_month' and single_day:
                selected_day = int(single_day)
                # Validate day for the given month
                _, last_day = calendar.monthrange(year, month)
                if selected_day < 1 or selected_day > last_day:
                    raise ValueError("Invalid day for month")
                
                target_date = date(year, month, selected_day)
                business_start_dt = datetime.combine(target_date, time(21, 0, 0)) - timedelta(days=1)
                business_end_dt = datetime.combine(target_date, time(20, 59, 59))
                
            elif filter_type == 'days_range_in_month' and start_day and end_day:
                start_day_int = int(start_day)
                end_day_int = int(end_day)
                
                # Validate days for the given month
                _, last_day = calendar.monthrange(year, month)
                if (start_day_int < 1 or start_day_int > last_day or 
                    end_day_int < 1 or end_day_int > last_day):
                    raise ValueError("Invalid day range for month")
                
                # Handle cross-month within the specified month context
                if end_day_int < start_day_int:
                    # Assume next month for end day
                    if month == 12:
                        end_date_obj = date(year + 1, 1, end_day_int)
                    else:
                        end_date_obj = date(year, month + 1, end_day_int)
                    start_date_obj = date(year, month, start_day_int)
                else:
                    start_date_obj = date(year, month, start_day_int)
                    end_date_obj = date(year, month, end_day_int)
                
                business_start_dt = datetime.combine(start_date_obj, time(21, 0, 0)) - timedelta(days=1)
                business_end_dt = datetime.combine(end_date_obj, time(20, 59, 59))
                
            else:
                # Full month
                start_date_obj = date(year, month, 1)
                _, last_day = calendar.monthrange(year, month)
                end_date_obj = date(year, month, last_day)
                
                business_start_dt = datetime.combine(start_date_obj, time(21, 0, 0)) - timedelta(days=1)
                business_end_dt = datetime.combine(end_date_obj, time(20, 59, 59))
            
            start_sql_str = business_start_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_sql_str = business_end_dt.strftime('%Y-%m-%d %H:%M:%S')

        # Priority 3: Current month day filters
        elif single_day:
            selected_day = int(single_day)
            # Validate day for current month
            _, last_day = calendar.monthrange(today.year, today.month)
            if selected_day < 1 or selected_day > last_day:
                raise ValueError("Invalid day for current month")
            
            target_date = today.replace(day=selected_day)
            business_start_dt = datetime.combine(target_date, time(21, 0, 0)) - timedelta(days=1)
            business_end_dt = datetime.combine(target_date, time(20, 59, 59))
            
            start_sql_str = business_start_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_sql_str = business_end_dt.strftime('%Y-%m-%d %H:%M:%S')

        elif start_day and end_day:
            start_day_int = int(start_day)
            end_day_int = int(end_day)
            
            # Validate days for current month
            _, last_day = calendar.monthrange(today.year, today.month)
            
            # Handle cross-month scenario
            if end_day_int < start_day_int:
                # End day is in next month
                start_date_obj = today.replace(day=start_day_int)
                if today.month == 12:
                    end_date_obj = date(today.year + 1, 1, end_day_int)
                else:
                    try:
                        end_date_obj = date(today.year, today.month + 1, end_day_int)
                    except ValueError:
                        # Day doesn't exist in next month, use last day of next month
                        if today.month == 12:
                            _, next_last_day = calendar.monthrange(today.year + 1, 1)
                            end_date_obj = date(today.year + 1, 1, min(end_day_int, next_last_day))
                        else:
                            _, next_last_day = calendar.monthrange(today.year, today.month + 1)
                            end_date_obj = date(today.year, today.month + 1, min(end_day_int, next_last_day))
            else:
                # Same month range
                start_date_obj = today.replace(day=min(start_day_int, last_day))
                end_date_obj = today.replace(day=min(end_day_int, last_day))
            
            business_start_dt = datetime.combine(start_date_obj, time(21, 0, 0)) - timedelta(days=1)
            business_end_dt = datetime.combine(end_date_obj, time(20, 59, 59))
            
            start_sql_str = business_start_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_sql_str = business_end_dt.strftime('%Y-%m-%d %H:%M:%S')

        # Priority 4: Quick filters (current month based)
        elif filter_type == 'mid_monthly':
            start_date_obj = today.replace(day=1)
            end_date_obj = today.replace(day=15)
            
            business_start_dt = datetime.combine(start_date_obj, time(21, 0, 0)) - timedelta(days=1)
            business_end_dt = datetime.combine(end_date_obj, time(20, 59, 59))
            
            start_sql_str = business_start_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_sql_str = business_end_dt.strftime('%Y-%m-%d %H:%M:%S')

        elif filter_type == 'monthly':
            start_date_obj = today.replace(day=1)
            _, last_day = calendar.monthrange(today.year, today.month)
            end_date_obj = today.replace(day=last_day)
            
            business_start_dt = datetime.combine(start_date_obj, time(21, 0, 0)) - timedelta(days=1)
            business_end_dt = datetime.combine(end_date_obj, time(20, 59, 59))
            
            start_sql_str = business_start_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_sql_str = business_end_dt.strftime('%Y-%m-%d %H:%M:%S')

    except (ValueError, TypeError) as e:
        print(f"Filter parsing error: {e}")
        # Return None to indicate no filtering (show all data)
        return None, None
            
    return start_sql_str, end_sql_str

def get_user_filters_string():
    """Build a centralized WHERE clause string from user-driven filters."""
    conditions = []
    
    try:
        # 1. Add date filter condition
        start_str, end_str = get_date_range_strings()
        if start_str and end_str:
            conditions.append(f"order_date BETWEEN DATETIME('{start_str}') AND DATETIME('{end_str}')")
            
        # 2. Add branch filter condition
        branch = request.args.get('branch')
        if branch and branch.strip():
            # Escape single quotes in branch name
            safe_branch = branch.replace("'", "''")
            conditions.append(f"branch = '{safe_branch}'")
        
        # 3. Add employee filter condition
        employee = request.args.get('employee')
        if employee and employee.strip():
            safe_employee = employee.replace("'", "''")
            conditions.append(f"employee_name = '{safe_employee}'")
        
        # 4. Add product category filter condition
        category = request.args.get('category')
        if category and category.strip():
            safe_category = category.replace("'", "''")
            conditions.append(f"product_category LIKE '%{safe_category}%'")
        
        # 5. Add product filter condition
        product = request.args.get('product')
        if product and product.strip():
            safe_product = product.replace("'", "''")
            conditions.append(f"(product_name LIKE '%{safe_product}%' OR product_barcode = '{safe_product}')")
        
        # 6. Add minimum amount filter
        min_amount = request.args.get('min_amount')
        if min_amount and min_amount.strip():
            try:
                min_val = float(min_amount)
                conditions.append(f"subtotal_incl >= {min_val}")
            except ValueError:
                pass
        
        # 7. Add maximum amount filter
        max_amount = request.args.get('max_amount')
        if max_amount and max_amount.strip():
            try:
                max_val = float(max_amount)
                conditions.append(f"subtotal_incl <= {max_val}")
            except ValueError:
                pass

        # 8. Add purchase source filter (if applicable)
        purchase_source = request.args.get('purchase_source')
        if purchase_source and purchase_source.strip():
            safe_source = purchase_source.replace("'", "''")
            if purchase_source.lower() == 'online':
                conditions.append("branch = 'المتجر الإلكتروني'")
            elif purchase_source.lower() == 'store':
                conditions.append("branch != 'المتجر الإلكتروني'")
            else:
                conditions.append(f"purchase_source = '{safe_source}'")

    except Exception as e:
        print(f"Error building filter conditions: {e}")
        # In case of any error, return basic filter
        start_str, end_str = get_date_range_strings()
        if start_str and end_str:
            return f"WHERE order_date BETWEEN DATETIME('{start_str}') AND DATETIME('{end_str}')"
        return ""

    if conditions:
        return "WHERE " + " AND ".join(conditions)
    else:
        return ""
