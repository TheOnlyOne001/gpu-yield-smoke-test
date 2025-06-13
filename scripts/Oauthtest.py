#!/usr/bin/env python3
"""
OAuth Authentication Testing Script for GPU Yield
"""
import os
import sys
import json
import asyncio
import logging
import httpx
import redis
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add the parent directory to the path so we can import from the API
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OAuthTester:
    def __init__(self):
        self.backend_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        self.database_url = os.getenv('DATABASE_URL')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        # Test credentials
        self.test_user = {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'username': 'testuser'
        }
        
        self.test_results = {
            'api_health': False,
            'database': False,
            'redis': False,
            'auth_endpoints': False,
            'oauth_providers': False,
            'jwt_tokens': False,
            'user_operations': False
        }

    async def test_api_health(self) -> bool:
        """Test if the API server is running and responsive."""
        logger.info("🌐 Testing API health...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.backend_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"  ✅ API health check successful: {data.get('status', 'ok')}")
                    return True
                else:
                    logger.error(f"  ❌ API health check failed with status {response.status_code}")
                    return False
                    
        except httpx.ConnectError as e:
            logger.error(f"  ❌ Cannot connect to API server at {self.backend_url}")
            logger.info(f"  💡 Make sure the API server is running: uvicorn main:app --reload")
            return False
        except Exception as e:
            logger.error(f"  ❌ API health check failed: {e}")
            return False

    async def test_database_connection(self) -> bool:
        """Test database connection and OAuth table structure."""
        logger.info("🗄️  Testing database connection...")
        
        if not self.database_url:
            logger.error("  ❌ DATABASE_URL not set in environment variables")
            logger.info("  💡 Add DATABASE_URL to your .env file")
            return False
        
        try:
            # Handle postgres:// URLs (convert to postgresql://)
            database_url = self.database_url
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            conn = await asyncpg.connect(database_url)
            
            # Check signups table structure (not users)
            columns = await conn.fetch("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'signups'
                ORDER BY ordinal_position
            """)
            
            if not columns:
                logger.error("  ❌ 'signups' table not found")
                logger.info("  💡 Run database migrations first")
                await conn.close()
                return False
            
            required_oauth_columns = [
                'auth_provider', 'provider_id', 'avatar_url', 
                'full_name', 'is_verified', 'last_login'
            ]
            
            existing_columns = [row['column_name'] for row in columns]
            missing_columns = [col for col in required_oauth_columns if col not in existing_columns]
            
            if missing_columns:
                logger.error(f"  ❌ Missing OAuth columns: {', '.join(missing_columns)}")
                logger.info("  💡 Run the OAuth migration: 002_add_oauth_support.sql")
                await conn.close()
                return False
            
            logger.info("  ✅ Database connection successful")
            logger.info("  ✅ OAuth columns present in signups table")
            
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Database test failed: {e}")
            return False

    async def test_redis_connection(self) -> bool:
        """Test Redis connection for session management."""
        logger.info("🔴 Testing Redis connection...")
        
        try:
            r = redis.from_url(self.redis_url)
            r.ping()
            
            # Test state storage (OAuth state management)
            test_state = "test_oauth_state_123"
            r.setex(f"oauth_state:{test_state}", 60, "google")
            
            stored_provider = r.get(f"oauth_state:{test_state}")
            if stored_provider and stored_provider.decode() == "google":
                logger.info("  ✅ Redis connection and OAuth state storage working")
                r.delete(f"oauth_state:{test_state}")
                return True
            else:
                logger.error("  ❌ Redis OAuth state storage test failed")
                return False
                
        except Exception as e:
            logger.warning(f"  ⚠️  Redis test failed: {e}")
            logger.info("  💡 Redis is optional but recommended for OAuth state management")
            return False

    async def test_auth_endpoints(self) -> bool:
        """Test authentication endpoints."""
        logger.info("🔐 Testing authentication endpoints...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test health endpoint first
                try:
                    response = await client.get(f"{self.backend_url}/health")
                    if response.status_code != 200:
                        logger.error("  ❌ API server not responding")
                        return False
                except httpx.ConnectError:
                    logger.error("  ❌ Cannot connect to API server")
                    logger.info("  💡 Start the API server: uvicorn main:app --reload")
                    return False
                
                # Test OAuth providers endpoint
                response = await client.get(f"{self.backend_url}/auth/providers")
                
                if response.status_code == 200:
                    providers = response.json()
                    logger.info(f"  ✅ OAuth providers endpoint working")
                    logger.info(f"    Available providers: {len(providers.get('providers', []))}")
                else:
                    logger.error(f"  ❌ OAuth providers endpoint failed: {response.status_code}")
                    return False
                
                # Test OAuth status endpoint
                response = await client.get(f"{self.backend_url}/auth/status")
                
                if response.status_code == 200:
                    status = response.json()
                    logger.info(f"  ✅ OAuth status endpoint working")
                    for provider, config in status.items():
                        if provider != 'frontend_url':
                            configured = config.get('configured', False)
                            status_icon = "✅" if configured else "⚠️"
                            logger.info(f"    {status_icon} {provider}: {'configured' if configured else 'not configured'}")
                else:
                    logger.warning(f"  ⚠️  OAuth status endpoint not available")
                
                return True
                
        except Exception as e:
            logger.error(f"  ❌ Auth endpoints test failed: {e}")
            return False

    async def test_oauth_providers(self) -> bool:
        """Test OAuth provider configurations."""
        logger.info("🔗 Testing OAuth provider configurations...")
        
        providers = [
            ('GOOGLE', ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']),
            ('TWITTER', ['TWITTER_CLIENT_ID', 'TWITTER_CLIENT_SECRET']),
            ('DISCORD', ['DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET'])
        ]
        
        configured_providers = []
        
        for provider_name, env_vars in providers:
            if all(os.getenv(var) for var in env_vars):
                configured_providers.append(provider_name.lower())
                logger.info(f"  ✅ {provider_name} OAuth configured")
                
                # Test OAuth login URL
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(f"{self.backend_url}/auth/{provider_name.lower()}/login", follow_redirects=False)
                        if response.status_code in [302, 307]:  # Redirect to OAuth provider
                            logger.info(f"    ✅ {provider_name} OAuth redirect working")
                        else:
                            logger.warning(f"    ⚠️  {provider_name} OAuth redirect returned {response.status_code}")
                            
                except Exception as e:
                    logger.warning(f"    ⚠️  {provider_name} OAuth test failed: {e}")
            else:
                missing_vars = [var for var in env_vars if not os.getenv(var)]
                logger.warning(f"  ⚠️  {provider_name} OAuth not configured (missing: {', '.join(missing_vars)})")
        
        if configured_providers:
            logger.info(f"  ✅ {len(configured_providers)} OAuth providers configured: {', '.join(configured_providers)}")
            return True
        else:
            logger.warning("  ⚠️  No OAuth providers configured")
            logger.info("  💡 Add OAuth credentials to your .env file")
            return False

    async def test_jwt_tokens(self) -> bool:
        """Test JWT token generation and validation."""
        logger.info("🎫 Testing JWT token operations...")
        
        try:
            # Try to import security functions
            try:
                from security import create_access_token
                from datetime import timedelta
                
                # Test token creation
                test_data = {"sub": "test@example.com", "provider": "email"}
                token = create_access_token(
                    data=test_data,
                    expires_delta=timedelta(minutes=30)
                )
                
                if token and isinstance(token, str) and len(token) > 50:
                    logger.info("  ✅ JWT token creation working")
                    logger.info(f"    Token length: {len(token)} characters")
                    return True
                else:
                    logger.error("  ❌ JWT token creation failed - invalid token")
                    return False
                    
            except ImportError as e:
                logger.error(f"  ❌ Cannot import security module: {e}")
                logger.info("  💡 Make sure security.py exists in the api directory")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ JWT token test failed: {e}")
            return False

    async def test_user_operations(self) -> bool:
        """Test user CRUD operations with OAuth support."""
        logger.info("👤 Testing user operations...")
        
        if not self.database_url:
            logger.error("  ❌ DATABASE_URL not set")
            return False
        
        try:
            # Import required modules
            try:
                from models import AuthProvider
            except ImportError:
                logger.error("  ❌ Cannot import models module")
                return False
            
            # Handle postgres:// URLs
            database_url = self.database_url
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            conn = await asyncpg.connect(database_url)
            
            # Test basic user query
            try:
                result = await conn.fetch("SELECT COUNT(*) as count FROM signups LIMIT 1")
                user_count = result[0]['count']
                logger.info(f"  ✅ Database query successful - {user_count} users in database")
                
                # Test OAuth-specific columns
                oauth_columns_query = """
                SELECT auth_provider, COUNT(*) as count 
                FROM signups 
                GROUP BY auth_provider
                """
                oauth_result = await conn.fetch(oauth_columns_query)
                
                if oauth_result:
                    logger.info("  ✅ OAuth columns accessible:")
                    for row in oauth_result:
                        logger.info(f"    - {row['auth_provider']}: {row['count']} users")
                else:
                    logger.info("  ✅ OAuth columns accessible (no users yet)")
                
                await conn.close()
                return True
                
            except Exception as e:
                logger.error(f"  ❌ Database operations failed: {e}")
                await conn.close()
                return False
                
        except Exception as e:
            logger.error(f"  ❌ User operations test failed: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all OAuth tests and return results."""
        logger.info("🧪 Starting OAuth Authentication Tests\n")
        
        # Run tests in order
        self.test_results['api_health'] = await self.test_api_health()
        self.test_results['database'] = await self.test_database_connection()
        self.test_results['redis'] = await self.test_redis_connection()
        self.test_results['auth_endpoints'] = await self.test_auth_endpoints()
        self.test_results['oauth_providers'] = await self.test_oauth_providers()
        self.test_results['jwt_tokens'] = await self.test_jwt_tokens()
        self.test_results['user_operations'] = await self.test_user_operations()
        
        # Print summary
        logger.info("\n📊 Test Results Summary:")
        logger.info("=" * 50)
        
        passed_tests = 0
        total_tests = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name.replace('_', ' ').title():<20} {status}")
            if result:
                passed_tests += 1
        
        logger.info("=" * 50)
        logger.info(f"Total: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed! OAuth authentication is ready to use.")
        elif passed_tests >= total_tests * 0.7:
            logger.info("⚠️  Most tests passed. Check failed tests above.")
        else:
            logger.error("❌ Many tests failed. Please review your configuration.")
        
        return self.test_results

    def generate_test_report(self):
        """Generate a detailed test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"oauth_test_report_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "backend_url": self.backend_url,
            "frontend_url": self.frontend_url,
            "test_results": self.test_results,
            "environment": {
                "database_url_set": bool(self.database_url),
                "redis_url_set": bool(self.redis_url),
                "oauth_env_vars": {
                    "google": bool(os.getenv('GOOGLE_CLIENT_ID')),
                    "twitter": bool(os.getenv('TWITTER_CLIENT_ID')),
                    "discord": bool(os.getenv('DISCORD_CLIENT_ID'))
                }
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n📄 Test report saved to: {report_file}")

async def main():
    """Main test runner."""
    tester = OAuthTester()
    
    try:
        results = await tester.run_all_tests()
        tester.generate_test_report()
        
        # Exit with appropriate code
        passed_tests = sum(results.values())
        total_tests = len(results)
        
        if passed_tests == total_tests:
            exit(0)  # All tests passed
        elif passed_tests >= total_tests * 0.7:
            exit(1)  # Most tests passed, but some issues
        else:
            exit(2)  # Many tests failed
            
    except KeyboardInterrupt:
        logger.info("\n❌ Testing interrupted by user")
        exit(3)
    except Exception as e:
        logger.error(f"❌ Testing failed: {e}")
        exit(4)

if __name__ == "__main__":
    asyncio.run(main())