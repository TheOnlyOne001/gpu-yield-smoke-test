# This file makes the routers directory a Python package
# It allows imports like: from routers.auth import router

"""
GPU Yield API Routers Package

This package contains all the API route handlers:
- auth: Authentication and user management
- oauth: OAuth2 integration (Google, Twitter, Discord)
- admin_oauth: Admin OAuth management
- account_linking: Link multiple OAuth accounts
- password_reset: Password reset functionality
"""

__all__ = [
    'auth',
    'oauth',
    'admin_oauth',
    'account_linking',
    'password_reset'
]