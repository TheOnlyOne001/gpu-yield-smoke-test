#!/usr/bin/env python3
"""
User Database Verification Script
Check if the OAuth user exists in the database
"""

import os
import asyncio
import asyncpg

# Load environment variables
def load_env():
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

async def check_user_in_database():
    """Check if the OAuth user exists in the database."""
    
    print("🔍 User Database Verification")
    print("=" * 40)
    
    # Load environment
    load_env()
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    # Handle postgres:// URLs
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Your OAuth user email (from the logs)
    test_email = "shayanahmad78600@gmail.com"
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        # Check if user exists
        print(f"\n🔄 Checking user: {test_email}")
        
        user_query = """
        SELECT id, email, username, full_name, auth_provider, provider_id, 
               is_active, is_verified, created_at, last_login
        FROM signups 
        WHERE email = $1
        """
        
        user_record = await conn.fetchrow(user_query, test_email)
        
        if user_record:
            print("✅ User found in database:")
            print(f"   ID: {user_record['id']}")
            print(f"   Email: {user_record['email']}")
            print(f"   Username: {user_record['username']}")
            print(f"   Full Name: {user_record['full_name']}")
            print(f"   Auth Provider: {user_record['auth_provider']}")
            print(f"   Provider ID: {user_record['provider_id']}")
            print(f"   Is Active: {user_record['is_active']}")
            print(f"   Is Verified: {user_record['is_verified']}")
            print(f"   Created: {user_record['created_at']}")
            print(f"   Last Login: {user_record['last_login']}")
            
            # Check for issues
            issues = []
            if not user_record['is_active']:
                issues.append("User is not active")
            if not user_record['is_verified']:
                issues.append("User is not verified")
            if not user_record['email']:
                issues.append("User has no email")
            
            if issues:
                print("\n⚠️  Potential Issues:")
                for issue in issues:
                    print(f"   - {issue}")
            else:
                print("\n✅ User record looks good")
                
        else:
            print("❌ User NOT found in database")
            print("   This could be why JWT validation fails")
            
            # Check if any similar users exist
            similar_query = """
            SELECT email, auth_provider FROM signups 
            WHERE email ILIKE $1 OR email ILIKE $2
            """
            
            similar_users = await conn.fetch(
                similar_query, 
                f"%{test_email.split('@')[0]}%",
                f"%{test_email.split('@')[1]}%"
            )
            
            if similar_users:
                print("\n🔍 Similar users found:")
                for user in similar_users:
                    print(f"   - {user['email']} ({user['auth_provider']})")
        
        # Check total OAuth users
        oauth_query = """
        SELECT auth_provider, COUNT(*) as count
        FROM signups 
        WHERE auth_provider != 'email'
        GROUP BY auth_provider
        """
        
        oauth_stats = await conn.fetch(oauth_query)
        
        print(f"\n📊 OAuth Users in Database:")
        for stat in oauth_stats:
            print(f"   {stat['auth_provider']}: {stat['count']} users")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")

async def test_user_lookup_function():
    """Test the actual user lookup function used by JWT validation."""
    
    print("\n🧪 Testing User Lookup Function")
    print("=" * 40)
    
    try:
        # Try to import and use the actual function
        import sys
        sys.path.append('api')
        
        from crud import get_user_by_email
        from dependencies import db_dependency
        
        test_email = "shayanahmad78600@gmail.com"
        
        # Get database connection using the same method as the app
        async for conn in db_dependency():
            print(f"🔄 Testing get_user_by_email('{test_email}')")
            
            user_record = await get_user_by_email(conn, test_email)
            
            if user_record:
                print("✅ get_user_by_email() found user")
                print(f"   User ID: {user_record.get('id')}")
                print(f"   Email: {user_record.get('email')}")
                print(f"   Active: {user_record.get('is_active')}")
            else:
                print("❌ get_user_by_email() returned None")
                print("   This is why JWT validation fails!")
            break
            
    except Exception as e:
        print(f"⚠️  Could not test user lookup function: {e}")
        print("   This is normal if running outside the API directory")

if __name__ == "__main__":
    asyncio.run(check_user_in_database())
    asyncio.run(test_user_lookup_function())