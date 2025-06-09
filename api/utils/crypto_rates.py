import os
import json
import time
import requests
import redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL")
CACHE_HOURS = int(os.getenv("FX_RATE_CACHE_HOURS", 1))
CACHE_KEY = "crypto:rates"

redis_conn = None
if REDIS_URL:
    try:
        redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.error(f"Redis connection error for crypto rates: {e}")

def get_crypto_rates() -> dict:
    """Fetch crypto rates from CoinGecko with caching."""
    global redis_conn
    if redis_conn:
        cached = redis_conn.get(CACHE_KEY)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

    ids = "bitcoin,ethereum,bittensor,io-net,akash-network"
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ids, "vs_currencies": "usd"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if redis_conn:
            redis_conn.setex(CACHE_KEY, CACHE_HOURS * 3600, json.dumps(data))
        return data
    except Exception as e:
        logger.error(f"Error fetching crypto rates: {e}")
        return {}