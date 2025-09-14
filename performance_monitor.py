# performance_monitor.py
# Performance monitoring utilities for the Flask application

import time
import functools
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

# Thread-safe storage for performance metrics
metrics_lock = threading.Lock()
performance_metrics = defaultdict(lambda: {
    'call_count': 0,
    'total_time': 0,
    'avg_time': 0,
    'min_time': float('inf'),
    'max_time': 0,
    'recent_calls': deque(maxlen=100),  # Store last 100 calls
    'errors': 0
})

def performance_monitor(operation_name):
    """
    Decorator to monitor the performance of functions.
    
    Args:
        operation_name (str): Name to identify the operation in metrics
    
    Returns:
        decorator: Function decorator that measures execution time
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error_occurred = False
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error_occurred = True
                raise e
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Update metrics in a thread-safe manner
                with metrics_lock:
                    metrics = performance_metrics[operation_name]
                    metrics['call_count'] += 1
                    metrics['total_time'] += execution_time
                    metrics['avg_time'] = metrics['total_time'] / metrics['call_count']
                    metrics['min_time'] = min(metrics['min_time'], execution_time)
                    metrics['max_time'] = max(metrics['max_time'], execution_time)
                    
                    # Store recent call info
                    call_info = {
                        'timestamp': datetime.now(),
                        'execution_time': execution_time,
                        'error': error_occurred
                    }
                    metrics['recent_calls'].append(call_info)
                    
                    if error_occurred:
                        metrics['errors'] += 1
                
                # Log slow operations (> 5 seconds)
                if execution_time > 5.0:
                    print(f"⚠️  SLOW OPERATION: {operation_name} took {execution_time:.2f}s")
        
        return wrapper
    return decorator

def get_performance_report():
    """
    Get a comprehensive performance report of all monitored operations.
    
    Returns:
        dict: Performance metrics for all operations
    """
    with metrics_lock:
        report = {}
        
        for operation_name, metrics in performance_metrics.items():
            # Calculate recent performance (last 10 calls)
            recent_calls = list(metrics['recent_calls'])[-10:]
            recent_avg = 0
            recent_errors = 0
            
            if recent_calls:
                recent_times = [call['execution_time'] for call in recent_calls]
                recent_avg = sum(recent_times) / len(recent_times)
                recent_errors = sum(1 for call in recent_calls if call['error'])
            
            # Calculate calls per minute (last hour)
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            recent_calls_last_hour = [
                call for call in metrics['recent_calls'] 
                if call['timestamp'] > hour_ago
            ]
            calls_per_minute = len(recent_calls_last_hour) / 60 if recent_calls_last_hour else 0
            
            report[operation_name] = {
                'total_calls': metrics['call_count'],
                'total_time': round(metrics['total_time'], 2),
                'avg_time': round(metrics['avg_time'], 4),
                'min_time': round(metrics['min_time'], 4) if metrics['min_time'] != float('inf') else 0,
                'max_time': round(metrics['max_time'], 4),
                'recent_avg_time': round(recent_avg, 4),
                'total_errors': metrics['errors'],
                'recent_errors': recent_errors,
                'calls_per_minute': round(calls_per_minute, 2),
                'error_rate': round((metrics['errors'] / metrics['call_count'] * 100), 2) if metrics['call_count'] > 0 else 0
            }
        
        return report

def clear_metrics():
    """
    Clear all performance metrics.
    """
    with metrics_lock:
        performance_metrics.clear()
    print("✅ Performance metrics cleared")

def get_slow_operations(threshold=2.0):
    """
    Get operations that are running slower than the threshold.
    
    Args:
        threshold (float): Time threshold in seconds
    
    Returns:
        list: List of operations with recent slow calls
    """
    with metrics_lock:
        slow_operations = []
        
        for operation_name, metrics in performance_metrics.items():
            # Check recent calls for slow operations
            recent_calls = list(metrics['recent_calls'])[-10:]
            slow_calls = [call for call in recent_calls if call['execution_time'] > threshold]
            
            if slow_calls:
                avg_slow_time = sum(call['execution_time'] for call in slow_calls) / len(slow_calls)
                slow_operations.append({
                    'operation': operation_name,
                    'slow_calls_count': len(slow_calls),
                    'avg_slow_time': round(avg_slow_time, 4),
                    'recent_calls_count': len(recent_calls)
                })
        
        return sorted(slow_operations, key=lambda x: x['avg_slow_time'], reverse=True)

def get_error_summary():
    """
    Get a summary of operations with errors.
    
    Returns:
        list: List of operations with error information
    """
    with metrics_lock:
        error_summary = []
        
        for operation_name, metrics in performance_metrics.items():
            if metrics['errors'] > 0:
                error_rate = (metrics['errors'] / metrics['call_count'] * 100) if metrics['call_count'] > 0 else 0
                
                # Check recent errors
                recent_calls = list(metrics['recent_calls'])[-20:]
                recent_errors = sum(1 for call in recent_calls if call['error'])
                
                error_summary.append({
                    'operation': operation_name,
                    'total_errors': metrics['errors'],
                    'total_calls': metrics['call_count'],
                    'error_rate': round(error_rate, 2),
                    'recent_errors': recent_errors,
                    'recent_calls': len(recent_calls)
                })
        
        return sorted(error_summary, key=lambda x: x['error_rate'], reverse=True)

# Initialize monitoring
print("✅ Performance monitor initialized")
