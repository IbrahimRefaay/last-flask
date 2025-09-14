
# database.py
# Database connection and query utilities
from cache import cache_query
from google.cloud import bigquery
from google.oauth2 import service_account
from config import Config
from performance_monitor import performance_monitor

# Global variables for BigQuery client
client = None
PROJECT_ID = None

def init_bigquery_client():
    """Initialize the BigQuery client with credentials."""
    global client, PROJECT_ID
    
    try:
        # Load credentials from file
        credentials = service_account.Credentials.from_service_account_file(Config.GOOGLE_APPLICATION_CREDENTIALS)
        client = bigquery.Client(credentials=credentials, project=credentials.project_id)
        PROJECT_ID = credentials.project_id
        
        print(f"✅ BigQuery client initialized successfully for project: {PROJECT_ID}")
        return True
        
    except FileNotFoundError:
        print(f"❌ CRITICAL ERROR: The credentials file '{Config.GOOGLE_APPLICATION_CREDENTIALS}' was not found.")
        print("Ensure the file is in the correct directory and the filename is correct.")
        client = None
        return False
        
    except Exception as e:
        print(f"❌ An error occurred during BigQuery client initialization: {e}")
        client = None
        return False

@performance_monitor('bigquery_query')
def run_query(sql_query):
    """Execute a BigQuery query and return the results."""
    if not client:
        raise Exception("BigQuery client is not available. Check credential setup.")
    
    return client.query(sql_query).result()

def get_project_id():
    """Get the current project ID."""
    return PROJECT_ID

def get_dataset_id():
    """Get the dataset ID from config."""
    return Config.DATASET_ID

def get_table_id():
    """Get the table ID from config."""
    return Config.TABLE_ID


# --- PRODUCTS PAGE QUERIES ---
@cache_query(cache_time=300)  # Cache for 5 minutes (reduced for fresh data)
def get_top_10_products(date_filter='all'):
    """Get top 10 products by total sales from pos_order_lines, excluding خدمات."""
    # Build date filter condition
    date_condition = ""
    if date_filter == 'today':
        date_condition = "AND DATE(order_date) = CURRENT_DATE()"
    elif date_filter == 'yesterday':
        date_condition = "AND DATE(order_date) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)"
    elif date_filter == 'last_7_days':
        date_condition = "AND DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)"
    elif date_filter == 'last_30_days':
        date_condition = "AND DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)"
    elif date_filter == 'current_month':
        date_condition = "AND EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE()) AND EXTRACT(MONTH FROM order_date) = EXTRACT(MONTH FROM CURRENT_DATE())"
    
    sql = f'''
        SELECT 
            product_name, 
            product_barcode, 
            COUNT(*) as sales_count,
            SUM(quantity) as total_quantity,
            ROUND(SUM(subtotal_incl), 2) as total_sales_value,
            MIN(DATE(order_date)) as first_sale_date,
            MAX(DATE(order_date)) as last_sale_date
        FROM `{get_project_id()}.{get_dataset_id()}.pos_order_lines`
        WHERE product_name NOT LIKE '%خدمات%' 
        AND product_name NOT LIKE '%خصومات%'
        AND product_name NOT LIKE '%خدمة%'
        AND product_name NOT LIKE '%خصم%'
        AND product_barcode IS NOT NULL
        AND product_barcode != ''
        AND SPLIT(product_category, '/')[SAFE_OFFSET(0)] != 'خدمات'
        {date_condition}
        GROUP BY product_name, product_barcode
        ORDER BY total_sales_value DESC
        LIMIT 10
    '''
    return [dict(row) for row in run_query(sql)]

@cache_query(cache_time=300)  # Cache for 5 minutes (reduced for fresh data)
def get_top_10_products_by_category(date_filter='all'):
    """Get top 10 products by category, excluding خدمات."""
    # Build date filter condition
    date_condition = ""
    if date_filter == 'today':
        date_condition = "AND DATE(order_date) = CURRENT_DATE()"
    elif date_filter == 'yesterday':
        date_condition = "AND DATE(order_date) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)"
    elif date_filter == 'last_7_days':
        date_condition = "AND DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)"
    elif date_filter == 'last_30_days':
        date_condition = "AND DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)"
    elif date_filter == 'current_month':
        date_condition = "AND EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE()) AND EXTRACT(MONTH FROM order_date) = EXTRACT(MONTH FROM CURRENT_DATE())"
    
    sql = f'''
        SELECT 
            SPLIT(product_category, '/')[SAFE_OFFSET(0)] as main_category,
            product_name, 
            product_barcode, 
            COUNT(*) as sales_count,
            SUM(quantity) as total_quantity,
            ROUND(SUM(subtotal_incl), 2) as total_sales_value,
            MIN(DATE(order_date)) as first_sale_date,
            MAX(DATE(order_date)) as last_sale_date
        FROM `{get_project_id()}.{get_dataset_id()}.pos_order_lines`
        WHERE product_name NOT LIKE '%خدمات%' 
        AND product_name NOT LIKE '%خصومات%'
        AND product_name NOT LIKE '%خدمة%'
        AND product_name NOT LIKE '%خصم%'
        AND product_barcode IS NOT NULL
        AND product_barcode != ''
        AND SPLIT(product_category, '/')[SAFE_OFFSET(0)] != 'خدمات'
        {date_condition}
        GROUP BY main_category, product_name, product_barcode
        ORDER BY total_sales_value DESC
        LIMIT 10
    '''
    return [dict(row) for row in run_query(sql)]

@cache_query(cache_time=600)  # Cache for 10 minutes
def get_latest_inventory_date():
    """Get the latest snapshot date from inventory tables."""
    try:
        sql = f'''
            SELECT MAX(snapshot_date) as latest_date
            FROM `{get_project_id()}.{get_dataset_id()}.historical_inventory`
        '''
        result = list(run_query(sql))
        if result:
            return result[0]['latest_date']
    except Exception:
        pass
    
    try:
        sql = f'''
            SELECT MAX(snapshot_date) as latest_date
            FROM `{get_project_id()}.{get_dataset_id()}.inventory_levels_history`
        '''
        result = list(run_query(sql))
        if result:
            return result[0]['latest_date']
    except Exception:
        pass
    
    return None

@cache_query(cache_time=600)  # Cache for 10 minutes
def get_all_inventory_dates():
    """Get all available snapshot dates (latest first)."""
    sql = f'''
        SELECT DISTINCT snapshot_date
        FROM `{get_project_id()}.{get_dataset_id()}.historical_inventory`
        ORDER BY snapshot_date DESC
        LIMIT 60
    '''
    return [str(row['snapshot_date']) for row in run_query(sql)]

@cache_query(cache_time=300)  # Cache for 5 minutes
def get_products_info(barcodes, snapshot_date=None):
    """Get product info for a list of barcodes from stock_data table or latest inventory snapshot."""
    if not barcodes:
        return []
    
    # Limit to first 20 barcodes for performance
    barcodes = barcodes[:20]
    barcodes_str = ','.join([f'"{b}"' for b in barcodes])
    
    # If no snapshot_date specified, use latest available date
    if snapshot_date is None:
        snapshot_date = get_latest_inventory_date()
    
    # Try stock_data table first (current inventory)
    try:
        sql = f'''
            SELECT *,
                CURRENT_DATE() as snapshot_date
            FROM `{get_project_id()}.{get_dataset_id()}.stock_data`
            WHERE Barcode IN ({barcodes_str})
            LIMIT 50
        '''
        return [dict(row) for row in run_query(sql)]
    except Exception as e:
        print(f"Error querying stock_data: {e}")
        
    # Fallback: try historical_inventory for specific date
    try:
        date_condition = f"AND snapshot_date = '{snapshot_date}'" if snapshot_date else ""
        if not snapshot_date:
            date_condition = '''AND snapshot_date = (
                SELECT MAX(snapshot_date) 
                FROM `{get_project_id()}.{get_dataset_id()}.historical_inventory`
            )'''
        
        sql = f'''
            SELECT DISTINCT
                product_name,
                product_barcode,
                product_category,
                on_hand_quantity,
                reserved_quantity,
                available_quantity,
                snapshot_date
            FROM `{get_project_id()}.{get_dataset_id()}.historical_inventory`
            WHERE product_barcode IN ({barcodes_str})
            {date_condition}
            LIMIT 50
        '''
        return [dict(row) for row in run_query(sql)]
    except Exception as e:
        print(f"Error querying historical_inventory: {e}")
        return []

@cache_query(cache_time=900)  # Cache for 15 minutes
def get_products_stock_history(barcodes, days=30, end_date=None):
    """Get daily stock history for a list of barcodes from inventory_levels_history table."""
    if not barcodes:
        return []
    
    # Limit to first 5 barcodes for performance
    barcodes = barcodes[:5]
    barcodes_str = ','.join([f'"{b}"' for b in barcodes])
    
    # Build date filter - if end_date not specified, use latest date
    if end_date is None:
        end_date = get_latest_inventory_date()
    
    date_condition = f'''
        AND snapshot_date <= '{end_date}'
        AND snapshot_date >= DATE_SUB('{end_date}', INTERVAL {days} DAY)
    ''' if end_date else f'''
        AND snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
    '''
    
    # Try inventory_levels_history first
    try:
        sql = f'''
            SELECT snapshot_date, product_barcode, product_name, 
                   on_hand_quantity, reserved_quantity, available_quantity
            FROM `{get_project_id()}.{get_dataset_id()}.inventory_levels_history`
            WHERE product_barcode IN ({barcodes_str})
            {date_condition}
            ORDER BY snapshot_date ASC
            LIMIT 500
        '''
        return [dict(row) for row in run_query(sql)]
    except Exception as e:
        print(f"Error querying inventory_levels_history: {e}")
        
    # Fallback: try historical_inventory
    try:
        sql = f'''
            SELECT snapshot_date, product_barcode, product_name, 
                   on_hand_quantity, reserved_quantity, available_quantity
            FROM `{get_project_id()}.{get_dataset_id()}.historical_inventory`
            WHERE product_barcode IN ({barcodes_str})
            {date_condition}
            ORDER BY snapshot_date ASC
            LIMIT 500
        '''
        return [dict(row) for row in run_query(sql)]
    except Exception as e:
        print(f"Error querying historical_inventory: {e}")
        return []
