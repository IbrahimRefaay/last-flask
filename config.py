# config.py
# Configuration settings for the Flask application

import os

class Config:
    """Application configuration class."""
    
    # BigQuery Configuration
    CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spartan-cedar-467808-p9-dda96452a885.json")
    GOOGLE_APPLICATION_CREDENTIALS = CREDENTIALS_FILE  # Add this attribute
    DATASET_ID = "Orders"
    TABLE_ID = "pos_order_lines"
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    DEBUG = True
    
    # Other configurations can be added here as needed
