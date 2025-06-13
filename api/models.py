from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime
import logging
import os

class HealthCheck(BaseModel):
    status: str = "ok"
    timestamp: Optional[str] = None
    version: Optional[str] = "1.0.0"

class GPUModel(str, Enum):
    """Common GPU models for validation"""
    RTX_4090 = "RTX 4090"
    RTX_4080 = "RTX 4080" 
    RTX_4070 = "RTX 4070"
    RTX_3090 = "RTX 3090"
    RTX_3080 = "RTX 3080"
    RTX_3070 = "RTX 3070"
    A100 = "A100"
    H100 = "H100"
    V100 = "V100"
    T4 = "T4"
    A10G = "A10G"
    K80 = "K80"
    OTHER = "Other"

# AWS Spot specific models
class AWSSpotOffer(BaseModel):
    """AWS Spot GPU offer with enrichment"""
    model: str = Field(..., description="GPU model (A100, T4, V100, etc.)")
    usd_hr: float = Field(..., ge=0, description="Per-GPU hourly price in USD")
    region: str = Field(..., description="AWS region (us-east-1, etc.)")
    availability: int = Field(..., ge=1, description="Number of GPUs per instance")
    instance_type: str = Field(..., description="EC2 instance type")
    provider: str = Field(default="aws_spot", description="Provider identifier")
    
    # Additional fields from scraper
    total_instance_price: Optional[float] = Field(None, description="Total hourly cost for entire instance")
    gpu_memory_gb: Optional[int] = Field(None, description="VRAM per GPU in GB")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of price fetch")
    synthetic: Optional[bool] = Field(False, description="Whether this is synthetic data")
    
    # Enriched fields
    interruption_risk: Optional[str] = Field(None, description="Spot interruption risk: low/medium/high")
    data_freshness: Optional[str] = Field(None, description="Data age: live/recent/stale")
    vcpu_count: Optional[int] = Field(None, description="Number of vCPUs")
    ram_gb: Optional[int] = Field(None, description="RAM in GB")
    network_performance: Optional[str] = Field(None, description="Network performance")
    storage_gb: Optional[int] = Field(None, description="Local storage in GB")
    ebs_optimized: Optional[bool] = Field(None, description="EBS optimization support")
    
    # Yield metrics (for operators)
    yield_metrics: Optional[Dict[str, Any]] = Field(None, description="Yield calculation metrics")

class AWSSpotResponse(BaseModel):
    """Response for AWS Spot pricing endpoint"""
    offers: List[AWSSpotOffer]
    total_count: int
    metadata: Dict[str, Any]

class AWSRegion(BaseModel):
    """AWS Region information"""
    code: str = Field(..., description="Region code (us-east-1, etc.)")
    name: str = Field(..., description="Human-readable region name")
    available: bool = Field(True, description="Whether region has current data")

class AWSRegionsResponse(BaseModel):
    """Response for AWS regions endpoint"""
    regions: List[AWSRegion]
    total_count: int

class GPUModelInfo(BaseModel):
    """GPU Model information"""
    name: str = Field(..., description="GPU model name")
    available: bool = Field(True, description="Whether model has current data")
    category: Optional[str] = Field(None, description="GPU category (datacenter/gaming)")

class AWSModelsResponse(BaseModel):
    """Response for AWS GPU models endpoint"""
    models: List[GPUModelInfo]
    total_count: int

class AWSSpotSummary(BaseModel):
    """Summary statistics for AWS Spot pricing"""
    total_offers: int
    unique_models: int
    unique_regions: int
    price_range: Dict[str, float]
    avg_price: float
    last_updated: Optional[str]
    models: Optional[List[str]] = None
    regions: Optional[List[str]] = None

# Existing models...
class ROICalcRequest(BaseModel):
    gpu_model: str = Field(..., min_length=1, max_length=50, description="GPU model name")
    hours_per_day: float = Field(..., gt=0, le=24, description="Hours of operation per day")
    power_cost_kwh: float = Field(..., ge=0, le=1.0, description="Electricity cost per kWh in USD")
    
    @field_validator('gpu_model')
    @classmethod
    def validate_gpu_model(cls, v):
        return v.strip().title()
    
    @field_validator('hours_per_day')
    @classmethod
    def validate_hours(cls, v):
        if v <= 0 or v > 24:
            raise ValueError('Hours per day must be between 0 and 24')
        return round(v, 2)
    
    @field_validator('power_cost_kwh')
    @classmethod
    def validate_power_cost(cls, v):
        if v < 0:
            raise ValueError('Power cost cannot be negative')
        if v > 1.0:
            raise ValueError('Power cost seems unreasonably high (>$1/kWh)')
        return round(v, 4)

class ROICalcResponse(BaseModel):
    potential_monthly_profit: float = Field(..., description="Estimated monthly profit in USD")
    break_even_hours: Optional[float] = Field(None, description="Hours needed to break even daily")
    daily_profit: Optional[float] = Field(None, description="Estimated daily profit in USD")
    
    class Config:
        json_schema_extra = {
            "example": {
                "potential_monthly_profit": 250.75,
                "break_even_hours": 8.5,
                "daily_profit": 8.36
            }
        }

class SignupRequest(BaseModel):
    email: EmailStr = Field(..., description="Valid email address")
    hcaptcha_response: str = Field(..., min_length=1, description="hCaptcha response token")
    gpu_models_interested: Optional[List[str]] = Field(default=[], description="List of GPU models of interest")
    min_profit_threshold: Optional[float] = Field(default=0.0, ge=0, description="Minimum daily profit threshold for alerts")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return v.lower().strip()

class SignupResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[str] = None

class GPUPriceDelta(BaseModel):
    gpu_model: str = Field(..., description="GPU model name")
    best_source: str = Field(..., description="Platform with the best price")
    price_usd_hr: float = Field(..., ge=0, description="Price per hour in USD")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    availability_count: Optional[int] = Field(None, description="Number of available instances")
    
    @field_validator('price_usd_hr')
    @classmethod
    def validate_price(cls, v):
        return round(v, 4)

class DeltaResponse(BaseModel):
    deltas: List[GPUPriceDelta] = Field(..., description="List of GPU pricing deltas")
    total_count: Optional[int] = Field(None, description="Total number of pricing records")
    last_updated: Optional[str] = Field(None, description="Last data refresh timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "deltas": [
                    {
                        "gpu_model": "RTX 4090",
                        "best_source": "vast.ai",
                        "price_usd_hr": 0.75,
                        "availability_count": 15
                    }
                ],
                "total_count": 1,
                "last_updated": "2024-01-15T10:30:00Z"
            }
        }

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: Optional[str] = None

# Additional existing models...
class StatsResponse(BaseModel):
    gpu_count: int = Field(..., description="Number of unique GPUs tracked in the last 24 hours")
    total_providers: int = Field(default=5, description="Number of cloud providers monitored")
    last_update: Optional[str] = Field(None, description="Timestamp of last data update")
    active_models: Optional[List[str]] = Field(None, description="List of active GPU models")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gpu_count": 45678,
                "total_providers": 5,
                "last_update": "2024-01-15T10:30:00Z",
                "active_models": ["RTX 4090", "A100", "H100", "RTX 3090", "V100"]
            }
        }

class DetailedStatsResponse(BaseModel):
    """Extended statistics response with more metrics"""
    gpu_count: int = Field(..., description="Total unique GPUs tracked")
    total_providers: int = Field(..., description="Number of cloud providers")
    active_regions: int = Field(..., description="Number of geographic regions covered")
    price_range: Dict[str, float] = Field(..., description="Min and max prices observed")
    top_gpu_models: List[Dict[str, Union[str, float]]] = Field(..., description="Most tracked GPU models")
    last_24h_updates: int = Field(..., description="Price updates in last 24 hours")
    system_health: str = Field(..., description="Overall system health status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gpu_count": 45678,
                "total_providers": 5,
                "active_regions": 12,
                "price_range": {"min": 0.15, "max": 2.50},
                "top_gpu_models": [
                    {"model": "RTX 4090", "count": 15420, "avg_price": 0.75},
                    {"model": "A100", "count": 8950, "avg_price": 1.20}
                ],
                "last_24h_updates": 125430,
                "system_health": "excellent"
            }
        }

# Auth related models

# User model for authentication
class User(BaseModel):
    id: str
    email: EmailStr
    username: Optional[str] = None
    hashed_password: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    gpu_models_interested: Optional[List[str]] = []
    min_profit_threshold: float = 0.0

    class Config:
        from_attributes = True

# Token models
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: Optional[int] = Field(None, description="Token expiry in seconds")

class TokenData(BaseModel):
    email: Optional[str] = None

# Alert Job model for Redis queue
class AlertJob(BaseModel):
    job_type: str
    email: str
    user_id: str
    data: Optional[dict] = None

# Add these new models for OAuth authentication

class AuthProvider(str, Enum):
    """Enumeration of supported authentication providers."""
    EMAIL = "email"
    GOOGLE = "google"
    TWITTER = "twitter"
    DISCORD = "discord"

class UserBase(BaseModel):
    """Base user model with common fields."""
    email: EmailStr
    username: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    gpu_models_interested: Optional[List[str]] = []
    min_profit_threshold: Optional[float] = Field(default=10.0, ge=0, le=1000)

class UserCreate(UserBase):
    """User creation model."""
    password: Optional[str] = None  # Optional for OAuth users
    auth_provider: AuthProvider = AuthProvider.EMAIL
    provider_id: Optional[str] = None  # OAuth provider user ID
    avatar_url: Optional[str] = None
    full_name: Optional[str] = None

class UserOAuth(BaseModel):
    """OAuth user data model."""
    provider: AuthProvider
    provider_id: str
    email: EmailStr
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = {}

class User(UserBase):
    """Complete user model."""
    id: int
    auth_provider: AuthProvider
    provider_id: Optional[str] = None
    avatar_url: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserInDB(User):
    """User model with sensitive data for database operations."""
    hashed_password: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserProfile(BaseModel):
    """User profile update model."""
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    gpu_models_interested: Optional[List[str]] = None
    min_profit_threshold: Optional[float] = Field(None, ge=0, le=1000)

class UserStats(BaseModel):
    """User statistics model."""
    total_users: int
    verified_users: int
    verification_rate: float
    recent_signups: int
    active_users: int
    activity_rate: float
    auth_providers: Dict[str, int]

# Update your existing Token model
class Token(BaseModel):
    """JWT Token model."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    user: Optional[User] = None

class TokenData(BaseModel):
    """JWT Token data model."""
    email: Optional[str] = None
    provider: Optional[AuthProvider] = None

# Update your existing SignupRequest model
class SignupRequest(BaseModel):
    """User signup request model."""
    email: EmailStr
    password: Optional[str] = None
    username: Optional[str] = None
    gpu_models_interested: Optional[List[str]] = []
    min_profit_threshold: Optional[float] = Field(default=10.0, ge=0, le=1000)
    hcaptcha_response: str = Field(..., min_length=1)
    auth_provider: AuthProvider = AuthProvider.EMAIL
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return v.lower().strip()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v, info):
        # Password required for email auth, optional for OAuth
        if info.data.get('auth_provider') == AuthProvider.EMAIL and not v:
            raise ValueError('Password is required for email authentication')
        if v and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

# Update your existing SignupResponse model  
class SignupResponse(BaseModel):
    """User signup response model."""
    status: str
    message: str
    user_id: Optional[str] = None
    requires_verification: bool = True

class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return v.lower().strip()

class OAuthLoginRequest(BaseModel):
    """OAuth login request model."""
    provider: AuthProvider
    code: Optional[str] = None
    state: Optional[str] = None
    redirect_uri: Optional[str] = None

class OAuthState(BaseModel):
    """OAuth state management model."""
    state_token: str
    provider: AuthProvider
    redirect_url: Optional[str] = None
    created_at: datetime
    expires_at: datetime

class OAuthCallback(BaseModel):
    """OAuth callback data model."""
    code: str
    state: str
    provider: AuthProvider
    error: Optional[str] = None
    error_description: Optional[str] = None

class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    email: EmailStr
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return v.lower().strip()

class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model."""
    token: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class ChangePasswordRequest(BaseModel):
    """Change password request model."""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class EmailVerificationRequest(BaseModel):
    """Email verification request model."""
    email: Optional[EmailStr] = None  # Optional - uses current user if not provided

class EmailVerificationResponse(BaseModel):
    """Email verification response model."""
    message: str
    expires_in: int

class VerificationStatusResponse(BaseModel):
    """Verification status response model."""
    email: str
    is_verified: bool
    auth_provider: AuthProvider
    requires_verification: bool

class LoginHistoryEntry(BaseModel):
    """Login history entry model."""
    login_time: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    auth_provider: str
    success: bool
    failure_reason: Optional[str] = None

class UserActivity(BaseModel):
    """User activity summary model."""
    user_id: int
    last_login: Optional[datetime] = None
    login_count: int = 0
    failed_login_attempts: int = 0
    last_login_ip: Optional[str] = None
    account_locked: bool = False

class OAuthProviderConfig(BaseModel):
    """OAuth provider configuration model."""
    provider: AuthProvider
    display_name: str
    is_enabled: bool
    client_id: Optional[str] = None
    redirect_uri: Optional[str] = None
    scope: Optional[str] = None

class OAuthProvidersResponse(BaseModel):
    """OAuth providers list response model."""
    providers: List[OAuthProviderConfig]
    total_count: int

class UserSearchRequest(BaseModel):
    """User search request model."""
    query: Optional[str] = None
    auth_provider: Optional[AuthProvider] = None
    is_verified: Optional[bool] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)

class UserSearchResponse(BaseModel):
    """User search response model."""
    users: List[User]
    total_count: int
    has_more: bool

# Admin models
class AdminUserUpdate(BaseModel):
    """Admin user update model."""
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    auth_provider: Optional[AuthProvider] = None
    full_name: Optional[str] = None
    gpu_models_interested: Optional[List[str]] = None
    min_profit_threshold: Optional[float] = Field(None, ge=0, le=1000)

class BulkUserAction(BaseModel):
    """Bulk user action model."""
    user_ids: List[int]
    action: str  # 'verify', 'deactivate', 'delete', etc.
    reason: Optional[str] = None

class SystemHealth(BaseModel):
    """System health check model."""
    status: str
    database: str
    redis: str
    email_service: str
    oauth_providers: Dict[str, str]
    timestamp: datetime

# Rate limiting models
class RateLimitInfo(BaseModel):
    """Rate limit information model."""
    limit: int
    remaining: int
    reset_time: datetime
    
class RateLimitExceeded(BaseModel):
    """Rate limit exceeded error model."""
    error: str = "Rate limit exceeded"
    retry_after: int
    limit: int

# ...existing models continue here...