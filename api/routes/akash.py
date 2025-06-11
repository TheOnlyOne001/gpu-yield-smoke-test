import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
import redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/akash", tags=["Akash Network"])

# Redis connection function
def get_redis_connection():
    """Get Redis connection for reading Akash data"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    if not redis_url:
        raise HTTPException(status_code=500, detail="Redis configuration missing")
    return redis.from_url(redis_url, decode_responses=True)

def get_synthetic_akash_data():
    """Get synthetic Akash data for testing"""
    return [
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
            'model': 'RTX 3090',
            'usd_hr': 0.22,
            'region': 'akash-network',
            'availability': 1,
            'provider': 'akash',
            'provider_address': 'akash1def456...',
            'synthetic': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        },
        {
            'model': 'A100',
            'usd_hr': 1.40,
            'region': 'akash-network',
            'availability': 1,
            'provider': 'akash',
            'provider_address': 'akash1ghi789...',
            'synthetic': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        },
        {
            'model': 'V100',
            'usd_hr': 0.45,
            'region': 'akash-network',
            'availability': 1,
            'provider': 'akash',
            'provider_address': 'akash1jkl012...',
            'synthetic': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        },
        {
            'model': 'T4',
            'usd_hr': 0.11,
            'region': 'akash-network',
            'availability': 1,
            'provider': 'akash',
            'provider_address': 'akash1mno345...',
            'synthetic': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    ]

@router.get("/prices",
           summary="Get Akash Network GPU Prices",
           description="Retrieve current Akash Network GPU prices")
async def get_akash_prices(
    model: Optional[str] = Query(None, description="Filter by GPU model"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    include_synthetic: bool = Query(True, description="Include synthetic data"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results")
) -> Dict[str, Any]:
    """Get Akash Network GPU pricing data with filtering options."""
    try:
        # Get data from Redis stream
        redis_conn = get_redis_connection()
        
        # Read recent Akash data from Redis stream
        raw_offers = []
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=1000)
            
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'akash' or fields.get('provider') == 'akash':
                    # Validate required fields
                    gpu_model = fields.get('gpu_model') or fields.get('model')
                    price_str = fields.get('price_usd_hr') or fields.get('usd_hr')
                    region_val = fields.get('region', 'akash-network')
                    
                    if not all([gpu_model, price_str]):
                        continue
                    
                    try:
                        price_val = float(price_str)
                        if price_val <= 0:
                            continue
                    except (ValueError, TypeError):
                        continue
                    
                    offer = {
                        'model': gpu_model,
                        'usd_hr': price_val,
                        'region': region_val,
                        'availability': int(fields.get('availability', 1)),
                        'provider': 'akash',
                        'timestamp': fields.get('iso_timestamp') or fields.get('timestamp'),
                        'provider_address': fields.get('provider_address', 'unknown'),
                        'synthetic': fields.get('synthetic', 'false').lower() == 'true'
                    }
                    
                    # Add optional fields if present
                    for optional_field in ['bid_id', 'state', 'token_price', 'original_currency']:
                        if fields.get(optional_field):
                            offer[optional_field] = fields.get(optional_field)
                    
                    raw_offers.append(offer)
        
        except Exception as e:
            logger.warning(f"Error reading Akash data from Redis: {e}")
            raw_offers = []
        
        # If no real data and synthetic allowed, get synthetic data
        if not raw_offers and include_synthetic:
            logger.info("No real Akash data found, using synthetic data")
            raw_offers = get_synthetic_akash_data()
        
        if not raw_offers:
            return {
                "offers": [],
                "total_count": 0,
                "metadata": {
                    "filtered_by": {
                        "model": model,
                        "min_price": min_price,
                        "max_price": max_price
                    },
                    "last_updated": None,
                    "data_source": "none",
                    "models_available": []
                }
            }
        
        # Apply filters
        filtered_offers = raw_offers
        if model:
            filtered_offers = [o for o in filtered_offers if model.lower() in o.get("model", "").lower()]
        if min_price is not None:
            filtered_offers = [o for o in filtered_offers if o.get("usd_hr", 0) >= min_price]
        if max_price is not None:
            filtered_offers = [o for o in filtered_offers if o.get("usd_hr", 0) <= max_price]
        
        # Apply limit
        limited_offers = filtered_offers[:limit]
        
        # Get latest timestamp
        latest_timestamp = None
        if limited_offers:
            timestamps = [o.get('timestamp') for o in limited_offers if o.get('timestamp')]
            if timestamps:
                latest_timestamp = max(timestamps)
        
        # Get available models
        all_models = list(set(o.get('model', '') for o in raw_offers if o.get('model')))
        
        return {
            "offers": limited_offers,
            "total_count": len(filtered_offers),
            "metadata": {
                "filtered_by": {
                    "model": model,
                    "min_price": min_price,
                    "max_price": max_price
                },
                "last_updated": latest_timestamp,
                "data_source": "synthetic" if any(o.get('synthetic') for o in limited_offers) else "live",
                "models_available": sorted(all_models)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching Akash prices: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Akash prices: {str(e)}"
        )

@router.get("/models")
async def get_available_akash_models() -> Dict[str, Any]:
    """Get list of GPU models available on Akash Network."""
    try:
        redis_conn = get_redis_connection()
        
        models = set()
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=500)
            for stream_id, fields in stream_data:
                if (fields.get('cloud') == 'akash' or fields.get('provider') == 'akash') and fields.get('gpu_model'):
                    models.add(fields['gpu_model'])
        except Exception as e:
            logger.warning(f"Error reading Akash models from Redis: {e}")
            # Fallback to common Akash models
            models = {"RTX 4090", "RTX 3090", "RTX 3080", "RTX 3070", "A100", "V100", "T4"}
        
        model_list = []
        for model in sorted(models):
            model_list.append({
                "name": model,
                "available": True,
                "provider": "akash"
            })
        
        return {
            "models": model_list,
            "total_count": len(model_list)
        }
        
    except Exception as e:
        logger.error(f"Error fetching Akash models: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch models")

@router.get("/summary")
async def get_akash_summary() -> Dict[str, Any]:
    """Get summary statistics for Akash Network pricing."""
    try:
        redis_conn = get_redis_connection()
        
        offers = []
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=1000)
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'akash' or fields.get('provider') == 'akash':
                    gpu_model = fields.get('gpu_model') or fields.get('model')
                    price_str = fields.get('price_usd_hr') or fields.get('usd_hr')
                    timestamp = fields.get('iso_timestamp') or fields.get('timestamp')
                    
                    if gpu_model and price_str:
                        try:
                            price = float(price_str)
                            if price > 0:
                                offers.append({
                                    'model': gpu_model,
                                    'usd_hr': price,
                                    'timestamp': timestamp
                                })
                        except (ValueError, TypeError):
                            continue
        except Exception as e:
            logger.warning(f"Error reading Akash summary data: {e}")
        
        if not offers:
            # Return synthetic summary
            return {
                "total_offers": 5,
                "unique_models": 5,
                "price_range": {"min": 0.11, "max": 1.40},
                "avg_price": 0.51,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "models": ["RTX 4090", "RTX 3090", "A100", "V100", "T4"]
            }
        
        # Calculate statistics
        prices = [o['usd_hr'] for o in offers if o['usd_hr'] > 0]
        models = set(o['model'] for o in offers if o['model'])
        timestamps = [o['timestamp'] for o in offers if o['timestamp']]
        
        return {
            "total_offers": len(offers),
            "unique_models": len(models),
            "price_range": {
                "min": min(prices) if prices else 0,
                "max": max(prices) if prices else 0
            },
            "avg_price": sum(prices) / len(prices) if prices else 0,
            "last_updated": max(timestamps) if timestamps else None,
            "models": list(models)
        }
        
    except Exception as e:
        logger.error(f"Error generating Akash summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate summary")

@router.get("/health")
async def akash_health_check() -> Dict[str, Any]:
    """Health check specifically for Akash data pipeline"""
    try:
        redis_conn = get_redis_connection()
        redis_conn.ping()
        
        # Check for Akash data
        stream_data = redis_conn.xrevrange("raw_prices", count=100)
        akash_count = 0
        
        for stream_id, fields in stream_data:
            if fields.get('cloud') == 'akash' or fields.get('provider') == 'akash':
                akash_count += 1
        
        return {
            "status": "healthy",
            "redis_connected": True,
            "akash_offers_count": akash_count,
            "has_real_data": akash_count > 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Akash health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Akash service unhealthy: {str(e)}"
        )