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

GRAPHQL_ENDPOINT = "https://api.runpod.ai/graphql"
CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

_cache = None
_cache_time = 0

def fetch_runpod_offers() -> List[Dict]:
    """
    Fetch GPU offers from RunPod using GraphQL API.
    """
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached RunPod data")
        return _cache

    query = {
        "query": """
        query {
            publicMarketplace {
                gpuName
                pricePerHr
                region
            }
        }
        """
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "GPU-Yield-Calculator/1.0"
    }
    
    offers = []
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Fetching RunPod data (attempt {attempt + 1}/{MAX_RETRIES})")
            
            response = requests.post(
                GRAPHQL_ENDPOINT,
                json=query,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 404:
                raise ProviderConfigError(f"RunPod GraphQL endpoint not found: {GRAPHQL_ENDPOINT}")
            elif response.status_code == 401:
                raise ProviderConfigError("RunPod API authentication failed")
            elif response.status_code >= 500:
                raise ProviderTransientError(f"RunPod server error: {response.status_code}")
            elif response.status_code != 200:
                raise ProviderTransientError(f"RunPod API error: {response.status_code}")
            
            try:
                data = response.json()
            except ValueError as e:
                raise ProviderTransientError(f"Invalid JSON response from RunPod: {e}")
            
            # Check for GraphQL errors
            if "errors" in data:
                error_msg = "; ".join([err.get("message", "Unknown error") for err in data["errors"]])
                raise ProviderTransientError(f"RunPod GraphQL errors: {error_msg}")
            
            # Extract marketplace data
            marketplace_data = data.get("data", {}).get("publicMarketplace", [])
            if not isinstance(marketplace_data, list):
                raise ProviderTransientError("Invalid marketplace data structure from RunPod")
            
            # Convert to standardized format
            for item in marketplace_data:
                try:
                    gpu_name = item.get("gpuName")
                    price_per_hr = item.get("pricePerHr")
                    region = item.get("region", "global")
                    
                    if not gpu_name or price_per_hr is None:
                        logger.warning(f"Skipping incomplete RunPod offer: {item}")
                        continue
                    
                    # Validate and convert price
                    try:
                        price_float = float(price_per_hr)
                        if price_float <= 0 or price_float > 100:
                            logger.warning(f"Skipping RunPod offer with invalid price: {price_float}")
                            continue
                    except (ValueError, TypeError):
                        logger.warning(f"Skipping RunPod offer with invalid price format: {price_per_hr}")
                        continue
                    
                    # Normalize GPU name
                    gpu_model = normalize_gpu_name(gpu_name)
                    
                    offer = {
                        "model": gpu_model,
                        "usd_hr": round(price_float, 4),
                        "region": str(region).lower() if region else "global"
                    }
                    
                    offers.append(offer)
                    
                except Exception as e:
                    logger.warning(f"Error processing RunPod offer {item}: {e}")
                    continue
            
            if not offers:
                raise ProviderTransientError("No valid offers found in RunPod response")
            
            # Cache successful result
            _cache = offers
            _cache_time = time.time()
            
            logger.info(f"Successfully fetched {len(offers)} RunPod offers")
            return offers
            
        except ProviderConfigError:
            # Don't retry configuration errors
            raise
        except ProviderTransientError as e:
            if attempt == MAX_RETRIES - 1:
                raise
            logger.warning(f"RunPod attempt {attempt + 1} failed: {e}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError("RunPod API timeout after all retries")
            logger.warning(f"RunPod timeout on attempt {attempt + 1}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.ConnectionError as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"RunPod connection error: {e}")
            logger.warning(f"RunPod connection error on attempt {attempt + 1}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"Unexpected RunPod error: {e}")
            logger.warning(f"Unexpected RunPod error on attempt {attempt + 1}: {e}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
    
    raise ProviderTransientError("RunPod fetch failed after all retries")

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