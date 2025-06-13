from datetime import datetime
from typing import Annotated, List
import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
import redis

from models import User, AuthProvider
from security import get_current_user
from dependencies import redis_dependency, db_dependency
from crud import (
    get_user_oauth_providers, 
    link_oauth_to_existing_user, 
    unlink_oauth_provider,
    get_user_by_oauth,
    update_user_last_login
)
from utils.email_service import send_oauth_linked_email, send_security_alert_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Account Linking"])

@router.get("/linked-accounts")
async def get_linked_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    conn = Depends(db_dependency)
):
    """
    Get all OAuth providers linked to the current user's account.
    
    Args:
        current_user: Current authenticated user
        conn: Database connection
        
    Returns:
        List of linked OAuth accounts
    """
    try:
        linked_accounts = await get_user_oauth_providers(conn, current_user.id)
        
        # Format the response
        formatted_accounts = []
        for account in linked_accounts:
            formatted_accounts.append({
                "provider": account['auth_provider'],
                "provider_id": account['provider_id'],
                "linked_at": account['created_at'].isoformat() if account['created_at'] else None,
                "is_primary": account['auth_provider'] == current_user.auth_provider,
                "avatar_url": account.get('avatar_url')
            })
        
        return {
            "accounts": formatted_accounts,
            "primary_provider": current_user.auth_provider,
            "total_linked": len(formatted_accounts)
        }
        
    except Exception as e:
        logger.error(f"Error getting linked accounts for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve linked accounts"
        )

@router.post("/link/{provider}")
async def initiate_account_linking(
    provider: str,
    current_user: Annotated[User, Depends(get_current_user)],
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Initiate OAuth account linking process.
    
    Args:
        provider: OAuth provider to link (google, twitter, discord, whatsapp)
        current_user: Current authenticated user
        redis_conn: Redis connection for state management
        
    Returns:
        OAuth authorization URL for linking
    """
    try:
        # Validate provider
        valid_providers = ['google', 'twitter', 'discord', 'whatsapp']
        if provider not in valid_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider. Valid providers: {', '.join(valid_providers)}"
            )
        
        # Check if provider is already linked
        linked_accounts = await get_user_oauth_providers(conn, current_user.id)
        if any(account['auth_provider'] == provider for account in linked_accounts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{provider.title()} account is already linked"
            )
        
        # Store linking intent in Redis
        import secrets
        link_state = secrets.token_urlsafe(32)
        
        await redis_conn.setex(
            f"oauth_link:{link_state}",
            600,  # 10 minutes
            f"{current_user.id}:{provider}"
        )
        
        # Return OAuth URL (this would typically redirect to OAuth provider)
        oauth_url = f"/auth/{provider}/login?state={link_state}&link=true"
        
        logger.info(f"Account linking initiated for user {current_user.id} with {provider}")
        
        return {
            "oauth_url": oauth_url,
            "provider": provider,
            "state": link_state,
            "expires_in": 600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating account linking for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate account linking"
        )

@router.post("/complete-linking")
async def complete_account_linking(
    state: str,
    provider_id: str,
    provider_data: dict,
    background_tasks: BackgroundTasks,
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Complete OAuth account linking process.
    
    Args:
        state: OAuth state parameter
        provider_id: Provider-specific user ID
        provider_data: Additional provider data (avatar, name, etc.)
        background_tasks: FastAPI background tasks
        conn: Database connection
        redis_conn: Redis connection
        
    Returns:
        Success message
    """
    try:
        # Get linking intent from Redis
        link_data = await redis_conn.get(f"oauth_link:{state}")
        
        if not link_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired linking state"
            )
        
        link_data = link_data.decode('utf-8') if isinstance(link_data, bytes) else link_data
        user_id, provider = link_data.split(':', 1)
        user_id = int(user_id)
        
        # Check if this OAuth account is already linked to another user
        existing_oauth_user = await get_user_by_oauth(
            conn, 
            AuthProvider(provider), 
            provider_id
        )
        
        if existing_oauth_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This {provider.title()} account is already linked to another user"
            )
        
        # Link OAuth account to user
        success = await link_oauth_to_existing_user(
            conn=conn,
            user_id=user_id,
            provider=AuthProvider(provider),
            provider_id=provider_id,
            avatar_url=provider_data.get('avatar_url'),
            full_name=provider_data.get('full_name')
        )
        
        if success:
            # Delete linking state
            await redis_conn.delete(f"oauth_link:{state}")
            
            # Get user info for email notification
            from crud import get_user_by_id
            user = await get_user_by_id(conn, user_id)
            
            if user:
                # Send notification email
                background_tasks.add_task(
                    send_oauth_linked_email,
                    user['email'],
                    user.get('full_name') or user.get('username') or "User",
                    provider
                )
            
            logger.info(f"OAuth account {provider} linked successfully for user {user_id}")
            
            return {
                "message": f"{provider.title()} account linked successfully",
                "provider": provider,
                "linked_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to link account"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing account linking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete account linking"
        )

@router.post("/unlink/{provider}")
async def unlink_oauth_account(
    provider: str,
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    conn = Depends(db_dependency)
):
    """
    Unlink OAuth provider from user account.
    
    Args:
        provider: OAuth provider to unlink
        current_user: Current authenticated user
        background_tasks: FastAPI background tasks
        conn: Database connection
        
    Returns:
        Success message
    """
    try:
        # Validate provider
        valid_providers = ['google', 'twitter', 'discord', 'whatsapp']
        if provider not in valid_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider. Valid providers: {', '.join(valid_providers)}"
            )
        
        # Check if this is the user's primary authentication method
        if current_user.auth_provider == provider:
            # Check if user has a password set
            if not hasattr(current_user, 'hashed_password') or not current_user.hashed_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot unlink primary authentication method. Please set a password first."
                )
        
        # Get linked accounts to verify the provider is actually linked
        linked_accounts = await get_user_oauth_providers(conn, current_user.id)
        if not any(account['auth_provider'] == provider for account in linked_accounts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{provider.title()} account is not linked to your account"
            )
        
        # Unlink the OAuth provider
        success = await unlink_oauth_provider(
            conn, 
            current_user.id, 
            AuthProvider(provider)
        )
        
        if success:
            # Send security alert email
            background_tasks.add_task(
                send_security_alert_email,
                current_user.email,
                current_user.full_name or current_user.username or "User",
                f"{provider.title()} account unlinked",
                f"Your {provider.title()} account has been unlinked from your GPU Yield account."
            )
            
            logger.info(f"OAuth account {provider} unlinked for user {current_user.id}")
            
            return {
                "message": f"{provider.title()} account unlinked successfully",
                "provider": provider,
                "unlinked_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to unlink account"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlinking account {provider} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink account"
        )

@router.post("/set-primary/{provider}")
async def set_primary_auth_method(
    provider: str,
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    conn = Depends(db_dependency)
):
    """
    Set a linked OAuth provider as the primary authentication method.
    
    Args:
        provider: OAuth provider to set as primary
        current_user: Current authenticated user
        background_tasks: FastAPI background tasks
        conn: Database connection
        
    Returns:
        Success message
    """
    try:
        # Validate provider
        valid_providers = ['email', 'google', 'twitter', 'discord', 'whatsapp']
        if provider not in valid_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider. Valid providers: {', '.join(valid_providers)}"
            )
        
        # Check if provider is already primary
        if current_user.auth_provider == provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{provider.title()} is already your primary authentication method"
            )
        
        # If setting OAuth provider as primary, verify it's linked
        if provider != 'email':
            linked_accounts = await get_user_oauth_providers(conn, current_user.id)
            if not any(account['auth_provider'] == provider for account in linked_accounts):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{provider.title()} account is not linked to your account"
                )
        
        # Update primary authentication method
        from crud import update_user_auth_provider
        success = await update_user_auth_provider(
            conn, 
            current_user.id, 
            AuthProvider(provider)
        )
        
        if success:
            # Send security alert email
            background_tasks.add_task(
                send_security_alert_email,
                current_user.email,
                current_user.full_name or current_user.username or "User",
                "Primary authentication method changed",
                f"Your primary authentication method has been changed to {provider.title()}."
            )
            
            logger.info(f"Primary auth method changed to {provider} for user {current_user.id}")
            
            return {
                "message": f"Primary authentication method changed to {provider.title()}",
                "provider": provider,
                "changed_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update primary authentication method"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting primary auth method {provider} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update primary authentication method"
        )

@router.get("/auth-methods")
async def get_available_auth_methods(
    current_user: Annotated[User, Depends(get_current_user)],
    conn = Depends(db_dependency)
):
    """
    Get available authentication methods for the current user.
    
    Args:
        current_user: Current authenticated user
        conn: Database connection
        
    Returns:
        Available authentication methods
    """
    try:
        # Get linked OAuth accounts
        linked_accounts = await get_user_oauth_providers(conn, current_user.id)
        
        # Check if user has password set
        has_password = hasattr(current_user, 'hashed_password') and current_user.hashed_password
        
        # Build available methods
        available_methods = []
        
        if has_password:
            available_methods.append({
                "provider": "email",
                "name": "Email & Password",
                "is_primary": current_user.auth_provider == "email",
                "can_set_primary": True,
                "can_unlink": len(linked_accounts) > 0  # Can only unlink if other methods available
            })
        
        for account in linked_accounts:
            provider = account['auth_provider']
            available_methods.append({
                "provider": provider,
                "name": provider.title(),
                "is_primary": current_user.auth_provider == provider,
                "can_set_primary": True,
                "can_unlink": has_password or len(linked_accounts) > 1,  # Can unlink if password or multiple OAuth
                "linked_at": account['created_at'].isoformat() if account['created_at'] else None
            })
        
        return {
            "available_methods": available_methods,
            "primary_method": current_user.auth_provider,
            "has_password": has_password,
            "total_methods": len(available_methods)
        }
        
    except Exception as e:
        logger.error(f"Error getting auth methods for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve authentication methods"
        )