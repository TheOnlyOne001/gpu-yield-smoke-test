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

# RunPod constants - Updated endpoints
GRAPHQL_ENDPOINT = "https://api.runpod.ai/graphql"
API_V2_ENDPOINT = "https://api.runpod.io/v2/gpuTypes"
CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

_cache = None
_cache_time = 0

def fetch_runpod_offers() -> List[Dict]:
    """
    Fetch GPU offers from RunPod using their API.
    Try multiple endpoints for better reliability.
    """
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached RunPod data")
        return _cache

    # Try REST API first (more reliable)
    offers = fetch_via_rest_api()
    if offers:
        return offers
    
    # Fallback to GraphQL if REST fails
    return fetch_via_graphql()

def fetch_via_rest_api() -> List[Dict]:
    """Fetch RunPod data via REST API"""
    headers = {
        "Accept": "application/json",
        "User-Agent": "GPU-Yield-Calculator/1.0"
    }
    
    # Add API key if available
    api_key = os.getenv("RUNPOD_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    offers = []
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Fetching RunPod data via REST (attempt {attempt + 1}/{MAX_RETRIES})")
            
            response = requests.get(
                API_V2_ENDPOINT,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 404:
                logger.warning("RunPod REST endpoint not found, trying alternate approach")
                return []
            elif response.status_code == 401:
                logger.warning("RunPod API authentication failed - API key may be required")
                return []
            elif response.status_code != 200:
                raise ProviderTransientError(f"RunPod API error: {response.status_code}")
            
            data = response.json()
            
            # Handle different response structures
            if isinstance(data, dict):
                gpu_types = data.get("data", []) or data.get("gpuTypes", [])
            elif isinstance(data, list):
                gpu_types = data
            else:
                raise ProviderTransientError("Invalid data structure from RunPod")
            
            # Process GPU types
            for item in gpu_types:
                try:
                    gpu_name = (
                        item.get("displayName") or 
                        item.get("name") or 
                        item.get("gpuName")
                    )
                    
                    price_per_hr = (
                        item.get("costPerHr") or 
                        item.get("price") or 
                        item.get("pricePerHr")
                    )
                    
                    if not gpu_name or price_per_hr is None:
                        continue
                    
                    price_float = float(price_per_hr)
                    if price_float <= 0 or price_float > 100:
                        continue
                    
                    offer = {
                        "model": normalize_gpu_name(gpu_name),
                        "usd_hr": round(price_float, 4),
                        "region": "global",
                        "availability": item.get("stockLevel", 1),
                        "memory_gb": item.get("memoryInGb"),
                        "secure_cloud": item.get("secureCloud", False)
                    }
                    
                    offers.append(offer)
                    
                except Exception as e:
                    logger.debug(f"Error processing RunPod item: {e}")
                    continue
            
            if offers:
                # Cache successful result
                global _cache, _cache_time
                _cache = offers
                _cache_time = time.time()
                logger.info(f"Successfully fetched {len(offers)} RunPod offers via REST")
                return offers
                
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                logger.warning(f"RunPod REST API failed: {e}")
            else:
                time.sleep(RETRY_DELAY)
    
    return []

def fetch_via_graphql() -> List[Dict]:
    """Fallback to GraphQL API"""
    # Simple GraphQL query that should work without auth
    query = {
        "query": """
        query GetGPUTypes {
            gpuTypes {
                id
                displayName
                memoryInGb
            }
        }
        """
    }
    
    # Try a simpler query if available
    simple_query = {
        "query": "{ gpuTypes { displayName } }"
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "GPU-Yield-Calculator/1.0"
    }
    
    offers = []
    
    for attempt in range(2):  # Fewer retries for fallback
        try:
            logger.info(f"Fetching RunPod data via GraphQL (attempt {attempt + 1})")
            
            # Try simple query first
            response = requests.post(
                GRAPHQL_ENDPOINT,
                json=simple_query if attempt == 0 else query,
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                continue
                
            data = response.json()
            
            if "errors" in data:
                logger.warning(f"GraphQL errors: {data['errors']}")
                continue
            
            gpu_types = data.get("data", {}).get("gpuTypes", [])
            
            # Generate synthetic pricing data if not available
            for item in gpu_types:
                gpu_name = item.get("displayName", "Unknown")
                
                # Estimate price based on GPU model
                price = estimate_gpu_price(gpu_name)
                
                offer = {
                    "model": normalize_gpu_name(gpu_name),
                    "usd_hr": price,
                    "region": "global",
                    "memory_gb": item.get("memoryInGb")
                }
                
                offers.append(offer)
            
            if offers:
                logger.info(f"Fetched {len(offers)} RunPod GPU types via GraphQL")
                return offers
                
        except Exception as e:
            logger.debug(f"GraphQL attempt {attempt + 1} failed: {e}")
    
    # Return synthetic data as last resort
    return get_synthetic_runpod_data()

def estimate_gpu_price(gpu_name: str) -> float:
    """Estimate GPU price based on model"""
    gpu_name = gpu_name.upper()
    
    # Rough price estimates
    price_map = {
        "H100": 4.5,
        "A100": 2.8,
        "A6000": 1.5,
        "RTX 4090": 0.74,
        "RTX 4080": 0.56,
        "RTX 4070": 0.39,
        "RTX 3090": 0.44,
        "RTX 3080": 0.32,
        "A40": 0.79,
        "V100": 0.89,
        "T4": 0.21
    }
    
    for model, price in price_map.items():
        if model in gpu_name:
            return price
    
    return 0.5  # Default price

def get_synthetic_runpod_data() -> List[Dict]:
    """Return synthetic RunPod data based on typical offerings"""
    logger.warning("Using synthetic RunPod data as fallback")
    
    typical_gpus = [
        {"model": "RTX 4090", "price": 0.74, "memory": 24},
        {"model": "RTX 4080", "price": 0.56, "memory": 16},
        {"model": "RTX 3090", "price": 0.44, "memory": 24},
        {"model": "A100 40GB", "price": 1.89, "memory": 40},
        {"model": "A100 80GB", "price": 2.79, "memory": 80},
        {"model": "A6000", "price": 1.50, "memory": 48},
        {"model": "RTX A5000", "price": 0.77, "memory": 24},
        {"model": "RTX A4000", "price": 0.35, "memory": 16},
    ]
    
    offers = []
    for gpu in typical_gpus:
        offer = {
            "model": gpu["model"],
            "usd_hr": gpu["price"],
            "region": "global",
            "memory_gb": gpu["memory"],
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
    
    return gpu_name.title()

# Plugin interface
def fetch() -> List[Dict]:
    """Main plugin interface function"""
    return fetch_runpod_offers()

# Plugin metadata
name = "runpod"