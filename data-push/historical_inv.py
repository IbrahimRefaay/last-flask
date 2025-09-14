# historical_inventory_to_bigquery.py
# This script generates historical inventory snapshots for a given date range
# and uploads the data to a BigQuery table, preserving history.

import requests
import pandas as pd
import logging
from datetime import datetime, date, timedelta
from google.oauth2 import service_account
import pandas_gbq
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# --- 1. Odoo Connection Settings ---
ODOO_URL = "https://rahatystore.odoo.com"
ODOO_DB = "rahatystore-live-12723857"
ODOO_USERNAME = "Data.team@rahatystore.com"
ODOO_PASSWORD = "Rs.Data.team"

# --- 2. Report Configuration ---
# Set the date range for which you want to generate historical snapshots
START_DATE = date(2025, 8, 21)
END_DATE = date(2025, 8, 30)

# --- 3. Google BigQuery Settings ---
PROJECT_ID = "spartan-cedar-467808-p9" 
DATASET_ID = "Orders" 
TABLE_ID = "historical_inventory" # Final table for storing history
STAGING_TABLE_ID = "historical_inventory_staging"

# !! Path to your BigQuery JSON credentials file !!
CREDENTIALS_FILE_PATH = "spartan-cedar-467808-p9-dda96452a885.json" 

# --- 4. Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("historical_inventory_activity.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# --- Core Functions ---
DESTINATION_TABLE = f"{DATASET_ID}.{TABLE_ID}"
STAGING_DESTINATION_TABLE = f"{DATASET_ID}.{STAGING_TABLE_ID}"
session = requests.Session()

def get_odoo_session():
    """Authenticates with Odoo and returns a session object and user ID."""
    auth_url = f"{ODOO_URL}/web/session/authenticate"
    payload = {"jsonrpc": "2.0", "method": "call", "params": {"db": ODOO_DB, "login": ODOO_USERNAME, "password": ODOO_PASSWORD}}
    try:
        logging.info("Authenticating to Odoo...")
        response = session.post(auth_url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        uid = result.get('result', {}).get('uid')
        if uid:
            logging.info(f"✅ Odoo authentication successful. UID: {uid}")
            return session, uid
        else: 
            logging.error("Authentication failed. Check credentials.")
            return None, None
    except Exception as e:
        logging.error(f"Odoo connection error: {e}")
        return None, None

def call_odoo(session, uid, model, method, args=[], kwargs={}, timeout=600):
    """Makes a JSON-RPC call to Odoo."""
    rpc_url = f"{ODOO_URL}/web/dataset/call_kw"
    payload = {
        "jsonrpc": "2.0", "method": "call", 
        "params": {"model": model, "method": method, "args": args, "kwargs": kwargs}
    }
    try:
        response = session.post(rpc_url, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        if 'error' in result:
            logging.error(f"RPC Error on {model}.{method}: {result['error']['data']['message']}")
            return []
        return result.get('result', [])
    except Exception as e:
        logging.error(f"RPC call to {model}.{method} failed: {e}")
        return []

def get_inventory_snapshot(session, uid, target_date, all_product_ids):
    """Fetches a historical inventory snapshot for a list of products on a specific date."""
    target_datetime = datetime.combine(target_date, datetime.max.time())
    date_str = target_datetime.strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"📦 Fetching inventory snapshot for date: {target_date.strftime('%Y-%m-%d')}...")
    
    all_products_data = []
    batch_size = 1000 
    
    for i in range(0, len(all_product_ids), batch_size):
        batch_ids = all_product_ids[i:i + batch_size]
        logging.info(f"  -> Processing product batch {i//batch_size + 1} of {len(all_product_ids)//batch_size + 1}...")
        
        context_with_date = {'to_date': date_str}
        
        products_data = call_odoo(session, uid, "product.product", "read", 
                                  [batch_ids], 
                                  {"fields": ["display_name", "barcode", "qty_available", "outgoing_qty"], 
                                   "context": context_with_date})
        
        for product in products_data:
            on_hand = product.get('qty_available', 0)
            reserved = product.get('outgoing_qty', 0)
            
            all_products_data.append({
                'snapshot_date': target_date,
                'product_id': str(product['id']),
                'product_name': product['display_name'],
                'product_barcode': product.get('barcode', ''),
                'location_id': None,
                'location_name': 'All Locations',
                'on_hand_quantity': on_hand,
                'reserved_quantity': reserved,
                'available_quantity': on_hand - reserved
            })
            
    logging.info(f"✅ Snapshot for {target_date.strftime('%Y-%m-%d')} complete.")
    return all_products_data

def ensure_table_exists(client, dataset_id, table_id, schema):
    """Checks if a table exists, and creates it if it doesn't."""
    table_ref = client.dataset(dataset_id).table(table_id)
    try:
        client.get_table(table_ref)
        logging.info(f"Table {table_id} already exists.")
    except NotFound:
        logging.info(f"Table {table_id} not found. Creating it now...")
        table = bigquery.Table(table_ref, schema=schema)
        client.create_table(table)
        logging.info(f"Created table {table_id} in dataset {dataset_id}.")

def upload_df_to_bigquery(df, project_id, credentials_path):
    """Uploads data to staging, then rebuilds the final table to store history."""
    if df.empty:
        logging.warning("DataFrame is empty. Skipping BigQuery upload.")
        return
        
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    client = bigquery.Client(credentials=credentials, project=project_id)

    # Define the schema for our final table
    schema = [
        bigquery.SchemaField("snapshot_date", "DATE"),
        bigquery.SchemaField("product_id", "STRING"),
        bigquery.SchemaField("product_name", "STRING"),
        bigquery.SchemaField("product_barcode", "STRING"),
        bigquery.SchemaField("location_id", "STRING"),
        bigquery.SchemaField("location_name", "STRING"),
        bigquery.SchemaField("on_hand_quantity", "FLOAT"),
        bigquery.SchemaField("reserved_quantity", "FLOAT"),
        bigquery.SchemaField("available_quantity", "FLOAT"),
    ]
    ensure_table_exists(client, DATASET_ID, TABLE_ID, schema)
    
    logging.info(f"Uploading {len(df)} new rows to staging table: {STAGING_DESTINATION_TABLE}...")
    try:
        df.to_gbq(destination_table=STAGING_DESTINATION_TABLE, project_id=project_id, 
                  if_exists='replace', progress_bar=True, credentials=credentials)
        logging.info("✅ Data successfully uploaded to staging table.")
    except Exception as e:
        logging.error(f"An error occurred while uploading to the staging table: {e}")
        raise

    logging.info(f"Rebuilding final historical table {DESTINATION_TABLE}...")
    
    rebuild_query = f"""
        -- Select all historical data from the final table that is NOT in the new date range
        SELECT *
        FROM `{project_id}.{DESTINATION_TABLE}`
        WHERE snapshot_date NOT IN (SELECT DISTINCT snapshot_date FROM `{project_id}.{STAGING_DESTINATION_TABLE}`)
        
        UNION ALL
        
        -- Add all the new and updated data from the staging table
        SELECT *
        FROM `{project_id}.{STAGING_DESTINATION_TABLE}`
    """
    
    try:
        job_config = bigquery.QueryJobConfig(
            destination=f"{project_id}.{DESTINATION_TABLE}",
            write_disposition="WRITE_TRUNCATE",
        )
        query_job = client.query(rebuild_query, job_config=job_config)
        query_job.result()
        logging.info(f"✅ Rebuild successful. Final historical table is now up-to-date.")
    except Exception as e:
        logging.error(f"An error occurred during the table rebuild operation: {e}")
        raise

def main():
    session, uid = get_odoo_session()
    if not session: return

    logging.info("--- Generating Historical Inventory Snapshots ---")
    logging.info(f"--- Period: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')} ---")
    
    logging.info("Fetching list of all storable products...")
    all_product_ids = call_odoo(session, uid, "product.product", "search", [[('type', '=', 'product')]])
    if not all_product_ids:
        logging.error("Could not fetch any products to analyze. Exiting.")
        return
    logging.info(f"Found {len(all_product_ids)} products to process.")

    all_snapshots = []
    current_date = START_DATE
    while current_date <= END_DATE:
        daily_snapshot_data = get_inventory_snapshot(session, uid, current_date, all_product_ids)
        all_snapshots.extend(daily_snapshot_data)
        current_date += timedelta(days=1)

    if not all_snapshots:
        logging.warning("No data was generated for the entire period.")
        return

    final_df = pd.DataFrame(all_snapshots)
    final_df['snapshot_date'] = pd.to_datetime(final_df['snapshot_date']).dt.date
    
    final_df = final_df[[
        'snapshot_date', 'product_id', 'product_name', 'product_barcode',
        'location_id', 'location_name', 'on_hand_quantity', 'reserved_quantity',
        'available_quantity'
    ]]

    upload_df_to_bigquery(final_df, PROJECT_ID, CREDENTIALS_FILE_PATH)

if __name__ == "__main__":
    main()