import os
import time
import boto3
import botocore
from botocore.config import Config
from datetime import datetime, timedelta, timezone
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Disable AWS metadata service to prevent credential errors
os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

class ProviderError(Exception):
    """Base exception for provider errors"""
    pass

class ProviderTransientError(ProviderError):
    """Transient error that may be retried"""
    pass

class ProviderConfigError(ProviderError):
    """Configuration error that should not be retried"""
    pass

# AWS constants
AWS_REGIONS = ["us-east-1", "us-west-2", "eu-west-1"]
INSTANCE_TYPES = ["g4dn.xlarge", "g5.2xlarge", "p4d.24xlarge"]
CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

# Instance to GPU mapping
INSTANCE_GPU_MAP = {
    "g4dn.xlarge": "T4",
    "g4dn.2xlarge": "T4",
    "g4dn.4xlarge": "T4", 
    "g4dn.8xlarge": "T4",
    "g4dn.12xlarge": "T4",
    "g4dn.16xlarge": "T4",
    "g5.xlarge": "A10G",
    "g5.2xlarge": "A10G",
    "g5.4xlarge": "A10G",
    "g5.8xlarge": "A10G",
    "g5.12xlarge": "A10G",
    "g5.16xlarge": "A10G",
    "g5.24xlarge": "A10G",
    "g5.48xlarge": "A10G",
    "p4d.24xlarge": "A100",
    "p4de.24xlarge": "A100",
    "p5.48xlarge": "H100"
}

# GPU count per instance (for per-GPU pricing)
GPU_COUNT = {
    "g4dn.xlarge": 1,
    "g4dn.2xlarge": 1,
    "g4dn.4xlarge": 1,
    "g4dn.8xlarge": 1,
    "g4dn.12xlarge": 4,
    "g4dn.16xlarge": 1,
    "g5.xlarge": 1,
    "g5.2xlarge": 1,
    "g5.4xlarge": 1,
    "g5.8xlarge": 1,
    "g5.12xlarge": 4,
    "g5.16xlarge": 1,
    "g5.24xlarge": 4,
    "g5.48xlarge": 8,
    "p4d.24xlarge": 8,
    "p4de.24xlarge": 8,
    "p5.48xlarge": 8
}

_cache = None
_cache_time = 0

def fetch_aws_spot_prices(config: Dict[str, any]) -> List[Dict]:
    """Backward compatibility function"""
    return fetch_aws_spot_offers()

def fetch_aws_spot_offers() -> List[Dict]:
    """
    Fetch AWS Spot instance prices using unsigned credentials.
    """
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached AWS Spot data")
        return _cache

    offers = []
    latest_prices = {}  # Track latest price per instance type per region
    
    for region in AWS_REGIONS:
        region_offers = fetch_region_spot_prices(region)
        
        # Track latest prices to avoid duplicates
        for offer in region_offers:
            key = f"{offer['instance_type']}_{region}"
            if key not in latest_prices or offer['timestamp'] > latest_prices[key]['timestamp']:
                latest_prices[key] = offer
    
    # Convert latest prices to standardized format
    for offer in latest_prices.values():
        try:
            instance_type = offer['instance_type']
            gpu_model = INSTANCE_GPU_MAP.get(instance_type, instance_type)
            gpu_count = GPU_COUNT.get(instance_type, 1)
            
            # Calculate per-GPU price
            instance_price = offer['price']
            per_gpu_price = instance_price / gpu_count
            
            standardized_offer = {
                "instance_type": instance_type,
                "gpu_model": gpu_model,
                "price": per_gpu_price,
                "region": offer['region'],
                "timestamp": offer['timestamp'],
                "model": gpu_model,
                "usd_hr": round(per_gpu_price, 4)
            }
            
            offers.append(standardized_offer)
            
        except Exception as e:
            logger.warning(f"Error processing AWS offer {offer}: {e}")
            continue
    
    if not offers:
        raise ProviderTransientError("No valid AWS Spot offers found")
    
    # Cache successful result
    _cache = offers
    _cache_time = time.time()
    
    logger.info(f"Successfully fetched {len(offers)} AWS Spot offers")
    return offers

def fetch_region_spot_prices(region: str) -> List[Dict]:
    """Fetch spot prices for a specific AWS region."""
    offers = []
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Fetching AWS Spot prices for {region} (attempt {attempt + 1}/{MAX_RETRIES})")
            
            # Create client with unsigned config to avoid credential requirements
            config = Config(
                signature_version=botocore.UNSIGNED,
                region_name=region,
                retries={'max_attempts': 2}
            )
            
            client = boto3.client("ec2", region_name=region, config=config)
            
            # Get recent spot price history
            start_time = datetime.now(timezone.utc) - timedelta(minutes=65)
            
            response = client.describe_spot_price_history(
                InstanceTypes=INSTANCE_TYPES,
                ProductDescriptions=["Linux/UNIX (Amazon VPC)"],
                StartTime=start_time,
                MaxResults=100
            )
            
            spot_prices = response.get("SpotPriceHistory", [])
            
            if not spot_prices:
                logger.warning(f"No spot price data returned for region {region}")
                return []
            
            # Process spot prices
            for item in spot_prices:
                try:
                    instance_type = item.get("InstanceType")
                    spot_price = item.get("SpotPrice")
                    timestamp = item.get("Timestamp")
                    availability_zone = item.get("AvailabilityZone", "")
                    
                    if not all([instance_type, spot_price, timestamp]):
                        continue
                    
                    price_float = float(spot_price)
                    
                    # Basic validation
                    if price_float <= 0 or price_float > 1000:  # Reasonable bounds
                        continue
                    
                    offer = {
                        "instance_type": instance_type,
                        "price": price_float,
                        "region": region,
                        "availability_zone": availability_zone,
                        "timestamp": timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
                    }
                    
                    offers.append(offer)
                    
                except Exception as e:
                    logger.debug(f"Error processing AWS spot price item: {e}")
                    continue
            
            logger.debug(f"Fetched {len(offers)} spot prices from {region}")
            return offers
            
        except botocore.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code in ['UnauthorizedOperation', 'InvalidUserID.NotFound']:
                # Try unsigned access approach
                if attempt == MAX_RETRIES - 1:
                    logger.warning(f"AWS credentials issue in {region}, skipping: {e}")
                    return []
                
            elif error_code in ['RequestLimitExceeded', 'Throttling']:
                if attempt == MAX_RETRIES - 1:
                    raise ProviderTransientError(f"AWS rate limit exceeded for {region}")
                logger.warning(f"AWS rate limit in {region}, retrying in {RETRY_DELAY}s")
                time.sleep(RETRY_DELAY)
                
            else:
                if attempt == MAX_RETRIES - 1:
                    raise ProviderTransientError(f"AWS API error in {region}: {e}")
                logger.warning(f"AWS API error in {region} on attempt {attempt + 1}: {e}")
                time.sleep(RETRY_DELAY)
                
        except botocore.exceptions.EndpointConnectionError as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"AWS connection error for {region}: {e}")
            logger.warning(f"AWS connection error in {region} on attempt {attempt + 1}, retrying")
            time.sleep(RETRY_DELAY)
            
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"Unexpected AWS error in {region}: {e}")
            logger.warning(f"Unexpected AWS error in {region} on attempt {attempt + 1}: {e}")
            time.sleep(RETRY_DELAY)
    
    return []

# Plugin interface
def fetch() -> List[Dict]:
    """Main plugin interface function"""
    return fetch_aws_spot_offers()

# Plugin metadata
name = "aws_spot"