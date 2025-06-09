import os
import time
import boto3
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

REGIONS = os.getenv("AWS_SPOT_REGIONS", "us-east-1").split(",")
CACHE_SECONDS = 300
_instance_map = {
    "g4dn.xlarge": "T4",
    "g5.xlarge": "A10G",
    "p3.2xlarge": "V100",
    "p4d.24xlarge": "A100",
    "p5.48xlarge": "H100",
}
_cache = None
_cache_time = 0


def fetch_aws_spot_prices(config: Dict[str, any]) -> List[Dict]:
    global _cache, _cache_time
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        return _cache

    offers = []
    try:
        for region in REGIONS:
            client = boto3.client("ec2", region_name=region)
            resp = client.describe_spot_price_history(
                InstanceTypes=list(_instance_map.keys()),
                ProductDescriptions=["Linux/UNIX"],
                MaxResults=100,
            )
            for item in resp.get("SpotPriceHistory", []):
                inst = item.get("InstanceType")
                price = float(item.get("SpotPrice", 0))
                gpu_model = _instance_map.get(inst, inst)
                offers.append(
                    {
                        "instance_type": inst,
                        "gpu_model": gpu_model,
                        "price": price,
                        "region": region,
                        "timestamp": item.get("Timestamp").isoformat(),
                    }
                )
    except Exception as e:
        logger.error(f"Error fetching AWS Spot prices: {e}")

    _cache = offers
    _cache_time = time.time()
    return offers