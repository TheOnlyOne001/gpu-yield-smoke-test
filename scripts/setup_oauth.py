#!/usr/bin/env python3
"""
OAuth Authentication Setup Script for GPU Yield

This script helps set up the OAuth authentication system by:
1. Installing required dependencies
2. Running database migrations
3. Validating environment variables
4. Testing OAuth provider configurations
5. Creating initial admin user (optional)

Run with: python setup_oauth.py
"""

import os
import sys
import subprocess
import asyncio
import asyncpg
import redis
from typing import Dict, List, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OAuthSetup:
    def __init__(self):
        self.env_vars = self.load_env_vars()
        self.required_packages = [
            'authlib==1.3.0',
            'httpx==0.25.0',
            'python-multipart==0.0.6',
            'itsdangerous==2.1.2',
            'requests-oauthlib==1.3.1'
        ]
        
    def load_env_vars(self) -> Dict[str, Optional[str]]:
        """Load environment variables from .env file or environment."""
        env_vars = {}
        
        # Try to load from .env file
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
        
        # Override with actual environment variables
        for key in [
            'DATABASE_URL', 'REDIS_URL', 'JWT_SECRET_KEY', 'SESSION_SECRET',
            'FRONTEND_URL', 'BACKEND_URL',
            'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET',
            'TWITTER_CLIENT_ID', 'TWITTER_CLIENT_SECRET',
            'DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET'
        ]:
            env_vars[key] = os.getenv(key, env_vars.get(key))
            
        return env_vars

    def check_dependencies(self) -> bool:
        """Check if required Python packages are installed."""
        logger.info("📦 Checking Python dependencies...")
        
        missing_packages = []
        
        for package in self.required_packages:
            package_name = package.split('==')[0]
            try:
                __import__(package_name.replace('-', '_'))
                logger.info(f"  ✅ {package_name} is installed")
            except ImportError:
                missing_packages.append(package)
                logger.warning(f"  ❌ {package_name} is missing")
        
        if missing_packages:
            logger.info("Installing missing packages...")
            for package in missing_packages:
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                    logger.info(f"  ✅ Installed {package}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"  ❌ Failed to install {package}: {e}")
                    return False
        
        return True

    def validate_environment(self) -> Dict[str, List[str]]:
        """Validate environment variables and return status."""
        logger.info("🔧 Validating environment configuration...")
        
        status = {
            'required': [],
            'missing': [],
            'oauth_providers': []
        }
        
        # Required variables
        required_vars = [
            'DATABASE_URL',
            'JWT_SECRET_KEY'
        ]
        
        for var in required_vars:
            if self.env_vars.get(var):
                status['required'].append(var)
                logger.info(f"  ✅ {var} is set")
            else:
                status['missing'].append(var)
                logger.warning(f"  ❌ {var} is missing")
        
        # OAuth providers (optional but recommended)
        oauth_configs = [
            ('Google', ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']),
            ('Twitter', ['TWITTER_CLIENT_ID', 'TWITTER_CLIENT_SECRET']),
            ('Discord', ['DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET'])
        ]
        
        for provider_name, vars_needed in oauth_configs:
            if all(self.env_vars.get(var) for var in vars_needed):
                status['oauth_providers'].append(provider_name)
                logger.info(f"  ✅ {provider_name} OAuth is configured")
            else:
                logger.warning(f"  ⚠️  {provider_name} OAuth is not configured")
        
        return status

    async def test_database_connection(self) -> bool:
        """Test database connection and check if users table exists."""
        logger.info("🗄️  Testing database connection...")
        
        database_url = self.env_vars.get('DATABASE_URL')
        if not database_url:
            logger.error("  ❌ DATABASE_URL not set")
            return False
        
        try:
            # Handle postgres:// URLs
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
                
            conn = await asyncpg.connect(database_url)
            
            # Check if signups table exists
            result = await conn.fetch("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'signups'
            """)
            
            if result:
                logger.info("  ✅ Database connection successful, signups table exists")
                
                # Check if OAuth columns exist
                oauth_columns = await conn.fetch("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'signups' AND column_name IN 
                    ('auth_provider', 'provider_id', 'avatar_url', 'full_name', 'is_verified')
                """)
                
                if len(oauth_columns) >= 4:
                    logger.info("  ✅ OAuth columns exist in signups table")
                else:
                    logger.warning("  ⚠️  OAuth columns missing, migration needed")
                    
            else:
                logger.warning("  ⚠️  Signups table does not exist, migration needed")
            
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Database connection failed: {e}")
            return False

    def test_redis_connection(self) -> bool:
        """Test Redis connection."""
        logger.info("🔴 Testing Redis connection...")
        
        redis_url = self.env_vars.get('REDIS_URL', 'redis://localhost:6379')
        
        try:
            r = redis.from_url(redis_url)
            r.ping()
            logger.info("  ✅ Redis connection successful")
            return True
        except Exception as e:
            logger.warning(f"  ⚠️  Redis connection failed: {e}")
            logger.info("  💡 Redis is optional but recommended for session management")
            return False

    async def run_migrations(self) -> bool:
        """Run database migrations."""
        logger.info("🚀 Running database migrations...")
        
        database_url = self.env_vars.get('DATABASE_URL')
        if not database_url:
            logger.error("  ❌ DATABASE_URL not set")
            return False
        
        try:
            # Handle postgres:// URLs
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
                
            conn = await asyncpg.connect(database_url)
            
            # Create OAuth migration SQL
            migration_sql = """
            -- Add OAuth columns to signups table if they don't exist
            DO $$ 
            BEGIN
                -- Add auth_provider column
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name = 'signups' AND column_name = 'auth_provider') THEN
                    ALTER TABLE signups ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'email';
                END IF;
                
                -- Add provider_id column
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name = 'signups' AND column_name = 'provider_id') THEN
                    ALTER TABLE signups ADD COLUMN provider_id VARCHAR(255);
                END IF;
                
                -- Add avatar_url column
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name = 'signups' AND column_name = 'avatar_url') THEN
                    ALTER TABLE signups ADD COLUMN avatar_url TEXT;
                END IF;
                
                -- Add full_name column
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name = 'signups' AND column_name = 'full_name') THEN
                    ALTER TABLE signups ADD COLUMN full_name VARCHAR(255);
                END IF;
                
                -- Add is_verified column if it doesn't exist
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name = 'signups' AND column_name = 'is_verified') THEN
                    ALTER TABLE signups ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
                END IF;
                
                -- Add last_login column if it doesn't exist
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name = 'signups' AND column_name = 'last_login') THEN
                    ALTER TABLE signups ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;
                END IF;
            END $$;
            
            -- Create indexes for OAuth
            CREATE INDEX IF NOT EXISTS idx_signups_auth_provider ON signups(auth_provider);
            CREATE INDEX IF NOT EXISTS idx_signups_provider_id ON signups(provider_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_signups_oauth 
                ON signups(auth_provider, provider_id) 
                WHERE auth_provider != 'email' AND provider_id IS NOT NULL;
            """
            
            await conn.execute(migration_sql)
            await conn.close()
            
            logger.info("  ✅ Database migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Migration failed: {e}")
            return False

    async def create_admin_user(self) -> bool:
        """Create initial admin user (optional)."""
        response = input("\n🤖 Would you like to create an admin user? (y/N): ")
        
        if response.lower() != 'y':
            return True
        
        email = input("Admin email: ")
        password = input("Admin password: ")
        
        if not email or not password:
            logger.warning("Email and password are required")
            return False
        
        try:
            # Add the parent directory to path to import modules
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            from security import get_password_hash
            from crud import create_user, AuthProvider
            
            database_url = self.env_vars.get('DATABASE_URL')
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
                
            conn = await asyncpg.connect(database_url)
            
            hashed_password = get_password_hash(password)
            
            # Create admin user
            admin_user = await create_user(
                conn=conn,
                email=email,
                username="admin",
                hashed_password=hashed_password,
                auth_provider=AuthProvider.EMAIL
            )
            
            await conn.close()
            
            logger.info(f"  ✅ Admin user created: {email}")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Failed to create admin user: {e}")
            return False

    def generate_env_template(self):
        """Generate .env template file."""
        logger.info("📝 Generating .env template...")
        
        template = """# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/gpu_yield
REDIS_URL=redis://localhost:6379

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Configuration
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
ENVIRONMENT=development

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Twitter OAuth 2.0
TWITTER_CLIENT_ID=your-twitter-client-id
TWITTER_CLIENT_SECRET=your-twitter-client-secret

# Discord OAuth
DISCORD_CLIENT_ID=your-discord-client-id
DISCORD_CLIENT_SECRET=your-discord-client-secret

# Email Configuration (SendGrid)
SENDGRID_API_KEY=your-sendgrid-api-key
FROM_EMAIL=your-from-email@domain.com

# hCaptcha
HCAPTCHA_SECRET_KEY=your-hcaptcha-secret-key
HCAPTCHA_SITE_KEY=your-hcaptcha-site-key
"""
        
        with open('.env.template', 'w') as f:
            f.write(template)
        
        logger.info("  ✅ .env template created")
        logger.info("  💡 Copy .env.template to .env and fill in your credentials")

    async def run_setup(self):
        """Run the complete OAuth setup process."""
        logger.info("🚀 Starting OAuth Authentication Setup for GPU Yield\n")
        
        # Step 1: Check dependencies
        if not self.check_dependencies():
            logger.error("❌ Dependency check failed")
            return False
        
        # Step 2: Validate environment
        env_status = self.validate_environment()
        
        if env_status['missing']:
            logger.error(f"❌ Missing required environment variables: {', '.join(env_status['missing'])}")
            self.generate_env_template()
            return False
        
        # Step 3: Test connections
        db_ok = await self.test_database_connection()
        redis_ok = self.test_redis_connection()
        
        if not db_ok:
            logger.error("❌ Database connection failed")
            return False
        
        # Step 4: Run migrations
        if not await self.run_migrations():
            logger.error("❌ Database migration failed")
            return False
        
        # Step 5: Create admin user (optional)
        await self.create_admin_user()
        
        # Success summary
        logger.info("\n🎉 OAuth Authentication Setup Complete!")
        logger.info(f"✅ Database: Connected and migrated")
        logger.info(f"{'✅' if redis_ok else '⚠️'} Redis: {'Connected' if redis_ok else 'Not available (optional)'}")
        logger.info(f"✅ OAuth Providers: {len(env_status['oauth_providers'])} configured")
        
        if env_status['oauth_providers']:
            for provider in env_status['oauth_providers']:
                logger.info(f"   - {provider}")
        
        logger.info("\n🚀 Next Steps:")
        logger.info("1. Start your FastAPI server: uvicorn main:app --reload")
        logger.info("2. Start your Next.js frontend: npm run dev")
        logger.info("3. Test OAuth login at: http://localhost:3000/login")
        logger.info("4. Check API docs at: http://localhost:8000/docs")
        
        return True

def main():
    """Main entry point."""
    setup = OAuthSetup()
    
    try:
        asyncio.run(setup.run_setup())
    except KeyboardInterrupt:
        logger.info("\n❌ Setup interrupted by user")
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()