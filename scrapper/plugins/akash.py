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

# Akash network constants
LCD_ENDPOINT = "https://lcd-1.akash.network/akash/market/v1beta4/bids"
UAKT_TO_USD = 0.000001  # 1 uakt ≈ $0.000001 USD
MAX_BIDS = 50
CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

_cache = None
_cache_time = 0

def fetch_akash_bids(config: Dict[str, any]) -> List[Dict]:
    """
    Fetch GPU offers from Akash Network using LCD REST API.
    """
    return fetch_akash_offers()

def fetch_akash_offers() -> List[Dict]:
    """
    Fetch GPU offers from Akash Network using LCD REST API.
    """
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached Akash data")
        return _cache

    params = {
        "state": "active",
        "pagination.limit": str(MAX_BIDS)
    }
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "GPU-Yield-Calculator/1.0"
    }
    
    offers = []
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Fetching Akash data (attempt {attempt + 1}/{MAX_RETRIES})")
            
            response = requests.get(
                LCD_ENDPOINT,
                params=params,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 404:
                raise ProviderConfigError(f"Akash LCD endpoint not found: {LCD_ENDPOINT}")
            elif response.status_code >= 500:
                raise ProviderTransientError(f"Akash server error: {response.status_code}")
            elif response.status_code != 200:
                raise ProviderTransientError(f"Akash API error: {response.status_code}")
            
            try:
                data = response.json()
            except ValueError as e:
                raise ProviderTransientError(f"Invalid JSON response from Akash: {e}")
            
            # Extract bids data
            bids = data.get("bids", [])
            if not isinstance(bids, list):
                raise ProviderTransientError("Invalid bids data structure from Akash")
            
            if not bids:
                raise ProviderTransientError("No active bids found in Akash response")
            
            # Process bids
            for bid_data in bids[:MAX_BIDS]:
                try:
                    bid = bid_data.get("bid", {})
                    if not bid:
                        continue
                    
                    # Extract price information
                    price_info = bid.get("price", {})
                    amount = price_info.get("amount")
                    denom = price_info.get("denom", "")
                    
                    if not amount or denom != "uakt":
                        logger.debug(f"Skipping Akash bid with invalid price: {price_info}")
                        continue
                    
                    try:
                        uakt_amount = float(amount)
                        usd_price = uakt_amount * UAKT_TO_USD
                        
                        # Basic validation - prices should be reasonable
                        if usd_price <= 0 or usd_price > 100:
                            logger.debug(f"Skipping Akash bid with unrealistic price: ${usd_price}")
                            continue
                            
                    except (ValueError, TypeError):
                        logger.warning(f"Skipping Akash bid with invalid amount: {amount}")
                        continue
                    
                    # Try to extract GPU information from bid attributes
                    gpu_model = extract_gpu_from_bid(bid)
                    
                    offer = {
                        "gpu_model": gpu_model,
                        "price": usd_price,
                        "token_price": uakt_amount,
                        "region": "global",  # Akash is decentralized/global
                        "availability": 1,
                        "original_currency": "UAKT",
                        "model": gpu_model,
                        "usd_hr": round(usd_price, 6)
                    }
                    
                    offers.append(offer)
                    
                except Exception as e:
                    logger.warning(f"Error processing Akash bid {bid_data}: {e}")
                    continue
            
            if not offers:
                raise ProviderTransientError("No valid offers found in Akash response")
            
            # Cache successful result
            _cache = offers
            _cache_time = time.time()
            
            logger.info(f"Successfully fetched {len(offers)} Akash offers")
            return offers
            
        except ProviderConfigError:
            # Don't retry configuration errors
            raise
        except ProviderTransientError as e:
            if attempt == MAX_RETRIES - 1:
                raise
            logger.warning(f"Akash attempt {attempt + 1} failed: {e}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError("Akash API timeout after all retries")
            logger.warning(f"Akash timeout on attempt {attempt + 1}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.ConnectionError as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"Akash connection error: {e}")
            logger.warning(f"Akash connection error on attempt {attempt + 1}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise ProviderTransientError(f"Unexpected Akash error: {e}")
            logger.warning(f"Unexpected Akash error on attempt {attempt + 1}: {e}, retrying in {RETRY_DELAY}s")
            time.sleep(RETRY_DELAY)
    
    raise ProviderTransientError("Akash fetch failed after all retries")

def extract_gpu_from_bid(bid: Dict) -> str:
    """Extract GPU model from bid data."""
    try:
        # Check resources for GPU information
        resources = bid.get("resources", [])
        if isinstance(resources, list):
            for resource in resources:
                gpu_info = resource.get("gpu", {})
                if gpu_info:
                    # Look for attributes that might indicate GPU model
                    attrs = gpu_info.get("attributes", [])
                    if isinstance(attrs, list):
                        for attr in attrs:
                            if isinstance(attr, dict):
                                key = attr.get("key", "").lower()
                                value = attr.get("value", "")
                                if "model" in key or "gpu" in key:
                                    return normalize_gpu_name(value)
        
        # Check bid attributes as fallback
        attrs = bid.get("attributes", [])
        if isinstance(attrs, list):
            for attr in attrs:
                if isinstance(attr, dict):
                    key = attr.get("key", "").lower()
                    value = attr.get("value", "")
                    if "gpu" in key or "model" in key:
                        return normalize_gpu_name(value)
        
        # Default fallback
        return "GPU-Generic"
        
    except Exception as e:
        logger.debug(f"Error extracting GPU from bid: {e}")
        return "GPU-Generic"

def normalize_gpu_name(gpu_name: str) -> str:
    """Normalize GPU names for consistent comparison."""
    if not gpu_name:
        return "GPU-Generic"
    
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
    
    return gpu_name.title() if gpu_name != "GPU-GENERIC" else "GPU-Generic"

# Plugin interface
def fetch() -> List[Dict]:
    """Main plugin interface function"""
    return fetch_akash_offers()

# Plugin metadata
name = "akash"