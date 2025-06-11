# api/utils/aws_spot_enrichment.py
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Instance metadata for enrichment
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
}

# Regional power costs ($/kWh)
REGION_POWER_COSTS = {
    "us-east-1": 0.12,
    "us-west-2": 0.09,
    "eu-west-1": 0.18,
    "us-east-2": 0.11,
    "ap-southeast-1": 0.15,
    "eu-central-1": 0.20,
    "ap-northeast-1": 0.17,
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
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
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
        logger.warning(f"Error calculating freshness: {e}")
        return "unknown"

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
    })
    
    # Add risk and freshness indicators
    enriched["interruption_risk"] = calculate_interruption_risk(
        offer.get("availability", 1)
    )
    enriched["data_freshness"] = calculate_freshness(
        offer.get("timestamp", "")
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
                enriched_offers.append(offer)
        except Exception as e:
            logger.error(f"Error enriching offer: {e}")
            enriched_offers.append(offer)
    
    return enriched_offers

def filter_offers_for_view(offers: List[Dict], view_type: str = "operator") -> List[Dict]:
    """Filter offers based on view type (operator vs renter)."""
    filtered = []
    
    for offer in offers:
        filtered_offer = offer.copy()
        
        if view_type == "operator":
            # Operators don't need total instance price in main view
            filtered_offer.pop("total_instance_price", None)
        elif view_type == "renter":
            # Renters don't need yield metrics
            filtered_offer.pop("yield_metrics", None)
        
        filtered.append(filtered_offer)
    
    return filtered

# Example usage in API endpoint
def get_enriched_aws_spot_prices(
    region: Optional[str] = None,
    model: Optional[str] = None,
    min_availability: Optional[int] = None,
    view_type: str = "operator"
) -> List[Dict]:
    """
    Get enriched AWS Spot prices with filtering.
    
    This would be called from your FastAPI endpoint.
    """
    # Get raw offers from Redis or scraper
    # raw_offers = get_aws_spot_offers_from_redis()
    
    # For demonstration, using dummy data
    raw_offers = [
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
        }
    ]
    
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