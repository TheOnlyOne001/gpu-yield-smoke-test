from datetime import datetime, timedelta
from typing import Annotated, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
import redis
import csv
import io

from models import User, AuthProvider
from security import get_current_user
from dependencies import redis_dependency, db_dependency
from crud import (
    get_user_stats, 
    search_users, 
    get_users_by_auth_provider,
    get_user_by_id,
    update_user_verification,
    delete_user,
    hard_delete_user,
    get_user_login_history
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin OAuth Management"])

def require_admin(current_user: User = Depends(get_current_user)):
    """
    Dependency to require admin privileges.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User if admin, raises HTTPException otherwise
    """
    # You'll need to add is_admin field to your User model
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

@router.get("/users/stats")
async def get_user_statistics(
    admin_user: Annotated[User, Depends(require_admin)],
    conn = Depends(db_dependency)
):
    """
    Get comprehensive user statistics.
    
    Args:
        admin_user: Current admin user
        conn: Database connection
        
    Returns:
        User statistics and analytics
    """
    try:
        stats = await get_user_stats(conn)
        
        # Add additional admin-specific stats
        recent_stats_query = """
        SELECT 
            DATE_TRUNC('day', created_at) as date,
            auth_provider,
            COUNT(*) as signups
        FROM signups 
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE_TRUNC('day', created_at), auth_provider
        ORDER BY date DESC
        """
        
        recent_result = await conn.fetch(recent_stats_query)
        
        # Format daily signup data
        daily_signups = {}
        for row in recent_result:
            date_str = row['date'].strftime('%Y-%m-%d')
            if date_str not in daily_signups:
                daily_signups[date_str] = {}
            daily_signups[date_str][row['auth_provider']] = row['signups']
        
        stats['daily_signups'] = daily_signups
        
        logger.info(f"User statistics accessed by admin {admin_user.email}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting user statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user statistics"
        )

@router.get("/users/search")
async def search_users_admin(
    admin_user: Annotated[User, Depends(require_admin)],
    conn = Depends(db_dependency),  # Move this here - before default parameters
    q: str = Query(..., description="Search query"),
    auth_provider: Optional[AuthProvider] = Query(None, description="Filter by auth provider"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    Search users with admin privileges.
    
    Args:
        admin_user: Current admin user
        conn: Database connection
        q: Search query
        auth_provider: Optional auth provider filter
        is_verified: Optional verification status filter
        is_active: Optional active status filter
        limit: Number of results to return
        offset: Number of results to skip
        
    Returns:
        Search results with user details
    """
    try:
        users = await search_users(
            conn=conn,
            query=q,
            auth_provider=auth_provider,
            is_verified=is_verified,
            limit=limit,
            offset=offset
        )
        
        # Get total count for pagination
        count_query = """
        SELECT COUNT(*) as total 
        FROM signups 
        WHERE is_active = TRUE
        AND (email ILIKE $1 OR username ILIKE $2 OR full_name ILIKE $3)
        """
        count_params = [f"%{q}%", f"%{q}%", f"%{q}%"]
        param_count = 3
        
        if auth_provider:
            param_count += 1
            count_query += f" AND auth_provider = ${param_count}"
            count_params.append(auth_provider.value)
        
        if is_verified is not None:
            param_count += 1
            count_query += f" AND is_verified = ${param_count}"
            count_params.append(is_verified)
        
        if is_active is not None:
            param_count += 1
            count_query += f" AND is_active = ${param_count}"
            count_params.append(is_active)
        
        count_result = await conn.fetch(count_query, *count_params)
        total_count = count_result[0]['total'] if count_result else 0
        
        logger.info(f"User search performed by admin {admin_user.email}: '{q}'")
        
        return {
            "users": users,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(users) < total_count
        }
        
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search users"
        )

@router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    admin_user: Annotated[User, Depends(require_admin)],
    conn = Depends(db_dependency)  # This is fine as it's after path/annotated params
):
    """
    Get detailed user information.
    
    Args:
        user_id: User ID to retrieve
        admin_user: Current admin user
        conn: Database connection
        
    Returns:
        Detailed user information
    """
    try:
        user = await get_user_by_id(conn, user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get login history
        login_history = await get_user_login_history(conn, user_id, limit=20)
        
        # Get OAuth providers linked to this user
        from crud import get_user_oauth_providers
        oauth_providers = await get_user_oauth_providers(conn, user_id)
        
        # Remove sensitive information
        if 'hashed_password' in user:
            user['has_password'] = bool(user['hashed_password'])
            del user['hashed_password']
        
        logger.info(f"User {user_id} details accessed by admin {admin_user.email}")
        
        return {
            "user": user,
            "login_history": login_history,
            "oauth_providers": oauth_providers,
            "account_age_days": (datetime.utcnow() - user['created_at']).days if user['created_at'] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user details"
        )

@router.patch("/users/{user_id}/verify")
async def admin_verify_user(
    user_id: int,
    admin_user: Annotated[User, Depends(require_admin)],
    conn = Depends(db_dependency)  # This is fine
):
    """
    Manually verify a user's email address.
    
    Args:
        user_id: User ID to verify
        admin_user: Current admin user
        conn: Database connection
        
    Returns:
        Success message
    """
    try:
        success = await update_user_verification(conn, user_id, True)
        
        if success:
            logger.info(f"User {user_id} manually verified by admin {admin_user.email}")
            
            return {
                "message": "User verified successfully",
                "user_id": user_id,
                "verified_by": admin_user.email,
                "verified_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify user"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify user"
        )

@router.delete("/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    admin_user: Annotated[User, Depends(require_admin)],
    conn = Depends(db_dependency),  # Move before default parameters
    hard_delete: bool = Query(False, description="Permanently delete user")
):
    """
    Delete a user account.
    
    Args:
        user_id: User ID to delete
        admin_user: Current admin user
        conn: Database connection
        hard_delete: Whether to permanently delete (default: soft delete)
        
    Returns:
        Success message
    """
    try:
        # Prevent admin from deleting themselves
        if user_id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        if hard_delete:
            success = await hard_delete_user(conn, user_id)
            action = "permanently deleted"
        else:
            success = await delete_user(conn, user_id)
            action = "deactivated"
        
        if success:
            logger.warning(f"User {user_id} {action} by admin {admin_user.email}")
            
            return {
                "message": f"User {action} successfully",
                "user_id": user_id,
                "action": action,
                "performed_by": admin_user.email,
                "performed_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to {action.split()[0]} user"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )

@router.get("/users/export")
async def export_users(
    admin_user: Annotated[User, Depends(require_admin)],
    conn = Depends(db_dependency),
    auth_provider: Optional[AuthProvider] = Query(None),
    is_verified: Optional[bool] = Query(None),
    format: str = Query("csv", regex="^(csv|json)$")
):
    """
    Export user data in CSV or JSON format.
    
    Args:
        admin_user: Current admin user
        conn: Database connection
        auth_provider: Optional auth provider filter
        is_verified: Optional verification status filter
        format: Export format (csv or json)
        
    Returns:
        File download with user data
    """
    try:
        # Build query with filters
        query = """
        SELECT id, email, username, full_name, auth_provider, 
               is_verified, is_active, created_at, last_login
        FROM signups
        WHERE 1=1
        """
        params = []
        
        if auth_provider:
            query += " AND auth_provider = $1"
            params.append(auth_provider.value)
        
        if is_verified is not None:
            param_num = len(params) + 1
            query += f" AND is_verified = ${param_num}"
            params.append(is_verified)
        
        query += " ORDER BY created_at DESC"
        
        result = await conn.fetch(query, *params)
        
        # Convert to list of dictionaries
        users = []
        for row in result:
            user = dict(row)
            # Format dates
            if user['created_at']:
                user['created_at'] = user['created_at'].isoformat()
            if user['last_login']:
                user['last_login'] = user['last_login'].isoformat()
            users.append(user)
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"gpu_yield_users_{timestamp}.{format}"
        
        if format == "csv":
            # Create CSV content
            output = io.StringIO()
            if users:
                writer = csv.DictWriter(output, fieldnames=users[0].keys())
                writer.writeheader()
                writer.writerows(users)
            
            content = output.getvalue()
            output.close()
            
            # Create streaming response
            response = StreamingResponse(
                io.BytesIO(content.encode('utf-8')),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
        else:  # JSON format
            import json
            content = json.dumps(users, indent=2, default=str)
            
            response = StreamingResponse(
                io.BytesIO(content.encode('utf-8')),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
        logger.info(f"User data exported by admin {admin_user.email} ({len(users)} users)")
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data"
        )

@router.get("/oauth/stats")
async def get_oauth_statistics(
    admin_user: Annotated[User, Depends(require_admin)],
    conn = Depends(db_dependency)  # Ensure this is before any default parameters
):
    """
    Get OAuth-specific statistics.
    
    Args:
        admin_user: Current admin user
        conn: Database connection
        
    Returns:
        OAuth statistics and analytics
    """
    try:
        # OAuth provider usage stats - Fix table name from 'users' to 'signups'
        provider_stats_query = """
        SELECT 
            auth_provider,
            COUNT(*) as total_users,
            COUNT(CASE WHEN is_verified THEN 1 END) as verified_users,
            COUNT(CASE WHEN last_login >= NOW() - INTERVAL '30 days' THEN 1 END) as active_users,
            MIN(created_at) as first_signup,
            MAX(created_at) as latest_signup
        FROM signups 
        WHERE is_active = TRUE
        GROUP BY auth_provider
        ORDER BY total_users DESC
        """
        
        provider_result = await conn.fetch(provider_stats_query)
        
        provider_stats = []
        for row in provider_result:
            stats = dict(row)
            if stats['first_signup']:
                stats['first_signup'] = stats['first_signup'].isoformat()
            if stats['latest_signup']:
                stats['latest_signup'] = stats['latest_signup'].isoformat()
            
            # Calculate rates
            total = stats['total_users']
            stats['verification_rate'] = round((stats['verified_users'] / total * 100), 2) if total > 0 else 0
            stats['activity_rate'] = round((stats['active_users'] / total * 100), 2) if total > 0 else 0
            
            provider_stats.append(stats)
        
        # OAuth adoption trends (last 12 months) - Fix table name
        trends_query = """
        SELECT 
            DATE_TRUNC('month', created_at) as month,
            auth_provider,
            COUNT(*) as signups
        FROM signups 
        WHERE created_at >= NOW() - INTERVAL '12 months'
        AND is_active = TRUE
        GROUP BY DATE_TRUNC('month', created_at), auth_provider
        ORDER BY month DESC, auth_provider
        """
        
        trends_result = await conn.fetch(trends_query)
        
        # Format trends data
        trends = {}
        for row in trends_result:
            month_str = row['month'].strftime('%Y-%m')
            if month_str not in trends:
                trends[month_str] = {}
            trends[month_str][row['auth_provider']] = row['signups']
        
        logger.info(f"OAuth statistics accessed by admin {admin_user.email}")
        
        return {
            "provider_statistics": provider_stats,
            "adoption_trends": trends,
            "summary": {
                "total_oauth_users": sum(stat['total_users'] for stat in provider_stats if stat['auth_provider'] != 'email'),
                "email_users": next((stat['total_users'] for stat in provider_stats if stat['auth_provider'] == 'email'), 0),
                "most_popular_oauth": max(
                    (stat for stat in provider_stats if stat['auth_provider'] != 'email'),
                    key=lambda x: x['total_users'],
                    default={"auth_provider": "none", "total_users": 0}
                )['auth_provider']
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting OAuth statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OAuth statistics"
        )

@router.post("/system/clear-oauth-cache")
async def clear_oauth_cache(
    admin_user: Annotated[User, Depends(require_admin)],
    redis_conn: redis.Redis = Depends(redis_dependency)
):
    """
    Clear OAuth-related cache entries.
    
    Args:
        admin_user: Current admin user
        redis_conn: Redis connection
        
    Returns:
        Success message with cleared entries count
    """
    try:
        # Clear OAuth state tokens
        oauth_state_keys = await redis_conn.keys("oauth_state:*")
        if oauth_state_keys:
            await redis_conn.delete(*oauth_state_keys)
        
        # Clear OAuth linking states
        oauth_link_keys = await redis_conn.keys("oauth_link:*")
        if oauth_link_keys:
            await redis_conn.delete(*oauth_link_keys)
        
        # Clear email verification tokens
        email_verify_keys = await redis_conn.keys("email_verification:*")
        if email_verify_keys:
            await redis_conn.delete(*email_verify_keys)
        
        # Clear password reset tokens
        password_reset_keys = await redis_conn.keys("password_reset:*")
        if password_reset_keys:
            await redis_conn.delete(*password_reset_keys)
        
        # Clear rate limiting keys
        rate_limit_keys = await redis_conn.keys("*_rate_limit:*")
        if rate_limit_keys:
            await redis_conn.delete(*rate_limit_keys)
        
        total_cleared = (
            len(oauth_state_keys) + 
            len(oauth_link_keys) + 
            len(email_verify_keys) + 
            len(password_reset_keys) +
            len(rate_limit_keys)
        )
        
        logger.warning(f"OAuth cache cleared by admin {admin_user.email} ({total_cleared} entries)")
        
        return {
            "message": "OAuth cache cleared successfully",
            "entries_cleared": total_cleared,
            "categories": {
                "oauth_states": len(oauth_state_keys),
                "oauth_links": len(oauth_link_keys),
                "email_verifications": len(email_verify_keys),
                "password_resets": len(password_reset_keys),
                "rate_limits": len(rate_limit_keys)
            },
            "cleared_by": admin_user.email,
            "cleared_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing OAuth cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear OAuth cache"
        )