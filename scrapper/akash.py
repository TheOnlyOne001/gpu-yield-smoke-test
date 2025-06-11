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

# Akash network constants - Multiple endpoints for redundancy
LCD_ENDPOINTS = [
    "https://rest.cosmos.directory/akash/akash/market/v1beta4/bids",
    "https://akash-api.polkachu.com/akash/market/v1beta4/bids",
    "https://api.akash.smartnodes.one/akash/market/v1beta4/bids",
    "https://akash.api.ping.pub/akash/market/v1beta4/bids",
]

# Alternative: Use deployment endpoint which might have more data
DEPLOYMENT_ENDPOINTS = [
    "https://api.akashnet.net/akash/deployment/v1beta3/deployments/list",
    "https://console.akash.network/api/akash/deployments"
]

UAKT_TO_USD = 0.003  # Updated conversion rate (check current price)
MAX_BIDS = 50
CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

_cache = None
_cache_time = 0

def fetch_akash_offers() -> List[Dict]:
    """
    Fetch GPU offers from Akash Network using multiple endpoints.
    """
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached Akash data")
        return _cache

    # Try multiple endpoints
    for endpoint in LCD_ENDPOINTS:
        offers = fetch_from_lcd_endpoint(endpoint)
        if offers:
            return offers
    
    # If LCD endpoints fail, try alternative approach
    offers = fetch_via_marketplace_api()
    if offers:
        return offers
    
    # Last resort: return synthetic data
    return get_synthetic_akash_data()

def fetch_from_lcd_endpoint(endpoint: str) -> List[Dict]:
    """Try to fetch from a specific LCD endpoint"""
    params = {
        "state": "active",
        "pagination.limit": str(MAX_BIDS)
    }
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "GPU-Yield-Calculator/1.0"
    }
    
    offers = []
    
    try:
        logger.info(f"Trying Akash endpoint: {endpoint}")
        
        response = requests.get(
            endpoint,
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            logger.warning(f"Akash endpoint {endpoint} returned {response.status_code}")
            return []
        
        data = response.json()
        bids = data.get("bids", [])
        
        if not bids:
            logger.warning(f"No bids found at {endpoint}")
            return []
        
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
                    continue
                
                uakt_amount = float(amount)
                usd_price = (uakt_amount / 1000000) * UAKT_TO_USD  # uakt is in micro units
                
                # Basic validation
                if usd_price <= 0 or usd_price > 100:
                    continue
                
                # Try to extract GPU information
                gpu_model = extract_gpu_from_bid(bid_data)
                
                offer = {
                    "model": gpu_model,
                    "usd_hr": round(usd_price, 6),
                    "region": "global",
                    "availability": 1,
                    "provider": "akash",
                    "token_price": uakt_amount,
                    "original_currency": "UAKT"
                }
                
                offers.append(offer)
                
            except Exception as e:
                logger.debug(f"Error processing Akash bid: {e}")
                continue
        
        if offers:
            # Cache successful result
            global _cache, _cache_time
            _cache = offers
            _cache_time = time.time()
            logger.info(f"Successfully fetched {len(offers)} Akash offers from {endpoint}")
            return offers
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch from {endpoint}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error with {endpoint}: {e}")
    
    return []

def fetch_via_marketplace_api() -> List[Dict]:
    """Alternative approach using marketplace API"""
    try:
        # Try Cloudmos API (Akash marketplace frontend)
        cloudmos_url = "https://api.cloudmos.io/v1/providers"
        
        response = requests.get(
            cloudmos_url,
            headers={"User-Agent": "GPU-Yield-Calculator/1.0"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            offers = []
            
            # Process provider data
            for provider in data:
                if provider.get("isActive") and "gpu" in str(provider.get("attributes", [])).lower():
                    # Extract GPU offerings
                    gpu_models = extract_gpu_models_from_attributes(provider.get("attributes", []))
                    
                    for gpu_model in gpu_models:
                        # Estimate pricing based on GPU model
                        estimated_price = estimate_akash_gpu_price(gpu_model)
                        
                        offer = {
                            "model": gpu_model,
                            "usd_hr": estimated_price,
                            "region": provider.get("region", "global"),
                            "availability": 1,
                            "provider": "akash",
                            "provider_address": provider.get("owner"),
                            "estimated": True
                        }
                        offers.append(offer)
            
            if offers:
                logger.info(f"Fetched {len(offers)} estimated Akash offers via Cloudmos")
                return offers
                
    except Exception as e:
        logger.warning(f"Cloudmos API failed: {e}")
    
    return []

def extract_gpu_models_from_attributes(attributes: List[Dict]) -> List[str]:
    """Extract GPU models from provider attributes"""
    gpu_models = []
    
    for attr in attributes:
        key = attr.get("key", "").lower()
        value = attr.get("value", "")
        
        if "gpu" in key or "model" in key:
            if value:
                gpu_models.append(normalize_gpu_name(value))
    
    # If no specific models found, look for GPU capability indicators
    if not gpu_models:
        for attr in attributes:
            value = str(attr.get("value", "")).lower()
            if "rtx" in value or "nvidia" in value or "amd" in value:
                # Try to extract model from value
                model = extract_model_from_string(value)
                if model:
                    gpu_models.append(model)
    
    return gpu_models or ["GPU-Generic"]

def extract_model_from_string(text: str) -> Optional[str]:
    """Extract GPU model from text string"""
    text = text.upper()
    
    # Common GPU patterns
    patterns = [
        "RTX 4090", "RTX 4080", "RTX 4070",
        "RTX 3090", "RTX 3080", "RTX 3070",
        "A100", "A6000", "V100", "T4",
        "H100", "A40", "A30"
    ]
    
    for pattern in patterns:
        if pattern in text:
            return pattern
    
    return None

def estimate_akash_gpu_price(gpu_model: str) -> float:
    """Estimate Akash GPU price based on model"""
    # Akash typically offers 30-50% discount vs major clouds
    base_prices = {
        "RTX 4090": 0.35,
        "RTX 4080": 0.28,
        "RTX 4070": 0.20,
        "RTX 3090": 0.22,
        "RTX 3080": 0.16,
        "RTX 3070": 0.14,
        "A100": 1.40,
        "A6000": 0.75,
        "V100": 0.45,
        "T4": 0.11,
        "H100": 2.25,
        "GPU-Generic": 0.25
    }
    
    gpu_upper = gpu_model.upper()
    for model, price in base_prices.items():
        if model in gpu_upper:
            return price
    
    return 0.25  # Default price

def get_synthetic_akash_data() -> List[Dict]:
    """Return synthetic Akash data based on typical offerings"""
    logger.warning("Using synthetic Akash data as fallback")
    
    # Common GPUs available on Akash
    typical_offers = [
        {"model": "RTX 3090", "price": 0.22},
        {"model": "RTX 3080", "price": 0.16},
        {"model": "RTX 3070", "price": 0.14},
        {"model": "RTX 4070", "price": 0.20},
        {"model": "RTX 4080", "price": 0.28},
        {"model": "RTX 4090", "price": 0.35},
        {"model": "A100 40GB", "price": 0.95},
        {"model": "V100", "price": 0.45},
        {"model": "T4", "price": 0.11},
    ]
    
    offers = []
    for gpu in typical_offers:
        offer = {
            "model": gpu["model"],
            "usd_hr": gpu["price"],
            "region": "global",
            "availability": 1,
            "provider": "akash",
            "synthetic": True
        }
        offers.append(offer)
    
    return offers

def extract_gpu_from_bid(bid_data: Dict) -> str:
    """Extract GPU model from bid data"""
    try:
        # Try multiple paths to find GPU info
        bid = bid_data.get("bid", {})
        
        # Check escrow account attributes
        escrow = bid_data.get("escrow_account", {})
        if escrow:
            attrs = escrow.get("attributes", [])
            for attr in attrs:
                if isinstance(attr, dict):
                    key = attr.get("key", "").lower()
                    value = attr.get("value", "")
                    if "gpu" in key or "model" in key:
                        return normalize_gpu_name(value)
        
        # Check deployment specs
        deployment = bid.get("deployment", {})
        if deployment:
            groups = deployment.get("groups", [])
            for group in groups:
                resources = group.get("resources", [])
                for resource in resources:
                    gpu = resource.get("gpu")
                    if gpu:
                        return normalize_gpu_name(gpu.get("model", "GPU-Generic"))
        
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