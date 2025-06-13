import logging
import os
import time
import json
import redis
import asyncpg

# Initialize logger early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timezone, timedelta
from typing import Optional

# Import utilities and connections
try:
    from utils.connections import init_sentry, get_redis_connection
except ImportError:
    logger.warning("utils.connections not found, using fallbacks")
    
    def init_sentry():
        pass
    
    def get_redis_connection():
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        return redis.from_url(redis_url, decode_responses=True)

# Import models
from models import (
    HealthCheck, ROICalcRequest, ROICalcResponse, SignupRequest, SignupResponse,
    DeltaResponse, GPUPriceDelta, ErrorResponse, AlertJob, StatsResponse, DetailedStatsResponse
)

# Import routers
try:
    from routers import auth
    logger.info("Auth router imported successfully")
except ImportError:
    logger.warning("Auth router not found")
    auth = None

# Import OAuth router
try:
    from routers.oauth import router as oauth_router
    oauth_router_available = True
    logger.info("OAuth router imported successfully")
except ImportError as e:
    logger.warning(f"OAuth router not found: {e}")
    oauth_router_available = False
except Exception as e:
    logger.error(f"Error importing OAuth router: {e}")
    oauth_router_available = False

# Import CRUD and security
from crud import (
    get_db_connection, create_user, get_user_by_email, 
    connect_to_db, close_db_connection, get_user_count,
    check_database_health
)
from security import get_password_hash
from dependencies import redis_dependency, db_dependency

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

# Add session middleware for OAuth state management
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("JWT_SECRET_KEY", "your-session-secret-key")
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
        
        # Test Redis connection
        try:
            redis_conn = get_redis_connection()
            redis_conn.ping()
            logger.info("Redis connection tested successfully")
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}")
        
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
        
        logger.info("API shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure this properly for production
)

# Updated CORS middleware to include OAuth callback URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Your frontend
        "http://localhost:8000",  # Your backend
        "https://your-domain.com",  # Production frontend
        "https://accounts.google.com",  # Google OAuth
        "https://api.twitter.com",  # Twitter OAuth
        "https://discord.com",  # Discord OAuth
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

# API Endpoints
@app.get("/health", response_model=HealthCheck, summary="Health Check Endpoint")
async def health_check(redis_conn: redis.Redis = Depends(redis_dependency)):
    """Returns the health status of the API and its dependencies."""
    try:
        # Test Redis connection
        redis_conn.ping()
        
        # Test database connection
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
    """Calculate potential monthly profit based on GPU model and usage parameters."""
    try:
        # Enhanced calculation logic
        base_yield_per_hour = 0.15  # Base estimate in $/hr
        
        # GPU-specific multipliers
        gpu_multipliers = {
            "RTX 4090": 1.5,
            "RTX 4080": 1.2,
            "RTX 4070": 1.0,
            "A100": 3.0,
            "H100": 4.0,
            "V100": 2.0,
            "T4": 0.8,
            "A10G": 1.1,
            "K80": 0.6
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
        hourly_cost = request.power_cost_kwh * 0.4
        if estimated_hourly_yield > hourly_cost:
            break_even_hours = 0  # Profitable from hour 1
        elif hourly_cost > 0:
            break_even_hours = hourly_cost / estimated_hourly_yield
        
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

# Updated stats endpoint with enhanced functionality
@app.get("/stats", response_model=StatsResponse, summary="Get GPU Statistics")
async def get_gpu_stats(
    redis_conn: redis.Redis = Depends(redis_dependency),
    detailed: bool = False
):
    """
    Get real-time GPU tracking statistics.
    
    Args:
        redis_conn: Redis connection dependency
        detailed: Whether to return detailed statistics
        
    Returns:
        Statistics about tracked GPUs and system health
    """
    try:
        # Try to get cached stats first
        cache_key = "cache:gpu_stats"
        cached_stats = redis_conn.get(cache_key)
        
        if cached_stats and not detailed:
            logger.info("Returning cached GPU stats")
            stats_data = json.loads(cached_stats)
            return JSONResponse(
                content=stats_data,
                headers={
                    "X-Updated-At": str(int(time.time() * 1000)),
                    "Cache-Control": "public, max-age=60"
                }
            )
        
        # Calculate stats from Redis stream
        logger.info("Calculating fresh GPU stats")
        
        # Get entries from the last 24 hours
        current_time = int(time.time() * 1000)
        past_24h = current_time - (24 * 60 * 60 * 1000)
        
        # Read stream entries
        stream_entries = redis_conn.xrange(
            "raw_prices",
            min=f"{past_24h}-0",
            max=f"{current_time}-0",
            count=10000
        )
        
        # Track unique GPUs and models
        unique_gpus = set()
        gpu_models = {}
        provider_set = set()
        price_updates = 0
        
        for entry_id, fields in stream_entries:
            try:
                gpu_model = fields.get('gpu_model')
                cloud = fields.get('cloud')
                
                if gpu_model and cloud:
                    unique_gpus.add(f"{gpu_model}_{cloud}")
                    gpu_models[gpu_model] = gpu_models.get(gpu_model, 0) + 1
                    provider_set.add(cloud)
                    price_updates += 1
            except Exception as e:
                continue
        
        # Get top GPU models
        top_models = sorted(gpu_models.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Create response
        stats_data = StatsResponse(
            gpu_count=len(unique_gpus),
            total_providers=len(provider_set),
            last_update=datetime.now(timezone.utc).isoformat(),
            active_models=[model for model, _ in top_models]
        ).dict()
        
        # Cache for 60 seconds
        redis_conn.setex(cache_key, 60, json.dumps(stats_data, default=str))
        
        return JSONResponse(
            content=stats_data,
            headers={
                "X-Updated-At": str(int(time.time() * 1000)),
                "Cache-Control": "public, max-age=60"
            }
        )
        
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating statistics"
        )

@app.get("/stats/detailed", response_model=DetailedStatsResponse, summary="Get Detailed Statistics")
async def get_detailed_stats(
    redis_conn: redis.Redis = Depends(redis_dependency),
    conn = Depends(db_dependency)
):
    """
    Get detailed system statistics including AWS Spot data.
    """
    try:
        # Get basic stats first
        basic_stats = await get_gpu_stats(redis_conn, detailed=True)
        
        # Get additional metrics for detailed view
        stream_entries = redis_conn.xrange("raw_prices", count=5000)
        
        prices = []
        aws_count = 0
        total_updates = 0
        
        for entry_id, fields in stream_entries:
            try:
                price = float(fields.get('price_usd_hr', 0))
                if price > 0:
                    prices.append(price)
                
                if fields.get('cloud') == 'aws_spot':
                    aws_count += 1
                
                total_updates += 1
            except Exception:
                continue
        
        # Calculate price range
        price_range = {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0
        }
        
        # Get user count from database
        try:
            user_count = await get_user_count(conn)
        except Exception:
            user_count = 0
        
        # Build detailed response
        detailed_stats = DetailedStatsResponse(
            gpu_count=len(set(f"{fields.get('gpu_model')}_{fields.get('cloud')}" 
                             for _, fields in stream_entries if fields.get('gpu_model'))),
            total_providers=len(set(fields.get('cloud') for _, fields in stream_entries 
                                  if fields.get('cloud'))),
            active_regions=len(set(fields.get('region') for _, fields in stream_entries 
                                 if fields.get('region'))),
            price_range=price_range,
            top_gpu_models=[],  # Can be populated from gpu_models calculation above
            last_24h_updates=total_updates,
            system_health="excellent" if total_updates > 1000 else "good" if total_updates > 100 else "poor"
        )
        
        return detailed_stats
        
    except Exception as e:
        logger.error(f"Error calculating detailed stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating detailed statistics"
        )

# Include routers with proper error handling
try:
    from routes.aws_spot import router as aws_spot_router
    app.include_router(aws_spot_router, prefix="/api")
    logger.info("AWS Spot router included successfully")
except ImportError as e:
    logger.warning(f"Could not import AWS Spot router: {e}")

try:
    from routes.akash import router as akash_router
    app.include_router(akash_router, prefix="/api")
    logger.info("Akash router included successfully")
except ImportError as e:
    logger.warning(f"Could not import Akash router: {e}")

try:
    from routes.websocket import router as websocket_router
    app.include_router(websocket_router)
    logger.info("WebSocket router included successfully")
except ImportError as e:
    logger.warning(f"Could not import WebSocket router: {e}")

# Include existing auth router if available
if auth:
    app.include_router(auth.router)
    logger.info("Auth router included successfully")

# Include OAuth router
if oauth_router_available:
    app.include_router(oauth_router)
    logger.info("OAuth router included successfully")
    
    # Add debug endpoint to verify routes
    @app.get("/debug/routes")
    async def debug_routes():
        """Debug endpoint to show all registered routes."""
        routes = []
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                routes.append({
                    "path": route.path,
                    "methods": list(route.methods),
                    "name": route.name
                })
        return {"routes": routes, "total": len(routes)}
else:
    logger.error("OAuth router not available - OAuth endpoints will not work")

# Add OAuth callback success/error pages
@app.get("/auth/success")
async def auth_success():
    """OAuth success callback page."""
    return {"message": "Authentication successful", "status": "success"}

@app.get("/auth/error")
async def auth_error(message: str = "Authentication failed"):
    """OAuth error callback page."""
    return {"message": message, "status": "error"}

@app.get("/")
async def root():
    return {
        "message": "GPU Yield API", 
        "status": "running", 
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "oauth_providers": ["google", "twitter", "discord"]
    }

# Test endpoint for AWS data
@app.get("/test/aws-spot")
async def test_aws_spot(redis_conn: redis.Redis = Depends(redis_dependency)):
    """Test endpoint to check AWS Spot data in Redis"""
    try:
        stream_data = redis_conn.xrevrange("raw_prices", count=10)
        aws_data = []
        
        for stream_id, fields in stream_data:
            if fields.get('cloud') == 'aws_spot':
                aws_data.append({
                    'id': stream_id,
                    'model': fields.get('gpu_model'),
                    'price': fields.get('price_usd_hr'),
                    'region': fields.get('region'),
                    'timestamp': fields.get('iso_timestamp')
                })
        
        return {
            'total_stream_entries': len(stream_data),
            'aws_spot_entries': len(aws_data),
            'sample_data': aws_data[:5],
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"Error testing AWS Spot data: {e}")
        return {
            'error': str(e),
            'status': 'failed'
        }

# Add a synthetic data injection endpoint for testing
@app.post("/test/inject-aws-data")
async def inject_test_aws_data(redis_conn: redis.Redis = Depends(redis_dependency)):
    """Inject synthetic AWS Spot data for testing"""
    try:
        from utils.aws_spot_enrichment import get_synthetic_aws_data
        
        synthetic_data = get_synthetic_aws_data()
        injected = 0
        
        for offer in synthetic_data:
            # Convert to Redis stream format
            stream_fields = {
                'cloud': 'aws_spot',
                'gpu_model': offer['model'],
                'price_usd_hr': str(offer['usd_hr']),
                'region': offer['region'],
                'availability': str(offer['availability']),
                'instance_type': offer['instance_type'],
                'total_instance_price': str(offer['total_instance_price']),
                'gpu_memory_gb': str(offer['gpu_memory_gb']),
                'iso_timestamp': offer['timestamp'],
                'synthetic': 'true'
            }
            
            stream_id = redis_conn.xadd('raw_prices', stream_fields)
            injected += 1
        
        return {
            'status': 'success',
            'injected_offers': injected,
            'message': f'Injected {injected} synthetic AWS Spot offers'
        }
        
    except Exception as e:
        logger.error(f"Error injecting test data: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }

# Add test endpoints for Akash
@app.get("/test/akash")
async def test_akash(redis_conn: redis.Redis = Depends(redis_dependency)):
    """Test endpoint to check Akash data in Redis"""
    try:
        stream_data = redis_conn.xrevrange("raw_prices", count=10)
        akash_data = []
        
        for stream_id, fields in stream_data:
            if fields.get('cloud') == 'akash' or fields.get('provider') == 'akash':
                akash_data.append({
                    'id': stream_id,
                    'model': fields.get('gpu_model') or fields.get('model'),
                    'price': fields.get('price_usd_hr') or fields.get('usd_hr'),
                    'region': fields.get('region'),
                    'timestamp': fields.get('iso_timestamp') or fields.get('timestamp')
                })
        
        return {
            'total_stream_entries': len(stream_data),
            'akash_entries': len(akash_data),
            'sample_data': akash_data[:5],
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"Error testing Akash data: {e}")
        return {
            'error': str(e),
            'status': 'failed'
        }

@app.post("/test/inject-akash-data")
async def inject_test_akash_data(redis_conn: redis.Redis = Depends(redis_dependency)):
    """Inject synthetic Akash data for testing"""
    try:
        synthetic_data = [
            {
                'model': 'RTX 4090',
                'usd_hr': 0.35,
                'region': 'akash-network',
                'availability': 1,
                'provider': 'akash',
                'provider_address': 'akash1abc123...',
                'synthetic': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'model': 'A100',
                'usd_hr': 1.40,
                'region': 'akash-network',
                'availability': 1,
                'provider': 'akash',
                'provider_address': 'akash1def456...',
                'synthetic': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        injected = 0
        
        for offer in synthetic_data:
            # Convert to Redis stream format
            stream_fields = {
                'cloud': 'akash',
                'provider': 'akash',
                'gpu_model': offer['model'],
                'price_usd_hr': str(offer['usd_hr']),
                'region': offer['region'],
                'availability': str(offer['availability']),
                'provider_address': offer['provider_address'],
                'iso_timestamp': offer['timestamp'],
                'synthetic': 'true'
            }
            
            stream_id = redis_conn.xadd('raw_prices', stream_fields)
            injected += 1
        
        return {
            'status': 'success',
            'injected_offers': injected,
            'message': f'Injected {injected} synthetic Akash offers'
        }
        
    except Exception as e:
        logger.error(f"Error injecting Akash test data: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }