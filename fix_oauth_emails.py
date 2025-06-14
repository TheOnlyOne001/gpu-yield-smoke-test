import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def fix_oauth_emails():
    load_dotenv()
    
    try:
        # Connect to database using DATABASE_URL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("ERROR: DATABASE_URL not found in environment variables")
            return
            
        print(f"Connecting to database...")
        conn = await asyncpg.connect(database_url)
        
        print("Connected to database...")
        
        # Check current records with @oauth.local
        records_before = await conn.fetch('''
            SELECT id, email, auth_provider, provider_id 
            FROM signups 
            WHERE email LIKE '%@oauth.local'
        ''')
        
        print(f"Found {len(records_before)} records with @oauth.local domain:")
        for record in records_before:
            print(f"  ID: {record[0]}, Email: {record[1]}, Provider: {record[2]}")
        
        # Update emails that end with @oauth.local to @noemail.example
        result = await conn.execute('''
            UPDATE signups 
            SET email = REPLACE(email, '@oauth.local', '@noemail.example')
            WHERE email LIKE '%@oauth.local'
        ''')
        
        print(f"\nUpdate result: {result}")
        
        # Check updated records
        records_after = await conn.fetch('''
            SELECT id, email, auth_provider, provider_id 
            FROM signups 
            WHERE email LIKE '%@noemail.example'
        ''')
        
        print(f"\nRecords with @noemail.example domain ({len(records_after)}):")
        for record in records_after:
            print(f"  ID: {record[0]}, Email: {record[1]}, Provider: {record[2]}")
        
        # Also check for any remaining @oauth.local records
        remaining_bad = await conn.fetch('''
            SELECT id, email, auth_provider, provider_id 
            FROM signups 
            WHERE email LIKE '%@oauth.local'
        ''')
        
        if remaining_bad:
            print(f"\nWARNING: Still found {len(remaining_bad)} records with @oauth.local:")
            for record in remaining_bad:
                print(f"  ID: {record[0]}, Email: {record[1]}, Provider: {record[2]}")
        else:
            print(f"\nSUCCESS: No more @oauth.local records found!")
        
        await conn.close()
        print("\nDatabase check completed!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(fix_oauth_emails())
