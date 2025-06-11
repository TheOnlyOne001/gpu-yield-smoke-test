"""
Redis publishing utilities for GPU pricing data.
"""

import os
import json
import time
import logging
from typing import List, Dict, Optional
import redis
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def publish_to_redis(source_name: str, offers: List[Dict], redis_conn: Optional[redis.Redis] = None) -> int:
    """
    Publish GPU offers to Redis stream.
    
    Args:
        source_name: Name of the data source (e.g., 'runpod', 'akash', 'aws_spot')
        offers: List of standardized offer dictionaries
        redis_conn: Redis connection (optional, will create if None)
        
    Returns:
        int: Number of records successfully published
        
    Raises:
        Exception: If Redis operations fail
    """
    if not offers:
        logger.warning(f"No offers to publish for {source_name}")
        return 0
    
    # Create Redis connection if not provided
    if redis_conn is None:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("REDIS_URL environment variable not set")
        redis_conn = redis.from_url(redis_url, decode_responses=True)
    
    stream_name = "raw_prices"
    published_count = 0
    timestamp = int(time.time())
    iso_timestamp = datetime.now(timezone.utc).isoformat()
    
    try:
        for offer in offers:
            try:
                # Validate offer structure
                if not isinstance(offer, dict):
                    logger.warning(f"Skipping invalid offer format from {source_name}: {offer}")
                    continue
                
                required_fields = ['model', 'usd_hr', 'region']
                if not all(field in offer for field in required_fields):
                    logger.warning(f"Skipping incomplete offer from {source_name}: {offer}")
                    continue
                
                # Create Redis stream payload with AWS-specific fields
                payload = {
                    'timestamp': timestamp,
                    'iso_timestamp': iso_timestamp,
                    'cloud': source_name,
                    'gpu_model': str(offer['model']),
                    'price_usd_hr': float(offer['usd_hr']),
                    'region': str(offer['region']),
                    'availability': offer.get('availability', 1),
                    'source_record_id': offer.get('id', ''),
                    'data_quality_score': offer.get('quality_score', 1.0)
                }
                
                # Add AWS-specific fields if available
                if source_name == 'aws_spot':
                    payload.update({
                        'instance_type': offer.get('instance_type', ''),
                        'total_instance_price': offer.get('total_instance_price', 0),
                        'gpu_memory_gb': offer.get('gpu_memory_gb', 16),
                        'provider': offer.get('provider', 'aws_spot'),
                        'synthetic': offer.get('synthetic', False)
                    })
                
                # Add to Redis stream
                redis_conn.xadd(stream_name, payload)
                published_count += 1
                
            except Exception as e:
                logger.warning(f"Error publishing offer from {source_name}: {e}")
                continue
        
        # Trim stream to prevent unlimited growth
        try:
            redis_conn.xtrim(stream_name, maxlen=10000, approximate=True)
        except Exception as e:
            logger.warning(f"Error trimming Redis stream: {e}")
        
        logger.info(f"Published {published_count}/{len(offers)} offers from {source_name} to Redis")
        return published_count
        
    except Exception as e:
        logger.error(f"Redis publishing error for {source_name}: {e}")
        raise

def get_recent_offers(
    redis_conn: Optional[redis.Redis] = None,
    source_name: Optional[str] = None,
    count: int = 100
) -> List[Dict]:
    """
    Get recent offers from Redis stream.
    
    Args:
        redis_conn: Redis connection
        source_name: Filter by specific source (optional)
        count: Number of recent entries to fetch
        
    Returns:
        List of offer dictionaries
    """
    if redis_conn is None:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("REDIS_URL environment variable not set")
        redis_conn = redis.from_url(redis_url, decode_responses=True)
    
    try:
        stream_data = redis_conn.xrevrange("raw_prices", count=count)
        offers = []
        
        for stream_id, fields in stream_data:
            # Filter by source if specified
            if source_name and fields.get('cloud') != source_name:
                continue
            
            # Reconstruct offer
            offer = {
                'model': fields.get('gpu_model'),
                'usd_hr': float(fields.get('price_usd_hr', 0)),
                'region': fields.get('region'),
                'availability': int(fields.get('availability', 1)),
                'timestamp': fields.get('iso_timestamp'),
                'source': fields.get('cloud'),
                'quality_score': float(fields.get('data_quality_score', 1.0))
            }
            
            # Add AWS-specific fields if available
            if fields.get('cloud') == 'aws_spot':
                offer.update({
                    'instance_type': fields.get('instance_type', ''),
                    'total_instance_price': float(fields.get('total_instance_price', 0)),
                    'gpu_memory_gb': int(fields.get('gpu_memory_gb', 16)),
                    'provider': fields.get('provider', 'aws_spot'),
                    'synthetic': fields.get('synthetic', 'false').lower() == 'true'
                })
            
            offers.append(offer)
        
        return offers
        
    except Exception as e:
        logger.error(f"Error reading from Redis stream: {e}")
        raise