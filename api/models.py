from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime

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
        orm_mode = True

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