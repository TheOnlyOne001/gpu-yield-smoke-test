import os
import time
import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ProviderError(Exception):
    """Base exception for provider errors"""
    pass

class ProviderTransientError(ProviderError):
    """Transient error that may be retried"""
    pass

class ProviderConfigError(ProviderError):
    """Configuration error that should not be retried"""
    pass

# IO.net constants - Multiple endpoints
API_ENDPOINTS = [
    "https://api.ionet.io/v1/offers",  # Primary endpoint
    "https://cloud.io.net/api/v1/offerings",  # Alternative
    "https://bc.io.net/api/v1/capacity",  # Blockchain API
    "https://explorer.io.net/api/v1/gpus"  # Explorer API
]

# Public market data endpoint
MARKET_ENDPOINTS = [
    "https://cloud.io.net/api/marketplace/offers",
    "https://api.io.worker/v1/public/gpu-offers"
]

CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

_cache = None
_cache_time = 0

def fetch_io_net_offers() -> List[Dict]:
    """
    Fetch GPU offers from IO.net using multiple approaches.
    """
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached IO.net data")
        return _cache

    # Try primary endpoints
    for endpoint in API_ENDPOINTS:
        offers = fetch_from_endpoint(endpoint)
        if offers:
            return offers
    
    # Try market endpoints
    for endpoint in MARKET_ENDPOINTS:
        offers = fetch_from_market_endpoint(endpoint)
        if offers:
            return offers
    
    # Try web scraping approach
    offers = fetch_via_web_api()
    if offers:
        return offers
    
    # Last resort: synthetic data
    return get_synthetic_io_net_data()

def fetch_from_endpoint(endpoint: str) -> List[Dict]:
    """Fetch from a specific IO.net API endpoint"""
    headers = {
        "Accept": "application/json",
        "User-Agent": "GPU-Yield-Calculator/1.0",
        "Content-Type": "application/json"
    }
    
    # Add API key if available
    api_key = os.getenv("IO_NET_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-API-Key"] = api_key
    
    params = {
        "type": "gpu",
        "status": "available",
        "limit": 100
    }
    
    try:
        logger.info(f"Trying IO.net endpoint: {endpoint}")
        
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code == 404:
            logger.debug(f"IO.net endpoint not found: {endpoint}")
            return []
        elif response.status_code != 200:
            logger.warning(f"IO.net endpoint {endpoint} returned {response.status_code}")
            return []
        
        data = response.json()
        
        # Handle different response structures
        if isinstance(data, dict):
            items = data.get("offers") or data.get("devices") or data.get("data", [])
        elif isinstance(data, list):
            items = data
        else:
            return []
        
        offers = []
        for item in items:
            offer = parse_io_net_offer(item)
            if offer:
                offers.append(offer)
        
        if offers:
            # Cache successful result
            global _cache, _cache_time
            _cache = offers
            _cache_time = time.time()
            logger.info(f"Successfully fetched {len(offers)} IO.net offers from {endpoint}")
            return offers
            
    except requests.exceptions.RequestException as e:
        logger.debug(f"Failed to fetch from {endpoint}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error with {endpoint}: {e}")
    
    return []

def fetch_from_market_endpoint(endpoint: str) -> List[Dict]:
    """Fetch from IO.net marketplace endpoints"""
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; GPU-Calculator/1.0)"
    }
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            offers = []
            
            # Parse marketplace data
            if isinstance(data, list):
                for item in data:
                    offer = parse_marketplace_offer(item)
                    if offer:
                        offers.append(offer)
            
            if offers:
                logger.info(f"Fetched {len(offers)} offers from IO.net marketplace")
                return offers
                
    except Exception as e:
        logger.debug(f"Market endpoint {endpoint} failed: {e}")
    
    return []

def fetch_via_web_api() -> List[Dict]:
    """Try to fetch via web API / cloud platform"""
    try:
        # IO.net cloud platform API
        cloud_url = "https://cloud.io.net/api/v1/compute/gpus/available"
        
        response = requests.get(
            cloud_url,
            headers={
                "Accept": "application/json",
                "Referer": "https://cloud.io.net",
                "User-Agent": "Mozilla/5.0"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            offers = []
            
            # Process cloud platform data
            for gpu_type in data.get("gpu_types", []):
                base_price = gpu_type.get("base_price_usd", 0)
                if base_price > 0:
                    offer = {
                        "model": normalize_gpu_name(gpu_type.get("name", "Unknown")),
                        "usd_hr": round(base_price, 4),
                        "region": "global",
                        "availability": gpu_type.get("available_count", 1),
                        "provider": "io.net"
                    }
                    offers.append(offer)
            
            if offers:
                return offers
                
    except Exception as e:
        logger.debug(f"Web API approach failed: {e}")
    
    return []

def parse_io_net_offer(item: Dict) -> Optional[Dict]:
    """Parse an IO.net offer item"""
    try:
        # Extract GPU information
        gpu_info = item.get("gpu", {}) or item.get("hardware", {}).get("gpu", {})
        pricing = item.get("pricing", {}) or item.get("price", {})
        
        # Get GPU model
        gpu_name = (
            gpu_info.get("model") or 
            gpu_info.get("name") or 
            item.get("gpu_model") or
            item.get("device_type")
        )
        
        if not gpu_name:
            return None
        
        # Get pricing
        price_per_hr = (
            pricing.get("usd_per_hour") or
            pricing.get("hourly_rate") or
            pricing.get("price_usd") or
            item.get("hourly_price") or
            item.get("price_per_hour")
        )
        
        # Convert IO token pricing if needed
        if not price_per_hr:
            io_price = pricing.get("io_per_hour") or pricing.get("tokens_per_hour")
            if io_price:
                io_to_usd_rate = get_io_token_rate()
                price_per_hr = float(io_price) * io_to_usd_rate
        
        if not price_per_hr:
            return None
        
        price_float = float(price_per_hr)
        if price_float <= 0 or price_float > 100:
            return None
        
        # Get location
        location = item.get("location", {})
        region = (
            location.get("country") or
            location.get("region") or
            item.get("region") or
            "unknown"
        )
        
        return {
            "model": normalize_gpu_name(gpu_name),
            "usd_hr": round(price_float, 4),
            "region": str(region).lower(),
            "availability": item.get("available_gpus", 1),
            "provider": "io.net",
            "gpu_memory": gpu_info.get("memory"),
            "device_id": item.get("device_id")
        }
        
    except Exception as e:
        logger.debug(f"Error parsing IO.net offer: {e}")
        return None

def parse_marketplace_offer(item: Dict) -> Optional[Dict]:
    """Parse marketplace format offer"""
    try:
        gpu_model = item.get("gpu_type") or item.get("model")
        price = item.get("price_per_hour") or item.get("cost")
        
        if gpu_model and price:
            return {
                "model": normalize_gpu_name(gpu_model),
                "usd_hr": round(float(price), 4),
                "region": item.get("location", "global"),
                "availability": item.get("quantity", 1),
                "provider": "io.net"
            }
    except Exception:
        pass
    
    return None

def get_io_token_rate() -> float:
    """Get current IO token to USD rate"""
    # Try to fetch current rate
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "io-net", "vs_currencies": "usd"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("io-net", {}).get("usd", 0.003)
    except Exception:
        pass
    
    # Fallback to environment variable or default
    return float(os.getenv("IO_TOKEN_USD_RATE", "0.003"))

def get_synthetic_io_net_data() -> List[Dict]:
    """Return synthetic IO.net data based on typical offerings"""
    logger.warning("Using synthetic IO.net data as fallback")
    
    # IO.net typically offers consumer GPUs at competitive rates
    typical_offers = [
        {"model": "RTX 4090", "price": 0.49},
        {"model": "RTX 4080", "price": 0.39},
        {"model": "RTX 4070 Ti", "price": 0.29},
        {"model": "RTX 4070", "price": 0.25},
        {"model": "RTX 3090", "price": 0.29},
        {"model": "RTX 3080", "price": 0.19},
        {"model": "RTX 3070", "price": 0.15},
        {"model": "RTX 3060 Ti", "price": 0.12},
        {"model": "A100 40GB", "price": 1.10},
        {"model": "A100 80GB", "price": 1.89},
        {"model": "A6000", "price": 0.80},
        {"model": "V100", "price": 0.55},
        {"model": "T4", "price": 0.15},
    ]
    
    offers = []
    for gpu in typical_offers:
        offer = {
            "model": gpu["model"],
            "usd_hr": gpu["price"],
            "region": "global",
            "availability": 1,
            "provider": "io.net",
            "synthetic": True
        }
        offers.append(offer)
    
    return offers

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
    if "RTX" in gpu_name and not gpu_name.startswith("RTX"):
        gpu_name = gpu_name.replace("RTX", "").strip()
        gpu_name = f"RTX {gpu_name}"
    
    # Handle common variations
    gpu_name = gpu_name.replace("RTX4090", "RTX 4090")
    gpu_name = gpu_name.replace("RTX4080", "RTX 4080")
    gpu_name = gpu_name.replace("RTX4070", "RTX 4070")
    gpu_name = gpu_name.replace("RTX3090", "RTX 3090")
    gpu_name = gpu_name.replace("RTX3080", "RTX 3080")
    gpu_name = gpu_name.replace("RTX3070", "RTX 3070")
    gpu_name = gpu_name.replace("RTX3060", "RTX 3060")
    
    # Handle datacenter GPUs
    if "H100" in gpu_name:
        return "H100"
    elif "A100" in gpu_name:
        if "80GB" in gpu_name or "80G" in gpu_name:
            return "A100 80GB"
        elif "40GB" in gpu_name or "40G" in gpu_name:
            return "A100 40GB"
        return "A100"
    elif "V100" in gpu_name:
        return "V100"
    elif "T4" in gpu_name:
        return "T4"
    elif "A6000" in gpu_name:
        return "A6000"
    
    return gpu_name.title()

# Plugin interface
def fetch() -> List[Dict]:
    """Main plugin interface function"""
    return fetch_io_net_offers()

# Plugin metadata
name = "io_net"