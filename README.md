# BigQuery Dashboard Flask Application

A complete Flask application for BigQuery data visualization and analytics dashboard.

## Project Structure

```
last-flask/
├── app.py                              # Main application entry point
├── config.py                           # Configuration settings
├── database.py                         # Database connection and utilities
├── utils.py                            # Helper functions and utilities
├── cache.py                            # Caching utilities
├── performance_monitor.py              # Performance monitoring
├── check_tables.py                     # Table validation utility
├── requirements.txt                    # Python dependencies
├── spartan-cedar-467808-p9-dda96452a885.json  # BigQuery credentials
├── b-01.png                            # Application logo/image
├── historical_inventory_activity.log   # Inventory activity logs
├── data-push/                          # Data processing directory
├── routes/                             # Application routes
│   ├── __init__.py                     # Routes package initialization
│   ├── dashboard_routes.py             # Main dashboard routes
│   ├── kpi_routes.py                   # KPI and metrics routes
│   ├── analytics_routes.py             # Analytics and reporting routes
│   ├── seller_routes.py                # Seller management routes
│   ├── returns_routes.py               # Returns and refunds routes
│   ├── inventory_routes.py             # Inventory management routes
│   ├── products_routes.py              # Current products routes
│   ├── products_routes_old.py          # Legacy products routes
│   └── products_routes_optimized.py    # Optimized products routes
├── templates/                          # HTML templates
│   ├── base.html                       # Base template layout
│   ├── index.html                      # Main dashboard template
│   ├── inventory_dashboard.html        # Inventory dashboard
│   ├── products.html                   # Current products page
│   ├── products_new.html               # New products interface
│   ├── products_old.html               # Legacy products page
│   ├── products_old2.html              # Alternative legacy products
│   └── products_optimized.html         # Optimized products page
├── static/                             # Static files
│   ├── css/                            # Stylesheets
│   ├── js/                             # JavaScript files
│   └── b-01.png                        # Static image assets
└── __pycache__/                        # Python cache files
```

## Key Components

### Core Files
- **app.py** - Flask application entry point and configuration
- **config.py** - Application configuration and environment settings
- **database.py** - BigQuery connection management and database utilities
- **utils.py** - Common utility functions and helpers
- **cache.py** - Caching implementation for performance optimization
- **performance_monitor.py** - Application performance monitoring

### Route Modules
- **dashboard_routes.py** - Main dashboard and overview pages
- **kpi_routes.py** - Key Performance Indicators and metrics endpoints
- **analytics_routes.py** - Advanced analytics and reporting features
- **seller_routes.py** - Seller management and performance tracking
- **returns_routes.py** - Returns processing and refund management
- **inventory_routes.py** - Inventory tracking and management
- **products_routes.py** - Product catalog and management (current version)

### Template System
- **base.html** - Common layout and navigation structure
- **index.html** - Main dashboard interface
- **inventory_dashboard.html** - Dedicated inventory management interface
- **products.html** - Product management interface
- Multiple product template variations for different use cases

## Setup Instructions

1. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **BigQuery Credentials**
   - Ensure the BigQuery service account JSON file `spartan-cedar-467808-p9-dda96452a885.json` is in the root directory
   - Update the `CREDENTIALS_FILE` path in `config.py` if needed

3. **Configuration**
   - Review and update `config.py` for any environment-specific settings
   - Update BigQuery project, dataset, and table IDs if different

4. **Table Validation**
   ```bash
   python check_tables.py
   ```

## Running the Application

1. **Development Mode**
   ```bash
   python app.py
   ```

2. **Production Mode**
   ```bash
   # Set environment variables
   export FLASK_APP=app.py
   export FLASK_ENV=production
   
   # Run with Gunicorn (recommended for production)
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

## API Endpoints

The application provides comprehensive API endpoints organized by module:

### Dashboard & KPI Routes
- `/api/data` - Main KPI data
- `/api/services-details` - Services details
- `/api/sales-details` - Sales details
- `/api/branch-sales` - Branch sales data
- `/api/branch-profits` - Branch profits data

### Analytics Routes
- `/api/top-categories` - Top categories by sales
- `/api/top-categories-by-profit` - Top categories by profit
- `/api/top-sellers` - Top sellers by branch
- `/api/top-10-sellers` - Top 10 sellers overall

### Product Routes
- `/api/top_products_by_sales_value` - Top products by sales value
- `/api/top_products_by_quantity` - Top products by quantity
- `/api/top_products_by_profit` - Top products by profit

### Returns & Inventory Routes
- `/api/top_categories_by_returns` - Top categories by returns
- `/api/top_sellers_by_returns` - Top sellers by returns
- `/api/inventory` - Inventory management endpoints

### Utility Routes
- `/api/get-branches` - Available branches
- `/api/performance` - Performance metrics

## Filter Parameters

All API endpoints support the following filter parameters:

- `single_day` - Filter by single day (1-31)
- `start_day` & `end_day` - Filter by day range
- `filter` - Quick filters (`mid_monthly`, `monthly`)
- `branch` - Filter by specific branch

## Features

- **Modular Architecture**: Clean separation of concerns with organized route modules
- **Performance Monitoring**: Built-in performance tracking and optimization
- **Caching System**: Redis-like caching for improved response times
- **Inventory Management**: Comprehensive inventory tracking and reporting
- **Product Management**: Multiple product interface variations
- **Blueprint-based Routing**: Scalable route organization using Flask blueprints
- **Centralized Configuration**: Easy configuration management
- **Error Handling**: Comprehensive error handling and logging
- **Filter System**: Flexible filtering system for all endpoints
- **Arabic Support**: Full RTL support for Arabic interface
- **Responsive Design**: Mobile-friendly dashboard interface

## Business Logic

The application implements specific business day logic:
- Business day starts at 21:00 on the previous calendar day
- Business day ends at 20:59 on the current day
- This logic is applied consistently across all date filters

## Development Notes

- The application uses multiple route modules for better maintainability
- Performance monitoring tracks response times and query optimization
- Caching system reduces database load and improves response times
- Multiple product template versions allow for A/B testing and gradual rollouts
- All database queries use parameterized queries for security
- BigQuery client is initialized once and reused across requests
- Error handling includes both console logging and user-friendly error messages

## Troubleshooting

1. **BigQuery Connection Issues**
   - Verify the credentials file exists and is valid
   - Check the project ID, dataset ID, and table ID in the configuration
   - Ensure the service account has proper BigQuery permissions
   - Run `python check_tables.py` to validate table access

2. **Import Errors**
   - Make sure all required packages are installed: `pip install -r requirements.txt`
   - Verify Python version compatibility (Python 3.7+)

3. **Template Not Found**
   - Ensure the `templates/` directory exists
   - Verify template files are in the templates directory
   - Check template inheritance in `base.html`

4. **Performance Issues**
   - Check `performance_monitor.py` logs for slow queries
   - Enable caching in `cache.py` for frequently accessed data
   - Review `historical_inventory_activity.log` for inventory bottlenecks

## Security Considerations

- Never commit the BigQuery credentials file to version control
- Use environment variables for sensitive configuration in production
- Implement proper authentication and authorization for production use
- Validate and sanitize all user inputs
- Monitor performance logs for potential security issues
