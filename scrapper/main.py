import os
import time
import logging
import schedule
import requests
import redis
import sentry_sdk
from dotenv import load_dotenv

# Assuming utils.py is in the same directory
from utils import init_sentry

# --- Basic Configuration ---

# Load environment variables from .env file
load_dotenv()

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Sentry for error tracking
init_sentry()

# --- Constants & Environment Variables ---

REDIS_URL = os.getenv("REDIS_URL")
REDIS_STREAM_NAME = "raw_prices"

# For the smoke test, we'll focus on these two sources
DATA_SOURCES = {
    "io.net": "https://cloud.io.net/api/v2/gpus/all-offers",
    # Using a known public endpoint from a similar service as a placeholder
    "hyperbolic": "https://api.vast.ai/v0/asks",
}

# --- Redis Connection ---

try:
    redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
    # Check if the connection is alive
    redis_conn.ping()
    logging.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logging.error(f"Could not connect to Redis: {e}")
    sentry_sdk.capture_exception(e)
    # Exit if we can't connect to Redis, as it's critical
    exit(1)

# --- Core Functions ---

def fetch_data(url: str, source_name: str) -> dict | None:
    """Fetches JSON data from a given URL."""
    try:
        response = requests.get(url, timeout=15)  # 15-second timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        logging.info(f"Successfully fetched data from {source_name}.")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from {source_name}: {e}")
        sentry_sdk.capture_exception(e)
        return None

def normalize_and_publish(data: dict, source_name: str, r_conn: redis.Redis):
    """
    Normalizes fetched data and publishes it to a Redis Stream.
    This function needs to be adapted based on the actual structure of each source's API response.
    """
    # Handle different data structures for different sources
    if source_name == "io.net":
        # io.net might have a different structure
        offers = data.get('data', data.get('offers', []))
    elif source_name == "hyperbolic":
        # vast.ai returns data directly as a list
        offers = data if isinstance(data, list) else data.get('offers', [])
    else:
        offers = data.get('offers', data)
    
    if not isinstance(offers, list):
        logging.warning(f"Could not find a list of offers in the response from {source_name}.")
        sentry_sdk.capture_message(f"Unexpected data structure from {source_name}", extra={"data_keys": list(data.keys()) if isinstance(data, dict) else "not_dict"})
        return

    records_published = 0
    for item in offers:
        try:
            # Source-specific field mapping
            if source_name == "io.net":
                gpu_model = item.get('gpu_type') or item.get('model', 'N/A')
                price = item.get('price_per_hour') or item.get('hourly_price', 0.0)
                region = item.get('location') or item.get('datacenter', 'N/A')
            else:  # hyperbolic/vast.ai
                gpu_model = item.get('gpu_name', 'N/A')
                price = item.get('dph_total', 0.0)
                region = item.get('geolocation', 'N/A')

            payload = {
                'timestamp': int(time.time()),
                'cloud': source_name,
                'gpu_model': gpu_model,
                'price_usd_hr': round(float(price), 5),
                'region': region,
                'raw_data': str(item)
            }

            # Basic validation: ensure we have a model and a price
            if payload['gpu_model'] != 'N/A' and payload['price_usd_hr'] > 0:
                r_conn.xadd(REDIS_STREAM_NAME, payload)
                records_published += 1

        except (TypeError, KeyError, ValueError) as e:
            logging.warning(f"Skipping record from {source_name} due to normalization error: {e}")
            continue

    logging.info(f"Published {records_published} records from {source_name} to Redis Stream '{REDIS_STREAM_NAME}'.")


def run_scrape_job():
    """The main job to be executed by the scheduler."""
    logging.info("--- Starting new scrape cycle ---")
    start_time = time.time()
    total_records = 0
    
    for source, url in DATA_SOURCES.items():
        try:
            data = fetch_data(url, source)
            if data:
                records_before = total_records
                normalize_and_publish(data, source, redis_conn)
                # This is approximate since we don't return the count
                logging.debug(f"Processed data from {source}")
        except Exception as e:
            logging.error(f"Unexpected error processing {source}: {e}")
            sentry_sdk.capture_exception(e)
    
    elapsed = time.time() - start_time
    logging.info(f"--- Scrape cycle completed in {elapsed:.2f} seconds ---")

# --- Main Execution Block ---

if __name__ == "__main__":
    logging.info("🚀 Scraper service starting...")
    sentry_sdk.capture_message("Scraper Service Started")

    # Schedule the job to run every 60 seconds
    schedule.every(60).seconds.do(run_scrape_job)

    # Run the job once immediately at startup
    logging.info("Running initial scrape job...")
    run_scrape_job()

    # Main loop to run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(1)