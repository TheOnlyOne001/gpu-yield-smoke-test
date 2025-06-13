#!/usr/bin/env python3
"""
OAuth Quick Fix Script
Attempts to resolve common OAuth authentication issues automatically
"""

import os
import asyncio
import subprocess
import sys
from pathlib import Path
import httpx

class OAuthQuickFix:
    def __init__(self):
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    def check_redis(self):
        """Check if Redis is running and attempt to start if needed."""
        print("🔄 Checking Redis connection...")
        try:
            import redis
            r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
            r.ping()
            print("   ✅ Redis is running")
            return True
        except ImportError:
            print("   ❌ Redis package not installed")
            self.install_package('redis')
            return self.check_redis()
        except Exception as e:
            print(f"   ❌ Redis connection failed: {e}")
            print("   🔄 Attempting to start Redis...")
            return self.start_redis()
    
    def start_redis(self):
        """Attempt to start Redis server."""
        try:
            # Try different Redis start commands
            commands = [
                ['redis-server', '--daemonize', 'yes'],
                ['brew', 'services', 'start', 'redis'],  # macOS
                ['sudo', 'service', 'redis-server', 'start'],  # Ubuntu/Debian
                ['sudo', 'systemctl', 'start', 'redis'],  # CentOS/RHEL
            ]
            
            for cmd in commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"   ✅ Started Redis with: {' '.join(cmd)}")
                        # Wait a moment for Redis to start
                        import time
                        time.sleep(2)
                        return self.test_redis_connection()
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            print("   ❌ Could not start Redis automatically")
            print("   💡 Please start Redis manually:")
            print("      - macOS: brew services start redis")
            print("      - Ubuntu: sudo service redis-server start")
            print("      - Manual: redis-server")
            return False
            
        except Exception as e:
            print(f"   ❌ Error starting Redis: {e}")
            return False
    
    def test_redis_connection(self):
        """Test Redis connection after starting."""
        try:
            import redis
            r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
            r.ping()
            return True
        except:
            return False
    
    def install_package(self, package):
        """Install missing Python package."""
        print(f"   🔄 Installing {package}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"   ✅ Installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to install {package}: {e}")
    
    def check_dependencies(self):
        """Check and install missing dependencies."""
        print("🔄 Checking Python dependencies...")
        required_packages = {
            'httpx': 'httpx',
            'redis': 'redis',
            'authlib': 'authlib',
            'itsdangerous': 'itsdangerous',
            'multipart': 'python-multipart'
        }
        
        missing = []
        for import_name, package_name in required_packages.items():
            try:
                __import__(import_name)
                print(f"   ✅ {package_name}")
            except ImportError:
                print(f"   ❌ {package_name} missing")
                missing.append(package_name)
        
        if missing:
            print(f"   🔄 Installing missing packages: {', '.join(missing)}")
            for package in missing:
                self.install_package(package)
    
    def check_env_file(self):
        """Check and create .env file if missing."""
        print("🔄 Checking environment configuration...")
        env_path = Path('.env')
        
        if not env_path.exists():
            print("   ❌ .env file not found")
            self.create_env_template()
            return False
        
        # Check for OAuth variables
        with open('.env', 'r') as f:
            content = f.read()
        
        oauth_vars = [
            'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET',
            'TWITTER_CLIENT_ID', 'TWITTER_CLIENT_SECRET', 
            'DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET'
        ]
        
        configured_count = 0
        for var in oauth_vars:
            if f"{var}=" in content and not f"{var}=your-" in content:
                configured_count += 1
        
        print(f"   ✅ .env file exists")
        print(f"   📊 {configured_count}/{len(oauth_vars)} OAuth variables configured")
        
        if configured_count == 0:
            print("   ⚠️  No OAuth providers configured")
            print("   💡 Add your OAuth credentials to .env file")
            return False
        
        return True
    
    def create_env_template(self):
        """Create .env template file."""
        template = """# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/gpu_yield
REDIS_URL=redis://localhost:6379

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Configuration
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development

# Google OAuth - Get from https://console.cloud.google.com/
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Twitter OAuth - Get from https://developer.twitter.com/
TWITTER_CLIENT_ID=your-twitter-client-id
TWITTER_CLIENT_SECRET=your-twitter-client-secret

# Discord OAuth - Get from https://discord.com/developers/applications
DISCORD_CLIENT_ID=your-discord-client-id
DISCORD_CLIENT_SECRET=your-discord-client-secret
"""
        with open('.env', 'w') as f:
            f.write(template)
        print("   ✅ Created .env template")
        print("   💡 Please fill in your OAuth credentials and restart")
    
    async def test_backend_endpoints(self):
        """Test backend OAuth endpoints."""
        print("🔄 Testing backend endpoints...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test main OAuth endpoints
                endpoints = [
                    ('/auth/status', 'OAuth Status'),
                    ('/auth/providers', 'OAuth Providers'),
                    ('/auth/test', 'OAuth Router Test')
                ]
                
                for endpoint, name in endpoints:
                    try:
                        response = await client.get(f"{self.backend_url}{endpoint}")
                        if response.status_code == 200:
                            print(f"   ✅ {name} endpoint working")
                        else:
                            print(f"   ❌ {name} endpoint returned {response.status_code}")
                    except Exception as e:
                        print(f"   ❌ {name} endpoint failed: {e}")
                
                return True
                        
        except Exception as e:
            print(f"   ❌ Backend connection failed: {e}")
            print("   💡 Make sure your backend server is running:")
            print("      uvicorn main:app --reload --port 8000")
            return False
    
    def restart_services_guide(self):
        """Provide guidance on restarting services."""
        print("\n🔄 Service Restart Guide:")
        print("   1. Stop your FastAPI server (Ctrl+C)")
        print("   2. Restart with: uvicorn main:app --reload --port 8000")
        print("   3. Check Redis is running: redis-cli ping")
        print("   4. Test OAuth endpoints after restart")
    
    async def run_fix(self):
        """Run all fixes in sequence."""
        print("🚀 OAuth Quick Fix Starting...\n")
        
        # Step 1: Check dependencies
        self.check_dependencies()
        print()
        
        # Step 2: Check Redis
        redis_ok = self.check_redis()
        print()
        
        # Step 3: Check environment
        env_ok = self.check_env_file()
        print()
        
        # Step 4: Test backend
        backend_ok = await self.test_backend_endpoints()
        print()
        
        # Summary
        print("📋 Fix Summary:")
        issues = []
        if not redis_ok:
            issues.append("Redis connection")
        if not env_ok:
            issues.append("OAuth configuration")
        if not backend_ok:
            issues.append("Backend endpoints")
        
        if issues:
            print(f"   ❌ Issues found: {', '.join(issues)}")
            print("   🔧 Please address the issues above and restart your services")
            self.restart_services_guide()
        else:
            print("   ✅ All systems appear to be working!")
            print("   🎉 Try your social login again")
        
        return len(issues) == 0

if __name__ == "__main__":
    fix = OAuthQuickFix()
    success = asyncio.run(fix.run_fix())
    sys.exit(0 if success else 1)