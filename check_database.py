#!/usr/bin/env python3
"""
Comprehensive database check for OAuth email issues.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_database():
    """Check all OAuth-related records in the database."""
    # Database connection
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not found in environment")
        return
    
    print("Connecting to database...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected to database successfully!")        # Check ALL user records
        print("\n=== ALL USER RECORDS ===")
        all_users = await conn.fetch("SELECT id, email, username, auth_provider, provider_id FROM signups ORDER BY id")
        
        for user in all_users:
            print(f"ID: {user['id']}, Email: {user['email']}, Username: {user['username']}, Provider: {user['auth_provider']}, Provider_ID: {user['provider_id']}")
        
        # Check specifically for @oauth.local records
        print("\n=== @oauth.local RECORDS ===")
        oauth_local_users = await conn.fetch("SELECT * FROM signups WHERE email LIKE '%@oauth.local'")
        print(f"Found {len(oauth_local_users)} records with @oauth.local")
        for user in oauth_local_users:
            print(f"  ID: {user['id']}, Email: {user['email']}")
        
        # Check for @noemail.example records
        print("\n=== @noemail.example RECORDS ===")
        noemail_users = await conn.fetch("SELECT * FROM signups WHERE email LIKE '%@noemail.example'")
        print(f"Found {len(noemail_users)} records with @noemail.example")
        for user in noemail_users:
            print(f"  ID: {user['id']}, Email: {user['email']}")
        
        # Check the specific user from the error
        print("\n=== SPECIFIC TWITTER USER CHECK ===")
        twitter_user = await conn.fetchrow(
            "SELECT * FROM signups WHERE auth_provider = 'twitter' AND provider_id = '1484052317418954754'"
        )
        if twitter_user:
            print(f"Found Twitter user: ID={twitter_user['id']}, Email={twitter_user['email']}")
        else:
            print("Twitter user with ID 1484052317418954754 not found")
        
        await conn.close()
        print("\nDatabase check completed!")
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    asyncio.run(check_database())
