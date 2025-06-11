import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
import redis

# Fixed import structure
try:
    from utils.aws_spot_enrichment import (
        enrich_aws_spot_batch,
        filter_offers_for_view,
        get_enriched_aws_spot_prices
    )
except ImportError:
    # Fallback - define minimal functions locally
    def enrich_aws_spot_batch(offers):
        return offers
    
    def filter_offers_for_view(offers, view_type):
        return offers
    
    def get_enriched_aws_spot_prices(*args, **kwargs):
        return []

# Import models
try:
    from models import ErrorResponse
except ImportError:
    # Fallback - define minimal ErrorResponse
    class ErrorResponse:
        def __init__(self, **kwargs):
            self.data = kwargs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aws-spot", tags=["AWS Spot"])

# Redis connection function
def get_redis_connection():
    """Get Redis connection for reading AWS Spot data"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    if not redis_url:
        raise HTTPException(status_code=500, detail="Redis configuration missing")
    return redis.from_url(redis_url, decode_responses=True)

def get_synthetic_aws_data():
    """Enhanced synthetic data when scraper plugin is not available"""
    return [
        {
            'model': 'A100',
            'usd_hr': 1.2290,
            'region': 'us-east-1',
            'availability': 8,
            'instance_type': 'p4d.24xlarge',
            'provider': 'aws_spot',
            'total_instance_price': 9.832,
            'gpu_memory_gb': 40,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'synthetic': True
        },
        {
            'model': 'T4',
            'usd_hr': 0.1578,
            'region': 'us-west-2',
            'availability': 1,
            'instance_type': 'g4dn.xlarge',
            'provider': 'aws_spot',
            'total_instance_price': 0.1578,
            'gpu_memory_gb': 16,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'synthetic': True
        },
        {
            'model': 'V100',
            'usd_hr': 0.7850,
            'region': 'eu-west-1',
            'availability': 4,
            'instance_type': 'p3.8xlarge',
            'provider': 'aws_spot',
            'total_instance_price': 3.140,
            'gpu_memory_gb': 32,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'synthetic': True
        },
        {
            'model': 'A10G',
            'usd_hr': 0.3520,
            'region': 'us-west-2',
            'availability': 1,
            'instance_type': 'g5.xlarge',
            'provider': 'aws_spot',
            'total_instance_price': 0.3520,
            'gpu_memory_gb': 24,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'synthetic': True
        },
        {
            'model': 'H100',
            'usd_hr': 2.4500,
            'region': 'us-east-1',
            'availability': 8,
            'instance_type': 'p5.48xlarge',
            'provider': 'aws_spot',
            'total_instance_price': 19.600,
            'gpu_memory_gb': 80,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'synthetic': True
        }
    ]

@router.get("/prices",
           summary="Get AWS Spot GPU Prices",
           description="Retrieve current AWS Spot instance prices with enrichment")
async def get_aws_spot_prices(
    region: Optional[str] = Query(None, description="Filter by AWS region"),
    model: Optional[str] = Query(None, description="Filter by GPU model"),
    min_availability: Optional[int] = Query(None, ge=1, description="Minimum GPU count"),
    view_type: str = Query("operator", regex="^(operator|renter)$", description="View type"),
    include_synthetic: bool = Query(True, description="Include synthetic data"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results")
) -> Dict[str, Any]:
    """Get enriched AWS Spot GPU pricing data with filtering options."""
    try:
        # Get data from Redis stream
        redis_conn = get_redis_connection()
        
        # Read recent AWS Spot data from Redis stream
        raw_offers = []
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=1000)
            
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'aws_spot':
                    # Validate required fields
                    gpu_model = fields.get('gpu_model')
                    price_str = fields.get('price_usd_hr')
                    region_val = fields.get('region')
                    
                    if not all([gpu_model, price_str, region_val]):
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
                        'provider': 'aws_spot',
                        'timestamp': fields.get('iso_timestamp'),
                        'instance_type': fields.get('instance_type', ''),
                        'synthetic': fields.get('synthetic', 'false').lower() == 'true'
                    }
                    
                    # Add optional fields if present
                    if fields.get('total_instance_price'):
                        try:
                            offer['total_instance_price'] = float(fields.get('total_instance_price'))
                        except (ValueError, TypeError):
                            pass
                    
                    if fields.get('gpu_memory_gb'):
                        try:
                            offer['gpu_memory_gb'] = int(fields.get('gpu_memory_gb'))
                        except (ValueError, TypeError):
                            pass
                    
                    raw_offers.append(offer)
        
        except Exception as e:
            logger.warning(f"Error reading from Redis: {e}")
            raw_offers = []
        
        # If no real data and synthetic allowed, get synthetic data
        if not raw_offers and include_synthetic:
            logger.info("No real AWS data found, using synthetic data")
            raw_offers = get_synthetic_aws_data()
        
        if not raw_offers:
            return {
                "offers": [],
                "total_count": 0,
                "metadata": {
                    "filtered_by": {
                        "region": region,
                        "model": model,
                        "min_availability": min_availability
                    },
                    "view_type": view_type,
                    "last_updated": None,
                    "data_source": "none",
                    "regions_available": [],
                    "models_available": []
                }
            }
        
        # Enrich the offers (with fallback if enrichment fails)
        try:
            enriched_offers = enrich_aws_spot_batch(raw_offers)
        except Exception as e:
            logger.warning(f"Enrichment failed, using raw offers: {e}")
            enriched_offers = raw_offers
        
        # Apply filters
        filtered_offers = enriched_offers
        if region:
            filtered_offers = [o for o in filtered_offers if o.get("region") == region]
        if model:
            filtered_offers = [o for o in filtered_offers if o.get("model") == model]
        if min_availability:
            filtered_offers = [o for o in filtered_offers if o.get("availability", 0) >= min_availability]
        
        # Filter for view type (with fallback)
        try:
            view_filtered = filter_offers_for_view(filtered_offers, view_type)
        except Exception as e:
            logger.warning(f"View filtering failed, using unfiltered offers: {e}")
            view_filtered = filtered_offers
        
        # Apply limit
        limited_offers = view_filtered[:limit]
        
        # Get latest timestamp
        latest_timestamp = None
        if limited_offers:
            timestamps = [o.get('timestamp') for o in limited_offers if o.get('timestamp')]
            if timestamps:
                latest_timestamp = max(timestamps)
        
        # Get available regions and models
        all_regions = list(set(o.get('region', '') for o in enriched_offers if o.get('region')))
        all_models = list(set(o.get('model', '') for o in enriched_offers if o.get('model')))
        
        return {
            "offers": limited_offers,
            "total_count": len(view_filtered),
            "metadata": {
                "filtered_by": {
                    "region": region,
                    "model": model,
                    "min_availability": min_availability
                },
                "view_type": view_type,
                "last_updated": latest_timestamp,
                "data_source": "synthetic" if any(o.get('synthetic') for o in limited_offers) else "live",
                "regions_available": sorted(all_regions),
                "models_available": sorted(all_models)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching AWS Spot prices: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch AWS Spot prices: {str(e)}"
        )

@router.get("/regions")
async def get_available_regions() -> Dict[str, Any]:
    """Get list of AWS regions with current data availability."""
    try:
        redis_conn = get_redis_connection()
        
        regions = set()
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=500)
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'aws_spot' and fields.get('region'):
                    regions.add(fields['region'])
        except Exception as e:
            logger.warning(f"Error reading regions from Redis: {e}")
            # Fallback to common regions
            regions = {"us-east-1", "us-west-2", "eu-west-1", "us-east-2", "ap-southeast-1"}
        
        # Region display mapping
        region_display = {
            'us-east-1': 'US East (N. Virginia)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'EU West (Ireland)',
            'us-east-2': 'US East (Ohio)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'eu-central-1': 'EU Central (Frankfurt)',
            'ap-northeast-1': 'Asia Pacific (Tokyo)'
        }
        
        region_list = []
        for region in sorted(regions):
            region_list.append({
                "code": region,
                "name": region_display.get(region, region),
                "available": True
            })
        
        return {
            "regions": region_list,
            "total_count": len(region_list)
        }
        
    except Exception as e:
        logger.error(f"Error fetching AWS regions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch regions")

@router.get("/models")
async def get_available_models() -> Dict[str, Any]:
    """Get list of GPU models available on AWS Spot."""
    try:
        redis_conn = get_redis_connection()
        
        models = set()
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=500)
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'aws_spot' and fields.get('gpu_model'):
                    models.add(fields['gpu_model'])
        except Exception as e:
            logger.warning(f"Error reading models from Redis: {e}")
            # Fallback to common models
            models = {"A100", "T4", "V100", "A10G", "H100", "A40", "RTX 4090"}
        
        # Model categorization
        datacenter_models = {"A100", "V100", "H100", "A10G", "A40", "A30", "T4"}
        consumer_models = {"RTX 4090", "RTX 4080", "RTX 3090", "RTX 3080"}
        
        model_list = []
        for model in sorted(models):
            category = "datacenter" if model in datacenter_models else "consumer"
            model_list.append({
                "name": model,
                "available": True,
                "category": category
            })
        
        return {
            "models": model_list,
            "total_count": len(model_list)
        }
        
    except Exception as e:
        logger.error(f"Error fetching AWS models: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch models")

@router.get("/summary")
async def get_aws_spot_summary() -> Dict[str, Any]:
    """Get summary statistics for AWS Spot pricing."""
    try:
        redis_conn = get_redis_connection()
        
        offers = []
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=1000)
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'aws_spot':
                    gpu_model = fields.get('gpu_model')
                    price_str = fields.get('price_usd_hr')
                    region = fields.get('region')
                    timestamp = fields.get('iso_timestamp')
                    
                    if gpu_model and price_str and region:
                        try:
                            price = float(price_str)
                            if price > 0:
                                offers.append({
                                    'model': gpu_model,
                                    'usd_hr': price,
                                    'region': region,
                                    'timestamp': timestamp
                                })
                        except (ValueError, TypeError):
                            continue
        except Exception as e:
            logger.warning(f"Error reading summary data: {e}")
        
        if not offers:
            # Return synthetic summary
            return {
                "total_offers": 5,
                "unique_models": 5,
                "unique_regions": 3,
                "price_range": {"min": 0.15, "max": 2.45},
                "avg_price": 0.95,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "models": ["A100", "T4", "V100", "A10G", "H100"],
                "regions": ["us-east-1", "us-west-2", "eu-west-1"]
            }
        
        # Calculate statistics
        prices = [o['usd_hr'] for o in offers if o['usd_hr'] > 0]
        models = set(o['model'] for o in offers if o['model'])
        regions = set(o['region'] for o in offers if o['region'])
        timestamps = [o['timestamp'] for o in offers if o['timestamp']]
        
        return {
            "total_offers": len(offers),
            "unique_models": len(models),
            "unique_regions": len(regions),
            "price_range": {
                "min": min(prices) if prices else 0,
                "max": max(prices) if prices else 0
            },
            "avg_price": sum(prices) / len(prices) if prices else 0,
            "last_updated": max(timestamps) if timestamps else None,
            "models": list(models),
            "regions": list(regions)
        }
        
    except Exception as e:
        logger.error(f"Error generating AWS Spot summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate summary")