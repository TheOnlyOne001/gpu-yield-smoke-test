import os
import asyncpg
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timezone
from contextlib import asynccontextmanager

# Initialize logger
logger = logging.getLogger(__name__)

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

async def init_database_schema(conn: asyncpg.Connection):
    """
    Initializes the database schema if it doesn't exist.
    
    Args:
        conn: AsyncPG connection object
    """
    try:
        # Create signups table if it doesn't exist
        create_table_query = """
            CREATE TABLE IF NOT EXISTS signups (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100),
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                gpu_models_interested TEXT[],
                min_profit_threshold DECIMAL(10, 2) DEFAULT 0.0
            );
            
            CREATE INDEX IF NOT EXISTS idx_signups_email ON signups(email);
            CREATE INDEX IF NOT EXISTS idx_signups_created_at ON signups(created_at);
            CREATE INDEX IF NOT EXISTS idx_signups_is_active ON signups(is_active);
        """
        
        await conn.execute(create_table_query)
        logger.info("Database schema initialized successfully")
        
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