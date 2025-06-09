import requests
import os
import time
import logging
from typing import List, Dict
from crypto_rates import get_crypto_rates

logger = logging.getLogger(__name__)

AKASH_URL = "https://akash-api.akash.network/gpu/bids"
CACHE_SECONDS = 300
_cache = None
_cache_time = 0

def fetch_akash_bids(config: Dict[str, any]) -> List[Dict]:
    global _cache, _cache_time
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        return _cache

    offers = []
    try:
        resp = requests.get(AKASH_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        bids = data.get("bids", data if isinstance(data, list) else [])
        rates = get_crypto_rates().get("akash-network", {}).get("usd", 0)
        for bid in bids:
            attrs = bid.get("attributes", {})
            gpu_model = attrs.get("gpu_model") or attrs.get("gpu") or "Unknown"
            token_price = float(bid.get("price", 0))
            usd_price = token_price * rates if rates else 0
            region = bid.get("provider", {}).get("region", "Unknown")
            availability = bid.get("quantity", 1)
            offers.append(
                {
                    "gpu_model": gpu_model,
                    "price": usd_price,
                    "token_price": token_price,
                    "region": region,
                    "availability": availability,
                    "original_currency": "AKT",
                }
            )
    except Exception as e:
        logger.error(f"Error fetching Akash bids: {e}")

    _cache = offers
    _cache_time = time.time()
    return offers