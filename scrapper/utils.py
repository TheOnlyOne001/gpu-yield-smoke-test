import sentry_sdk
import os
from logging import getLogger

# Initialize a logger
logger = getLogger(__name__)

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
        return True
    else:
        logger.warning("SENTRY_DSN not found. Sentry will not be initialized.")
        return False