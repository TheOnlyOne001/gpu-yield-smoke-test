import redis
import os
import logging
from fastapi import HTTPException, status
from crud import get_db_connection

logger = logging.getLogger(__name__)

def redis_dependency():
    """Dependency to inject Redis connection into endpoints."""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        connection = redis.from_url(redis_url, decode_responses=True)
        connection.ping()  # Test connection
        return connection
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service is unavailable"
        )

async def db_dependency():
    """Database dependency that yields database connection"""
    try:
        async for connection in get_db_connection():
            yield connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is unavailable"
        )