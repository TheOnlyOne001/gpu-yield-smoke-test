import os
import sys
import time
import logging
import schedule
import requests
import redis
import sentry_sdk
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv

from sentry_utils import init_sentry

# Remove the sys.path line as it's no longer needed
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Use local copies instead of API utils
from crypto_rates import get_crypto_rates
from power_prices import get_power_prices
from aws_spot import fetch_aws_spot_prices
from akash import fetch_akash_bids

# Add these imports after existing ones
from plugins import runpod, akash, aws_spot, vast_ai, io_net  # Add io_net here
from utils.publish import publish_to_redis

# Add these exception classes after imports
class ProviderError(Exception):
    """Base exception for provider errors"""
    pass

class ProviderTransientError(ProviderError):
    """Transient error that may be retried"""
    pass

class ProviderConfigError(ProviderError):
    """Configuration error that should not be retried"""
    pass

# --- Configuration and Setup ---

load_dotenv()

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log') if os.getenv("ENVIRONMENT") == "development" else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Sentry
init_sentry()

# --- Constants ---

REDIS_URL = os.getenv("REDIS_URL")
REDIS_STREAM_NAME = "raw_prices"
MAX_STREAM_LENGTH = 10000  # Prevent stream from growing indefinitely

MIN_DATA_QUALITY_SCORE = float(os.getenv("MIN_DATA_QUALITY_SCORE", 0.5))

@dataclass
class ScrapingMetrics:
    """Track scraping performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_records_processed: int = 0
    total_records_published: int = 0
    start_time: float = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def processing_rate(self) -> float:
        if self.total_records_processed == 0:
            return 0.0
        return (self.total_records_published / self.total_records_processed) * 100

# Global metrics tracker
metrics = ScrapingMetrics()

def reset_metrics_if_needed():
    """Reset global metrics every hour to avoid memory leak."""
    global metrics
    if time.time() - metrics.start_time > 3600:
        metrics = ScrapingMetrics()
        metrics.start_time = time.time()

# Enhanced data sources with better endpoint information
DATA_SOURCES = {
    "vast.ai": {
        "url": "https://console.vast.ai/api/v0/bundles/",
        "timeout": 15,
        "headers": {"User-Agent": "GPU-Yield-Calculator/1.0"},
        "rate_limit": 2
    },
    "runpod": {
        "url": "https://api.runpod.io/v2/gpuTypes",
        "method": "GET",
        "headers": {
            "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY', '')}",
            "Content-Type": "application/json",
            "User-Agent": "GPU-Yield-Calculator/1.0"
        },
        "timeout": 15,
        "rate_limit": 3
    },
    "aws_spot": {
        "custom_handler": fetch_aws_spot_prices,
        "rate_limit": 10
    },
    "akash": {
        "custom_handler": fetch_akash_bids,
        "rate_limit": 5
    },
    "io_net": {
        "url": "https://api.io.net/v1/devices",
        "timeout": 15,
        "headers": {"User-Agent": "GPU-Yield-Calculator/1.0"},
        "rate_limit": 3
    }
}

# --- Redis Connection with Retry Logic ---

def connect_to_redis(max_retries: int = 5) -> Optional[redis.Redis]:
    """Connect to Redis with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            if not REDIS_URL:
                logger.error("REDIS_URL environment variable not set")
                return None
                
            redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
            redis_conn.ping()
            logger.info("Successfully connected to Redis")
            return redis_conn
            
        except redis.exceptions.ConnectionError as e:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(f"Redis connection attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
    
    logger.error("Failed to connect to Redis after all retries")
    return None

redis_conn = connect_to_redis()
if not redis_conn:
    logger.critical("Cannot proceed without Redis connection")
    exit(1)

# --- Core Functions ---

def fetch_data(source_name: str, config: Dict[str, Any]) -> Optional[Dict]:
    """Enhanced data fetching with better error handling and rate limiting."""
    global metrics
    metrics.total_requests += 1
    
    try:
        # Rate limiting
        time.sleep(config.get('rate_limit', 1))

        # Custom handler support
        if 'custom_handler' in config:
            handler = config['custom_handler']
            data = handler(config)
            metrics.successful_requests += 1
            logger.info(f"Successfully fetched custom data from {source_name}")
            return data

        # Prepare request
        method = config.get('method', 'GET').upper()
        url = config['url']
        headers = config.get('headers', {})
        timeout = config.get('timeout', 15)
        
        # Make request
        if method == 'POST':
            payload = config.get('payload', {})
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        else:
            response = requests.get(url, headers=headers, timeout=timeout)
        
        response.raise_for_status()
        
        # Validate response
        if not response.content:
            raise ValueError("Empty response received")
        
        data = response.json()
        
        # Basic data validation
        if not isinstance(data, (dict, list)):
            raise ValueError("Invalid JSON structure")
        
        metrics.successful_requests += 1
        logger.info(f"Successfully fetched data from {source_name} (size: {len(str(data))} chars)")
        return data
        
    except requests.exceptions.Timeout:
        metrics.failed_requests += 1
        logger.error(f"Timeout fetching data from {source_name}")
        sentry_sdk.capture_message(f"Timeout for {source_name}", level="warning")
        
    except requests.exceptions.HTTPError as e:
        metrics.failed_requests += 1
        logger.error(f"HTTP error fetching data from {source_name}: {e.response.status_code}")
        sentry_sdk.capture_exception(e)
        
    except requests.exceptions.RequestException as e:
        metrics.failed_requests += 1
        logger.error(f"Network error fetching data from {source_name}: {e}")
        sentry_sdk.capture_exception(e)
        
    except json.JSONDecodeError as e:
        metrics.failed_requests += 1
        logger.error(f"JSON decode error for {source_name}: {e}")
        sentry_sdk.capture_exception(e)
        
    except Exception as e:
        metrics.failed_requests += 1
        logger.error(f"Unexpected error fetching data from {source_name}: {e}")
        sentry_sdk.capture_exception(e)
    
    return None

def fetch_data_with_retry(source_name: str, config: Dict[str, Any], max_retries: int = 2) -> Optional[Dict]:
    """Enhanced data fetching with retry logic for transient failures"""
    global metrics

    for attempt in range(max_retries + 1):
        try:
            result = fetch_data(source_name, config)
            if result:
                return result
            elif attempt < max_retries:
                logger.warning(f"No data from {source_name}, retrying attempt {attempt + 1}")
                time.sleep(2 ** attempt)
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Retry {attempt + 1} for {source_name}: {e}")
                time.sleep(2 ** attempt)
            else:
                logger.error(f"Final attempt failed for {source_name}: {e}")
                metrics.failed_requests += 1

    return None

def normalize_gpu_name(gpu_name: str) -> str:
    """Normalize GPU names for consistent comparison."""
    if not gpu_name:
        return "Unknown"
    
    # Common normalization patterns
    gpu_name = gpu_name.upper().strip()
    
    # Remove common prefixes/suffixes
    gpu_name = gpu_name.replace("NVIDIA ", "").replace("AMD ", "")
    gpu_name = gpu_name.replace("GEFORCE ", "").replace("RADEON ", "")
    
    # Standardize RTX naming
    if "RTX" in gpu_name and "RTX" not in gpu_name[:3]:
        gpu_name = gpu_name.replace("RTX", "").strip()
        gpu_name = f"RTX {gpu_name}"
    
    # Handle common variations
    gpu_name = gpu_name.replace("RTX4090", "RTX 4090")
    gpu_name = gpu_name.replace("RTX4080", "RTX 4080")
    gpu_name = gpu_name.replace("RTX4070", "RTX 4070")
    
    return gpu_name.title()

def validate_price(price: Any) -> Optional[float]:
    """Validate and normalize price values."""
    try:
        price_float = float(price)
        
        # Reasonable bounds checking
        if price_float <= 0:
            return None
        if price_float > 100:  # Unreasonably high
            return None
        if price_float < 0.001:  # Too low to be realistic
            return None
            
        return round(price_float, 4)
    except (ValueError, TypeError):
        return None

def normalize_and_publish(data: Any, source_name: str, r_conn: redis.Redis) -> int:
    """Enhanced data normalization with better quality control."""
    global metrics
    records_published = 0
    
    try:
        # Handle AWS Spot data differently for better structure
        if source_name == "aws_spot":
            # AWS data is already well-structured from the plugin
            if isinstance(data, list):
                offers = data
            else:
                offers = [data] if isinstance(data, dict) else []
                
            # Use the specialized publish function for AWS
            records_published = publish_to_redis(source_name, offers, r_conn)
            metrics.total_records_published += records_published
            return records_published
        
        # Handle other data sources
        if source_name == "vast.ai":
            offers = data.get('offers', []) if isinstance(data, dict) else []
        elif source_name == "runpod":
            # Handle GraphQL response structure
            if isinstance(data, dict) and 'data' in data:
                offers = data['data'].get('podTypes', [])
            else:
                offers = []
        else:
            offers = data if isinstance(data, list) else data.get('offers', [])
        
        if not isinstance(offers, list):
            logger.warning(f"No valid offers list found in {source_name} response")
            return 0
        
        metrics.total_records_processed += len(offers)
        
        # Convert to standardized format
        standardized_offers = []
        
        for item in offers:
            try:
                # Source-specific field mapping with validation
                if source_name == "vast.ai":
                    gpu_model = item.get('gpu_name') or item.get('gpu_display_name', 'Unknown')
                    price = item.get('dph_total') or item.get('cost_per_hr', 0)
                    region = item.get('geolocation', 'Unknown')
                    availability = item.get('num_gpus', 1)
                    
                elif source_name == "runpod":
                    gpu_model = item.get('displayName', 'Unknown')
                    price = item.get('costPerHr', 0)
                    region = 'Global'  # RunPod doesn't specify regions in this endpoint
                    availability = 1
                    
                else:
                    # Generic fallback
                    gpu_model = item.get('gpu_model') or item.get('model', 'Unknown')
                    price = item.get('price') or item.get('hourly_price', 0)
                    region = item.get('region', 'Unknown')
                    availability = item.get('availability', 1)
                
                # Normalize and validate data
                gpu_model = normalize_gpu_name(gpu_model)
                validated_price = validate_price(price)
                
                if not validated_price:
                    continue  # Skip invalid prices
                
                # Create standardized offer
                offer = {
                    'model': gpu_model,
                    'usd_hr': validated_price,
                    'region': str(region)[:50],  # Limit region length
                    'availability': max(1, int(availability)) if availability else 1,
                    'id': item.get('id', ''),
                    'quality_score': calculate_quality_score(item)
                }
                
                standardized_offers.append(offer)
                
            except Exception as e:
                logger.warning(f"Error processing record from {source_name}: {e}")
                continue
        
        # Use the publish utility
        records_published = publish_to_redis(source_name, standardized_offers, r_conn)
        metrics.total_records_published += records_published
        logger.info(f"Published {records_published}/{len(standardized_offers)} records from {source_name}")
        
    except Exception as e:
        logger.error(f"Error in normalize_and_publish for {source_name}: {e}")
        sentry_sdk.capture_exception(e)
    
    return records_published

def calculate_quality_score(item: Dict) -> float:
    """Calculate a data quality score for filtering."""
    score = 0.0
    max_score = 1.0
    
    # Check for required fields
    if item.get('gpu_name') or item.get('displayName'):
        score += 0.3
    if item.get('dph_total') or item.get('costPerHr'):
        score += 0.4
    if item.get('geolocation') or item.get('region'):
        score += 0.1
    if item.get('id'):
        score += 0.1
    if item.get('num_gpus') or item.get('availability'):
        score += 0.1
    
    return min(score, max_score)

def run_scrape_job():
    """Enhanced main scraping job with comprehensive monitoring."""
    global metrics
    reset_metrics_if_needed()
    
    logger.info("--- Starting new scrape cycle ---")
    cycle_start = time.time()
    cycle_records = 0
    
    for source_name, config in DATA_SOURCES.items():
        try:
            logger.info(f"Scraping {source_name}...")
            data = fetch_data(source_name, config)
            
            if data:
                published = normalize_and_publish(data, source_name, redis_conn)
                cycle_records += published
                
                # Log source-specific metrics
                logger.info(f"{source_name}: {published} records published")
            else:
                logger.warning(f"No data received from {source_name}")
                
        except Exception as e:
            logger.error(f"Unexpected error processing {source_name}: {e}")
            sentry_sdk.capture_exception(e)
    
    cycle_duration = time.time() - cycle_start
    
    # Log cycle summary
    logger.info(f"--- Scrape cycle completed ---")
    logger.info(f"Duration: {cycle_duration:.2f}s")
    logger.info(f"Records this cycle: {cycle_records}")
    logger.info(f"Success rate: {metrics.success_rate:.1f}%")
    logger.info(f"Processing rate: {metrics.processing_rate:.1f}%")
    
    # Send metrics to monitoring (if configured)
    send_metrics_to_monitoring(cycle_duration, cycle_records)

def send_metrics_to_monitoring(duration: float, records: int):
    """Send metrics to external monitoring service."""
    try:
        # Store metrics in Redis for the API stats endpoint
        metrics_data = {
            'last_scrape_duration': duration,
            'last_scrape_records': records,
            'last_scrape_timestamp': int(time.time()),
            'total_requests': metrics.total_requests,
            'success_rate': metrics.success_rate,
            'processing_rate': metrics.processing_rate
        }
        
        redis_conn.hset('scraper:metrics', mapping=metrics_data)
        redis_conn.expire('scraper:metrics', 3600)  # Expire after 1 hour
        
    except Exception as e:
        logger.warning(f"Error storing metrics: {e}")

def cleanup_old_data():
    """Clean up old data to prevent resource exhaustion."""
    try:
        # Keep only last 24 hours of data (approximately)
        cutoff_timestamp = int(time.time()) - (24 * 3600)
        
        # This is a simplified cleanup - in production you might want more sophisticated logic
        logger.info("Cleanup task completed")
        
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")

def test_new_plugins():
    """
    Test function to verify the new plugin implementations.
    """
    logger.info("🧪 Testing new plugins...")
    
    plugins_to_test = [runpod, akash, aws_spot, vast_ai, io_net]  # Add io_net here
    results = {}
    
    for plugin in plugins_to_test:
        plugin_name = getattr(plugin, 'name', plugin.__name__)
        
        try:
            logger.info(f"Testing {plugin_name}...")
            start_time = time.time()
            
            offers = plugin.fetch()
            duration = time.time() - start_time
            
            if offers:
                # Validate offers format
                valid_count = 0
                for offer in offers:
                    if (isinstance(offer, dict) and 
                        'model' in offer and 
                        'usd_hr' in offer and 
                        'region' in offer):
                        valid_count += 1
                
                results[plugin_name] = {
                    'status': 'success',
                    'total_offers': len(offers),
                    'valid_offers': valid_count,
                    'duration': duration,
                    'sample': offers[:3] if offers else []
                }
                logger.info(f"✅ {plugin_name}: {valid_count} valid offers in {duration:.2f}s")
            else:
                results[plugin_name] = {
                    'status': 'no_data',
                    'total_offers': 0,
                    'duration': duration
                }
                logger.warning(f"⚠️  {plugin_name}: No offers returned")
                
        except Exception as e:
            results[plugin_name] = {
                'status': 'error',
                'error': str(e),
                'duration': time.time() - start_time if 'start_time' in locals() else 0
            }
            logger.error(f"❌ {plugin_name}: {e}")
    
    # Print summary
    print("\n" + "="*60)
    print("NEW PLUGIN TEST SUMMARY")
    print("="*60)
    
    for plugin_name, result in results.items():
        status = result['status']
        if status == 'success':
            print(f"✅ {plugin_name:12} | {result['valid_offers']:3d} offers | {result['duration']:.2f}s")
            # Show sample data
            if result['sample']:
                sample = result['sample'][0]
                print(f"   Sample: {sample.get('model', 'N/A')} - ${sample.get('usd_hr', 0):.4f}/hr")
        elif status == 'no_data':
            print(f"⚠️  {plugin_name:12} | No data returned | {result['duration']:.2f}s")
        else:
            print(f"❌ {plugin_name:12} | ERROR: {result.get('error', 'Unknown')}")
    
    total_offers = sum(r.get('valid_offers', 0) for r in results.values())
    successful = sum(1 for r in results.values() if r['status'] == 'success')
    
    print("-" * 60)
    print(f"Total valid offers: {total_offers}")
    print(f"Success rate: {successful}/{len(plugins_to_test)} ({(successful/len(plugins_to_test)*100):.1f}%)")
    
    # Expected results check
    expectations = {
        'runpod': 30,
        'aws_spot': 3,
        'akash': 20,
        'vast_ai': 50,
        'io_net': 25  # Add expectation for IO.net
    }
    
    print("\n📊 EXPECTATION CHECK:")
    for plugin_name, expected in expectations.items():
        actual = results.get(plugin_name, {}).get('valid_offers', 0)
        status = "✅ PASS" if actual >= expected else "❌ FAIL"
        print(f"{status} {plugin_name}: {actual} >= {expected} expected")
    
    print("="*60)
    
    return results

# --- Main Execution ---

if __name__ == "__main__":
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        logger.info("🧪 Running in test mode...")
        test_results = test_new_plugins()
        exit(0)
    
    # Check if running new plugin test
    if len(sys.argv) > 1 and sys.argv[1] == "test-new":
        logger.info("🧪 Running new plugin test mode...")
        test_results = test_new_plugins()
        exit(0)
    
    logger.info("🚀 Enhanced GPU Price Scraper starting...")
    sentry_sdk.capture_message("Enhanced Scraper Service Started")
    
    metrics.start_time = time.time()
    
    # Schedule jobs
    schedule.every(2).minutes.do(run_scrape_job)  # Main scraping every 2 minutes
    schedule.every().hour.do(cleanup_old_data)    # Cleanup every hour
    
    # Run initial scrape
    logger.info("Running initial scrape job...")
    run_scrape_job()
    
    # Main scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        logger.info("Scraper stopped by user")
    except Exception as e:
        logger.critical(f"Critical error in main loop: {e}")
        sentry_sdk.capture_exception(e)
        exit(1)