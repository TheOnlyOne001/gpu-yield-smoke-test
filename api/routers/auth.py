from datetime import timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
import redis  # Add this missing import
import logging

from ..models import User, Token, SignupRequest, SignupResponse, AlertJob
from ..security import authenticate_user, create_access_token, get_current_active_user, get_password_hash
from ..dependencies import redis_dependency, db_dependency  
from ..crud import get_user_by_email, create_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=SignupResponse, summary="User Signup")
async def signup(
    signup_data: dict = Body(...),
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Handles user signup requests with database integration and job queuing.
    """
    try:
        email = signup_data.get('email')
        password = signup_data.get('password')
        username = signup_data.get('username')
        hcaptcha_response = signup_data.get('hcaptcha_response', 'development-test-key')
        gpu_models_interested = signup_data.get('gpu_models_interested', [])
        min_profit_threshold = signup_data.get('min_profit_threshold')
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        if not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required"
            )
        
        logger.info(f"New signup request from: {email}")
        
        # Basic hCaptcha validation (in production, verify with hCaptcha service)
        if not hcaptcha_response or len(hcaptcha_response) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid captcha response"
            )
        
        # Check if email already exists in database
        existing_user = await get_user_by_email(conn, email)
        if existing_user:
            logger.warning(f"Signup attempt with existing email: {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Use the provided password instead of generating a temp one
        hashed_password = get_password_hash(password)
        
        # Create user in database
        new_user = await create_user(
            conn=conn,
            email=email,
            username=username,
            hashed_password=hashed_password,
            gpu_models_interested=gpu_models_interested,
            min_profit_threshold=min_profit_threshold
        )
        
        user_id = str(new_user["id"])
        
        # Queue welcome email job
        welcome_job = AlertJob(
            job_type="send_welcome_email",
            email=email,
            user_id=user_id
        )
        
        try:
            redis_conn.xadd("alert_queue", welcome_job.dict())
            logger.info(f"Welcome email job queued for user: {email}")
        except Exception as e:
            logger.warning(f"Failed to queue welcome email for {email}: {e}")
            # Don't fail the signup if email queueing fails
        
        logger.info(f"User {email} successfully registered with ID {user_id}")
        
        return SignupResponse(
            status="success",
            message="Signup successful! You can now log in with your credentials.",
            user_id=user_id
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like validation errors)
        raise
    except ValueError as e:
        # Handle database constraint errors (like duplicate email)
        logger.error(f"Database constraint error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during signup"
        )

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
            from ..security import revoke_token
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