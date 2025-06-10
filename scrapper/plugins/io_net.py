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

# IO.net constants
API_ENDPOINT = "https://api.io.net/v1/devices"
CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

_cache = None
_cache_time = 0

def fetch_io_net_offers() -> List[Dict]:
    """
    Fetch GPU offers from IO.net using their public API.
    """
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached IO.net data")
        return _cache

    headers = {
        "Accept": "application/json",
        "User-Agent": "GPU-Yield-Calculator/1.0",
        "Content-Type": "application/json"
    }
    
    # IO.net API parameters for GPU devices
    params = {
        "type": "gpu",
        "status": "available",
        "limit": 100
    }
    
    offers = []
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Fetching IO.net data (attempt {attempt + 1}/{MAX_RETRIES})")
            
            response = requests.get(
                API_ENDPOINT,
                headers=headers,
                params=params,
                timeout=15
            )
            
            if response.status_code == 404:
                raise ProviderConfigError(f"IO.net API endpoint not found: {API_ENDPOINT}")
            elif response.status_code == 429:
                raise ProviderTransientError("IO.net rate limit exceeded")
            elif response.status_code >= 500:
                raise ProviderTransientError(f"IO.net server error: {response.status_code}")
            elif response.status_code != 200:
                raise ProviderTransientError(f"IO.net API error: {response.status_code}")
            
            try:
                data = response.json()
            except ValueError as e:
                raise ProviderTransientError(f"Invalid JSON response from IO.net: {e}")
            
            # Extract devices data
            if isinstance(data, dict):
                devices_data = data.get("devices", []) or data.get("data", [])
            elif isinstance(data, list):
                devices_data = data
            else:
                raise ProviderTransientError("Invalid data structure from IO.net")
            
            if not devices_data:
                raise ProviderTransientError("No devices found in IO.net response")
            
            # Process devices
            for item in devices_data:
                try:
                    # Extract required fields from IO.net device structure
                    gpu_info = item.get("gpu", {}) or item.get("specs", {}).get("gpu", {})
                    pricing = item.get("pricing", {}) or item.get("price", {})
                    location = item.get("location", {}) or item.get("region", {})
                    
                    # Extract GPU name
                    gpu_name = (
                        gpu_info.get("model") or 
                        gpu_info.get("name") or 
                        item.get("gpu_model") or
                        item.get("device_type")
                    )
                    
                    # Extract pricing (IO.net typically prices in IO tokens or USD)
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
                            # Approximate IO token to USD conversion (this should be dynamic)
                            io_to_usd_rate = float(os.getenv("IO_TOKEN_USD_RATE", "0.003"))
                            price_per_hr = float(io_price) * io_to_usd_rate
                    
                    # Extract region/location
                    region = (
                        location.get("country") or
                        location.get("region") or
                        item.get("region") or
                        item.get("location") or
                        "Unknown"
                    )
                    
                    # Extract availability
                    availability = (
                        item.get("available_gpus") or
                        item.get("gpu_count") or
                        gpu_info.get("count") or
                        1
                    )
                    
                    if not gpu_name or price_per_hr is None:
                        logger.debug(f"Skipping incomplete IO.net offer: {item}")
                        continue
                    
                    # Validate and convert price
                    try:
                        price_float = float(price_per_hr)
                        if price_float <= 0 or price_float > 100:
                            logger.debug(f"Skipping IO.net offer with invalid price: {price_float}")
                            continue
                    except (ValueError, TypeError):
                        logger.debug(f"Skipping IO.net offer with invalid price format: {price_per_hr}")
                        continue
                    
                    # Normalize GPU name
                    gpu_model = normalize_gpu_name(gpu_name)
                    
                    # Additional fields for context
                    offer = {
                        "model": gpu_model,
                        "usd_hr": round(price_float, 4),
                        "region": str(region).lower() if region else "unknown",
                        "availability": max(1, int(availability)) if availability else 1,
                        "gpu_memory": gpu_info.get("memory") or gpu_info.get("vram"),
                        "cpu_cores": item.get("cpu", {}).get("cores"),
                        "ram_gb": item.get("memory", {}).get("total_gb"),
                        "storage_gb": item.get("storage", {}).get("total_gb"),
                        "bandwidth_mbps": item.get("network", {}).get("bandwidth"),
                        "device_id": item.get("device_id") or item.get("id"),
                        "original_gpu_name": gpu_name,
                        "status": item.get("status", "available"),
                        "provider": "io.net"
                    }
                    
                    offers.append(offer)
                    
                except Exception as e:
                    logger.warning(f"Error processing IO.net offer {item}: {e}")
                    continue
            
            if not offers:
                raise ProviderTransientError("No valid offers found in IO.net response")
            
            # Cache successful result
            _cache = offers
            _cache_time = time.time()
            
            logger.info(f"Successfully fetched {len(offers)} IO.net offers")
            return offers
            
        except ProviderConfigError:
            # Don't retry configuration errors
            raise
        except ProviderTransientError as e:
            if attempt == MAX_RETRIES - 1:
                raise
            logger.warning(f"IO.net attempt {attempt + 1} failed: {e}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError("IO.net API timeout after all retries")
            logger.warning(f"IO.net timeout on attempt {attempt + 1}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.ConnectionError as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"IO.net connection error: {e}")
            logger.warning(f"IO.net connection error on attempt {attempt + 1}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"Unexpected IO.net error: {e}")
            logger.warning(f"Unexpected IO.net error on attempt {attempt + 1}: {e}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
    
    raise ProviderTransientError("IO.net fetch failed after all retries")

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
    
    # Handle Tesla/datacenter GPUs
    if "TESLA" in gpu_name:
        gpu_name = gpu_name.replace("TESLA ", "Tesla ")
    
    # Handle H100/A100 variations
    if "H100" in gpu_name:
        gpu_name = "H100"
    elif "A100" in gpu_name:
        gpu_name = "A100"
    elif "V100" in gpu_name:
        gpu_name = "V100"
    
    return gpu_name.title()

# Plugin interface
def fetch() -> List[Dict]:
    """Main plugin interface function"""
    return fetch_io_net_offers()

# Plugin metadata
name = "io_net"