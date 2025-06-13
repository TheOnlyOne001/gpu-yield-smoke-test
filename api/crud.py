import os
import asyncpg
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from enum import Enum

# Initialize logger
logger = logging.getLogger(__name__)

# Add AuthProvider enum
class AuthProvider(Enum):
    EMAIL = "email"
    GOOGLE = "google"
    TWITTER = "twitter"
    DISCORD = "discord"

# Add UserOAuth model class
class UserOAuth:
    def __init__(self, email: str, provider: AuthProvider, provider_id: str, 
                 username: Optional[str] = None, avatar_url: Optional[str] = None, 
                 full_name: Optional[str] = None):
        self.email = email
        self.provider = provider
        self.provider_id = provider_id
        self.username = username
        self.avatar_url = avatar_url
        self.full_name = full_name

# Global database pool
db_pool: Optional[asyncpg.Pool] = None

async def connect_to_db():
    """
    Initialize the global database connection pool.
    Reads DATABASE_URL from environment variables.
    """
    global db_pool
    
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # Handle both postgres:// and postgresql:// URLs
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # Create connection pool
        db_pool = await asyncpg.create_pool(
            database_url,
            min_size=5,
            max_size=20,
            command_timeout=60,
            server_settings={
                'jit': 'off'  # Disable JIT for better compatibility
            }
        )
        
        logger.info("Database connection pool created successfully")
        
        # Initialize database schema
        async with db_pool.acquire() as conn:
            await init_database_schema(conn)
        
    except Exception as e:
        logger.error(f"Failed to create database connection pool: {e}")
        raise

async def close_db_connection():
    """
    Gracefully close the database connection pool.
    """
    global db_pool
    
    if db_pool:
        try:
            await db_pool.close()
            db_pool = None
            logger.info("Database connection pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connection pool: {e}")

async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependency function that yields a database connection from the pool.
    
    Yields:
        asyncpg.Connection: Database connection from the pool
    """
    if not db_pool:
        raise RuntimeError("Database pool not initialized. Call connect_to_db() first.")
    
    async with db_pool.acquire() as connection:
        try:
            yield connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise

async def get_user_by_email(conn: asyncpg.Connection, email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a user by their email address from the signups table.
    
    Args:
        conn: AsyncPG connection object
        email: User's email address
        
    Returns:
        Dictionary containing user data if found, None otherwise
    """
    try:
        # Use parameterized query to prevent SQL injection
        query = """
            SELECT id, email, username, hashed_password, is_active, 
                   created_at, gpu_models_interested, min_profit_threshold
            FROM signups 
            WHERE email = $1
        """
        
        result = await conn.fetchrow(query, email.lower().strip())
        
        if result:
            # Convert asyncpg.Record to dictionary
            user_data = dict(result)
            logger.info(f"User found for email: {email}")
            return user_data
        else:
            logger.info(f"No user found for email: {email}")
            return None
            
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching user by email {email}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching user by email {email}: {e}")
        raise

async def create_user(
    conn: asyncpg.Connection, 
    email: str, 
    username: Optional[str], 
    hashed_password: str,
    gpu_models_interested: Optional[list] = None, 
    min_profit_threshold: float = 0.0
) -> Dict[str, Any]:
    """
    Creates a new user in the signups table.
    
    Args:
        conn: AsyncPG connection object
        email: User's email address
        username: Optional username
        hashed_password: Pre-hashed password string
        gpu_models_interested: List of GPU models user is interested in
        min_profit_threshold: Minimum profit threshold for alerts
        
    Returns:
        Dictionary containing the newly created user's data
    """
    try:
        # Use parameterized query to prevent SQL injection
        query = """
            INSERT INTO signups (email, username, hashed_password, is_active, 
                               created_at, gpu_models_interested, min_profit_threshold)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, email, username, hashed_password, is_active, 
                     created_at, gpu_models_interested, min_profit_threshold
        """
        
        # Prepare values
        current_time = datetime.now(timezone.utc)
        gpu_models = gpu_models_interested or []
        
        result = await conn.fetchrow(
            query,
            email.lower().strip(),
            username,
            hashed_password,
            True,  # is_active
            current_time,
            gpu_models,
            min_profit_threshold
        )
        
        if result:
            user_data = dict(result)
            logger.info(f"User created successfully with email: {email}")
            return user_data
        else:
            raise Exception("Failed to create user - no data returned")
            
    except asyncpg.UniqueViolationError as e:
        logger.error(f"Unique constraint violation while creating user {email}: {e}")
        raise ValueError(f"User with email {email} already exists")
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while creating user {email}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while creating user {email}: {e}")
        raise

async def update_user_by_email(
    conn: asyncpg.Connection, 
    email: str, 
    update_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Updates a user's information by email address.
    
    Args:
        conn: AsyncPG connection object
        email: User's email address
        update_data: Dictionary containing fields to update
        
    Returns:
        Dictionary containing updated user data if successful, None otherwise
    """
    try:
        if not update_data:
            raise ValueError("No update data provided")
        
        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        param_counter = 1
        
        allowed_fields = {
            'username', 'hashed_password', 'is_active', 
            'gpu_models_interested', 'min_profit_threshold'
        }
        
        for field, value in update_data.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ${param_counter}")
                values.append(value)
                param_counter += 1
        
        if not set_clauses:
            raise ValueError("No valid fields to update")
        
        # Add email parameter
        values.append(email.lower().strip())
        
        query = f"""
            UPDATE signups 
            SET {', '.join(set_clauses)}
            WHERE email = ${param_counter}
            RETURNING id, email, username, hashed_password, is_active, 
                     created_at, gpu_models_interested, min_profit_threshold
        """
        
        result = await conn.fetchrow(query, *values)
        
        if result:
            user_data = dict(result)
            logger.info(f"User updated successfully: {email}")
            return user_data
        else:
            logger.warning(f"No user found to update with email: {email}")
            return None
            
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while updating user {email}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while updating user {email}: {e}")
        raise

async def delete_user_by_email(conn: asyncpg.Connection, email: str) -> bool:
    """
    Deletes a user by their email address.
    
    Args:
        conn: AsyncPG connection object
        email: User's email address
        
    Returns:
        True if user was deleted, False if user not found
    """
    try:
        query = "DELETE FROM signups WHERE email = $1"
        result = await conn.execute(query, email.lower().strip())
        
        # Extract row count from result string (e.g., "DELETE 1")
        rows_affected = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
        
        if rows_affected > 0:
            logger.info(f"User deleted successfully: {email}")
            return True
        else:
            logger.warning(f"No user found to delete with email: {email}")
            return False
            
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while deleting user {email}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while deleting user {email}: {e}")
        raise

async def get_all_users(
    conn: asyncpg.Connection, 
    limit: int = 100, 
    offset: int = 0
) -> list[Dict[str, Any]]:
    """
    Retrieves all users with pagination.
    
    Args:
        conn: AsyncPG connection object
        limit: Maximum number of users to return
        offset: Number of users to skip
        
    Returns:
        List of dictionaries containing user data
    """
    try:
        query = """
            SELECT id, email, username, is_active, created_at, 
                   gpu_models_interested, min_profit_threshold
            FROM signups 
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """
        
        results = await conn.fetch(query, limit, offset)
        
        users = [dict(row) for row in results]
        logger.info(f"Retrieved {len(users)} users")
        return users
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching all users: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching all users: {e}")
        raise

async def get_user_count(conn: asyncpg.Connection) -> int:
    """
    Gets the total count of users in the database.
    
    Args:
        conn: AsyncPG connection object
        
    Returns:
        Total number of users
    """
    try:
        query = "SELECT COUNT(*) FROM signups"
        result = await conn.fetchval(query)
        
        count = result if result else 0
        logger.info(f"Total user count: {count}")
        return count
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while counting users: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while counting users: {e}")
        raise

async def get_user_by_id(conn: asyncpg.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves a user by their ID from the signups table.
    
    Args:
        conn: AsyncPG connection object
        user_id: User's ID
        
    Returns:
        Dictionary containing user data if found, None otherwise
    """
    try:
        query = """
            SELECT id, email, username, hashed_password, is_active, 
                   created_at, gpu_models_interested, min_profit_threshold
            FROM signups 
            WHERE id = $1
        """
        
        result = await conn.fetchrow(query, user_id)
        
        if result:
            user_data = dict(result)
            logger.info(f"User found for ID: {user_id}")
            return user_data
        else:
            logger.info(f"No user found for ID: {user_id}")
            return None
            
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching user by ID {user_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching user by ID {user_id}: {e}")
        raise

async def get_user_by_oauth(conn: asyncpg.Connection, provider: AuthProvider, provider_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by OAuth provider and provider ID.
    
    Args:
        conn: Database connection
        provider: OAuth provider (google, twitter, etc.)
        provider_id: Provider-specific user ID
        
    Returns:
        User record if found, None otherwise
    """
    try:
        query = """
        SELECT id, email, username, is_active, is_verified, auth_provider, 
               provider_id, avatar_url, full_name, created_at, last_login,
               gpu_models_interested, min_profit_threshold
        FROM signups 
        WHERE auth_provider = $1 AND provider_id = $2
        """
        
        result = await conn.fetchrow(query, provider.value, provider_id)
        
        if result:
            user = dict(result)
            # Convert arrays and handle JSON fields
            if user.get('gpu_models_interested'):
                user['gpu_models_interested'] = list(user['gpu_models_interested'])
            logger.info(f"OAuth user found: {provider.value}:{provider_id}")
            return user
        
        logger.info(f"No OAuth user found: {provider.value}:{provider_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting user by OAuth {provider.value}:{provider_id}: {e}")
        return None

async def create_oauth_user(conn: asyncpg.Connection, oauth_user: UserOAuth) -> Dict[str, Any]:
    """
    Create a new user from OAuth data.
    
    Args:
        conn: Database connection
        oauth_user: OAuth user data
        
    Returns:
        Created user record
    """
    try:
        # Generate username if not provided
        username = oauth_user.username
        if not username and oauth_user.email:
            username = oauth_user.email.split('@')[0]
        elif not username:
            username = f"{oauth_user.provider.value}_{oauth_user.provider_id}"
        
        # Ensure unique username
        username = await ensure_unique_username(conn, username)
        
        query = """
        INSERT INTO signups (
            email, username, is_active, is_verified, auth_provider, 
            provider_id, avatar_url, full_name, created_at, hashed_password
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
        ) RETURNING id, email, username, is_active, is_verified, auth_provider, 
                   provider_id, avatar_url, full_name, created_at, last_login,
                   gpu_models_interested, min_profit_threshold
        """
        
        result = await conn.fetchrow(
            query,
            oauth_user.email,
            username,
            True,  # is_active
            True,  # is_verified (OAuth users are pre-verified)
            oauth_user.provider.value,
            oauth_user.provider_id,
            oauth_user.avatar_url,
            oauth_user.full_name,
            datetime.now(timezone.utc),
            None  # No password for OAuth users
        )
        
        if result:
            user = dict(result)
            # Handle JSON fields
            if user.get('gpu_models_interested'):
                user['gpu_models_interested'] = list(user['gpu_models_interested'])
            
            logger.info(f"OAuth user created: {oauth_user.email} via {oauth_user.provider.value}")
            return user
        
        raise Exception("Failed to create OAuth user")
        
    except Exception as e:
        logger.error(f"Error creating OAuth user {oauth_user.email}: {e}")
        raise

async def link_oauth_to_existing_user(
    conn: asyncpg.Connection, 
    user_id: int, 
    provider: AuthProvider, 
    provider_id: str,
    avatar_url: Optional[str] = None,
    full_name: Optional[str] = None
) -> bool:
    """
    Link OAuth provider to an existing user account.
    
    Args:
        conn: Database connection
        user_id: Existing user ID
        provider: OAuth provider
        provider_id: Provider-specific user ID
        avatar_url: User's avatar URL from provider
        full_name: User's full name from provider
        
    Returns:
        True if successful, False otherwise
    """
    try:
        query = """
        UPDATE signups 
        SET auth_provider = $1, provider_id = $2, avatar_url = COALESCE($3, avatar_url), 
            full_name = COALESCE($4, full_name), is_verified = true
        WHERE id = $5
        """
        
        result = await conn.execute(
            query,
            provider.value,
            provider_id,
            avatar_url,
            full_name,
            user_id
        )
        
        logger.info(f"OAuth provider {provider.value} linked to user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error linking OAuth provider to user {user_id}: {e}")
        return False

async def update_user_last_login(conn: asyncpg.Connection, user_id: int) -> bool:
    """
    Update user's last login timestamp.
    
    Args:
        conn: Database connection
        user_id: User ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        query = "UPDATE signups SET last_login = $1 WHERE id = $2"
        await conn.execute(query, datetime.now(timezone.utc), user_id)
        return True
        
    except Exception as e:
        logger.error(f"Error updating last login for user {user_id}: {e}")
        return False

async def ensure_unique_username(conn: asyncpg.Connection, base_username: str) -> str:
    """
    Ensure username is unique by appending numbers if necessary.
    
    Args:
        conn: Database connection
        base_username: Base username to check
        
    Returns:
        Unique username
    """
    try:
        username = base_username
        counter = 1
        
        while await username_exists(conn, username):
            username = f"{base_username}{counter}"
            counter += 1
            
            # Safety check to prevent infinite loop
            if counter > 1000:
                username = f"{base_username}_{int(datetime.now(timezone.utc).timestamp())}"
                break
        
        return username
        
    except Exception as e:
        logger.error(f"Error ensuring unique username for {base_username}: {e}")
        return f"{base_username}_{int(datetime.now(timezone.utc).timestamp())}"

async def username_exists(conn: asyncpg.Connection, username: str) -> bool:
    """
    Check if username already exists.
    
    Args:
        conn: Database connection
        username: Username to check
        
    Returns:
        True if username exists, False otherwise
    """
    try:
        query = "SELECT 1 FROM signups WHERE username = $1"
        result = await conn.fetchval(query, username)
        return result is not None
        
    except Exception as e:
        logger.error(f"Error checking username existence for {username}: {e}")
        return True  # Assume exists to be safe

async def get_user_oauth_providers(conn: asyncpg.Connection, user_id: int) -> list[Dict[str, Any]]:
    """
    Get OAuth providers linked to a user.
    
    Args:
        conn: Database connection
        user_id: User ID
        
    Returns:
        List of linked OAuth providers
    """
    try:
        # Since you're using a single table for auth, return the primary provider
        query = """
        SELECT auth_provider, provider_id, created_at
        FROM signups 
        WHERE id = $1 AND is_active = TRUE
        """
        
        result = await conn.fetch(query, user_id)
        
        providers = []
        for row in result:
            provider = dict(row)
            if provider.get('created_at'):
                provider['created_at'] = provider['created_at'].isoformat()
            providers.append(provider)
        
        return providers
        
    except Exception as e:
        logger.error(f"Error getting OAuth providers for user {user_id}: {e}")
        return []

async def init_database_schema(conn: asyncpg.Connection):
    """
    Initializes the database schema if it doesn't exist.
    Updated to include OAuth fields.
    
    Args:
        conn: AsyncPG connection object
    """
    try:
        # Create signups table if it doesn't exist with OAuth support
        create_table_query = """
            CREATE TABLE IF NOT EXISTS signups (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100),
                hashed_password VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_login TIMESTAMP WITH TIME ZONE,
                gpu_models_interested TEXT[],
                min_profit_threshold DECIMAL(10, 2) DEFAULT 0.0,
                auth_provider VARCHAR(50) DEFAULT 'email',
                provider_id VARCHAR(255),
                avatar_url TEXT,
                full_name VARCHAR(255)
            );
            
            CREATE INDEX IF NOT EXISTS idx_signups_email ON signups(email);
            CREATE INDEX IF NOT EXISTS idx_signups_created_at ON signups(created_at);
            CREATE INDEX IF NOT EXISTS idx_signups_is_active ON signups(is_active);
            CREATE INDEX IF NOT EXISTS idx_signups_auth_provider ON signups(auth_provider);
            CREATE INDEX IF NOT EXISTS idx_signups_provider_id ON signups(provider_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_signups_oauth 
                ON signups(auth_provider, provider_id) 
                WHERE auth_provider != 'email';
        """
        
        await conn.execute(create_table_query)
        logger.info("Database schema initialized successfully with OAuth support")
        
    except asyncpg.PostgresError as e:
        logger.error(f"Error initializing database schema: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing database schema: {e}")
        raise

# Health check function for database
async def check_database_health() -> bool:
    """
    Check if the database connection pool is healthy.
    
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        if not db_pool:
            return False
        
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            return True
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

# Context manager for transaction handling
@asynccontextmanager
async def get_db_transaction():
    """
    Async context manager for database transactions.
    Automatically handles transaction commit/rollback.
    """
    if not db_pool:
        raise RuntimeError("Database pool not initialized. Call connect_to_db() first.")
    
    async with db_pool.acquire() as connection:
        async with connection.transaction():
            try:
                yield connection
            except Exception as e:
                logger.error(f"Transaction error: {e}")
                raise

# Batch operations
async def create_users_batch(
    conn: asyncpg.Connection, 
    users_data: list[Dict[str, Any]]
) -> list[Dict[str, Any]]:
    """
    Create multiple users in a single transaction.
    
    Args:
        conn: AsyncPG connection object
        users_data: List of user dictionaries to create
        
    Returns:
        List of created user dictionaries
    """
    try:
        created_users = []
        
        for user_data in users_data:
            user = await create_user(
                conn,
                email=user_data['email'],
                username=user_data.get('username'),
                hashed_password=user_data['hashed_password'],
                gpu_models_interested=user_data.get('gpu_models_interested', []),
                min_profit_threshold=user_data.get('min_profit_threshold', 0.0)
            )
            created_users.append(user)
        
        logger.info(f"Created {len(created_users)} users in batch")
        return created_users
        
    except Exception as e:
        logger.error(f"Error creating users batch: {e}")
        raise

async def update_user_verification(conn: asyncpg.Connection, user_id: int, is_verified: bool) -> bool:
    """
    Update user email verification status.
    
    Args:
        conn: Database connection
        user_id: User ID
        is_verified: Verification status
        
    Returns:
        True if successful, False otherwise
    """
    try:
        query = """
        UPDATE signups 
        SET is_verified = $1
        WHERE id = $2
        """
        
        result = await conn.execute(query, is_verified, user_id)
        
        logger.info(f"User {user_id} verification status updated to {is_verified}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating verification status for user {user_id}: {e}")
        return False

async def update_user_password(conn: asyncpg.Connection, user_id: int, hashed_password: str) -> bool:
    """
    Update user password.
    
    Args:
        conn: Database connection
        user_id: User ID
        hashed_password: New hashed password
        
    Returns:
        True if successful, False otherwise
    """
    try:
        query = """
        UPDATE signups 
        SET hashed_password = $1
        WHERE id = $2
        """
        
        result = await conn.execute(query, hashed_password, user_id)
        
        logger.info(f"Password updated for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating password for user {user_id}: {e}")
        return False

async def update_user_auth_provider(conn: asyncpg.Connection, user_id: int, auth_provider: AuthProvider) -> bool:
    """
    Update user's primary authentication provider.
    
    Args:
        conn: Database connection
        user_id: User ID
        auth_provider: New primary auth provider
        
    Returns:
        True if successful, False otherwise
    """
    try:
        query = """
        UPDATE signups 
        SET auth_provider = $1
        WHERE id = $2
        """
        
        result = await conn.execute(query, auth_provider.value, user_id)
        
        logger.info(f"Auth provider updated to {auth_provider.value} for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating auth provider for user {user_id}: {e}")
        return False

async def update_user_profile(
    conn: asyncpg.Connection, 
    user_id: int, 
    email: Optional[str] = None,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
    avatar_url: Optional[str] = None
) -> bool:
    """
    Update user profile information.
    
    Args:
        conn: Database connection
        user_id: User ID
        email: New email (optional)
        username: New username (optional)
        full_name: New full name (optional)
        avatar_url: New avatar URL (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Build dynamic query based on provided fields
        updates = []
        values = []
        param_counter = 1
        
        if email is not None:
            updates.append(f"email = ${param_counter}")
            values.append(email)
            param_counter += 1
        
        if username is not None:
            updates.append(f"username = ${param_counter}")
            values.append(username)
            param_counter += 1
        
        if full_name is not None:
            updates.append(f"full_name = ${param_counter}")
            values.append(full_name)
            param_counter += 1
        
        if avatar_url is not None:
            updates.append(f"avatar_url = ${param_counter}")
            values.append(avatar_url)
            param_counter += 1
        
        if not updates:
            return True  # Nothing to update
        
        # Add user_id as final parameter
        values.append(user_id)
        
        query = f"""
        UPDATE signups 
        SET {', '.join(updates)}
        WHERE id = ${param_counter}
        """
        
        result = await conn.execute(query, *values)
        
        logger.info(f"Profile updated for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating profile for user {user_id}: {e}")
        return False

async def delete_user(conn: asyncpg.Connection, user_id: int) -> bool:
    """
    Delete user account (soft delete by setting is_active to False).
    
    Args:
        conn: Database connection
        user_id: User ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        query = """
        UPDATE signups 
        SET is_active = FALSE
        WHERE id = $1
        """
        
        result = await conn.execute(query, user_id)
        
        logger.info(f"User {user_id} account deactivated")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False

async def hard_delete_user(conn: asyncpg.Connection, user_id: int) -> bool:
    """
    Permanently delete user account (hard delete).
    
    Args:
        conn: Database connection
        user_id: User ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Delete user (cascading deletes will handle related records)
        query = "DELETE FROM signups WHERE id = $1"
        result = await conn.execute(query, user_id)
        
        logger.info(f"User {user_id} permanently deleted")
        return True
        
    except Exception as e:
        logger.error(f"Error hard deleting user {user_id}: {e}")
        return False

async def get_users_by_auth_provider(
    conn: asyncpg.Connection, 
    auth_provider: AuthProvider, 
    limit: int = 100, 
    offset: int = 0
) -> list[Dict[str, Any]]:
    """
    Get users by authentication provider.
    
    Args:
        conn: Database connection
        auth_provider: Authentication provider
        limit: Maximum number of users to return
        offset: Number of users to skip
        
    Returns:
        List of user records
    """
    try:
        query = """
        SELECT id, email, username, is_active, is_verified, auth_provider, 
               provider_id, avatar_url, full_name, created_at, last_login,
               gpu_models_interested, min_profit_threshold
        FROM signups 
        WHERE auth_provider = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """
        
        result = await conn.fetch(query, auth_provider.value, limit, offset)
        
        users = []
        for row in result:
            user = dict(row)
            if user.get('gpu_models_interested'):
                user['gpu_models_interested'] = list(user['gpu_models_interested'])
            users.append(user)
        
        return users
        
    except Exception as e:
        logger.error(f"Error getting users by auth provider {auth_provider.value}: {e}")
        return []

async def get_user_stats(conn: asyncpg.Connection) -> Dict[str, Any]:
    """
    Get user statistics.
    
    Args:
        conn: Database connection
        
    Returns:
        User statistics dictionary
    """
    try:
        # Total users
        total_users = await conn.fetchval(
            "SELECT COUNT(*) FROM signups WHERE is_active = TRUE"
        )
        
        # Users by auth provider
        provider_result = await conn.fetch("""
            SELECT auth_provider, COUNT(*) as count 
            FROM signups 
            WHERE is_active = TRUE 
            GROUP BY auth_provider
        """)
        
        provider_stats = {}
        for row in provider_result:
            provider_stats[row['auth_provider']] = row['count']
        
        # Verified users
        verified_users = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM signups 
            WHERE is_active = TRUE AND is_verified = TRUE
        """)
        
        # Recent signups (last 30 days)
        recent_signups = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM signups 
            WHERE is_active = TRUE AND created_at >= NOW() - INTERVAL '30 days'
        """)
        
        # Active users (logged in within last 30 days)
        active_users = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM signups 
            WHERE is_active = TRUE AND last_login >= NOW() - INTERVAL '30 days'
        """)
        
        return {
            "total_users": total_users or 0,
            "verified_users": verified_users or 0,
            "verification_rate": round((verified_users / total_users * 100), 2) if total_users and total_users > 0 else 0,
            "recent_signups": recent_signups or 0,
            "active_users": active_users or 0,
            "activity_rate": round((active_users / total_users * 100), 2) if total_users and total_users > 0 else 0,
            "auth_providers": provider_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {
            "total_users": 0,
            "verified_users": 0,
            "verification_rate": 0,
            "recent_signups": 0,
            "active_users": 0,
            "activity_rate": 0,
            "auth_providers": {}
        }

async def search_users(
    conn: asyncpg.Connection, 
    query: str, 
    auth_provider: Optional[AuthProvider] = None,
    is_verified: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
) -> list[Dict[str, Any]]:
    """
    Search users by email, username, or full name.
    
    Args:
        conn: Database connection
        query: Search query
        auth_provider: Filter by auth provider (optional)
        is_verified: Filter by verification status (optional)
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        List of matching user records
    """
    try:
        # Build dynamic query
        where_conditions = ["is_active = TRUE"]
        params = []
        param_count = 0
        
        # Add search condition
        if query:
            param_count += 1
            where_conditions.append(f"""
                (email ILIKE ${param_count} OR 
                 username ILIKE ${param_count} OR 
                 full_name ILIKE ${param_count})
            """)
            params.append(f"%{query}%")
        
        # Add auth provider filter
        if auth_provider:
            param_count += 1
            where_conditions.append(f"auth_provider = ${param_count}")
            params.append(auth_provider.value)
        
        # Add verification filter
        if is_verified is not None:
            param_count += 1
            where_conditions.append(f"is_verified = ${param_count}")
            params.append(is_verified)
        
        # Add limit and offset
        param_count += 1
        params.append(limit)
        limit_param = param_count
        
        param_count += 1
        params.append(offset)
        offset_param = param_count
        
        sql_query = f"""
        SELECT id, email, username, is_active, is_verified, auth_provider, 
               provider_id, avatar_url, full_name, created_at, last_login,
               gpu_models_interested, min_profit_threshold
        FROM signups 
        WHERE {' AND '.join(where_conditions)}
        ORDER BY created_at DESC
        LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        result = await conn.fetch(sql_query, *params)
        
        users = []
        for row in result:
            user = dict(row)
            if user.get('gpu_models_interested'):
                user['gpu_models_interested'] = list(user['gpu_models_interested'])
            users.append(user)
        
        return users
        
    except Exception as e:
        logger.error(f"Error searching users with query '{query}': {e}")
        return []

async def create_login_history_table(conn: asyncpg.Connection):
    """
    Create login history table if it doesn't exist.
    
    Args:
        conn: Database connection
    """
    try:
        query = """
        CREATE TABLE IF NOT EXISTS login_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES signups(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            ip_address INET,
            user_agent TEXT,
            auth_provider VARCHAR(50) NOT NULL,
            success BOOLEAN NOT NULL,
            login_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            failure_reason TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history(user_id);
        CREATE INDEX IF NOT EXISTS idx_login_history_email ON login_history(email);
        CREATE INDEX IF NOT EXISTS idx_login_history_time ON login_history(login_time);
        CREATE INDEX IF NOT EXISTS idx_login_history_success ON login_history(success);
        """
        
        await conn.execute(query)
        logger.info("Login history table created/verified")
        
    except Exception as e:
        logger.error(f"Error creating login history table: {e}")

async def record_login_attempt(
    conn: asyncpg.Connection, 
    user_id: Optional[int], 
    email: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
    auth_provider: str,
    success: bool,
    failure_reason: Optional[str] = None
) -> bool:
    """
    Record a login attempt.
    
    Args:
        conn: Database connection
        user_id: User ID (None for failed attempts)
        email: Email used for login
        ip_address: Client IP address
        user_agent: Client user agent
        auth_provider: Authentication provider used
        success: Whether login was successful
        failure_reason: Reason for failure (if applicable)
        
    Returns:
        True if recorded successfully
    """
    try:
        query = """
        INSERT INTO login_history (
            user_id, email, ip_address, user_agent, 
            auth_provider, success, login_time, failure_reason
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        
        await conn.execute(
            query,
            user_id,
            email,
            ip_address,
            user_agent,
            auth_provider,
            success,
            datetime.now(timezone.utc),
            failure_reason
        )
        
        return True
        
    except Exception as e:
        logger.warning(f"Could not record login attempt: {e}")
        return False

async def get_user_login_history(conn: asyncpg.Connection, user_id: int, limit: int = 10) -> list[Dict[str, Any]]:
    """
    Get user login history.
    
    Args:
        conn: Database connection
        user_id: User ID
        limit: Number of login records to return
        
    Returns:
        List of login history records
    """
    try:
        query = """
        SELECT login_time, ip_address, user_agent, auth_provider, success, failure_reason
        FROM login_history 
        WHERE user_id = $1
        ORDER BY login_time DESC
        LIMIT $2
        """
        
        result = await conn.fetch(query, user_id, limit)
        
        history = []
        for row in result:
            record = dict(row)
            if record.get('login_time'):
                record['login_time'] = record['login_time'].isoformat()
            history.append(record)
        
        return history
        
    except Exception as e:
        logger.warning(f"Could not get login history for user {user_id}: {e}")
        return []

async def get_failed_login_attempts(
    conn: asyncpg.Connection, 
    email: str, 
    time_window_minutes: int = 15
) -> int:
    """
    Get count of failed login attempts for an email within a time window.
    
    Args:
        conn: Database connection
        email: Email address
        time_window_minutes: Time window in minutes
        
    Returns:
        Number of failed login attempts
    """
    try:
        query = """
        SELECT COUNT(*) 
        FROM login_history 
        WHERE email = $1 
        AND success = FALSE 
        AND login_time >= NOW() - INTERVAL '%s minutes'
        """
        
        result = await conn.fetchval(query, email, time_window_minutes)
        return result or 0
        
    except Exception as e:
        logger.error(f"Error getting failed login attempts for {email}: {e}")
        return 0

async def clear_failed_login_attempts(conn: asyncpg.Connection, email: str) -> bool:
    """
    Clear failed login attempts for an email (called after successful login).
    
    Args:
        conn: Database connection
        email: Email address
        
    Returns:
        True if successful
    """
    try:
        query = """
        DELETE FROM login_history 
        WHERE email = $1 AND success = FALSE
        """
        
        await conn.execute(query, email)
        return True
        
    except Exception as e:
        logger.error(f"Error clearing failed login attempts for {email}: {e}")
        return False

async def get_oauth_stats(conn: asyncpg.Connection) -> Dict[str, Any]:
    """
    Get OAuth-specific statistics.
    
    Args:
        conn: Database connection
        
    Returns:
        OAuth statistics
    """
    try:
        # OAuth users by provider
        oauth_stats = await conn.fetch("""
            SELECT auth_provider, 
                   COUNT(*) as total_users,
                   COUNT(*) FILTER (WHERE is_verified = TRUE) as verified_users,
                   COUNT(*) FILTER (WHERE last_login >= NOW() - INTERVAL '30 days') as active_users
            FROM signups 
            WHERE is_active = TRUE AND auth_provider != 'email'
            GROUP BY auth_provider
            ORDER BY total_users DESC
        """)
        
        # Email vs OAuth breakdown
        auth_breakdown = await conn.fetch("""
            SELECT 
                CASE 
                    WHEN auth_provider = 'email' THEN 'email'
                    ELSE 'oauth'
                END as auth_type,
                COUNT(*) as count
            FROM signups 
            WHERE is_active = TRUE
            GROUP BY auth_type
        """)
        
        # Recent OAuth signups (last 7 days)
        recent_oauth = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM signups 
            WHERE is_active = TRUE 
            AND auth_provider != 'email'
            AND created_at >= NOW() - INTERVAL '7 days'
        """)
        
        result = {
            "oauth_providers": {},
            "auth_breakdown": {},
            "recent_oauth_signups": recent_oauth or 0
        }
        
        # Process OAuth provider stats
        for row in oauth_stats:
            provider = row['auth_provider']
            result["oauth_providers"][provider] = {
                "total_users": row['total_users'],
                "verified_users": row['verified_users'],
                "active_users": row['active_users'],
                "verification_rate": round((row['verified_users'] / row['total_users'] * 100), 2) if row['total_users'] > 0 else 0,
                "activity_rate": round((row['active_users'] / row['total_users'] * 100), 2) if row['total_users'] > 0 else 0
            }
        
        # Process auth breakdown
        for row in auth_breakdown:
            result["auth_breakdown"][row['auth_type']] = row['count']
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting OAuth stats: {e}")
        return {
            "oauth_providers": {},
            "auth_breakdown": {},
            "recent_oauth_signups": 0
        }

# Add this alias at the bottom of the file for backward compatibility
create_user_oauth = create_oauth_user