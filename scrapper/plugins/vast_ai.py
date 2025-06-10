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

# Vast.ai constants
API_ENDPOINT = "https://console.vast.ai/api/v0/bundles/"
CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

_cache = None
_cache_time = 0

def fetch_vast_offers() -> List[Dict]:
    """
    Fetch GPU offers from Vast.ai using their public API.
    """
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached Vast.ai data")
        return _cache

    headers = {
        "Accept": "application/json",
        "User-Agent": "GPU-Yield-Calculator/1.0"
    }
    
    offers = []
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Fetching Vast.ai data (attempt {attempt + 1}/{MAX_RETRIES})")
            
            response = requests.get(
                API_ENDPOINT,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 404:
                raise ProviderConfigError(f"Vast.ai API endpoint not found: {API_ENDPOINT}")
            elif response.status_code == 429:
                raise ProviderTransientError("Vast.ai rate limit exceeded")
            elif response.status_code >= 500:
                raise ProviderTransientError(f"Vast.ai server error: {response.status_code}")
            elif response.status_code != 200:
                raise ProviderTransientError(f"Vast.ai API error: {response.status_code}")
            
            try:
                data = response.json()
            except ValueError as e:
                raise ProviderTransientError(f"Invalid JSON response from Vast.ai: {e}")
            
            # Extract offers data
            if isinstance(data, dict):
                offers_data = data.get("offers", [])
            elif isinstance(data, list):
                offers_data = data
            else:
                raise ProviderTransientError("Invalid data structure from Vast.ai")
            
            if not offers_data:
                raise ProviderTransientError("No offers found in Vast.ai response")
            
            # Process offers
            for item in offers_data:
                try:
                    # Extract required fields
                    gpu_name = item.get("gpu_name") or item.get("gpu_display_name")
                    price_per_hr = item.get("dph_total") or item.get("cost_per_hr")
                    region = item.get("geolocation", "Unknown")
                    availability = item.get("num_gpus", 1)
                    
                    if not gpu_name or price_per_hr is None:
                        logger.debug(f"Skipping incomplete Vast.ai offer: {item}")
                        continue
                    
                    # Validate and convert price
                    try:
                        price_float = float(price_per_hr)
                        if price_float <= 0 or price_float > 100:
                            logger.debug(f"Skipping Vast.ai offer with invalid price: {price_float}")
                            continue
                    except (ValueError, TypeError):
                        logger.debug(f"Skipping Vast.ai offer with invalid price format: {price_per_hr}")
                        continue
                    
                    # Normalize GPU name
                    gpu_model = normalize_gpu_name(gpu_name)
                    
                    # Additional fields for context
                    offer = {
                        "model": gpu_model,
                        "usd_hr": round(price_float, 4),
                        "region": str(region).lower() if region else "unknown",
                        "availability": max(1, int(availability)) if availability else 1,
                        "gpu_ram": item.get("gpu_ram"),
                        "cpu_cores": item.get("cpu_cores"),
                        "ram_gb": item.get("ram"),
                        "disk_space": item.get("disk_space"),
                        "bandwidth": item.get("inet_down"),
                        "machine_id": item.get("machine_id"),
                        "original_gpu_name": gpu_name
                    }
                    
                    offers.append(offer)
                    
                except Exception as e:
                    logger.warning(f"Error processing Vast.ai offer {item}: {e}")
                    continue
            
            if not offers:
                raise ProviderTransientError("No valid offers found in Vast.ai response")
            
            # Cache successful result
            _cache = offers
            _cache_time = time.time()
            
            logger.info(f"Successfully fetched {len(offers)} Vast.ai offers")
            return offers
            
        except ProviderConfigError:
            # Don't retry configuration errors
            raise
        except ProviderTransientError as e:
            if attempt == MAX_RETRIES - 1:
                raise
            logger.warning(f"Vast.ai attempt {attempt + 1} failed: {e}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError("Vast.ai API timeout after all retries")
            logger.warning(f"Vast.ai timeout on attempt {attempt + 1}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.ConnectionError as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"Vast.ai connection error: {e}")
            logger.warning(f"Vast.ai connection error on attempt {attempt + 1}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"Unexpected Vast.ai error: {e}")
            logger.warning(f"Unexpected Vast.ai error on attempt {attempt + 1}: {e}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
    
    raise ProviderTransientError("Vast.ai fetch failed after all retries")

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
    
    return gpu_name.title()

# Plugin interface
def fetch() -> List[Dict]:
    """Main plugin interface function"""
    return fetch_vast_offers()

# Plugin metadata
name = "vast_ai"