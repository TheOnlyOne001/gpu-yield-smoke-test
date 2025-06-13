import os
import httpx
import secrets
from datetime import timedelta, datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlencode, quote

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
import redis
import logging

from models import Token, User, UserOAuth, AuthProvider, OAuthLoginRequest
from security import create_access_token, get_password_hash
from crud import (
    get_user_by_email, 
    get_user_by_oauth, 
    create_oauth_user,  # Changed from create_user_oauth
    update_user_last_login, 
    record_login_attempt,
    link_oauth_to_existing_user
)
from dependencies import redis_dependency, db_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["OAuth Authentication"])

# OAuth Configuration
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
TWITTER_CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')

# OAuth endpoints
OAUTH_ENDPOINTS = {
    'google': {
        'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'user_info_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
        'scope': 'openid email profile'
    },
    'twitter': {
        'auth_url': 'https://twitter.com/i/oauth2/authorize',
        'token_url': 'https://api.twitter.com/2/oauth2/token',
        'user_info_url': 'https://api.twitter.com/2/users/me?user.fields=profile_image_url,email',
        'scope': 'users.read tweet.read'
    },
    'discord': {
        'auth_url': 'https://discord.com/api/oauth2/authorize',
        'token_url': 'https://discord.com/api/oauth2/token',
        'user_info_url': 'https://discord.com/api/users/@me',
        'scope': 'identify email'
    }
}

# State management for OAuth flows
def create_oauth_state(redis_conn: redis.Redis, provider: str) -> str:
    """Create and store OAuth state parameter."""
    state = secrets.token_urlsafe(32)
    redis_conn.setex(f"oauth_state:{state}", 600, provider)  # REMOVED await
    return state

def verify_oauth_state(redis_conn: redis.Redis, state: str) -> Optional[str]:
    """Verify OAuth state parameter and return provider."""
    if not state:
        return None
    
    provider = redis_conn.get(f"oauth_state:{state}")  # REMOVED await
    if provider:
        redis_conn.delete(f"oauth_state:{state}")  # REMOVED await
        return provider.decode('utf-8') if isinstance(provider, bytes) else provider
    return None

# Google OAuth
@router.get("/google/login")
async def google_login(
    request: Request,
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """Initiate Google OAuth login."""
    try:
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        state = create_oauth_state(redis_conn, "google")  # REMOVED await
        redirect_uri = f"{request.base_url}auth/google/callback"
        
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'response_type': 'code',
            'scope': OAUTH_ENDPOINTS['google']['scope'],
            'redirect_uri': redirect_uri,
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        auth_url = f"{OAUTH_ENDPOINTS['google']['auth_url']}?{urlencode(params)}"
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.error(f"Google OAuth initiation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google login"
        )

@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """Handle Google OAuth callback."""
    try:
        if error:
            error_url = f"{FRONTEND_URL}/auth/error?error={error}&provider=google"
            return RedirectResponse(url=error_url)
        
        if not code or not state:
            error_url = f"{FRONTEND_URL}/auth/error?message=Missing authorization code or state"
            return RedirectResponse(url=error_url)
        
        # Verify state
        provider = verify_oauth_state(redis_conn, state)  # REMOVED await
        if provider != "google":
            error_url = f"{FRONTEND_URL}/auth/error?message=Invalid OAuth state"
            return RedirectResponse(url=error_url)
        
        # Exchange code for token
        redirect_uri = f"{request.base_url}auth/google/callback"
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                OAUTH_ENDPOINTS['google']['token_url'],
                data=token_data
            )
            token_json = token_response.json()
            
            if 'error' in token_json:
                raise Exception(f"Token exchange error: {token_json['error']}")
            
            # Get user info
            headers = {'Authorization': f"Bearer {token_json['access_token']}"}
            user_response = await client.get(
                OAUTH_ENDPOINTS['google']['user_info_url'],
                headers=headers
            )
            user_info = user_response.json()
        
        # Create OAuth user data
        oauth_user = UserOAuth(
            provider=AuthProvider.GOOGLE,
            provider_id=user_info['id'],
            email=user_info['email'],
            full_name=user_info.get('name'),
            avatar_url=user_info.get('picture'),
            raw_data=user_info
        )
        
        # Handle user creation/login
        user, access_token = await handle_oauth_user(conn, oauth_user, request)
        
        # Redirect to frontend with token
        user_data = quote(str({
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'avatar_url': user.avatar_url
        }))
        redirect_url = f"{FRONTEND_URL}/auth/success?token={access_token}&provider=google&user={user_data}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        error_url = f"{FRONTEND_URL}/auth/error?message=Google authentication failed&provider=google"
        return RedirectResponse(url=error_url)

# Twitter OAuth
@router.get("/twitter/login")
async def twitter_login(
    request: Request,
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """Initiate Twitter OAuth login."""
    try:
        if not TWITTER_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Twitter OAuth not configured")
        
        state = create_oauth_state(redis_conn, "twitter")  # REMOVED await
        redirect_uri = f"{request.base_url}auth/twitter/callback"
        
        params = {
            'client_id': TWITTER_CLIENT_ID,
            'response_type': 'code',
            'scope': OAUTH_ENDPOINTS['twitter']['scope'],
            'redirect_uri': redirect_uri,
            'state': state,
            'code_challenge': 'challenge',
            'code_challenge_method': 'plain'
        }
        
        auth_url = f"{OAUTH_ENDPOINTS['twitter']['auth_url']}?{urlencode(params)}"
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.error(f"Twitter OAuth initiation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Twitter login"
        )

@router.get("/twitter/callback")
async def twitter_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """Handle Twitter OAuth callback."""
    try:
        if error:
            error_url = f"{FRONTEND_URL}/auth/error?error={error}&provider=twitter"
            return RedirectResponse(url=error_url)
        
        if not code or not state:
            error_url = f"{FRONTEND_URL}/auth/error?message=Missing authorization code or state"
            return RedirectResponse(url=error_url)
        
        # Verify state
        provider = verify_oauth_state(redis_conn, state)  # REMOVED await
        if provider != "twitter":
            error_url = f"{FRONTEND_URL}/auth/error?message=Invalid OAuth state"
            return RedirectResponse(url=error_url)
        
        # Exchange code for token
        redirect_uri = f"{request.base_url}auth/twitter/callback"
        token_data = {
            'client_id': TWITTER_CLIENT_ID,
            'client_secret': TWITTER_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'code_verifier': 'challenge'
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                OAUTH_ENDPOINTS['twitter']['token_url'],
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            token_json = token_response.json()
            
            if 'error' in token_json:
                raise Exception(f"Token exchange error: {token_json['error']}")
            
            # Get user info
            headers = {'Authorization': f"Bearer {token_json['access_token']}"}
            user_response = await client.get(
                OAUTH_ENDPOINTS['twitter']['user_info_url'],
                headers=headers
            )
            user_data = user_response.json()['data']
        
        # Create OAuth user data
        oauth_user = UserOAuth(
            provider=AuthProvider.TWITTER,
            provider_id=user_data['id'],
            email=user_data.get('email'),  # May be None if not granted
            username=user_data['username'],
            full_name=user_data['name'],
            avatar_url=user_data.get('profile_image_url'),
            raw_data=user_data
        )
        
        # Handle user creation/login
        user, access_token = await handle_oauth_user(conn, oauth_user, request)
        
        # Redirect to frontend with token
        user_data = quote(str({
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name,
            'avatar_url': user.avatar_url
        }))
        redirect_url = f"{FRONTEND_URL}/auth/success?token={access_token}&provider=twitter&user={user_data}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Twitter OAuth callback error: {e}")
        error_url = f"{FRONTEND_URL}/auth/error?message=Twitter authentication failed&provider=twitter"
        return RedirectResponse(url=error_url)

# Discord OAuth
@router.get("/discord/login")
async def discord_login(
    request: Request,
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """Initiate Discord OAuth login."""
    try:
        if not DISCORD_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Discord OAuth not configured")
        
        state = create_oauth_state(redis_conn, "discord")  # REMOVED await
        redirect_uri = f"{request.base_url}auth/discord/callback"
        
        params = {
            'client_id': DISCORD_CLIENT_ID,
            'response_type': 'code',
            'scope': OAUTH_ENDPOINTS['discord']['scope'],
            'redirect_uri': redirect_uri,
            'state': state
        }
        
        auth_url = f"{OAUTH_ENDPOINTS['discord']['auth_url']}?{urlencode(params)}"
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.error(f"Discord OAuth initiation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Discord login"
        )

@router.get("/discord/callback")
async def discord_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    conn = Depends(db_dependency),
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """Handle Discord OAuth callback."""
    try:
        if error:
            error_url = f"{FRONTEND_URL}/auth/error?error={error}&provider=discord"
            return RedirectResponse(url=error_url)
        
        if not code or not state:
            error_url = f"{FRONTEND_URL}/auth/error?message=Missing authorization code or state"
            return RedirectResponse(url=error_url)
        
        # Verify state
        provider = verify_oauth_state(redis_conn, state)  # REMOVED await
        if provider != "discord":
            error_url = f"{FRONTEND_URL}/auth/error?message=Invalid OAuth state"
            return RedirectResponse(url=error_url)
        
        # Exchange code for token
        redirect_uri = f"{request.base_url}auth/discord/callback"
        token_data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                OAUTH_ENDPOINTS['discord']['token_url'],
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            token_json = token_response.json()
            
            if 'error' in token_json:
                raise Exception(f"Token exchange error: {token_json['error']}")
            
            # Get user info
            headers = {'Authorization': f"Bearer {token_json['access_token']}"}
            user_response = await client.get(
                OAUTH_ENDPOINTS['discord']['user_info_url'],
                headers=headers
            )
            user_data = user_response.json()
        
        # Build avatar URL
        avatar_url = None
        if user_data.get('avatar'):
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png"
        
        # Create OAuth user data
        oauth_user = UserOAuth(
            provider=AuthProvider.DISCORD,
            provider_id=user_data['id'],
            email=user_data.get('email'),
            username=user_data['username'],
            full_name=user_data.get('global_name', user_data['username']),
            avatar_url=avatar_url,
            raw_data=user_data
        )
        
        # Handle user creation/login
        user, access_token = await handle_oauth_user(conn, oauth_user, request)
        
        # Redirect to frontend with token
        user_data = quote(str({
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name,
            'avatar_url': user.avatar_url
        }))
        redirect_url = f"{FRONTEND_URL}/auth/success?token={access_token}&provider=discord&user={user_data}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Discord OAuth callback error: {e}")
        error_url = f"{FRONTEND_URL}/auth/error?message=Discord authentication failed&provider=discord"
        return RedirectResponse(url=error_url)

# Common OAuth user handling
async def handle_oauth_user(conn, oauth_user: UserOAuth, request: Request) -> tuple[User, str]:
    """Handle OAuth user creation or login."""
    try:
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Check if user exists by OAuth provider ID
        existing_user = await get_user_by_oauth_provider(conn, oauth_user.provider, oauth_user.provider_id)
        
        if existing_user:
            # Update last login
            await update_user_last_login(conn, existing_user['id'])
            user = User(**existing_user)
            
            # Record successful login
            await record_login_attempt(
                conn, user.id, user.email, client_ip, user_agent,
                oauth_user.provider.value, True
            )
        else:
            # Check if user exists by email
            if oauth_user.email:
                existing_email_user = await get_user_by_email(conn, oauth_user.email)
                if existing_email_user:
                    # Link OAuth account to existing email user
                    await link_oauth_to_user(conn, existing_email_user['id'], oauth_user)
                    user = User(**existing_email_user)
                else:
                    # Create new OAuth user
                    new_user = await create_oauth_user(conn, oauth_user)
                    user = User(**new_user)
            else:
                # For providers that don't provide email (like Twitter)
                # Generate a placeholder email
                placeholder_email = f"{oauth_user.provider.value}_{oauth_user.provider_id}@oauth.local"
                oauth_user.email = placeholder_email
                new_user = await create_oauth_user(conn, oauth_user)
                user = User(**new_user)
            
            # Record successful login for new user
            await record_login_attempt(
                conn, user.id, user.email, client_ip, user_agent,
                oauth_user.provider.value, True
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.email, "provider": oauth_user.provider.value, "user_id": user.id},
            expires_delta=access_token_expires
        )
        
        return user, access_token
        
    except Exception as e:
        logger.error(f"OAuth user handling error: {e}")
        
        # Record failed login attempt
        if oauth_user.email:
            await record_login_attempt(
                conn, None, oauth_user.email, client_ip, user_agent,
                oauth_user.provider.value, False, str(e)
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process OAuth authentication"
        )

async def get_user_by_oauth_provider(conn, provider: AuthProvider, provider_id: str):
    """Get user by OAuth provider and provider ID."""
    try:
        query = """
        SELECT id, email, username, is_active, is_verified, auth_provider, 
               provider_id, avatar_url, full_name, created_at, last_login,
               gpu_models_interested, min_profit_threshold
        FROM signups 
        WHERE auth_provider = $1 AND provider_id = $2 AND is_active = TRUE
        """
        
        result = await conn.fetch(query, provider.value, provider_id)
        
        if result:
            user = dict(result[0])
            if user.get('gpu_models_interested'):
                user['gpu_models_interested'] = list(user['gpu_models_interested'])
            return user
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting user by OAuth provider {provider.value} ID {provider_id}: {e}")
        return None

async def create_user_oauth(conn, oauth_user: UserOAuth):
    """Create new user from OAuth data."""
    try:
        query = """
        INSERT INTO signups (
            email, username, auth_provider, provider_id, avatar_url, 
            full_name, is_verified, is_active, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, email, username, is_active, is_verified, auth_provider, 
                  provider_id, avatar_url, full_name, created_at, last_login,
                  gpu_models_interested, min_profit_threshold
        """
        
        now = datetime.now(timezone.utc)
        result = await conn.fetch(
            query,
            oauth_user.email,
            oauth_user.username,
            oauth_user.provider.value,
            oauth_user.provider_id,
            oauth_user.avatar_url,
            oauth_user.full_name,
            True,  # OAuth users are automatically verified
            True,  # Active by default
            now
        )
        
        if result:
            user = dict(result[0])
            if user.get('gpu_models_interested'):
                user['gpu_models_interested'] = list(user['gpu_models_interested'])
            logger.info(f"Created new OAuth user: {oauth_user.email}")
            return user
        
        raise Exception("Failed to create OAuth user")
        
    except Exception as e:
        logger.error(f"Error creating OAuth user: {e}")
        raise

async def link_oauth_to_user(conn, user_id: int, oauth_user: UserOAuth):
    """Link OAuth account to existing user."""
    try:
        query = """
        UPDATE signups 
        SET auth_provider = $1, provider_id = $2, avatar_url = COALESCE($3, avatar_url),
            full_name = COALESCE($4, full_name), is_verified = TRUE
        WHERE id = $5
        """
        
        await conn.execute(
            query,
            oauth_user.provider.value,
            oauth_user.provider_id,
            oauth_user.avatar_url,
            oauth_user.full_name,
            user_id
        )
        
        logger.info(f"Linked {oauth_user.provider.value} OAuth to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error linking OAuth to user {user_id}: {e}")
        raise

# Get available OAuth providers
@router.get("/providers")
async def get_oauth_providers():
    """Get list of available OAuth providers."""
    providers = []
    
    if GOOGLE_CLIENT_ID:
        providers.append({
            "provider": "google",
            "display_name": "Google",
            "login_url": f"/auth/google/login"
        })
    
    if TWITTER_CLIENT_ID:
        providers.append({
            "provider": "twitter", 
            "display_name": "Twitter",
            "login_url": f"/auth/twitter/login"
        })
    
    if DISCORD_CLIENT_ID:
        providers.append({
            "provider": "discord",
            "display_name": "Discord", 
            "login_url": f"/auth/discord/login"
        })
    
    return {
        "providers": providers,
        "total_count": len(providers)
    }

@router.get("/status")
async def oauth_status():
    """Get OAuth configuration status."""
    return {
        "google": {"configured": bool(GOOGLE_CLIENT_ID)},
        "twitter": {"configured": bool(TWITTER_CLIENT_ID)},
        "discord": {"configured": bool(DISCORD_CLIENT_ID)},
        "frontend_url": FRONTEND_URL
    }

# Add a simple test endpoint to verify the router works
@router.get("/test")
async def test_oauth_router():
    """Test endpoint to verify OAuth router is working."""
    return {
        "message": "OAuth router is working",
        "endpoints": [
            "/auth/providers",
            "/auth/status", 
            "/auth/google/login",
            "/auth/twitter/login",
            "/auth/discord/login"
        ]
    }