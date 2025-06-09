import os
import json
import time
import requests
import redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL")
CACHE_HOURS = int(os.getenv("POWER_COST_UPDATE_HOURS", 4))

redis_conn = None
if REDIS_URL:
    try:
        redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.error(f"Redis connection error for power prices: {e}")

EIA_API_KEY = os.getenv("EIA_API_KEY")
ENTSO_E_API_KEY = os.getenv("ENTSO_E_API_KEY")

EIA_ENDPOINT = "https://api.eia.gov/v2/electricity/rto/region-price/data/"
ENTSO_ENDPOINT = "https://transparency.entsoe.eu/api"

CACHE_KEY = "power:prices"


def get_power_prices() -> dict:
    """Fetch power prices from EIA and ENTSO-e with caching."""
    if redis_conn:
        cached = redis_conn.get(CACHE_KEY)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

    prices = {}
    try:
        if EIA_API_KEY:
            params = {
                "api_key": EIA_API_KEY,
                "dataItems": "LMP",  # Locational marginal pricing
                "frequency": "hourly",
                "market": "RTM",
                "region": "ALL",
                "offset": 0,
                "length": 1,
            }
            resp = requests.get(EIA_ENDPOINT, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json().get("response", {}).get("data", [])
            if data:
                for entry in data:
                    region = entry.get("region")
                    price = entry.get("value")
                    if region and price is not None:
                        prices[region] = float(price) / 1000  # $/MWh -> $/kWh
    except Exception as e:
        logger.error(f"Error fetching EIA power prices: {e}")

    # ENTSO-e placeholder - simplified
    try:
        if ENTSO_E_API_KEY:
            params = {
                "securityToken": ENTSO_E_API_KEY,
                "documentType": "A44",
                "processType": "A16",
                "outBiddingZone_Domain": "10Y1001A1001A83F",
            }
            resp = requests.get(ENTSO_ENDPOINT, params=params, timeout=10)
            if resp.status_code == 200:
                prices["EU"] = 0.25  # placeholder
    except Exception as e:
        logger.error(f"Error fetching ENTSO-e power prices: {e}")

    if redis_conn and prices:
        redis_conn.setex(CACHE_KEY, CACHE_HOURS * 3600, json.dumps(prices))
    return prices