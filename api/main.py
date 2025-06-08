from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from utils import init_sentry, get_redis_connection
from models import HealthCheck, ROICalcRequest, ROICalcResponse, SignupRequest, DeltaResponse, GPUPriceDelta
import redis
import os
import json
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize Sentry
init_sentry()

# Create FastAPI application instance
app = FastAPI(title="GPU Price Scraper API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Changed from os.getenv("FRONTEND_URL", "http://localhost:3000")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencies
def redis_dependency():
    """Dependency to inject Redis connection into endpoints."""
    connection = get_redis_connection()
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service is unavailable"
        )
    return connection

# API Endpoints

@app.get("/health", response_model=HealthCheck, summary="Health Check Endpoint")
async def health_check():
    """Returns the health status of the API."""
    return {"status": "ok"}

@app.get("/delta", response_model=DeltaResponse, summary="Get GPU Price Deltas")
async def get_delta(redis_conn: redis.Redis = Depends(redis_dependency)):
    """
    Returns the cheapest GPU prices from different cloud providers.
    Uses caching to improve performance.
    """
    cache_key = "cache:/delta"
    
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
        # Get last 200 entries from the raw_prices stream
        stream_entries = redis_conn.xrevrange("raw_prices", count=200)
        
        # Dictionary to track cheapest offer per GPU model
        cheapest_offers = {}
        
        # Process stream entries
        for entry_id, fields in stream_entries:
            try:
                gpu_model = fields.get('gpu_model')
                price_str = fields.get('price_usd_hr')
                cloud = fields.get('cloud')
                
                if gpu_model and price_str and cloud:
                    price = float(price_str)
                    
                    # Update if this is the cheapest price for this GPU model
                    if gpu_model not in cheapest_offers or price < cheapest_offers[gpu_model]['price_usd_hr']:
                        cheapest_offers[gpu_model] = {
                            'gpu_model': gpu_model,
                            'best_source': cloud,
                            'price_usd_hr': price
                        }
            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing stream entry {entry_id}: {e}")
                continue
        
        # Convert to list of GPUPriceDelta objects
        deltas = [GPUPriceDelta(**offer) for offer in cheapest_offers.values()]
        response_data = DeltaResponse(deltas=deltas)
        
        # Cache the result for 30 seconds
        try:
            cache_data = response_data.dict()
            redis_conn.setex(cache_key, 30, json.dumps(cache_data))
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
    """
    # Placeholder logic with hardcoded price delta
    price_delta = 0.11  # $/hr average yield delta
    
    # Calculate monthly profit: (price_delta - power_cost) * hours_per_day * 30 days
    monthly_profit = (price_delta - request.power_cost_kwh) * request.hours_per_day * 30
    
    logger.info(f"ROI calculation for {request.gpu_model}: ${monthly_profit:.2f}")
    
    return ROICalcResponse(potential_monthly_profit=round(monthly_profit, 2))

@app.post("/signup", summary="User Signup")
async def signup(request: SignupRequest):
    """
    Handles user signup requests. Currently a placeholder implementation.
    """
    logger.info(f"New signup request from: {request.email}")
    
    # TODO: Add hCaptcha verification, database storage, and Stripe integration
    
    return {
        "status": "success",
        "message": "Signup received, welcome email queued."
    }