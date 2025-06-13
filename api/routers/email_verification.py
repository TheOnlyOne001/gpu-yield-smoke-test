import os
from datetime import timedelta
from typing import Annotated
import secrets
import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse
import redis

from models import User, AuthProvider
from security import get_current_user, create_access_token
from dependencies import redis_dependency, db_dependency
from crud import get_user_by_email, update_user_verification
from utils.email_service import send_verification_email, send_welcome_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Email Verification"])

@router.post("/send-verification-email")
async def send_verification_email_endpoint(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Send email verification link to the current user.
    
    Args:
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        conn: Database connection
        redis_conn: Redis connection for token storage
        
    Returns:
        Success message
    """
    try:
        if current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )
        
        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        
        # Store verification token in Redis (expires in 24 hours)
        await redis_conn.setex(
            f"email_verification:{verification_token}",
            86400,  # 24 hours
            current_user.email
        )
        
        # Send verification email in background
        background_tasks.add_task(
            send_verification_email,
            current_user.email,
            current_user.full_name or current_user.username or "User",
            verification_token
        )
        
        logger.info(f"Verification email sent to {current_user.email}")
        
        return {
            "message": "Verification email sent successfully",
            "expires_in": 86400
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending verification email to {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )

@router.get("/verify-email/{token}")
async def verify_email(
    token: str,
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Verify email address using verification token.
    
    Args:
        token: Email verification token
        conn: Database connection
        redis_conn: Redis connection
        
    Returns:
        HTML response with verification result
    """
    try:
        # Get email from Redis token
        email = await redis_conn.get(f"email_verification:{token}")
        
        if not email:
            return HTMLResponse(
                content=get_verification_html("expired"),
                status_code=400
            )
        
        email = email.decode('utf-8') if isinstance(email, bytes) else email
        
        # Get user from database
        user = await get_user_by_email(conn, email)
        
        if not user:
            return HTMLResponse(
                content=get_verification_html("user_not_found"),
                status_code=404
            )
        
        if user.get('is_verified'):
            return HTMLResponse(
                content=get_verification_html("already_verified")
            )
        
        # Update user verification status
        success = await update_user_verification(conn, user['id'], True)
        
        if success:
            # Delete verification token
            await redis_conn.delete(f"email_verification:{token}")
            
            logger.info(f"Email verified successfully for user: {email}")
            
            return HTMLResponse(
                content=get_verification_html("success", email)
            )
        else:
            return HTMLResponse(
                content=get_verification_html("error"),
                status_code=500
            )
            
    except Exception as e:
        logger.error(f"Email verification error for token {token}: {e}")
        return HTMLResponse(
            content=get_verification_html("error"),
            status_code=500
        )

@router.post("/resend-verification")
async def resend_verification_email(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Resend verification email to current user.
    
    Args:
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        conn: Database connection
        redis_conn: Redis connection
        
    Returns:
        Success message
    """
    try:
        if current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )
        
        # Check rate limiting (max 3 emails per hour)
        rate_limit_key = f"verification_rate_limit:{current_user.email}"
        current_count = await redis_conn.get(rate_limit_key)
        
        if current_count and int(current_count) >= 3:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification emails sent. Please wait an hour before requesting again."
            )
        
        # Increment rate limit counter
        await redis_conn.setex(rate_limit_key, 3600, int(current_count or 0) + 1)
        
        # Generate new verification token
        verification_token = secrets.token_urlsafe(32)
        
        # Store verification token in Redis (expires in 24 hours)
        await redis_conn.setex(
            f"email_verification:{verification_token}",
            86400,
            current_user.email
        )
        
        # Send verification email in background
        background_tasks.add_task(
            send_verification_email,
            current_user.email,
            current_user.full_name or current_user.username or "User",
            verification_token
        )
        
        logger.info(f"Verification email resent to {current_user.email}")
        
        return {
            "message": "Verification email sent successfully",
            "expires_in": 86400
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending verification email to {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email"
        )

@router.get("/verification-status")
async def get_verification_status(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get current user's email verification status.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Verification status information
    """
    return {
        "email": current_user.email,
        "is_verified": current_user.is_verified,
        "auth_provider": current_user.auth_provider,
        "requires_verification": current_user.auth_provider == AuthProvider.EMAIL and not current_user.is_verified
    }

def get_verification_html(status: str, email: str = None) -> str:
    """
    Generate HTML response for email verification.
    
    Args:
        status: Verification status (success, expired, error, etc.)
        email: User email (optional)
        
    Returns:
        HTML content
    """
    base_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Verification - GPU Yield</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                padding: 3rem;
                max-width: 500px;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                text-align: center;
            }}
            .icon {{
                font-size: 4rem;
                margin-bottom: 1rem;
            }}
            .success {{ color: #10b981; }}
            .error {{ color: #ef4444; }}
            .warning {{ color: #f59e0b; }}
            h1 {{
                color: #1f2937;
                margin-bottom: 1rem;
                font-size: 1.5rem;
            }}
            p {{
                color: #6b7280;
                line-height: 1.6;
                margin-bottom: 2rem;
            }}
            .button {{
                display: inline-block;
                background: #3b82f6;
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 6px;
                text-decoration: none;
                font-weight: 500;
                transition: background-color 0.2s;
            }}
            .button:hover {{
                background: #2563eb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {content}
        </div>
    </body>
    </html>
    """
    
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    if status == "success":
        content = f"""
            <div class="icon success">✅</div>
            <h1>Email Verified Successfully!</h1>
            <p>Your email address <strong>{email}</strong> has been verified. You now have full access to your GPU Yield account.</p>
            <a href="{frontend_url}/dashboard" class="button">Go to Dashboard</a>
        """
    elif status == "expired":
        content = f"""
            <div class="icon warning">⏰</div>
            <h1>Verification Link Expired</h1>
            <p>This verification link has expired or is invalid. Please request a new verification email from your account settings.</p>
            <a href="{frontend_url}/login" class="button">Sign In</a>
        """
    elif status == "already_verified":
        content = f"""
            <div class="icon success">✅</div>
            <h1>Already Verified</h1>
            <p>Your email address is already verified. You can continue using your GPU Yield account.</p>
            <a href="{frontend_url}/dashboard" class="button">Go to Dashboard</a>
        """
    elif status == "user_not_found":
        content = f"""
            <div class="icon error">❌</div>
            <h1>User Not Found</h1>
            <p>We couldn't find a user associated with this verification link. Please check your email or create a new account.</p>
            <a href="{frontend_url}/signup" class="button">Sign Up</a>
        """
    else:  # error
        content = f"""
            <div class="icon error">❌</div>
            <h1>Verification Failed</h1>
            <p>There was an error verifying your email address. Please try again or contact support if the problem persists.</p>
            <a href="{frontend_url}/support" class="button">Contact Support</a>
        """
    
    return base_html.format(content=content)