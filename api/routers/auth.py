from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import redis  # Add this missing import
import logging

from models import User, Token
from security import authenticate_user, create_access_token, get_current_active_user
from dependencies import redis_dependency, db_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    conn = Depends(db_dependency),  # Use the wrapper dependency
    redis_conn: Annotated[redis.Redis, Depends(redis_dependency)] = None,
):
    """
    Login endpoint to obtain access token.
    
    Args:
        form_data: OAuth2 form data containing username and password
        conn: Database connection dependency
        redis_conn: Optional Redis connection for enhanced security
        
    Returns:
        Token object with access_token and token_type
    """
    try:
        # Authenticate user with database
        user = await authenticate_user(conn, email=form_data.username, password=form_data.password)
        
        if not user:
            logger.warning(f"Authentication failed for email: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token with user's email as subject
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user["email"]},  # Use email from user record
            expires_delta=access_token_expires
        )
        
        logger.info(f"Access token created successfully for user: {user['email']}")
        
        return Token(
            access_token=access_token, 
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes in seconds
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like authentication failures)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )
    # Remove the finally block - let the dependency handle connection cleanup

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user from dependency
        
    Returns:
        User object with current user's information
    """
    logger.info(f"User profile accessed: {current_user.email}")
    return current_user

@router.post("/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
    redis_conn: Annotated[redis.Redis, Depends(redis_dependency)] = None,
):
    """
    Logout endpoint to revoke access token.
    
    Args:
        current_user: Current authenticated user
        redis_conn: Optional Redis connection for token revocation
        
    Returns:
        Success message
    """
    try:
        # Optional: Add token to revocation list if Redis is available
        if redis_conn:
            from security import revoke_token
            await revoke_token(current_user.email, redis_conn)
        
        logger.info(f"User logged out successfully: {current_user.email}")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Error during logout for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during logout"
        )

@router.get("/verify-token")
async def verify_token(current_user: Annotated[User, Depends(get_current_active_user)]):
    """
    Verify if the current token is valid and return user info.
    
    Args:
        current_user: Current authenticated user from dependency
        
    Returns:
        Token verification status and user info
    """
    return {
        "valid": True,
        "user": {
            "email": current_user.email,
            "username": current_user.username,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at
        }
    }

@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Refresh the access token for the current user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        New Token object with refreshed access_token
    """
    try:
        # Create new access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": current_user.email},
            expires_delta=access_token_expires
        )
        
        logger.info(f"Token refreshed successfully for user: {current_user.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes in seconds
        )
        
    except Exception as e:
        logger.error(f"Error refreshing token for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error refreshing token"
        )