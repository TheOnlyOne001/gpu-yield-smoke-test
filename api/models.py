from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import List, Optional, Dict, Any
from enum import Enum

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
    OTHER = "Other"

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

# Alert Models for the worker
class AlertJob(BaseModel):
    job_type: str
    email: Optional[str] = None
    user_id: Optional[str] = None
    gpu_model: Optional[str] = None
    target_profit: Optional[float] = None
    current_profit: Optional[float] = None

class PriceAlert(BaseModel):
    gpu_model: str
    platform: str
    current_price: float
    previous_price: Optional[float] = None
    profit_margin: float
    alert_threshold: float

# Authentication Models
class UserCreate(BaseModel):
    """Model for creating a new user"""
    email: EmailStr = Field(..., description="Valid email address")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=100, description="Password")
    gpu_models_interested: Optional[List[str]] = Field(default=[], description="List of GPU models of interest")
    min_profit_threshold: Optional[float] = Field(default=0.0, ge=0, description="Minimum profit threshold for alerts")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return v.lower().strip()
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if v:
            v = v.strip()
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class User(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    username: Optional[str] = None
    hashed_password: str
    is_active: bool = True
    created_at: Optional[str] = None
    gpu_models_interested: Optional[List[str]] = Field(default=[])
    min_profit_threshold: Optional[float] = Field(default=0.0, ge=0)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None

class TokenData(BaseModel):
    email: Optional[str] = None

# Statistics Models
class StatsResponse(BaseModel):
    """Response model for API statistics endpoint"""
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
    top_gpu_models: List[Dict[str, Any]] = Field(..., description="Most tracked GPU models")
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