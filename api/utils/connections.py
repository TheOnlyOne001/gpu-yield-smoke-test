import os
import logging
import redis
import sentry_sdk
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up a standard logger instance
logger = logging.getLogger(__name__)

def init_sentry():
    """
    Initializes the Sentry SDK for error reporting.

    Reads the SENTRY_DSN from environment variables. If the DSN is found,
    it initializes Sentry. Otherwise, it logs a warning.
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            traces_sample_rate=1.0,
        )
        logger.info("Sentry initialized successfully.")
    else:
        logger.warning("SENTRY_DSN not found. Sentry will not be initialized.")

# Global variable for Redis connection pool
redis_pool = None

def get_redis_connection():
    """
    Creates and returns a Redis connection from a thread-safe connection pool.
    
    Returns:
        redis.Redis: Redis connection object or None if connection fails
    """
    global redis_pool
    
    # Check if the pool needs to be created
    if redis_pool is None:
        try:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                logger.error("REDIS_URL not found in environment variables")
                return None
                
            redis_pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True)
            logger.info("Redis connection pool created successfully.")
        except Exception as e:
            logger.error(f"Failed to create Redis connection pool: {e}")
            sentry_sdk.capture_exception(e)
            return None
    
    # Get a connection from the pool and test it
    try:
        connection = redis.Redis(connection_pool=redis_pool)
        connection.ping()  # Test the connection
        return connection
    except Exception as e:
        logger.error(f"Failed to get Redis connection from pool: {e}")
        sentry_sdk.capture_exception(e)
        return None