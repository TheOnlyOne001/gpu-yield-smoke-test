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
                
                # Create Redis stream payload with consistent string formatting
                payload = {
                    'timestamp': str(timestamp),
                    'iso_timestamp': iso_timestamp,
                    'cloud': source_name,
                    'provider': source_name,  # Add provider field for compatibility
                    'gpu_model': str(offer['model']),
                    'price_usd_hr': str(float(offer['usd_hr'])),
                    'region': str(offer['region']),
                    'availability': str(offer.get('availability', 1)),
                    'source_record_id': str(offer.get('id', '')),
                    'data_quality_score': str(offer.get('quality_score', 1.0)),
                    'synthetic': 'true' if offer.get('synthetic', False) else 'false'
                }
                
                # Add source-specific fields
                if source_name == 'aws_spot':
                    payload.update({
                        'instance_type': str(offer.get('instance_type', '')),
                        'total_instance_price': str(offer.get('total_instance_price', 0)),
                        'gpu_memory_gb': str(offer.get('gpu_memory_gb', 16))
                    })
                elif source_name == 'akash':
                    payload.update({
                        'provider_address': str(offer.get('provider_address', '')),
                        'bid_id': str(offer.get('bid_id', '')),
                        'state': str(offer.get('state', 'active')),
                        'token_price': str(offer.get('token_price', 0)),
                        'original_currency': str(offer.get('original_currency', ''))
                    })
                elif source_name == 'runpod':
                    payload.update({
                        'gpu_memory_gb': str(offer.get('gpu_memory_gb', 0)),
                        'pod_type': str(offer.get('pod_type', '')),
                        'location': str(offer.get('location', ''))
                    })
                elif source_name == 'vast.ai':
                    payload.update({
                        'gpu_memory_gb': str(offer.get('gpu_memory_gb', 0)),
                        'machine_id': str(offer.get('machine_id', '')),
                        'location': str(offer.get('location', ''))
                    })
                elif source_name == 'io_net':
                    payload.update({
                        'device_id': str(offer.get('device_id', '')),
                        'device_type': str(offer.get('device_type', '')),
                        'location': str(offer.get('location', ''))
                    })
                
                # Add to Redis stream
                stream_id = redis_conn.xadd(stream_name, payload)
                published_count += 1
                
                if published_count % 10 == 0:  # Log progress for large batches
                    logger.debug(f"Published {published_count} offers from {source_name}")
                
            except Exception as e:
                logger.warning(f"Error publishing individual offer from {source_name}: {e}")
                continue
        
        # Trim stream to prevent unlimited growth (keep last 50,000 entries)
        try:
            redis_conn.xtrim(stream_name, maxlen=50000, approximate=True)
        except Exception as e:
            logger.warning(f"Error trimming Redis stream: {e}")
        
        logger.info(f"Successfully published {published_count}/{len(offers)} offers from {source_name} to Redis")
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
            cloud = fields.get('cloud') or fields.get('provider')
            if source_name and cloud != source_name:
                continue
            
            # Reconstruct offer with proper type conversion
            try:
                offer = {
                    'model': fields.get('gpu_model', ''),
                    'usd_hr': float(fields.get('price_usd_hr', 0)),
                    'region': fields.get('region', ''),
                    'availability': int(fields.get('availability', 1)),
                    'timestamp': fields.get('iso_timestamp'),
                    'source': cloud,
                    'provider': fields.get('provider', cloud),
                    'quality_score': float(fields.get('data_quality_score', 1.0)),
                    'synthetic': fields.get('synthetic', 'false').lower() == 'true'
                }
                
                # Add source-specific fields based on cloud provider
                if cloud == 'aws_spot':
                    offer.update({
                        'instance_type': fields.get('instance_type', ''),
                        'total_instance_price': float(fields.get('total_instance_price', 0)),
                        'gpu_memory_gb': int(fields.get('gpu_memory_gb', 16))
                    })
                elif cloud == 'akash':
                    offer.update({
                        'provider_address': fields.get('provider_address', ''),
                        'bid_id': fields.get('bid_id', ''),
                        'state': fields.get('state', 'active'),
                        'token_price': float(fields.get('token_price', 0)) if fields.get('token_price') else 0,
                        'original_currency': fields.get('original_currency', '')
                    })
                elif cloud == 'runpod':
                    offer.update({
                        'gpu_memory_gb': int(fields.get('gpu_memory_gb', 0)),
                        'pod_type': fields.get('pod_type', ''),
                        'location': fields.get('location', '')
                    })
                elif cloud == 'vast.ai':
                    offer.update({
                        'gpu_memory_gb': int(fields.get('gpu_memory_gb', 0)),
                        'machine_id': fields.get('machine_id', ''),
                        'location': fields.get('location', '')
                    })
                elif cloud == 'io_net':
                    offer.update({
                        'device_id': fields.get('device_id', ''),
                        'device_type': fields.get('device_type', ''),
                        'location': fields.get('location', '')
                    })
                
                offers.append(offer)
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing offer from Redis: {e}")
                continue
        
        logger.debug(f"Retrieved {len(offers)} offers from Redis stream")
        return offers
        
    except Exception as e:
        logger.error(f"Error reading from Redis stream: {e}")
        raise

def publish_metrics_to_redis(
    metrics: Dict,
    redis_conn: Optional[redis.Redis] = None
) -> bool:
    """
    Publish scraper metrics to Redis.
    
    Args:
        metrics: Dictionary containing scraper metrics
        redis_conn: Redis connection (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if redis_conn is None:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.error("REDIS_URL environment variable not set")
            return False
        redis_conn = redis.from_url(redis_url, decode_responses=True)
    
    try:
        # Store metrics with timestamp
        metrics_key = "scraper:metrics"
        metrics_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_requests': str(metrics.get('total_requests', 0)),
            'successful_requests': str(metrics.get('successful_requests', 0)),
            'failed_requests': str(metrics.get('failed_requests', 0)),
            'last_run': str(metrics.get('last_run', '')),
            'uptime_seconds': str(metrics.get('uptime_seconds', 0))
        }
        
        # Set metrics with expiration (24 hours)
        redis_conn.hset(metrics_key, mapping=metrics_data)
        redis_conn.expire(metrics_key, 86400)  # 24 hours
        
        logger.debug("Published metrics to Redis")
        return True
        
    except Exception as e:
        logger.error(f"Error publishing metrics to Redis: {e}")
        return False

def test_redis_connection(redis_url: Optional[str] = None) -> bool:
    """
    Test Redis connection.
    
    Args:
        redis_url: Redis connection URL (optional, uses env var if not provided)
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                logger.error("REDIS_URL environment variable not set")
                return False
        
        redis_conn = redis.from_url(redis_url, decode_responses=True)
        redis_conn.ping()
        
        # Test basic operations
        test_key = "test:connection"
        redis_conn.set(test_key, "test_value", ex=10)  # Expires in 10 seconds
        value = redis_conn.get(test_key)
        redis_conn.delete(test_key)
        
        if value == "test_value":
            logger.info("Redis connection test successful")
            return True
        else:
            logger.error("Redis connection test failed: value mismatch")
            return False
            
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False