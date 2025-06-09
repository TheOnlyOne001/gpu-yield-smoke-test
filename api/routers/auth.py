from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
import redis
import logging

from models import User, Token
from security import authenticate_user, create_access_token, get_current_active_user
from utils import get_redis_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def redis_dependency() -> redis.Redis:
    """Provide a Redis connection for request handlers."""
    connection = get_redis_connection()
    if connection is None:
        logger.error("Redis service unavailable")
        raise HTTPException(status_code=503, detail="Redis service is unavailable")
    return connection

@router.post("/token", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    redis_conn: Annotated[redis.Redis, Depends(redis_dependency)],
):
    user = await authenticate_user(form_data.username, form_data.password, redis_conn)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires  # Use email instead of username
    )
    return Token(access_token=access_token, token_type="bearer")

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user