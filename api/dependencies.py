import redis
import logging
from fastapi import HTTPException, status, Depends
from utils.connections import get_redis_connection
from crud import get_db_connection

logger = logging.getLogger(__name__)

def redis_dependency() -> redis.Redis:
    """Dependency to inject Redis connection into endpoints."""
    connection = get_redis_connection()
    if connection is None:
        logger.error("Redis service unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service is unavailable"
        )
    return connection

async def db_dependency():
    """Dependency to inject database connection into endpoints."""
    try:
        async for connection in get_db_connection():
            yield connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is unavailable"
        )