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

# Updated Akash network endpoints - Current working endpoints
LCD_ENDPOINTS = [
    "https://akash-api.stakecito.com/akash/market/v1beta4/bids",
    "https://rest.cosmos.directory/akash/akash/market/v1beta4/bids",
    "https://akash-api.polkachu.com/akash/market/v1beta4/bids",
    "https://api.akash.smartnodes.one/akash/market/v1beta4/bids",
    "https://akash-rest.publicnode.com/akash/market/v1beta4/bids",
    "https://akash.api.m.stavr.tech/akash/market/v1beta4/bids"
]

# Alternative RPC endpoints if REST fails
RPC_ENDPOINTS = [
    "https://rpc.akash.forbole.com:443",
    "https://akash-rpc.stakecito.com",
    "https://akash-rpc.polkachu.com"
]

# Cloudmos (Akash marketplace) API endpoints
MARKETPLACE_ENDPOINTS = [
    "https://api.cloudmos.io/v1/providers",
    "https://console.akash.network/api/v1/providers"
]

UAKT_TO_USD = 0.003  # Updated conversion rate
MAX_BIDS = 50
CACHE_SECONDS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

_cache = None
_cache_time = 0

def fetch_akash_offers() -> List[Dict]:
    """
    Fetch GPU offers from Akash Network using multiple current endpoints.
    """
    global _cache, _cache_time
    
    # Check cache first
    if _cache and time.time() - _cache_time < CACHE_SECONDS:
        logger.debug("Returning cached Akash data")
        return _cache

    # Try LCD REST endpoints first (most reliable)
    for endpoint in LCD_ENDPOINTS:
        offers = fetch_from_lcd_endpoint(endpoint)
        if offers:
            return offers
    
    # If LCD endpoints fail, try marketplace API
    offers = fetch_via_marketplace_api()
    if offers:
        return offers
    
    # Last resort: return synthetic data
    logger.warning("All Akash endpoints failed, using synthetic data")
    offers = get_synthetic_akash_data()
    
    # Cache fallback result
    _cache = offers
    _cache_time = time.time()
    
    return offers

def fetch_from_lcd_endpoint(endpoint: str) -> List[Dict]:
    """Try to fetch from a specific LCD endpoint with current API structure"""
    params = {
        "pagination.state": "active",
        "pagination.limit": str(MAX_BIDS),
        "pagination.count_total": "true"
    }
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "GPU-Yield-Calculator/1.0",
        "Content-Type": "application/json"
    }
    
    offers = []
    
    try:
        logger.info(f"Trying Akash LCD endpoint: {endpoint}")
        
        response = requests.get(
            endpoint,
            params=params,
            headers=headers,
            timeout=15
        )
        
        logger.debug(f"Akash response status: {response.status_code}")
        
        if response.status_code == 404:
            logger.warning(f"Endpoint not found: {endpoint}")
            return []
        elif response.status_code == 429:
            logger.warning(f"Rate limited: {endpoint}")
            return []
        elif response.status_code != 200:
            logger.warning(f"Akash endpoint {endpoint} returned {response.status_code}: {response.text[:200]}")
            return []
        
        try:
            data = response.json()
        except ValueError as e:
            logger.warning(f"Invalid JSON response from {endpoint}: {e}")
            return []
        
        # Handle different response structures
        bids = []
        if isinstance(data, dict):
            bids = data.get("bids", []) or data.get("result", {}).get("bids", [])
        elif isinstance(data, list):
            bids = data
        
        if not bids:
            logger.info(f"No active bids found at {endpoint}")
            return []
        
        logger.info(f"Found {len(bids)} bids from {endpoint}")
        
        # Process bids
        for bid_data in bids[:MAX_BIDS]:
            try:
                offer = process_akash_bid(bid_data)
                if offer:
                    offers.append(offer)
                    
            except Exception as e:
                logger.debug(f"Error processing Akash bid: {e}")
                continue
        
        if offers:
            # Cache successful result
            global _cache, _cache_time
            _cache = offers
            _cache_time = time.time()
            logger.info(f"Successfully processed {len(offers)} Akash offers from {endpoint}")
            return offers
        else:
            logger.warning(f"No valid offers found from {len(bids)} bids at {endpoint}")
            
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error with {endpoint}: {e}")
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout with {endpoint}")
    except Exception as e:
        logger.error(f"Unexpected error with {endpoint}: {e}")
    
    return []

def process_akash_bid(bid_data: Dict) -> Optional[Dict]:
    """Process a single Akash bid into our standard format"""
    try:
        # Handle different bid structures
        bid = bid_data.get("bid", bid_data)
        
        # Extract price information
        price_info = bid.get("price", {})
        if not price_info:
            return None
            
        amount = price_info.get("amount")
        denom = price_info.get("denom", "")
        
        if not amount or denom.lower() != "uakt":
            return None
        
        try:
            uakt_amount = float(amount)
            # Convert from uAKT (micro AKT) to USD
            akt_amount = uakt_amount / 1000000  # Convert uAKT to AKT
            usd_price = akt_amount * UAKT_TO_USD
        except (ValueError, TypeError):
            return None
        
        # Basic price validation
        if usd_price <= 0 or usd_price > 100:
            return None
        
        # Extract GPU information from bid
        gpu_model = extract_gpu_from_bid(bid_data)
        
        # Extract provider and region info
        provider_address = bid.get("provider", "unknown")
        
        # Try to determine region from provider info
        region = "akash-network"  # Default
        
        offer = {
            "model": gpu_model,
            "usd_hr": round(usd_price, 6),
            "region": region,
            "availability": 1,
            "provider": "akash",
            "provider_address": provider_address,
            "token_price": uakt_amount,
            "original_currency": "uAKT",
            "bid_id": bid.get("bid_id"),
            "state": bid.get("state", "active")
        }
        
        return offer
        
    except Exception as e:
        logger.debug(f"Error processing Akash bid: {e}")
        return None

def fetch_via_marketplace_api() -> List[Dict]:
    """Alternative approach using Cloudmos marketplace API"""
    for endpoint in MARKETPLACE_ENDPOINTS:
        try:
            logger.info(f"Trying Akash marketplace endpoint: {endpoint}")
            
            response = requests.get(
                endpoint,
                headers={"User-Agent": "GPU-Yield-Calculator/1.0"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                offers = []
                
                # Process provider data
                providers = data if isinstance(data, list) else data.get("providers", [])
                
                for provider in providers[:20]:  # Limit to prevent too much data
                    if not provider.get("isOnline", True):
                        continue
                        
                    # Extract GPU offerings from provider attributes
                    gpu_models = extract_gpu_models_from_attributes(provider.get("attributes", []))
                    
                    for gpu_model in gpu_models:
                        # Estimate pricing based on GPU model and Akash typical pricing
                        estimated_price = estimate_akash_gpu_price(gpu_model)
                        
                        offer = {
                            "model": gpu_model,
                            "usd_hr": estimated_price,
                            "region": provider.get("region", "global"),
                            "availability": 1,
                            "provider": "akash",
                            "provider_address": provider.get("owner", "unknown"),
                            "estimated": True,
                            "source": "marketplace"
                        }
                        offers.append(offer)
                
                if offers:
                    logger.info(f"Fetched {len(offers)} estimated Akash offers via marketplace")
                    return offers
                    
        except Exception as e:
            logger.warning(f"Marketplace API {endpoint} failed: {e}")
            continue
    
    return []

def extract_gpu_models_from_attributes(attributes: List[Dict]) -> List[str]:
    """Extract GPU models from provider attributes"""
    gpu_models = set()  # Use set to avoid duplicates
    
    for attr in attributes:
        if not isinstance(attr, dict):
            continue
            
        key = attr.get("key", "").lower()
        value = str(attr.get("value", "")).strip()
        
        if not value:
            continue
        
        # Look for GPU-related attributes
        if any(keyword in key for keyword in ["gpu", "model", "vendor", "device"]):
            normalized = normalize_gpu_name(value)
            if normalized and normalized != "GPU-Generic":
                gpu_models.add(normalized)
        
        # Also check value for GPU indicators
        value_lower = value.lower()
        if any(keyword in value_lower for keyword in ["rtx", "nvidia", "amd", "tesla", "quadro"]):
            model = extract_model_from_string(value)
            if model:
                gpu_models.add(model)
    
    return list(gpu_models) or ["GPU-Generic"]

def extract_model_from_string(text: str) -> Optional[str]:
    """Extract GPU model from text string"""
    text = text.upper()
    
    # Common GPU patterns - ordered by specificity
    patterns = [
        "RTX 4090", "RTX 4080", "RTX 4070", "RTX 4060",
        "RTX 3090", "RTX 3080", "RTX 3070", "RTX 3060",
        "RTX 2080", "RTX 2070", "RTX 2060",
        "GTX 1080", "GTX 1070", "GTX 1060",
        "A100", "A6000", "A5000", "A4000", "A40", "A30", "A10",
        "V100", "P100", "P40", "T4", "K80",
        "H100", "H200"
    ]
    
    for pattern in patterns:
        if pattern in text:
            return pattern
    
    # Check for generic patterns
    if "RTX" in text:
        return "RTX 4090"  # Default high-end
    elif "GTX" in text:
        return "GTX 1080"  # Default mid-range
    elif "TESLA" in text:
        return "V100"  # Default datacenter
    
    return None

def estimate_akash_gpu_price(gpu_model: str) -> float:
    """Estimate Akash GPU price based on model (typically 30-60% of cloud prices)"""
    base_prices = {
        "RTX 4090": 0.35,
        "RTX 4080": 0.28,
        "RTX 4070": 0.20,
        "RTX 4060": 0.15,
        "RTX 3090": 0.22,
        "RTX 3080": 0.16,
        "RTX 3070": 0.14,
        "RTX 3060": 0.10,
        "RTX 2080": 0.12,
        "RTX 2070": 0.10,
        "GTX 1080": 0.08,
        "GTX 1070": 0.06,
        "A100": 1.40,
        "A6000": 0.75,
        "A5000": 0.45,
        "A4000": 0.30,
        "A40": 0.65,
        "A30": 0.40,
        "A10": 0.25,
        "V100": 0.45,
        "P100": 0.20,
        "T4": 0.11,
        "H100": 2.25,
        "H200": 3.50,
        "GPU-Generic": 0.25
    }
    
    gpu_upper = gpu_model.upper()
    for model, price in base_prices.items():
        if model.upper() in gpu_upper:
            return price
    
    return 0.25  # Default price

def get_synthetic_akash_data() -> List[Dict]:
    """Return synthetic Akash data based on typical offerings"""
    # Common GPUs available on Akash with competitive pricing
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
            "region": "akash-network",
            "availability": 1,
            "provider": "akash",
            "synthetic": True
        }
        offers.append(offer)
    
    return offers

def extract_gpu_from_bid(bid_data: Dict) -> str:
    """Extract GPU model from bid data"""
    try:
        # Check multiple possible locations for GPU info
        bid = bid_data.get("bid", bid_data)
        
        # Check escrow account attributes first
        escrow = bid_data.get("escrow_account", {})
        if escrow:
            attrs = escrow.get("attributes", [])
            for attr in attrs:
                if isinstance(attr, dict):
                    key = attr.get("key", "").lower()
                    value = attr.get("value", "")
                    if any(keyword in key for keyword in ["gpu", "model", "vendor"]):
                        normalized = normalize_gpu_name(value)
                        if normalized != "GPU-Generic":
                            return normalized
        
        # Check bid attributes
        if "attributes" in bid:
            for attr in bid["attributes"]:
                if isinstance(attr, dict):
                    key = attr.get("key", "").lower()
                    value = attr.get("value", "")
                    if "gpu" in key:
                        return normalize_gpu_name(value)
        
        # Default to high-end GPU for Akash
        return "RTX 4090"
        
    except Exception as e:
        logger.debug(f"Error extracting GPU from bid: {e}")
        return "RTX 4090"

def normalize_gpu_name(gpu_name: str) -> str:
    """Normalize GPU names for consistent comparison."""
    if not gpu_name or not gpu_name.strip():
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
    replacements = {
        "RTX4090": "RTX 4090",
        "RTX4080": "RTX 4080", 
        "RTX4070": "RTX 4070",
        "RTX3090": "RTX 3090",
        "RTX3080": "RTX 3080",
        "RTX3070": "RTX 3070"
    }
    
    for old, new in replacements.items():
        gpu_name = gpu_name.replace(old, new)
    
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