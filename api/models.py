from pydantic import BaseModel, Field
from typing import List, Optional

class HealthCheck(BaseModel):
    status: str = "ok"

class ROICalcRequest(BaseModel):
    gpu_model: str
    hours_per_day: float = Field(..., gt=0, le=24)
    power_cost_kwh: float = Field(..., ge=0)

class ROICalcResponse(BaseModel):
    potential_monthly_profit: float

class SignupRequest(BaseModel):
    email: str
    hcaptcha_response: str

class GPUPriceDelta(BaseModel):
    gpu_model: str
    best_source: str
    price_usd_hr: float

class DeltaResponse(BaseModel):
    deltas: List[GPUPriceDelta]