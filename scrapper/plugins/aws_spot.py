import os
import boto3
import time
import logging
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Set

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

# AWS constants - Expanded list of GPU instances
AWS_REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "us-east-2", "ap-southeast-1"]

# More comprehensive list of GPU instances
GPU_INSTANCE_FAMILIES = {
    # T4 instances
    "g4dn": ["xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge", "16xlarge"],
    "g4ad": ["xlarge", "2xlarge", "4xlarge", "8xlarge", "16xlarge"],
    
    # A10G instances  
    "g5": ["xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge", "16xlarge", "24xlarge", "48xlarge"],
    
    # V100 instances
    "p3": ["2xlarge", "8xlarge", "16xlarge"],
    "p3dn": ["24xlarge"],
    
    # A100 instances
    "p4d": ["24xlarge"],
    "p4de": ["24xlarge"],
    
    # H100 instances (if available)
    "p5": ["48xlarge"],
    
    # Older generation (K80)
    "p2": ["xlarge", "8xlarge", "16xlarge"],
    
    # M60 instances
    "g3": ["4xlarge", "8xlarge", "16xlarge"],
    "g3s": ["xlarge"]
}

# Generate full instance type list
INSTANCE_TYPES = []
for family, sizes in GPU_INSTANCE_FAMILIES.items():
    for size in sizes:
        INSTANCE_TYPES.append(f"{family}.{size}")

# Instance to GPU mapping with counts
INSTANCE_GPU_MAP = {
    # G4dn - T4
    "g4dn.xlarge": {"gpu": "T4", "count": 1, "memory": 16},
    "g4dn.2xlarge": {"gpu": "T4", "count": 1, "memory": 16},
    "g4dn.4xlarge": {"gpu": "T4", "count": 1, "memory": 16},
    "g4dn.8xlarge": {"gpu": "T4", "count": 1, "memory": 16},
    "g4dn.12xlarge": {"gpu": "T4", "count": 4, "memory": 64},
    "g4dn.16xlarge": {"gpu": "T4", "count": 1, "memory": 16},
    
    # G4ad - AMD
    "g4ad.xlarge": {"gpu": "Radeon Pro V520", "count": 1, "memory": 8},
    "g4ad.2xlarge": {"gpu": "Radeon Pro V520", "count": 1, "memory": 8},
    "g4ad.4xlarge": {"gpu": "Radeon Pro V520", "count": 1, "memory": 8},
    "g4ad.8xlarge": {"gpu": "Radeon Pro V520", "count": 2, "memory": 16},
    "g4ad.16xlarge": {"gpu": "Radeon Pro V520", "count": 4, "memory": 32},
    
    # G5 - A10G
    "g5.xlarge": {"gpu": "A10G", "count": 1, "memory": 24},
    "g5.2xlarge": {"gpu": "A10G", "count": 1, "memory": 24},
    "g5.4xlarge": {"gpu": "A10G", "count": 1, "memory": 24},
    "g5.8xlarge": {"gpu": "A10G", "count": 1, "memory": 24},
    "g5.12xlarge": {"gpu": "A10G", "count": 4, "memory": 96},
    "g5.16xlarge": {"gpu": "A10G", "count": 1, "memory": 24},
    "g5.24xlarge": {"gpu": "A10G", "count": 4, "memory": 96},
    "g5.48xlarge": {"gpu": "A10G", "count": 8, "memory": 192},
    
    # P3 - V100
    "p3.2xlarge": {"gpu": "V100", "count": 1, "memory": 16},
    "p3.8xlarge": {"gpu": "V100", "count": 4, "memory": 64},
    "p3.16xlarge": {"gpu": "V100", "count": 8, "memory": 128},
    "p3dn.24xlarge": {"gpu": "V100", "count": 8, "memory": 256},
    
    # P4 - A100
    "p4d.24xlarge": {"gpu": "A100", "count": 8, "memory": 320},
    "p4de.24xlarge": {"gpu": "A100", "count": 8, "memory": 640},
    
    # P5 - H100
    "p5.48xlarge": {"gpu": "H100", "count": 8, "memory": 640},
    
    # P2 - K80
    "p2.xlarge": {"gpu": "K80", "count": 1, "memory": 12},
    "p2.8xlarge": {"gpu": "K80", "count": 8, "memory": 96},
    "p2.16xlarge": {"gpu": "K80", "count": 16, "memory": 192},
    
    # G3 - M60
    "g3.4xlarge": {"gpu": "M60", "count": 1, "memory": 8},
    "g3.8xlarge": {"gpu": "M60", "count": 2, "memory": 16},
    "g3.16xlarge": {"gpu": "M60", "count": 4, "memory": 32},
    "g3s.xlarge": {"gpu": "M60", "count": 1, "memory": 8},
}

# Product descriptions to try
PRODUCT_DESCRIPTIONS = [
    "Linux/UNIX",
    "Linux/UNIX (Amazon VPC)",
    "SUSE Linux",
    "SUSE Linux (Amazon VPC)",
    "Red Hat Enterprise Linux",
    "Red Hat Enterprise Linux (Amazon VPC)"
]

CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

_cache = None
_cache_time = 0

def check_aws_credentials() -> bool:
    """Check if AWS credentials are available and valid"""
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not aws_access_key or not aws_secret_key:
        logger.debug("AWS credentials not found in environment variables")
        return False
    
    if aws_access_key.strip() == "" or aws_secret_key.strip() == "":
        logger.debug("AWS credentials are empty")
        return False
        
    logger.debug("AWS credentials found")
    return True

def create_ec2_client(region: str):
    """Create EC2 client with explicit credentials"""
    if not check_aws_credentials():
        raise ProviderConfigError("AWS credentials not found or empty")
    
    config = Config(
        retries={'max_attempts': 3, 'mode': 'adaptive'},
        read_timeout=30,
        connect_timeout=30
    )
    
    try:
        client = boto3.client(
            'ec2',
            region_name=region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            config=config
        )
        return client
    except Exception as e:
        raise ProviderConfigError(f"Failed to create AWS EC2 client: {e}")

def get_all_spot_instance_types(ec2_client) -> Set[str]:
    """Get all instance types that support spot pricing in the region"""
    try:
        # Get all instance types in the region
        paginator = ec2_client.get_paginator('describe_instance_types')
        all_types = set()
        
        for page in paginator.paginate():
            for instance_type in page['InstanceTypes']:
                if instance_type.get('SupportedUsageClasses', []):
                    if 'spot' in instance_type['SupportedUsageClasses']:
                        all_types.add(instance_type['InstanceType'])
        
        logger.debug(f"Found {len(all_types)} instance types supporting spot")
        return all_types
    except Exception as e:
        logger.warning(f"Failed to get instance types: {e}")
        return set()

def fetch_aws_spot_prices() -> List[Dict]:
    """Fetch AWS Spot instance prices"""
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached AWS Spot data")
        return _cache
    
    # Check credentials upfront
    if not check_aws_credentials():
        logger.warning("AWS credentials not available, using synthetic data")
        return get_synthetic_aws_data()
    
    all_offers = []
    regions_tried = 0
    
    for region in AWS_REGIONS:
        if regions_tried >= 2 and all_offers:  # Stop after 2 regions if we have data
            break
            
        try:
            logger.info(f"Fetching AWS Spot prices for region: {region}")
            regions_tried += 1
            
            ec2_client = create_ec2_client(region)
            
            # First, check what spot instance types are available
            spot_types = get_all_spot_instance_types(ec2_client)
            gpu_spot_types = [t for t in INSTANCE_TYPES if t in spot_types]
            
            if gpu_spot_types:
                logger.debug(f"GPU instances with spot support in {region}: {len(gpu_spot_types)}")
            
            # Try different approaches to get spot prices
            offers = []
            
            # Approach 1: Try with specific instance types
            for product_desc in PRODUCT_DESCRIPTIONS[:2]:  # Try first 2 product descriptions
                if offers:  # Stop if we found offers
                    break
                    
                # Use smaller batches to avoid timeouts
                for i in range(0, len(INSTANCE_TYPES), 10):
                    batch = INSTANCE_TYPES[i:i+10]
                    
                    try:
                        response = ec2_client.describe_spot_price_history(
                            InstanceTypes=batch,
                            ProductDescriptions=[product_desc],
                            MaxResults=100,
                            StartTime=datetime.now(timezone.utc) - timedelta(hours=1)
                        )
                        
                        spot_prices = response.get('SpotPriceHistory', [])
                        if spot_prices:
                            logger.debug(f"Found {len(spot_prices)} prices for {product_desc} in batch {i//10 + 1}")
                            offers.extend(process_spot_prices(spot_prices, region))
                            
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'InvalidParameterValue':
                            # Some instance types might not be valid in this region
                            continue
                        else:
                            raise
            
            # Approach 2: Try without specifying instance types
            if not offers:
                logger.debug(f"Trying generic spot price query for {region}")
                try:
                    response = ec2_client.describe_spot_price_history(
                        ProductDescriptions=["Linux/UNIX (Amazon VPC)"],
                        MaxResults=1000,  # Get more results
                        StartTime=datetime.now(timezone.utc) - timedelta(hours=6)
                    )
                    
                    all_prices = response.get('SpotPriceHistory', [])
                    # Filter for GPU instances
                    gpu_prices = [p for p in all_prices if p['InstanceType'] in INSTANCE_GPU_MAP]
                    
                    if gpu_prices:
                        logger.debug(f"Found {len(gpu_prices)} GPU spot prices in generic query")
                        offers.extend(process_spot_prices(gpu_prices, region))
                        
                except Exception as e:
                    logger.warning(f"Generic query failed: {e}")
            
            if offers:
                logger.info(f"Successfully fetched {len(offers)} AWS Spot offers from {region}")
                all_offers.extend(offers)
            else:
                logger.warning(f"No GPU spot prices found in {region}")
                
        except ProviderConfigError as e:
            logger.warning(f"AWS configuration error: {e}")
            return get_synthetic_aws_data()
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.warning(f"AWS API error in {region}: {error_code}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error in {region}: {e}")
            continue
    
    if not all_offers:
        logger.warning("No real AWS data available, using synthetic data")
        all_offers = get_synthetic_aws_data()
    else:
        # Remove duplicates (keep latest price for each instance type/region combo)
        unique_offers = {}
        for offer in all_offers:
            key = f"{offer['instance_type']}_{offer['region']}"
            if key not in unique_offers or offer.get('timestamp', '') > unique_offers[key].get('timestamp', ''):
                unique_offers[key] = offer
        all_offers = list(unique_offers.values())
    
    # Cache successful result
    _cache = all_offers
    _cache_time = time.time()
    
    return all_offers

def process_spot_prices(spot_prices: List[Dict], region: str) -> List[Dict]:
    """Process spot price entries into offers"""
    offers = []
    price_map = {}
    
    for price_entry in spot_prices:
        instance_type = price_entry['InstanceType']
        
        if instance_type not in INSTANCE_GPU_MAP:
            continue
            
        spot_price = float(price_entry['SpotPrice'])
        timestamp = price_entry['Timestamp']
        
        # Keep only the most recent price for each instance type
        if instance_type not in price_map or timestamp > price_map[instance_type]['timestamp']:
            price_map[instance_type] = {
                'price': spot_price,
                'timestamp': timestamp,
                'availability_zone': price_entry.get('AvailabilityZone', '')
            }
    
    # Convert to offers
    for instance_type, price_data in price_map.items():
        gpu_info = INSTANCE_GPU_MAP[instance_type]
        
        # Calculate per-GPU price
        per_gpu_price = price_data['price'] / gpu_info['count']
        
        offer = {
            "model": gpu_info["gpu"],
            "usd_hr": round(per_gpu_price, 4),
            "region": region,
            "availability": gpu_info["count"],
            "instance_type": instance_type,
            "provider": "aws_spot",
            "total_instance_price": round(price_data['price'], 4),
            "gpu_memory_gb": gpu_info["memory"],
            "timestamp": price_data['timestamp'].isoformat() if hasattr(price_data['timestamp'], 'isoformat') else str(price_data['timestamp'])
        }
        
        offers.append(offer)
    
    return offers

def get_synthetic_aws_data() -> List[Dict]:
    """Generate realistic synthetic AWS Spot data"""
    synthetic_data = []
    
    # Base prices for different GPU types (per GPU)
    base_prices = {
        "T4": {"us-east-1": 0.1578, "us-west-2": 0.1678, "eu-west-1": 0.1878},
        "A10G": {"us-east-1": 0.3360, "us-west-2": 0.3560, "eu-west-1": 0.3960},
        "V100": {"us-east-1": 0.9180, "us-west-2": 0.9580, "eu-west-1": 1.0180},
        "A100": {"us-east-1": 1.2290, "us-west-2": 1.2890, "eu-west-1": 1.3890},
        "K80": {"us-east-1": 0.0900, "us-west-2": 0.0950, "eu-west-1": 0.1050},
        "M60": {"us-east-1": 0.2100, "us-west-2": 0.2200, "eu-west-1": 0.2400}
    }
    
    # Generate offers for common instances
    common_instances = [
        ("g4dn.xlarge", "T4", 1),
        ("g4dn.2xlarge", "T4", 1),
        ("g5.xlarge", "A10G", 1),
        ("g5.2xlarge", "A10G", 1),
        ("g5.4xlarge", "A10G", 1),
        ("p3.2xlarge", "V100", 1),
        ("p3.8xlarge", "V100", 4),
        ("p4d.24xlarge", "A100", 8),
    ]
    
    for instance_type, gpu_type, gpu_count in common_instances:
        for region in ["us-east-1", "us-west-2"]:
            if gpu_type in base_prices and region in base_prices[gpu_type]:
                base_price = base_prices[gpu_type][region]
                # Add some variance (±10%)
                variance = base_price * 0.1
                price = base_price + (variance * (0.5 - (hash(f"{instance_type}{region}") % 100) / 100))
                
                offer = {
                    "model": gpu_type,
                    "usd_hr": round(price, 4),
                    "region": region,
                    "availability": gpu_count,
                    "instance_type": instance_type,
                    "provider": "aws_spot",
                    "synthetic": True,
                    "gpu_memory_gb": INSTANCE_GPU_MAP.get(instance_type, {}).get("memory", 16)
                }
                synthetic_data.append(offer)
    
    return synthetic_data

# Plugin interface
def fetch() -> List[Dict]:
    """Main plugin interface function"""
    return fetch_aws_spot_prices()

# Plugin metadata
name = "aws_spot"