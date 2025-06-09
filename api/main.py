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
from crud import get_db_connection, create_user, get_user_by_email, connect_to_db, close_db_connection
from security import get_password_hash
from dependencies import redis_dependency, db_dependency

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

# Application startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application resources on startup."""
    try:
        logger.info("Starting GPU Yield Calculator API...")
        
        # Initialize database connection pool
        await connect_to_db()
        logger.info("Database connection pool initialized")
        
        # Additional startup tasks can be added here
        logger.info("API startup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up application resources on shutdown."""
    try:
        logger.info("Shutting down GPU Yield Calculator API...")
        
        # Close database connection pool
        await close_db_connection()
        logger.info("Database connection pool closed")
        
        # Additional cleanup tasks can be added here
        logger.info("API shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")

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
# def redis_dependency():
#     """Dependency to inject Redis connection into endpoints."""
#     connection = get_redis_connection()
#     if connection is None:
#         logger.error("Redis service unavailable")
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="Redis service is unavailable"
#         )
#     return connection

# Updated database dependency to work with asyncpg generator
# async def db_dependency():
#     """Dependency to inject database connection into endpoints."""
#     try:
#         async for connection in get_db_connection():
#             yield connection
#     except Exception as e:
#         logger.error(f"Database connection error: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="Database service is unavailable"
#         )

# API Endpoints
@app.get("/health", response_model=HealthCheck, summary="Health Check Endpoint")
async def health_check(redis_conn: redis.Redis = Depends(redis_dependency)):
    """Returns the health status of the API and its dependencies."""
    try:
        # Test Redis connection
        redis_conn.ping()
        
        # Test database connection
        from crud import check_database_health
        db_healthy = await check_database_health()
        
        if not db_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable"
            )
        
        return HealthCheck(
            status="ok",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="1.0.0"
        )
    except HTTPException:
        raise
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
    Includes X-Updated-At header with timestamp for freshness tracking.
    """
    cache_key = "cache:delta"
    cache_timestamp_key = "cache:delta:timestamp"
    
    # Check for cached result
    try:
        cached_result = redis_conn.get(cache_key)
        cached_timestamp = redis_conn.get(cache_timestamp_key)
        
        if cached_result:
            logger.info("Returning cached delta data")
            cached_data = json.loads(cached_result)
            
            # Create response with custom header
            return JSONResponse(
                content=cached_data,
                headers={
                    "X-Updated-At": cached_timestamp.decode() if cached_timestamp else str(int(time.time() * 1000)),
                    "Cache-Control": "public, max-age=30"
                }
            )
    except Exception as e:
        logger.warning(f"Error reading from cache: {e}")
    
    # Live logic: read from Redis stream
    try:
        # Get last 500 entries from the raw_prices stream for better data coverage
        stream_entries = redis_conn.xrevrange("raw_prices", count=500)
        
        if not stream_entries:
            logger.warning("No pricing data available in Redis stream")
            response_data = {
                "deltas": [],
                "total_count": 0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            return JSONResponse(
                content=response_data,
                headers={
                    "X-Updated-At": str(int(time.time() * 1000)),
                    "Cache-Control": "public, max-age=30"
                }
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
        
        # Get current timestamp
        current_timestamp = str(int(time.time() * 1000))
        
        # Cache the result for 30 seconds with timestamp
        try:
            cache_data = response_data.dict()
            redis_conn.setex(cache_key, 30, json.dumps(cache_data, default=str))
            redis_conn.setex(cache_timestamp_key, 30, current_timestamp)
            logger.info(f"Cached delta data with {len(deltas)} entries")
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
        
        # Return response with timestamp header
        return JSONResponse(
            content=cache_data,
            headers={
                "X-Updated-At": current_timestamp,
                "Cache-Control": "public, max-age=30"
            }
        )
        
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
async def signup(
    request: SignupRequest, 
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Handles user signup requests with database integration and job queuing.
    """
    try:
        logger.info(f"New signup request from: {request.email}")
        
        # Basic hCaptcha validation (in production, verify with hCaptcha service)
        if not request.hcaptcha_response or len(request.hcaptcha_response) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid captcha response"
            )
        
        # Check if email already exists in database
        existing_user = await get_user_by_email(conn, request.email)
        if existing_user:
            logger.warning(f"Signup attempt with existing email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Generate a temporary password (since this is signup without password)
        # In a real app, you might want to send a password setup email
        temp_password = f"temp_{int(time.time())}_{hash(request.email) % 10000}"
        
        # Hash the temporary password
        hashed_password = get_password_hash(temp_password)
        
        # Create user in database
        new_user = await create_user(
            conn=conn,
            email=request.email,
            username=None,  # No username provided in signup request
            hashed_password=hashed_password,
            gpu_models_interested=request.gpu_models_interested,
            min_profit_threshold=request.min_profit_threshold
        )
        
        user_id = str(new_user["id"])
        
        # Queue welcome email job
        welcome_job = AlertJob(
            job_type="send_welcome_email",
            email=request.email,
            user_id=user_id
        )
        
        try:
            redis_conn.xadd("alert_queue", welcome_job.dict())
            logger.info(f"Welcome email job queued for user: {request.email}")
        except Exception as e:
            logger.warning(f"Failed to queue welcome email for {request.email}: {e}")
            # Don't fail the signup if email queueing fails
        
        # Queue password setup email job
        password_setup_job = AlertJob(
            job_type="send_password_setup_email",
            email=request.email,
            user_id=user_id
        )
        
        try:
            redis_conn.xadd("alert_queue", password_setup_job.dict())
            logger.info(f"Password setup email job queued for user: {request.email}")
        except Exception as e:
            logger.warning(f"Failed to queue password setup email for {request.email}: {e}")
        
        logger.info(f"User {request.email} successfully registered with ID {user_id}")
        
        return SignupResponse(
            status="success",
            message="Signup successful! Check your email for account setup instructions.",
            user_id=user_id
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like validation errors)
        raise
    except ValueError as e:
        # Handle database constraint errors (like duplicate email)
        logger.error(f"Database constraint error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during signup"
        )

# Additional utility endpoints
@app.get("/stats", summary="Get API Statistics")
async def get_stats(
    redis_conn: redis.Redis = Depends(redis_dependency),
    conn = Depends(db_dependency)
):
    """Get basic API usage statistics."""
    try:
        # Get stream length
        stream_length = redis_conn.xlen("raw_prices")
        
        # Get actual user count from database
        from crud import get_user_count
        user_count = await get_user_count(conn)
        
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