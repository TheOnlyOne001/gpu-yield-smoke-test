from datetime import timedelta
import secrets
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
import redis

from models import PasswordResetRequest, PasswordResetConfirm, AuthProvider
from security import get_password_hash, verify_password
from dependencies import redis_dependency, db_dependency
from crud import get_user_by_email, update_user_password
from utils.email_service import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Password Reset"])

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Send password reset email to user.
    
    Args:
        request: Password reset request with email
        background_tasks: FastAPI background tasks
        conn: Database connection
        redis_conn: Redis connection for token storage
        
    Returns:
        Success message (always returns success for security)
    """
    try:
        # Always return success message for security (don't reveal if email exists)
        success_message = {
            "message": "If an account with that email exists, we've sent a password reset link.",
            "expires_in": 3600  # 1 hour
        }
        
        # Get user from database
        user = await get_user_by_email(conn, request.email)
        
        if not user:
            logger.info(f"Password reset requested for non-existent email: {request.email}")
            return success_message
        
        # Check if user uses email authentication
        if user.get('auth_provider') != AuthProvider.EMAIL.value:
            logger.info(f"Password reset requested for OAuth user: {request.email}")
            return success_message
        
        # Check rate limiting (max 3 requests per hour per email)
        rate_limit_key = f"password_reset_rate_limit:{request.email}"
        current_count = await redis_conn.get(rate_limit_key)
        
        if current_count and int(current_count) >= 3:
            logger.warning(f"Password reset rate limit exceeded for: {request.email}")
            return success_message  # Don't reveal rate limiting for security
        
        # Increment rate limit counter
        await redis_conn.setex(rate_limit_key, 3600, int(current_count or 0) + 1)
        
        # Generate password reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Store reset token in Redis (expires in 1 hour)
        await redis_conn.setex(
            f"password_reset:{reset_token}",
            3600,  # 1 hour
            request.email
        )
        
        # Send password reset email in background
        background_tasks.add_task(
            send_password_reset_email,
            request.email,
            user.get('full_name') or user.get('username') or "User",
            reset_token
        )
        
        logger.info(f"Password reset email sent to {request.email}")
        
        return success_message
        
    except Exception as e:
        logger.error(f"Error processing password reset for {request.email}: {e}")
        # Return success message even on error for security
        return {
            "message": "If an account with that email exists, we've sent a password reset link.",
            "expires_in": 3600
        }

@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirm,
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Reset user password using reset token.
    
    Args:
        request: Password reset confirmation with token and new password
        conn: Database connection
        redis_conn: Redis connection
        
    Returns:
        Success message
    """
    try:
        # Get email from Redis token
        email = await redis_conn.get(f"password_reset:{request.token}")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        email = email.decode('utf-8') if isinstance(email, bytes) else email
        
        # Get user from database
        user = await get_user_by_email(conn, email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user uses email authentication
        if user.get('auth_provider') != AuthProvider.EMAIL.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset not available for OAuth accounts"
            )
        
        # Validate new password strength
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Hash new password
        hashed_password = get_password_hash(request.new_password)
        
        # Update user password
        success = await update_user_password(conn, user['id'], hashed_password)
        
        if success:
            # Delete reset token
            await redis_conn.delete(f"password_reset:{request.token}")
            
            # Clear rate limiting
            await redis_conn.delete(f"password_reset_rate_limit:{email}")
            
            logger.info(f"Password reset successfully for user: {email}")
            
            return {
                "message": "Password reset successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error for token {request.token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    conn = Depends(db_dependency)
):
    """
    Change password for authenticated user.
    
    Args:
        current_password: Current password
        new_password: New password
        current_user: Current authenticated user
        conn: Database connection
        
    Returns:
        Success message
    """
    try:
        # Check if user uses email authentication
        if current_user.get('auth_provider') != AuthProvider.EMAIL.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password change not available for OAuth accounts"
            )
        
        # Verify current password
        stored_password = current_user.get('hashed_password')
        if not stored_password or not verify_password(current_password, stored_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password strength
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )
        
        # Check if new password is different from current
        if verify_password(new_password, stored_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )
        
        # Hash new password
        hashed_password = get_password_hash(new_password)
        
        # Update user password
        success = await update_user_password(conn, current_user['id'], hashed_password)
        
        if success:
            logger.info(f"Password changed successfully for user: {current_user['email']}")
            
            return {
                "message": "Password changed successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error for user {current_user.get('email')}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.get("/validate-reset-token/{token}")
async def validate_reset_token(
    token: str,
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Validate password reset token.
    
    Args:
        token: Password reset token
        redis_conn: Redis connection
        
    Returns:
        Token validation status
    """
    try:
        # Check if token exists and get associated email
        email = await redis_conn.get(f"password_reset:{token}")
        
        if email:
            email = email.decode('utf-8') if isinstance(email, bytes) else email
            
            # Get token TTL
            ttl = await redis_conn.ttl(f"password_reset:{token}")
            
            return {
                "valid": True,
                "email": email,
                "expires_in": ttl
            }
        else:
            return {
                "valid": False,
                "message": "Invalid or expired token"
            }
            
    except Exception as e:
        logger.error(f"Error validating reset token {token}: {e}")
        return {
            "valid": False,
            "message": "Error validating token"
        }