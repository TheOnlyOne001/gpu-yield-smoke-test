# performance_security.py
"""
Performance and Security enhancements for GPU Yield Calculator
"""

import asyncio
import aioredis
import time
import hashlib
import hmac
from functools import wraps
from typing import Dict, Any, Optional, Callable
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Advanced rate limiting with Redis backend"""
    
    def __init__(self, redis_client, default_limit: int = 60, window: int = 60):
        self.redis = redis_client
        self.default_limit = default_limit
        self.window = window
    
    async def is_allowed(self, key: str, limit: Optional[int] = None) -> bool:
        """Check if request is allowed under rate limit"""
        limit = limit or self.default_limit
        current_time = int(time.time())
        window_start = current_time - self.window
        
        # Use sliding window approach
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(f"rate_limit:{key}", 0, window_start)
        
        # Count current requests
        pipe.zcard(f"rate_limit:{key}")
        
        # Add current request
        pipe.zadd(f"rate_limit:{key}", {str(current_time): current_time})
        
        # Set expiration
        pipe.expire(f"rate_limit:{key}", self.window)
        
        results = await pipe.execute()
        current_requests = results[1]
        
        return current_requests < limit

def rate_limit(limit: int = 60, window: int = 60, key_func: Optional[Callable] = None):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args (assume first arg in FastAPI endpoints)
            request = args[0] if args and hasattr(args[0], 'client') else None
            
            if request:
                # Default key function uses client IP
                if key_func:
                    rate_key = key_func(request)
                else:
                    rate_key = get_client_ip(request)
                
                # Check rate limit (you'll need to inject rate limiter)
                # This is a simplified version - in practice you'd use dependency injection
                if hasattr(request.app.state, 'rate_limiter'):
                    if not await request.app.state.rate_limiter.is_allowed(rate_key, limit):
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Rate limit exceeded"
                        )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def get_client_ip(request: Request) -> str:
    """Extract client IP considering proxies"""
    # Check X-Forwarded-For header (common in load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"

class SecurityHeaders:
    """Add security headers to responses"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }

class DataValidator:
    """Enhanced data validation and sanitization"""
    
    @staticmethod
    def sanitize_gpu_model(gpu_model: str) -> str:
        """Sanitize GPU model input"""
        if not gpu_model:
            return ""
        
        # Remove potentially dangerous characters
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_.")
        sanitized = ''.join(c for c in gpu_model if c in safe_chars)
        
        # Limit length
        return sanitized[:50]
    
    @staticmethod
    def validate_email_domain(email: str) -> bool:
        """Validate email domain against common disposable email providers"""
        disposable_domains = {
            "10minutemail.com", "guerrillamail.com", "tempmail.org",
            "mailinator.com", "yopmail.com", "temp-mail.org"
        }
        
        domain = email.split("@")[-1].lower()
        return domain not in disposable_domains
    
    @staticmethod
    def validate_price_bounds(price: float) -> bool:
        """Validate price is within reasonable bounds"""
        return 0.001 <= price <= 100.0

class CacheManager:
    """Advanced caching with intelligent invalidation"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes
    
    async def get_or_set(
        self,
        key: str,
        factory_func: Callable,
        ttl: Optional[int] = None,
        force_refresh: bool = False
    ) -> Any:
        """Get from cache or set using factory function"""
        ttl = ttl or self.default_ttl
        
        if not force_refresh:
            cached_value = await self.redis.get(key)
            if cached_value:
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in cache for key: {key}")
        
        # Generate fresh value
        fresh_value = await factory_func()
        
        # Cache the result
        await self.redis.setex(key, ttl, json.dumps(fresh_value, default=str))
        
        return fresh_value
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def track_endpoint_performance(self, endpoint: str):
        """Decorator to track endpoint performance"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    status = "success"
                    return result
                except Exception as e:
                    status = "error"
                    raise
                finally:
                    duration = time.time() - start_time
                    self.record_metric(endpoint, duration, status)
            
            return wrapper
        return decorator
    
    def record_metric(self, endpoint: str, duration: float, status: str):
        """Record performance metric"""
        if endpoint not in self.metrics:
            self.metrics[endpoint] = {
                "total_requests": 0,
                "total_duration": 0,
                "error_count": 0,
                "avg_duration": 0
            }
        
        metric = self.metrics[endpoint]
        metric["total_requests"] += 1
        metric["total_duration"] += duration
        metric["avg_duration"] = metric["total_duration"] / metric["total_requests"]
        
        if status == "error":
            metric["error_count"] += 1
        
        # Log slow requests
        if duration > 5.0:  # 5 seconds
            logger.warning(f"Slow request: {endpoint} took {duration:.2f}s")

class DatabaseOptimizer:
    """Database query optimization utilities"""
    
    @staticmethod
    async def optimize_redis_stream(redis_client, stream_name: str, max_length: int = 10000):
        """Optimize Redis stream by trimming old entries"""
        try:
            # Get stream length
            length = await redis_client.xlen(stream_name)
            
            if length > max_length:
                # Trim to 80% of max length to avoid frequent trimming
                target_length = int(max_length * 0.8)
                await redis_client.xtrim(stream_name, maxlen=target_length, approximate=True)
                logger.info(f"Trimmed {stream_name} from {length} to ~{target_length} entries")
        
        except Exception as e:
            logger.error(f"Error optimizing stream {stream_name}: {e}")
    
    @staticmethod
    async def cleanup_expired_keys(redis_client, pattern: str, max_age_hours: int = 24):
        """Clean up expired keys based on pattern and age"""
        try:
            keys = await redis_client.keys(pattern)
            cleaned_count = 0
            
            for key in keys:
                ttl = await redis_client.ttl(key)
                if ttl == -1:  # No expiration set
                    # Check if key is old based on timestamp in data
                    key_data = await redis_client.get(key)
                    if key_data:
                        try:
                            data = json.loads(key_data)
                            if 'timestamp' in data:
                                age_hours = (time.time() - data['timestamp']) / 3600
                                if age_hours > max_age_hours:
                                    await redis_client.delete(key)
                                    cleaned_count += 1
                        except json.JSONDecodeError:
                            continue
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired keys")
        
        except Exception as e:
            logger.error(f"Error cleaning up keys: {e}")

# Security middleware for FastAPI
async def security_middleware(request: Request, call_next):
    """Add security headers and basic security checks"""
    # Basic security checks
    user_agent = request.headers.get("User-Agent", "")
    if not user_agent or len(user_agent) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing User-Agent"
        )
    
    # Process request
    response = await call_next(request)
    
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    return response

# API Key validation for premium features
class APIKeyAuth:
    """API Key authentication for premium endpoints"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return user info"""
        if not api_key:
            return None
        
        # Hash the API key for lookup
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Look up in Redis
        user_data = await self.redis.get(f"api_key:{key_hash}")
        if user_data:
            try:
                return json.loads(user_data)
            except json.JSONDecodeError:
                return None
        
        return None

# Async utilities for better performance
class AsyncUtils:
    """Utilities for async operations"""
    
    @staticmethod
    async def gather_with_timeout(tasks, timeout: float = 30.0):
        """Run multiple async tasks with timeout"""
        try:
            return await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Tasks timed out after {timeout} seconds")
            return [None] * len(tasks)
    
    @staticmethod
    async def retry_with_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0
    ):
        """Retry function with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                delay = base_delay * (backoff_factor ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)

# Export key classes and functions
__all__ = [
    'RateLimiter', 'rate_limit', 'SecurityHeaders', 'DataValidator',
    'CacheManager', 'PerformanceMonitor', 'DatabaseOptimizer',
    'security_middleware', 'APIKeyAuth', 'AsyncUtils'
]