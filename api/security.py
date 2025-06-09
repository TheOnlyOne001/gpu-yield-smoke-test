import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
import redis
import logging
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from models import TokenData, User
from utils.connections import get_redis_connection

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

# Password utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a hash for the given password."""
    return pwd_context.hash(password)

# Token creation function
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# User authentication and dependency functions
async def authenticate_user(username: str, password: str, redis_conn: redis.Redis):
    """Authenticate a user using credentials stored in Redis."""
    user_key = f"user:email:{username}"
    try:
        user_hash = redis_conn.hget(user_key, "password_hash")
        if user_hash and verify_password(password, user_hash):
            user_data = redis_conn.hgetall(user_key)
            if user_data:
                return User(
                    id=user_data.get("id"),
                    email=username,
                    username=user_data.get("username"),
                    hashed_password=user_hash,
                    is_active=user_data.get("status", "active") == "active",
                )
    except Exception as e:
        logger.error(f"Authentication error for {username}: {e}")
    return None

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    redis_conn: redis.Redis = Depends(get_redis_connection),
) -> User:
    """Get the current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    try:
        user_data = redis_conn.hgetall(f"user:email:{token_data.email}")
        if user_data:
            return User(
                id=user_data.get("id"),
                email=token_data.email,
                username=user_data.get("username"),
                hashed_password=user_data.get("password_hash", ""),
                is_active=user_data.get("status", "active") == "active",
            )
    except Exception as e:
        logger.error(f"Error retrieving user {token_data.email}: {e}")
    raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user