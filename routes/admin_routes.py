# routes/admin_routes.py
# Admin routes for system management and ETL triggers

from flask import Blueprint, jsonify, request
import requests
import os
from performance_monitor import performance_monitor

admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/api/trigger-update", methods=['POST'])
@performance_monitor('trigger_etl')
def trigger_etl_update():
    """
    Secure server-side proxy to trigger GitHub Actions ETL workflow.
    This prevents exposing sensitive credentials to the browser.
    """
    try:
        # Get GitHub credentials from environment variables
        github_token = os.environ.get('GITHUB_TOKEN')
        github_user = os.environ.get('GITHUB_USER', 'IbrahimRefaay')
        github_repo = os.environ.get('GITHUB_REPO', 'last-flask')
        
        if not github_token:
            return jsonify({
                'status': 'error',
                'message': 'GitHub token not configured. Please set GITHUB_TOKEN environment variable.'
            }), 500
        
        # GitHub API endpoint for repository dispatch
        api_url = f"https://api.github.com/repos/{github_user}/{github_repo}/dispatches"
        
        # Headers for GitHub API
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        # Payload to trigger the specific workflow
        payload = {
            'event_type': 'trigger-etl',
            'client_payload': {
                'triggered_by': 'web_interface',
                'timestamp': str(request.headers.get('User-Agent', 'Unknown')),
                'source': 'flask_admin'
            }
        }
        
        # Make the request to GitHub API
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 204:
            return jsonify({
                'status': 'success',
                'message': 'تم تشغيل عملية تحديث البيانات بنجاح! ستكون البيانات الجديدة متاحة خلال 5-10 دقائق.',
                'workflow_triggered': True
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'فشل في تشغيل التحديث. كود الخطأ: {response.status_code}',
                'github_response': response.text,
                'workflow_triggered': False
            }), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({
            'status': 'error',
            'message': 'انتهت مهلة الاتصال مع GitHub. يرجى المحاولة مرة أخرى.',
            'workflow_triggered': False
        }), 408
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': f'خطأ في الاتصال: {str(e)}',
            'workflow_triggered': False
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'خطأ غير متوقع: {str(e)}',
            'workflow_triggered': False
        }), 500

@admin_bp.route("/api/system-status")
@performance_monitor('system_status')
def system_status():
    """
    Get system status and configuration info for admin dashboard.
    """
    try:
        # Check GitHub token availability
        github_token_configured = bool(os.environ.get('GITHUB_TOKEN'))
        github_user = os.environ.get('GITHUB_USER', 'Not configured')
        github_repo = os.environ.get('GITHUB_REPO', 'Not configured')
        
        # Get performance metrics
        from performance_monitor import get_performance_report
        perf_metrics = get_performance_report()
        
        return jsonify({
            'status': 'success',
            'system_info': {
                'github_integration': {
                    'token_configured': github_token_configured,
                    'user': github_user,
                    'repository': github_repo
                },
                'performance_metrics': perf_metrics,
                'environment': {
                    'python_version': os.sys.version,
                    'flask_env': os.environ.get('FLASK_ENV', 'production')
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route("/api/clear-all-cache", methods=['POST'])
@performance_monitor('clear_all_cache')
def clear_all_cache():
    """
    Clear all application caches.
    """
    try:
        from cache import clear_cache
        from performance_monitor import clear_metrics
        
        # Clear application cache
        clear_cache()
        
        # Clear performance metrics
        clear_metrics()
        
        return jsonify({
            'status': 'success',
            'message': 'تم مسح جميع الذاكرة المؤقتة بنجاح!'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'خطأ في مسح الذاكرة المؤقتة: {str(e)}'
        }), 500
