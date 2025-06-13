#!/usr/bin/env python3
"""
Fixed OAuth Debug Script - Properly loads .env file
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """Manually load .env file to ensure variables are available."""
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ .env file not found in current directory")
        return False
    
    with open('.env', 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                try:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                except ValueError:
                    print(f"⚠️  Line {line_num}: Could not parse '{line}'")
    
    print("✅ .env file loaded successfully")
    return True

def check_oauth_env_vars():
    """Check OAuth environment variables after loading .env."""
    print("🔍 OAuth Environment Variables Check")
    print("=" * 40)
    
    oauth_vars = {
        'Google': ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'],
        'Twitter': ['TWITTER_CLIENT_ID', 'TWITTER_CLIENT_SECRET'],
        'Discord': ['DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET']
    }
    
    configured_providers = []
    
    for provider, vars_list in oauth_vars.items():
        client_id = os.getenv(vars_list[0])
        client_secret = os.getenv(vars_list[1])
        
        if client_id and client_secret:
            configured_providers.append(provider)
            print(f"   ✅ {provider}: Configured")
            print(f"      Client ID: {client_id[:20]}...")
            print(f"      Client Secret: {client_secret[:10]}...")
        else:
            print(f"   ❌ {provider}: Missing credentials")
            if not client_id:
                print(f"      - Missing {vars_list[0]}")
            if not client_secret:
                print(f"      - Missing {vars_list[1]}")
    
    return configured_providers

def check_other_important_vars():
    """Check other important environment variables."""
    print("\n🔍 Other Important Variables")
    print("=" * 35)
    
    important_vars = [
        'DATABASE_URL',
        'REDIS_URL', 
        'JWT_SECRET_KEY',
        'FRONTEND_URL',
        'BACKEND_URL'
    ]
    
    for var in important_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {value[:30]}...")
        else:
            print(f"   ❌ {var}: Not set")

def test_backend_with_details():
    """Test backend endpoints with better error reporting."""
    print("\n🔍 Backend Endpoint Detailed Test")
    print("=" * 40)
    
    try:
        import requests
        
        # Test status endpoint
        try:
            response = requests.get("http://localhost:8000/auth/status", timeout=5)
            print(f"   Status Endpoint: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Status Data: {data}")
        except Exception as e:
            print(f"   ❌ Status endpoint failed: {e}")
        
        # Test individual OAuth endpoints
        providers = ['google', 'twitter', 'discord']
        for provider in providers:
            try:
                response = requests.get(
                    f"http://localhost:8000/auth/{provider}/login", 
                    timeout=5, 
                    allow_redirects=False
                )
                print(f"   {provider.title()} Login: {response.status_code}")
                
                if response.status_code == 500:
                    try:
                        error_data = response.json()
                        print(f"      Error: {error_data}")
                    except:
                        print(f"      Error Text: {response.text[:200]}...")
                        
            except Exception as e:
                print(f"   ❌ {provider.title()} endpoint failed: {e}")
                
    except ImportError:
        print("   ⚠️  requests library not available for testing")
        print("   💡 Install with: pip install requests")

def main():
    print("🔧 Fixed OAuth Debug Script")
    print("=" * 50)
    
    # Load .env file manually
    if not load_env_file():
        return
    
    # Check OAuth variables
    configured_providers = check_oauth_env_vars()
    
    # Check other important variables
    check_other_important_vars()
    
    # Test backend
    test_backend_with_details()
    
    # Summary
    print("\n📋 Summary:")
    if configured_providers:
        print(f"   ✅ {len(configured_providers)} OAuth providers configured: {', '.join(configured_providers)}")
        print("   🔧 If you're still getting 500 errors, check your FastAPI server logs")
    else:
        print("   ❌ No OAuth providers configured properly")
    
    print("\n💡 Next Steps:")
    print("   1. If OAuth vars show as configured, the issue is in your server code")
    print("   2. Check your FastAPI server console for Python tracebacks")
    print("   3. Look for 500 error details when you click social login buttons")

if __name__ == "__main__":
    main()