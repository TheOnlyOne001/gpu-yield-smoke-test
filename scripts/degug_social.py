

import asyncio
import asyncpg
import os

async def fix_oauth_schema():
    # Your database URL from .env
    database_url = "postgresql://neondb_owner:npg_bkTu1WvLgNS3@ep-frosty-brook-a832ipn1-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"
    
    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        # Make hashed_password nullable
        await conn.execute("ALTER TABLE signups ALTER COLUMN hashed_password DROP NOT NULL;")
        print("✅ Made hashed_password nullable for OAuth users")
        
        # Verify the change
        result = await conn.fetchrow("""
            SELECT column_name, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'signups' AND column_name = 'hashed_password'
        """)
        
        if result and result['is_nullable'] == 'YES':
            print("✅ Schema fix successful - hashed_password is now nullable")
        else:
            print("❌ Schema fix may have failed")
            
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(fix_oauth_schema())

# Run with: python fix_oauth_schema.py