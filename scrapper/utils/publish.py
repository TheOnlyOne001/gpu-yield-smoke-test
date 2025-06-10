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
        source_name: Name of the data source (e.g., 'runpod', 'akash')
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
                
                # Create Redis stream payload
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