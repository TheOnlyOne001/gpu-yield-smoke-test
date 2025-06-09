import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
import redis
import logging
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from models import TokenData, User
from utils.connections import get_redis_connection
from crud import get_user_by_email

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
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Generate a hash for the given password."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise

# Token creation function
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with expiration."""
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
        
        logger.info(f"Access token created for subject: {data.get('sub')}")
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Token creation error: {e}")
        raise

# Updated database-based authentication
async def authenticate_user(conn, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user using credentials stored in the database.
    
    Args:
        conn: Database connection object
        email: User's email address
        password: Plain text password to verify
        
    Returns:
        User record dictionary if authentication successful, None otherwise
    """
    try:
        # Fetch user from database
        user_record = await get_user_by_email(conn, email)
        
        if not user_record:
            logger.info(f"Authentication failed: User not found for email {email}")
            return None
        
        # Verify password
        if not verify_password(password, user_record.get('hashed_password', '')):
            logger.info(f"Authentication failed: Invalid password for email {email}")
            return None
        
        # Check if user is active
        if not user_record.get('is_active', True):
            logger.info(f"Authentication failed: Inactive user {email}")
            return None
        
        logger.info(f"Authentication successful for email: {email}")
        return user_record
        
    except Exception as e:
        logger.error(f"Authentication error for email {email}: {e}")
        return None

# Database dependency
async def get_db():
    """Dependency to get database connection."""
    from dependencies import db_dependency
    async for conn in db_dependency():
        yield conn

# Updated database-based current user function
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    conn = Depends(get_db),
) -> User:
    """
    Get the current user from JWT token using database lookup.
    
    Args:
        token: JWT access token
        conn: Database connection
        
    Returns:
        User object if valid, raises HTTPException otherwise
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            logger.warning("JWT token missing subject (email)")
            raise credentials_exception
            
        token_data = TokenData(email=email)
        
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected JWT processing error: {e}")
        raise credentials_exception
    
    try:
        # Fetch user from database
        user_record = await get_user_by_email(conn, token_data.email)
        
        if not user_record:
            logger.warning(f"User not found in database: {token_data.email}")
            raise credentials_exception
        
        # Convert database record to User model
        user = User(
            id=str(user_record.get("id", "")),
            email=user_record.get("email", ""),
            username=user_record.get("username"),
            hashed_password=user_record.get("hashed_password", ""),
            is_active=user_record.get("is_active", True),
            created_at=user_record.get("created_at"),
            gpu_models_interested=user_record.get("gpu_models_interested", []),
            min_profit_threshold=user_record.get("min_profit_threshold", 0.0)
        )
        
        logger.info(f"Current user retrieved successfully: {user.email}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving current user {token_data.email}: {e}")
        raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User object if active, raises HTTPException if inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    return current_user