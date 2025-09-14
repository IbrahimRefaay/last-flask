# cache.py
# Simple caching mechanism for database queries

import time
from functools import wraps
import json

# Simple in-memory cache
_cache = {}
DEFAULT_CACHE_TIME = 300  # 5 minutes

def cache_query(cache_time=DEFAULT_CACHE_TIME):
    """Cache decorator for database queries"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Check if cached result exists and is still valid
            if cache_key in _cache:
                cached_result, timestamp = _cache[cache_key]
                if time.time() - timestamp < cache_time:
                    print(f"✅ Cache hit for {func.__name__}")
                    return cached_result
            
            # Execute function and cache result
            print(f"🔄 Cache miss for {func.__name__}, executing query...")
            result = func(*args, **kwargs)
            _cache[cache_key] = (result, time.time())
            
            return result
        return wrapper
    return decorator

def clear_cache():
    """Clear all cached data"""
    global _cache
    _cache = {}
    print("🗑️ Cache cleared")

def get_cache_info():
    """Get cache statistics"""
    return {
        'cached_queries': len(_cache),
        'cache_keys': list(_cache.keys())
    }
