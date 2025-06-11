import os
import sys
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
import redis

# Import enrichment utilities
from ..utils.aws_spot_enrichment import (
    enrich_aws_spot_batch,
    filter_offers_for_view,
    get_enriched_aws_spot_prices
)

# Import models
from ..models import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aws-spot", tags=["AWS Spot"])

# Redis connection function
def get_redis_connection():
    """Get Redis connection for reading AWS Spot data"""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise HTTPException(status_code=500, detail="Redis configuration missing")
    return redis.from_url(redis_url, decode_responses=True)

# Import synthetic data function
def get_synthetic_aws_data():
    """Fallback synthetic data when scraper plugin is not available"""
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
                    offer = {
                        'model': fields.get('gpu_model'),
                        'usd_hr': float(fields.get('price_usd_hr', 0)),
                        'region': fields.get('region'),
                        'availability': int(fields.get('availability', 1)),
                        'provider': 'aws_spot',
                        'timestamp': fields.get('iso_timestamp'),
                        'instance_type': fields.get('instance_type', ''),
                        'total_instance_price': float(fields.get('total_instance_price', 0)),
                        'gpu_memory_gb': int(fields.get('gpu_memory_gb', 16))
                    }
                    
                    if offer['model'] and offer['usd_hr'] > 0:
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
                    "data_source": "none"
                }
            }
        
        # Enrich the offers
        enriched_offers = enrich_aws_spot_batch(raw_offers)
        
        # Apply filters
        filtered_offers = enriched_offers
        if region:
            filtered_offers = [o for o in filtered_offers if o.get("region") == region]
        if model:
            filtered_offers = [o for o in filtered_offers if o.get("model") == model]
        if min_availability:
            filtered_offers = [o for o in filtered_offers if o.get("availability", 0) >= min_availability]
        
        # Filter for view type
        view_filtered = filter_offers_for_view(filtered_offers, view_type)
        
        # Apply limit
        limited_offers = view_filtered[:limit]
        
        # Get latest timestamp
        latest_timestamp = None
        if limited_offers:
            timestamps = [o.get('timestamp') for o in limited_offers if o.get('timestamp')]
            if timestamps:
                latest_timestamp = max(timestamps)
        
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
                "regions_available": list(set(o['region'] for o in enriched_offers)),
                "models_available": list(set(o['model'] for o in enriched_offers))
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching AWS Spot prices: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch AWS Spot prices: {str(e)}"
        )

@router.get("/regions",
           summary="Get Available AWS Regions",
           description="Get list of AWS regions with current Spot GPU availability")
async def get_available_regions() -> Dict[str, Any]:
    """Get list of AWS regions with current data availability."""
    try:
        redis_conn = get_redis_connection()
        
        # Get recent AWS data from Redis
        regions = set()
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=500)
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'aws_spot' and fields.get('region'):
                    regions.add(fields['region'])
        except Exception as e:
            logger.warning(f"Error reading regions from Redis: {e}")
            # Fallback to common regions
            regions = {"us-east-1", "us-west-2", "eu-west-1"}
        
        # Region display mapping
        region_display = {
            'us-east-1': 'US East (N. Virginia)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'EU West (Ireland)',
            'us-east-2': 'US East (Ohio)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
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

@router.get("/models",
           summary="Get Available GPU Models",
           description="Get list of GPU models available on AWS Spot")
async def get_available_models() -> Dict[str, Any]:
    """Get list of GPU models available on AWS Spot."""
    try:
        redis_conn = get_redis_connection()
        
        # Get recent AWS data from Redis
        models = set()
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=500)
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'aws_spot' and fields.get('gpu_model'):
                    models.add(fields['gpu_model'])
        except Exception as e:
            logger.warning(f"Error reading models from Redis: {e}")
            # Fallback to common models
            models = {"A100", "T4", "V100", "A10G", "H100"}
        
        # Model categorization
        datacenter_models = {"A100", "V100", "H100", "A10G"}
        consumer_models = {"T4"}
        
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

@router.get("/summary",
           summary="Get AWS Spot Summary",
           description="Get summary statistics for AWS Spot GPU pricing")
async def get_aws_spot_summary() -> Dict[str, Any]:
    """Get summary statistics for AWS Spot pricing."""
    try:
        redis_conn = get_redis_connection()
        
        # Get recent AWS data
        offers = []
        try:
            stream_data = redis_conn.xrevrange("raw_prices", count=1000)
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'aws_spot':
                    offers.append({
                        'model': fields.get('gpu_model'),
                        'usd_hr': float(fields.get('price_usd_hr', 0)),
                        'region': fields.get('region'),
                        'timestamp': fields.get('iso_timestamp')
                    })
        except Exception as e:
            logger.warning(f"Error reading summary data: {e}")
        
        if not offers:
            return {
                "total_offers": 0,
                "unique_models": 0,
                "unique_regions": 0,
                "price_range": {"min": 0, "max": 0},
                "avg_price": 0,
                "last_updated": None
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