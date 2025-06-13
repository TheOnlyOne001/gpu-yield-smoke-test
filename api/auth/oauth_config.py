import os
from typing import Dict, Any
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# Environment configuration
config = Config('.env')

# OAuth client configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID") 
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

# Note: WhatsApp authentication removed - using Google, Twitter, Discord only

# Base URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Initialize OAuth
oauth = OAuth()

# Google OAuth
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'redirect_uri': f'{BACKEND_URL}/auth/google/callback'
    }
)

# Twitter OAuth 2.0
oauth.register(
    name='twitter',
    client_id=TWITTER_CLIENT_ID,
    client_secret=TWITTER_CLIENT_SECRET,
    access_token_url='https://api.twitter.com/2/oauth2/token',
    authorize_url='https://twitter.com/i/oauth2/authorize',
    api_base_url='https://api.twitter.com/2/',
    client_kwargs={
        'scope': 'users.read tweet.read',
        'response_type': 'code',
        'redirect_uri': f'{BACKEND_URL}/auth/twitter/callback'
    }
)

# Discord OAuth
oauth.register(
    name='discord',
    client_id=DISCORD_CLIENT_ID,
    client_secret=DISCORD_CLIENT_SECRET,
    access_token_url='https://discord.com/api/oauth2/token',
    authorize_url='https://discord.com/api/oauth2/authorize',
    api_base_url='https://discord.com/api/',
    client_kwargs={
        'scope': 'identify email',
        'redirect_uri': f'{BACKEND_URL}/auth/discord/callback'
    }
)

# OAuth provider configurations
OAUTH_PROVIDERS = {
    'google': {
        'name': 'Google',
        'icon': 'google',
        'color': '#4285f4'
    },
    'twitter': {
        'name': 'Twitter', 
        'icon': 'twitter',
        'color': '#1da1f2'
    },
    'discord': {
        'name': 'Discord',
        'icon': 'discord', 
        'color': '#5865f2'
    }
}

def get_oauth_providers() -> Dict[str, Any]:
    """Return available OAuth providers with their configurations."""
    return OAUTH_PROVIDERS