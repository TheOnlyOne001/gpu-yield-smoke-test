# api/utils/aws_spot_enrichment.py
import redis
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Instance metadata for enrichment (keeping the existing comprehensive data)
AWS_INSTANCE_METADATA = {
    # G4dn - T4 instances
    "g4dn.xlarge": {
        "vcpu": 4, "ram_gb": 16, "network": "Up to 25 Gbps", 
        "storage_gb": 125, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "T4"
    },
    "g4dn.2xlarge": {
        "vcpu": 8, "ram_gb": 32, "network": "Up to 25 Gbps", 
        "storage_gb": 225, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "T4"
    },
    "g4dn.4xlarge": {
        "vcpu": 16, "ram_gb": 64, "network": "Up to 25 Gbps", 
        "storage_gb": 225, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "T4"
    },
    "g4dn.8xlarge": {
        "vcpu": 32, "ram_gb": 128, "network": "50 Gbps", 
        "storage_gb": 900, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "T4"
    },
    "g4dn.12xlarge": {
        "vcpu": 48, "ram_gb": 192, "network": "50 Gbps", 
        "storage_gb": 900, "ebs_optimized": True,
        "gpu_count": 4, "gpu_model": "T4"
    },
    "g4dn.16xlarge": {
        "vcpu": 64, "ram_gb": 256, "network": "50 Gbps", 
        "storage_gb": 900, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "T4"
    },
    
    # G5 - A10G instances
    "g5.xlarge": {
        "vcpu": 4, "ram_gb": 16, "network": "Up to 10 Gbps", 
        "storage_gb": 250, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "A10G"
    },
    "g5.2xlarge": {
        "vcpu": 8, "ram_gb": 32, "network": "Up to 10 Gbps", 
        "storage_gb": 450, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "A10G"
    },
    "g5.4xlarge": {
        "vcpu": 16, "ram_gb": 64, "network": "Up to 25 Gbps", 
        "storage_gb": 600, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "A10G"
    },
    "g5.8xlarge": {
        "vcpu": 32, "ram_gb": 128, "network": "25 Gbps", 
        "storage_gb": 900, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "A10G"
    },
    "g5.12xlarge": {
        "vcpu": 48, "ram_gb": 192, "network": "40 Gbps", 
        "storage_gb": 3800, "ebs_optimized": True,
        "gpu_count": 4, "gpu_model": "A10G"
    },
    "g5.16xlarge": {
        "vcpu": 64, "ram_gb": 256, "network": "25 Gbps", 
        "storage_gb": 1900, "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "A10G"
    },
    "g5.24xlarge": {
        "vcpu": 96, "ram_gb": 384, "network": "50 Gbps", 
        "storage_gb": 3800, "ebs_optimized": True,
        "gpu_count": 4, "gpu_model": "A10G"
    },
    "g5.48xlarge": {
        "vcpu": 192, "ram_gb": 768, "network": "100 Gbps", 
        "storage_gb": 7600, "ebs_optimized": True,
        "gpu_count": 8, "gpu_model": "A10G"
    },
    
    # P3 - V100 instances
    "p3.2xlarge": {
        "vcpu": 8, "ram_gb": 61, "network": "Up to 10 Gbps", 
        "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "V100"
    },
    "p3.8xlarge": {
        "vcpu": 32, "ram_gb": 244, "network": "10 Gbps", 
        "ebs_optimized": True,
        "gpu_count": 4, "gpu_model": "V100"
    },
    "p3.16xlarge": {
        "vcpu": 64, "ram_gb": 488, "network": "25 Gbps", 
        "ebs_optimized": True,
        "gpu_count": 8, "gpu_model": "V100"
    },
    "p3dn.24xlarge": {
        "vcpu": 96, "ram_gb": 768, "network": "100 Gbps", 
        "storage_gb": 1800, "ebs_optimized": True,
        "gpu_count": 8, "gpu_model": "V100"
    },
    
    # P4 - A100 instances
    "p4d.24xlarge": {
        "vcpu": 96, "ram_gb": 1152, "network": "400 Gbps", 
        "storage_gb": 8000, "ebs_optimized": True,
        "gpu_count": 8, "gpu_model": "A100"
    },
    "p4de.24xlarge": {
        "vcpu": 96, "ram_gb": 1152, "network": "400 Gbps", 
        "storage_gb": 8000, "ebs_optimized": True,
        "gpu_count": 8, "gpu_model": "A100"
    },
    
    # P5 - H100 instances
    "p5.48xlarge": {
        "vcpu": 192, "ram_gb": 2048, "network": "3200 Gbps", 
        "storage_gb": 30720, "ebs_optimized": True,
        "gpu_count": 8, "gpu_model": "H100"
    },
    
    # P2 - K80 instances
    "p2.xlarge": {
        "vcpu": 4, "ram_gb": 61, "network": "High", 
        "ebs_optimized": True,
        "gpu_count": 1, "gpu_model": "K80"
    },
    "p2.8xlarge": {
        "vcpu": 32, "ram_gb": 488, "network": "10 Gbps", 
        "ebs_optimized": True,
        "gpu_count": 8, "gpu_model": "K80"
    },
    "p2.16xlarge": {
        "vcpu": 64, "ram_gb": 732, "network": "20 Gbps", 
        "ebs_optimized": True,
        "gpu_count": 16, "gpu_model": "K80"
    },
}

# Regional power costs ($/kWh)
REGION_POWER_COSTS = {
    "us-east-1": 0.12,
    "us-west-2": 0.09,
    "us-east-2": 0.11,
    "us-west-1": 0.15,
    "eu-west-1": 0.18,
    "eu-central-1": 0.20,
    "ap-southeast-1": 0.15,
    "ap-northeast-1": 0.17,
    "ap-south-1": 0.13,
    "ca-central-1": 0.10,
    "sa-east-1": 0.14,
}

# GPU TDP values (Watts)
GPU_TDP_WATTS = {
    "T4": 70,
    "A10G": 150,
    "V100": 300,
    "A100": 400,
    "H100": 700,
    "K80": 300,
    "M60": 300,
    "RTX6000": 300,
}

# AWS Region display names
AWS_REGION_DISPLAY = {
    "us-east-1": "N. Virginia",
    "us-west-2": "Oregon", 
    "us-east-2": "Ohio",
    "us-west-1": "N. California",
    "eu-west-1": "Ireland",
    "eu-central-1": "Frankfurt",
    "ap-southeast-1": "Singapore",
    "ap-northeast-1": "Tokyo",
    "ap-south-1": "Mumbai",
    "ca-central-1": "Canada",
    "sa-east-1": "São Paulo",
}

def calculate_interruption_risk(availability: int) -> str:
    """Calculate spot interruption risk based on availability."""
    if availability >= 4:
        return "low"
    elif availability >= 2:
        return "medium"
    else:
        return "high"

def calculate_freshness(timestamp: str) -> str:
    """Calculate data freshness based on timestamp."""
    try:
        if isinstance(timestamp, str):
            # Handle both ISO format and timestamp with Z
            if timestamp.endswith('Z'):
                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif '+' in timestamp or timestamp.endswith('00:00'):
                ts = datetime.fromisoformat(timestamp)
            else:
                # Assume UTC if no timezone info
                ts = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
        else:
            ts = timestamp
            
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        
        if age_hours < 1:
            return "live"
        elif age_hours < 6:
            return "recent"
        else:
            return "stale"
    except Exception as e:
        logger.warning(f"Error calculating freshness for timestamp {timestamp}: {e}")
        return "unknown"

def calculate_yield_metrics(offer: Dict) -> Dict:
    """Calculate yield metrics for an offer."""
    try:
        region = offer.get("region", "us-east-1")
        gpu_model = offer.get("model", "T4")
        usd_hr = float(offer.get("usd_hr", 0))
        
        # Get power cost and TDP
        power_cost_kwh = REGION_POWER_COSTS.get(region, 0.12)
        tdp_watts = GPU_TDP_WATTS.get(gpu_model, 300)
        
        # Calculate power cost per hour
        power_cost_per_hour = (tdp_watts / 1000) * power_cost_kwh
        
        # Calculate net yield
        net_yield = usd_hr - power_cost_per_hour
        
        # Calculate margin percentage
        margin = (net_yield / usd_hr * 100) if usd_hr > 0 else 0
        
        return {
            "power_cost_per_hour": round(power_cost_per_hour, 4),
            "net_yield": round(net_yield, 4),
            "margin_percent": round(margin, 2),
            "break_even": net_yield > 0
        }
    except Exception as e:
        logger.warning(f"Error calculating yield metrics: {e}")
        return {
            "power_cost_per_hour": 0,
            "net_yield": 0,
            "margin_percent": 0,
            "break_even": False
        }

def enrich_aws_spot_offer(offer: Dict) -> Dict:
    """Enrich AWS Spot offer with additional metadata."""
    enriched = offer.copy()
    
    # Get instance metadata
    instance_type = offer.get("instance_type", "")
    metadata = AWS_INSTANCE_METADATA.get(instance_type, {})
    
    # Add instance specs
    enriched.update({
        "vcpu_count": metadata.get("vcpu"),
        "ram_gb": metadata.get("ram_gb"),
        "network_performance": metadata.get("network"),
        "storage_gb": metadata.get("storage_gb"),
        "ebs_optimized": metadata.get("ebs_optimized", False),
        "gpu_count": metadata.get("gpu_count", 1),
    })
    
    # Add risk and freshness indicators
    enriched["interruption_risk"] = calculate_interruption_risk(
        offer.get("availability", 1)
    )
    enriched["data_freshness"] = calculate_freshness(
        offer.get("timestamp", datetime.now(timezone.utc).isoformat())
    )
    
    # Add yield metrics
    enriched["yield_metrics"] = calculate_yield_metrics(offer)
    
    # Add region display name
    enriched["region_display"] = AWS_REGION_DISPLAY.get(
        offer.get("region", ""), offer.get("region", "")
    )
    
    return enriched

def enrich_aws_spot_batch(offers: List[Dict]) -> List[Dict]:
    """Enrich a batch of AWS Spot offers."""
    enriched_offers = []
    
    for offer in offers:
        try:
            if offer.get("provider") == "aws_spot":
                enriched = enrich_aws_spot_offer(offer)
                enriched_offers.append(enriched)
            else:
                # For non-AWS offers, just add basic enrichment
                enriched_offers.append(offer)
        except Exception as e:
            logger.error(f"Error enriching offer: {e}")
            # Add the offer without enrichment rather than skipping
            enriched_offers.append(offer)
    
    return enriched_offers

def filter_offers_for_view(offers: List[Dict], view_type: str = "operator") -> List[Dict]:
    """Filter offers based on view type (operator vs renter)."""
    filtered = []
    
    for offer in offers:
        filtered_offer = offer.copy()
        
        if view_type == "operator":
            # Operators focus on per-GPU yield, not total instance cost
            filtered_offer.pop("total_instance_price", None)
            # Keep yield metrics for operators
        elif view_type == "renter":
            # Renters care about total cost
            # Remove internal yield calculations
            filtered_offer.pop("yield_metrics", None)
            filtered_offer.pop("power_cost_per_hour", None)
        
        filtered.append(filtered_offer)
    
    return filtered

def get_aws_spot_offers_from_redis() -> List[Dict]:
    """Get AWS Spot offers from Redis stream"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        if not redis_url:
            logger.warning("No REDIS_URL configured")
            return []
        
        redis_conn = redis.from_url(redis_url, decode_responses=True)
        redis_conn.ping()  # Test connection
        
        # Read recent AWS data from stream
        stream_data = redis_conn.xrevrange("raw_prices", count=1000)
        offers = []
        
        for stream_id, fields in stream_data:
            if fields.get('cloud') == 'aws_spot':
                try:
                    offer = {
                        'model': fields.get('gpu_model'),
                        'usd_hr': float(fields.get('price_usd_hr', 0)),
                        'region': fields.get('region'),
                        'availability': int(fields.get('availability', 1)),
                        'instance_type': fields.get('instance_type', ''),
                        'provider': 'aws_spot',
                        'total_instance_price': float(fields.get('total_instance_price', 0)),
                        'gpu_memory_gb': int(fields.get('gpu_memory_gb', 16)),
                        'timestamp': fields.get('iso_timestamp'),
                        'synthetic': fields.get('synthetic', 'false').lower() == 'true'
                    }
                    
                    # Validate essential fields
                    if offer['model'] and offer['usd_hr'] > 0 and offer['region']:
                        offers.append(offer)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing offer from stream {stream_id}: {e}")
                    continue
        
        logger.info(f"Retrieved {len(offers)} AWS Spot offers from Redis")
        return offers
    
    except Exception as e:
        logger.error(f"Error reading AWS offers from Redis: {e}")
        return []

def get_synthetic_aws_data() -> List[Dict]:
    """Generate synthetic AWS Spot data for testing"""
    return [
        {
            "model": "A100",
            "usd_hr": 1.2290,
            "region": "us-east-1",
            "availability": 8,
            "instance_type": "p4d.24xlarge",
            "provider": "aws_spot",
            "total_instance_price": 9.832,
            "gpu_memory_gb": 40,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "synthetic": True,
        },
        {
            "model": "T4",
            "usd_hr": 0.1578,
            "region": "us-west-2",
            "availability": 1,
            "instance_type": "g4dn.xlarge",
            "provider": "aws_spot",
            "total_instance_price": 0.1578,
            "gpu_memory_gb": 16,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "synthetic": True,
        },
        {
            "model": "A10G",
            "usd_hr": 0.3360,
            "region": "us-east-1",
            "availability": 2,
            "instance_type": "g5.xlarge",
            "provider": "aws_spot",
            "total_instance_price": 0.3360,
            "gpu_memory_gb": 24,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "synthetic": True,
        },
        {
            "model": "V100",
            "usd_hr": 0.9180,
            "region": "eu-west-1",
            "availability": 4,
            "instance_type": "p3.8xlarge",
            "provider": "aws_spot",
            "total_instance_price": 3.672,
            "gpu_memory_gb": 16,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "synthetic": True,
        },
        {
            "model": "H100",
            "usd_hr": 2.1500,
            "region": "us-west-2",
            "availability": 2,
            "instance_type": "p5.48xlarge",
            "provider": "aws_spot",
            "total_instance_price": 17.200,
            "gpu_memory_gb": 80,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "synthetic": True,
        },
    ]

def get_enriched_aws_spot_prices(
    region: Optional[str] = None,
    model: Optional[str] = None,
    min_availability: Optional[int] = None,
    view_type: str = "operator"
) -> List[Dict]:
    """Get enriched AWS Spot prices with filtering."""
    
    # Get real offers from Redis
    raw_offers = get_aws_spot_offers_from_redis()
    
    # If no real data, use synthetic data
    if not raw_offers:
        logger.info("No real AWS data found, using synthetic data")
        raw_offers = get_synthetic_aws_data()
    
    # Enrich offers
    enriched = enrich_aws_spot_batch(raw_offers)
    
    # Apply filters
    if region:
        enriched = [o for o in enriched if o.get("region") == region]
    if model:
        enriched = [o for o in enriched if o.get("model") == model]
    if min_availability:
        enriched = [o for o in enriched if o.get("availability", 0) >= min_availability]
    
    # Filter based on view type
    filtered = filter_offers_for_view(enriched, view_type)
    
    return filtered

def get_available_regions() -> List[str]:
    """Get list of available AWS regions from Redis data"""
    try:
        offers = get_aws_spot_offers_from_redis()
        regions = list(set(offer.get("region") for offer in offers if offer.get("region")))
        return sorted(regions)
    except Exception as e:
        logger.error(f"Error getting available regions: {e}")
        return list(AWS_REGION_DISPLAY.keys())

def get_available_models() -> List[str]:
    """Get list of available GPU models from Redis data"""
    try:
        offers = get_aws_spot_offers_from_redis()
        models = list(set(offer.get("model") for offer in offers if offer.get("model")))
        return sorted(models)
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return ["A100", "H100", "V100", "T4", "A10G", "K80"]