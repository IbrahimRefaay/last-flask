# inventory_etl.py
# This script fetches the latest inventory snapshot from Odoo and uploads it to BigQuery.

import requests
import pandas as pd
import logging
from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud.exceptions import NotFound

# --- Odoo Connection Settings ---
ODOO_URL = "https://rahatystore.odoo.com"
ODOO_DB = "rahatystore-live-12723857"
ODOO_USERNAME = "Data.team@rahatystore.com"
ODOO_PASSWORD = "Rs.Data.team"

# --- BigQuery Settings ---
PROJECT_ID = "spartan-cedar-467808-p9"
DATASET_ID = "Orders"
STOCK_TABLE = "stock_data"
CREDENTIALS_FILE_PATH = "spartan-cedar-467808-p9-dda96452a885.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_odoo_session(url, db, username, password):
    auth_url = f"{url}/web/session/authenticate"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": db,
            "login": username,
            "password": password
        }
    }
    session = requests.Session()
    try:
        response = session.post(auth_url, json=payload, timeout=30)
        response.raise_for_status()
        if response.json().get("result", {}).get("uid"):
            logging.info("✅ Authentication successful.")
            return session
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Authentication request failed: {e}")
        return None
    logging.error("❌ Authentication failed. Check credentials or Odoo server status.")
    return None

def call_odoo_rpc(session, url, model, method, params):
    rpc_url = f"{url}/web/dataset/call_kw"
    rpc_params = {
        'model': model,
        'method': method,
        'args': params.get('args', []),
        'kwargs': params.get('kwargs', {})
    }
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": rpc_params
    }
    try:
        response = session.post(rpc_url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        if result.get('error'):
            error_details = result['error']
            logging.error(f"❌ Odoo RPC Error: {error_details.get('message')}")
            if 'data' in error_details and 'debug' in error_details['data']:
                logging.error(f"    - Debug Info:\n{error_details['data']['debug']}")
            else:
                logging.error(f"    - Data: {error_details.get('data')}")
            return None
        return result.get('result')
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ RPC call failed: {e}")
        return None

def ensure_stock_table_exists(client, dataset_id, table_id):
    table_ref = client.dataset(dataset_id).table(table_id)
    try:
        client.get_table(table_ref)
        logging.info(f"Table {table_id} already exists.")
    except NotFound:
        schema = [
            bigquery.SchemaField("Product Name", "STRING"),
            bigquery.SchemaField("Barcode", "STRING"),
            bigquery.SchemaField("Category", "STRING"),
            bigquery.SchemaField("Qty On Hand", "FLOAT"),
            bigquery.SchemaField("Reserved Qty", "FLOAT"),
            bigquery.SchemaField("Available Qty", "FLOAT"),
            bigquery.SchemaField("Unit Cost", "FLOAT"),
            bigquery.SchemaField("Total Cost", "FLOAT"),
        ]
        table = bigquery.Table(table_ref, schema=schema)
        client.create_table(table)
        logging.info(f"Created table {table_id} in dataset {dataset_id}.")

def main():
    logging.info("Connecting to Odoo...")
    session = get_odoo_session(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    if not session:
        return

    logging.info("📦 Fetching product data...")
    products = call_odoo_rpc(session, ODOO_URL, "product.product", "search_read", {
        "args": [[("type", "=", "product")]],
        "kwargs": {
            "fields": ["id", "display_name", "barcode", "product_tmpl_id", "standard_price", "categ_id"]
        }
    })
    if not products:
        logging.error("No products found or an error occurred. Exiting.")
        return

    products_df = pd.DataFrame(products)
    if products_df.empty:
        logging.error("❌ Product data is empty.")
        return

    products_df["product_id"] = products_df["id"]
    products_df["category"] = products_df["categ_id"].apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else "")
    logging.info(f"✅ Loaded {len(products_df)} products.")

    logging.info("📊 Fetching stock quantities...")
    stock_quants = call_odoo_rpc(session, ODOO_URL, "stock.quant", "search_read", {
        "args": [[("location_id.usage", "=", "internal")]],
        "kwargs": {
            "fields": ["product_id", "quantity", "reserved_quantity"]
        }
    })
    if stock_quants is None:
        logging.error("Could not fetch stock quantities. Exiting.")
        return

    quant_df = pd.DataFrame(stock_quants)
    if quant_df.empty or "product_id" not in quant_df.columns:
        logging.warning("⚠️ No stock quant data found.")
        stock_summary = pd.DataFrame(columns=['product_id', 'on_hand_quantity', 'reserved_quantity', 'available_quantity'])
    else:
        quant_df["product_id"] = quant_df["product_id"].apply(lambda x: x[0] if isinstance(x, list) else x)
        stock_summary = quant_df.groupby("product_id").agg({
            "quantity": "sum",
            "reserved_quantity": "sum"
        }).reset_index()
        stock_summary.rename(columns={"quantity": "on_hand_quantity"}, inplace=True)
        stock_summary["available_quantity"] = stock_summary["on_hand_quantity"] - stock_summary["reserved_quantity"]

    logging.info("📎 Merging data...")
    df = pd.merge(products_df, stock_summary, on="product_id", how="left")

    # Fill missing values for products that may not have stock records
    df["on_hand_quantity"].fillna(0, inplace=True)
    df["reserved_quantity"].fillna(0, inplace=True)
    df["available_quantity"].fillna(0, inplace=True)
    df["standard_price"].fillna(0, inplace=True)
    df["total_cost"] = df["on_hand_quantity"] * df["standard_price"]

    # Define the final structure of the stock table
    final_df = df[[
        "display_name", "barcode", "category",
        "on_hand_quantity", "reserved_quantity", "available_quantity",
        "standard_price", "total_cost"
    ]]
    final_df.columns = [
        "Product Name", "Barcode", "Category",
        "Qty On Hand", "Reserved Qty", "Available Qty",
        "Unit Cost", "Total Cost"
    ]

    # Upload to BigQuery
    logging.info(f"📤 Uploading to BigQuery table: {DATASET_ID}.{STOCK_TABLE}")
    try:
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE_PATH)
        bq_client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
        ensure_stock_table_exists(bq_client, DATASET_ID, STOCK_TABLE)
        final_df.to_gbq(destination_table=f"{DATASET_ID}.{STOCK_TABLE}", project_id=PROJECT_ID,
                        if_exists='replace', credentials=credentials)
        logging.info(f"✅ Data uploaded to BigQuery table: {DATASET_ID}.{STOCK_TABLE}")
    except Exception as e:
        logging.error(f"❌ Failed to upload to BigQuery: {e}")

if __name__ == "__main__":
    main()