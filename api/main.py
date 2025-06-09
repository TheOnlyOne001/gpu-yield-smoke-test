from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import redis
import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from utils.connections import init_sentry, get_redis_connection
from models import (
    HealthCheck, ROICalcRequest, ROICalcResponse, SignupRequest, SignupResponse,
    DeltaResponse, GPUPriceDelta, ErrorResponse, AlertJob
)
from routers import auth

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Sentry
init_sentry()

# Create FastAPI application instance
app = FastAPI(
    title="GPU Yield Calculator API",
    description="Real-time GPU rental price comparison and ROI calculation service",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# Include authentication router
app.include_router(auth.router)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure this properly for production
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error for {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            detail=str(exc.errors()),
            timestamp=datetime.now(timezone.utc).isoformat()
        ).dict()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error for {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            timestamp=datetime.now(timezone.utc).isoformat()
        ).dict()
    )

# Dependencies
def redis_dependency():
    """Dependency to inject Redis connection into endpoints."""
    connection = get_redis_connection()
    if connection is None:
        logger.error("Redis service unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service is unavailable"
        )
    return connection

# API Endpoints
@app.get("/health", response_model=HealthCheck, summary="Health Check Endpoint")
async def health_check(redis_conn: redis.Redis = Depends(redis_dependency)):
    """Returns the health status of the API and its dependencies."""
    try:
        # Test Redis connection
        redis_conn.ping()
        
        return HealthCheck(
            status="ok",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service dependencies unavailable"
        )

@app.get("/delta", response_model=DeltaResponse, summary="Get GPU Price Deltas")
async def get_delta(redis_conn: redis.Redis = Depends(redis_dependency)):
    """
    Returns the current best GPU prices from different cloud providers.
    Uses caching to improve performance and reduce API load.
    """
    cache_key = "cache:delta"
    
    # Check for cached result
    try:
        cached_result = redis_conn.get(cache_key)
        if cached_result:
            logger.info("Returning cached delta data")
            cached_data = json.loads(cached_result)
            return DeltaResponse(**cached_data)
    except Exception as e:
        logger.warning(f"Error reading from cache: {e}")
    
    # Live logic: read from Redis stream
    try:
        # Get last 500 entries from the raw_prices stream for better data coverage
        stream_entries = redis_conn.xrevrange("raw_prices", count=500)
        
        if not stream_entries:
            logger.warning("No pricing data available in Redis stream")
            return DeltaResponse(
                deltas=[],
                total_count=0,
                last_updated=datetime.now(timezone.utc).isoformat()
            )
        
        # Dictionary to track best offer per GPU model
        best_offers = {}
        
        # Process stream entries
        for entry_id, fields in stream_entries:
            try:
                gpu_model = fields.get('gpu_model')
                price_str = fields.get('price_usd_hr')
                cloud = fields.get('cloud')
                timestamp = fields.get('timestamp')
                
                if not all([gpu_model, price_str, cloud]):
                    continue
                
                price = float(price_str)
                
                # Skip unrealistic prices
                if price <= 0 or price > 50:  # Reasonable bounds
                    continue
                
                # Update if this is the highest price for this GPU model
                if (gpu_model not in best_offers or 
                    price > best_offers[gpu_model]['price_usd_hr']):
                    best_offers[gpu_model] = {
                        'gpu_model': gpu_model,
                        'best_source': cloud,
                        'price_usd_hr': price,
                        'last_updated': timestamp
                    }
            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing stream entry {entry_id}: {e}")
                continue
        
        # Convert to list of GPUPriceDelta objects
        deltas = [GPUPriceDelta(**offer) for offer in best_offers.values()]
        
        response_data = DeltaResponse(
            deltas=deltas,
            total_count=len(deltas),
            last_updated=datetime.now(timezone.utc).isoformat()
        )
        
        # Cache the result for 30 seconds
        try:
            cache_data = response_data.dict()
            redis_conn.setex(cache_key, 30, json.dumps(cache_data, default=str))
            logger.info(f"Cached delta data with {len(deltas)} entries")
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error reading from Redis stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving price data"
        )

@app.post("/roi", response_model=ROICalcResponse, summary="Calculate ROI")
async def calculate_roi(request: ROICalcRequest):
    """
    Calculates potential monthly profit based on GPU model and usage parameters.
    Includes enhanced calculations with daily profit and break-even analysis.
    """
    try:
        # Enhanced calculation logic
        # Base yield estimate (this should come from real market data)
        base_yield_per_hour = 0.15  # Base estimate in $/hr
        
        # GPU-specific multipliers (should be data-driven)
        gpu_multipliers = {
            "RTX 4090": 1.5,
            "RTX 4080": 1.2,
            "RTX 4070": 1.0,
            "A100": 3.0,
            "H100": 4.0,
            "V100": 2.0
        }
        
        # Get multiplier for specific GPU or use default
        gpu_multiplier = gpu_multipliers.get(request.gpu_model.strip(), 1.0)
        estimated_hourly_yield = base_yield_per_hour * gpu_multiplier
        
        # Calculate costs and profits
        daily_revenue = estimated_hourly_yield * request.hours_per_day
        daily_power_cost = request.power_cost_kwh * request.hours_per_day * 0.4  # Assuming 400W GPU
        daily_profit = daily_revenue - daily_power_cost
        monthly_profit = daily_profit * 30
        
        # Calculate break-even hours
        break_even_hours = None
        if estimated_hourly_yield > request.power_cost_kwh * 0.4:
            break_even_hours = 0  # Profitable from hour 1
        elif request.power_cost_kwh > 0:
            break_even_hours = request.power_cost_kwh * 0.4 / estimated_hourly_yield
        
        logger.info(f"ROI calculation for {request.gpu_model}: ${monthly_profit:.2f} monthly")
        
        return ROICalcResponse(
            potential_monthly_profit=round(monthly_profit, 2),
            daily_profit=round(daily_profit, 2),
            break_even_hours=round(break_even_hours, 2) if break_even_hours else None
        )
        
    except Exception as e:
        logger.error(f"Error in ROI calculation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating ROI"
        )

@app.post("/signup", response_model=SignupResponse, summary="User Signup")
async def signup(request: SignupRequest, redis_conn: redis.Redis = Depends(redis_dependency)):
    """
    Handles user signup requests with enhanced validation and job queuing.
    """
    try:
        logger.info(f"New signup request from: {request.email}")
        
        # Basic hCaptcha validation (in production, verify with hCaptcha service)
        if not request.hcaptcha_response or len(request.hcaptcha_response) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid captcha response"
            )
        
        # Check if email already exists (basic duplicate prevention)
        existing_user_key = f"user:email:{request.email}"
        if redis_conn.exists(existing_user_key):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Generate user ID and store user data
        user_id = f"user_{int(time.time())}_{hash(request.email) % 10000}"
        user_data = {
            "email": request.email,
            "signup_date": datetime.now(timezone.utc).isoformat(),
            "gpu_models_interested": json.dumps(request.gpu_models_interested),
            "min_profit_threshold": request.min_profit_threshold,
            "status": "active"
        }
        
        # Store user data
        redis_conn.hset(existing_user_key, mapping=user_data)
        redis_conn.expire(existing_user_key, 86400 * 365)  # 1 year expiration
        
        # Queue welcome email job
        welcome_job = AlertJob(
            job_type="send_welcome_email",
            email=request.email,
            user_id=user_id
        )
        
        redis_conn.xadd("alert_queue", welcome_job.dict())
        
        logger.info(f"User {request.email} successfully registered with ID {user_id}")
        
        return SignupResponse(
            status="success",
            message="Signup successful! Welcome email queued.",
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during signup"
        )

# Additional utility endpoints
@app.get("/stats", summary="Get API Statistics")
async def get_stats(redis_conn: redis.Redis = Depends(redis_dependency)):
    """Get basic API usage statistics."""
    try:
        # Get stream length
        stream_length = redis_conn.xlen("raw_prices")
        
        # Get number of registered users (approximate)
        user_keys = redis_conn.keys("user:email:*")
        user_count = len(user_keys)
        
        # Get cache hit ratio (if available)
        cache_info = redis_conn.info("stats")
        
        return {
            "total_price_records": stream_length,
            "registered_users": user_count,
            "cache_hits": cache_info.get("keyspace_hits", 0),
            "cache_misses": cache_info.get("keyspace_misses", 0),
            "uptime_seconds": cache_info.get("uptime_in_seconds", 0)
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving statistics"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)