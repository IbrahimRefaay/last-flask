# inventory_etl.py
# This script fetches a daily snapshot of inventory levels from Odoo
# and uploads it to a BigQuery table, preserving the history of each day.

import requests
import json
import logging
import pandas as pd
from google.oauth2 import service_account
import pandas_gbq
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from datetime import datetime

# ==============================================================================
# الإعدادات الرئيسية
# ==============================================================================

# --- Odoo Connection Settings ---
ODOO_URL = "https://rahatystore.odoo.com"
ODOO_DB = "rahatystore-live-12723857"
ODOO_USERNAME = "Data.team@rahatystore.com"
ODOO_PASSWORD = "Rs.Data.team"

# --- Google BigQuery Settings ---
PROJECT_ID = "spartan-cedar-467808-p9" 
DATASET_ID = "Orders" 
TABLE_ID = "inventory_levels_history" # Table for storing daily snapshots
STAGING_TABLE_ID = "inventory_levels_staging"

# !! Path to your BigQuery JSON credentials file !!
CREDENTIALS_FILE_PATH = "spartan-cedar-467808-p9-dda96452a885.json" 

# ==============================================================================
# إعدادات إضافية (لا تحتاج للتعديل)
# ==============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DESTINATION_TABLE = f"{DATASET_ID}.{TABLE_ID}"
STAGING_DESTINATION_TABLE = f"{DATASET_ID}.{STAGING_TABLE_ID}"
session = requests.Session()

# ==============================================================================
# الدوال الأساسية
# ==============================================================================

def odoo_call(endpoint, params):
    """A helper function to make JSON-RPC calls to Odoo."""
    url = f"{ODOO_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    payload = {"jsonrpc": "2.0", "method": "call", "params": params}
    try:
        response = session.post(url, headers=headers, data=json.dumps(payload), timeout=120)
        response.raise_for_status()
        result = response.json()
        if 'error' in result:
            logging.error(f"Odoo API Error: {result['error']['data']['message']}")
            return None
        return result.get('result')
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request Error: {e}")
        return None

def get_inventory_data_to_dataframe():
    """Fetches and merges inventory data from Odoo."""
    logging.info("Authenticating...")
    auth_params = {"db": ODOO_DB, "login": ODOO_USERNAME, "password": ODOO_PASSWORD}
    if not odoo_call("/web/session/authenticate", auth_params):
        raise Exception("Authentication failed.")
    logging.info("✅ Authentication successful!")

    logging.info("Step 1: Fetching all stock quants...")
    quant_params = {
        "model": "stock.quant", "method": "search_read", "args": [],
        "kwargs": {
            "domain": [('location_id.usage', '=', 'internal')],
            "fields": ['product_id', 'location_id', 'quantity', 'reserved_quantity']
        }
    }
    quants = odoo_call("/web/dataset/call_kw", quant_params)
    if not quants:
        logging.warning("No stock quants found.")
        return pd.DataFrame()
    logging.info(f"Found {len(quants)} stock records.")
    
    product_ids = list(set([q['product_id'][0] for q in quants if q.get('product_id')]))
    location_ids = list(set([q['location_id'][0] for q in quants if q.get('location_id')]))
    
    logging.info(f"Step 2: Fetching details for {len(product_ids)} products and {len(location_ids)} locations...")
    product_params = {
        "model": "product.product", "method": "read", "args": [product_ids],
        "kwargs": {"fields": ['display_name', 'barcode']}
    }
    products = odoo_call("/web/dataset/call_kw", product_params) or []
    
    location_params = {
        "model": "stock.location", "method": "read", "args": [list(location_ids)],
        "kwargs": {"fields": ['complete_name']}
    }
    locations = odoo_call("/web/dataset/call_kw", location_params) or []

    logging.info("Step 3: Building the final DataFrame...")
    products_by_id = {p['id']: p for p in products}
    locations_by_id = {l['id']: l for l in locations}

    final_rows = []
    # Use DATE() for the snapshot to easily join with sales data later
    snapshot_date = datetime.utcnow().date()
    for quant in quants:
        product_info = products_by_id.get(quant['product_id'][0], {})
        location_info = locations_by_id.get(quant['location_id'][0], {})
        
        on_hand = quant.get('quantity', 0)
        reserved = quant.get('reserved_quantity', 0)
        available = on_hand - reserved
        
        row = {
            'snapshot_date': snapshot_date,
            'product_id': str(quant['product_id'][0]),
            'product_name': product_info.get('display_name'),
            'product_barcode': product_info.get('barcode'),
            'location_id': str(quant['location_id'][0]),
            'location_name': location_info.get('complete_name'),
            'on_hand_quantity': on_hand,
            'reserved_quantity': reserved,
            'available_quantity': available
        }
        final_rows.append(row)
    
    df = pd.DataFrame(final_rows)
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date']).dt.date
    logging.info(f"✅ Final DataFrame created successfully with {len(df)} rows.")
    return df

def ensure_inventory_history_table_exists(client, dataset_id, table_id):
    table_ref = client.dataset(dataset_id).table(table_id)
    try:
        client.get_table(table_ref)
        logging.info(f"Table {table_id} already exists.")
    except NotFound:
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
    # Ensure the history table exists before rebuild
    ensure_inventory_history_table_exists(client, DATASET_ID, TABLE_ID)
    
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
        -- Select all historical data from previous days (using today's date)
        SELECT *
        FROM `{project_id}.{DESTINATION_TABLE}`
        WHERE snapshot_date != CURRENT_DATE('UTC')
        
        UNION ALL
        
        -- Add the new, updated snapshot for today from the staging table
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

# --- Main execution block ---
if __name__ == "__main__":
    logging.info("--- Starting Odoo Inventory History to BigQuery ETL Process ---")
    try:
        final_df = get_inventory_data_to_dataframe()
        if final_df is not None and not final_df.empty:
            upload_df_to_bigquery(final_df, PROJECT_ID, CREDENTIALS_FILE_PATH)
        logging.info("--- ETL Process Completed Successfully ---")
    except Exception as e:
        logging.critical(f"--- ETL Process Failed ---", exc_info=True)
