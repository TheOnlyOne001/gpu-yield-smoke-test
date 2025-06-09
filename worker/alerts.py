import os
import logging
import time
import redis
import sentry_sdk
import json
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load environment variables
load_dotenv()

# Set up standard logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_redis_with_retry(max_retries=6, delay_seconds=5):
    """Connect to Redis with retry logic for startup timing issues."""
    for attempt in range(max_retries):
        try:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                logger.warning(f"REDIS_URL not found, retrying in {delay_seconds} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay_seconds)
                continue
            
            # Attempt to connect
            conn = redis.from_url(redis_url, decode_responses=True)
            
            # Test the connection
            conn.ping()
            
            logger.info("Successfully connected to Redis")
            return conn
            
        except Exception as e:
            logger.warning(f"Redis not ready, retrying in {delay_seconds} seconds... (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(delay_seconds)
    
    logger.error("Failed to connect to Redis after all retries")
    return None

def init_sentry():
    """Initialize Sentry for error tracking in the worker."""
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=1.0,
        )
        logger.info("Sentry initialized for worker.")
    else:
        logger.warning("SENTRY_DSN not found. Sentry will not be initialized.")

# Initialize Sentry
init_sentry()

# Constants and Clients
ALERT_QUEUE_KEY = "alert_queue"
GROUP_NAME = "alert_group"
CONSUMER_NAME = "worker-1"

# Get environment variables
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# Instantiate SendGrid client
sendgrid_client = SendGridAPIClient(api_key=SENDGRID_API_KEY)

# Redis Connection with retry logic
redis_conn = connect_to_redis_with_retry()
if not redis_conn:
    exit(1)

# Create consumer group
try:
    redis_conn.xgroup_create(ALERT_QUEUE_KEY, GROUP_NAME, id="0", mkstream=True)
    logger.info(f"Created consumer group '{GROUP_NAME}' for stream '{ALERT_QUEUE_KEY}'")
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" in str(e):
        logger.info("Consumer group already exists.")
    else:
        logger.error(f"Error creating consumer group: {e}")
        sentry_sdk.capture_exception(e)

def send_welcome_email(recipient_email: str):
    """Send a welcome email to the specified recipient."""
    html_content = """
    <html>
    <body>
        <h2>Welcome to GPU Yield!</h2>
        <p>Thank you for signing up for GPU Yield. We're excited to help you maximize your GPU earnings!</p>
        <p>You'll receive alerts about the best pricing opportunities and profit margins.</p>
        <p>Best regards,<br>The GPU Yield Team</p>
    </body>
    </html>
    """
    
    try:
        message = Mail(
            from_email="alerts@gpuyield.xyz",
            to_emails=recipient_email,
            subject="Welcome to GPU Yield!",
            html_content=html_content
        )
        
        response = sendgrid_client.send(message)
        logger.info(f"Welcome email sent successfully to {recipient_email}. Status code: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {recipient_email}: {e}")
        sentry_sdk.capture_exception(e)

if __name__ == "__main__":
    logger.info("🚀 Alert worker starting...")
    sentry_sdk.capture_message("Alert Worker Started")
    
    while True:
        try:
            if not redis_conn.ping():
                redis_conn = connect_to_redis_with_retry()
            messages = redis_conn.xreadgroup(
                GROUP_NAME,
                CONSUMER_NAME,
                {ALERT_QUEUE_KEY: ">"},
                count=1,
                block=0  # Wait indefinitely for new messages
            )
            
            # Process messages
            for stream_name, stream_messages in messages:
                for message_id, fields in stream_messages:
                    try:
                        logger.info(f"Processing message {message_id}: {fields}")
                        
                        # Job dispatching based on job_type
                        job_type = fields.get("job_type")
                        
                        if job_type == "send_welcome_email":
                            email = fields.get("email")
                            if email:
                                send_welcome_email(email)
                            else:
                                logger.warning(f"No email field found in message {message_id}")
                        else:
                            logger.warning(f"Unknown job_type '{job_type}' in message {message_id}")
                        
                        # Acknowledge the message after successful processing
                        redis_conn.xack(ALERT_QUEUE_KEY, GROUP_NAME, message_id)
                        logger.info(f"Acknowledged message {message_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing message {message_id}: {e}")
                        sentry_sdk.capture_exception(e)
                        # Note: We don't acknowledge failed messages, so they remain in pending
                        
        except redis.ConnectionError:
            logger.error("Redis connection lost, reconnecting...")
            redis_conn = connect_to_redis_with_retry()
            continue
        except Exception as e:
            logger.error(f"Error in main worker loop: {e}")
            sentry_sdk.capture_exception(e)
            time.sleep(5)