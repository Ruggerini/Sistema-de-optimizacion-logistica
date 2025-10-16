from datetime import datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    company_id: str = Field(..., max_length=50)
    company_name: str = Field(..., max_length=150)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserRead(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class TruckInput(BaseModel):
    id: Optional[str] = None
    name: str
    start_address: str
    end_address: str


class StopInput(BaseModel):
    id: Optional[str] = None
    address: str


class OptimizationRequest(BaseModel):
    trucks: List[TruckInput]
    stops: List[StopInput]
    execution_date: Optional[str] = None


class StopDetail(BaseModel):
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    eta_minutes: Optional[float] = None


class TruckRoute(BaseModel):
    truck_id: Optional[str]
    truck_name: str
    zone_label: str
    total_duration_minutes: float
    total_distance_km: float
    google_maps_link: str
    mapbox_trip_id: Optional[str] = None
    geometry: Optional[dict] = None
    stops: List[StopDetail]


class OptimizationSummary(BaseModel):
    trucks_needed: int
    total_distance_km: float
    total_duration_minutes: float
    unassigned_stops: int


class OptimizationResponse(BaseModel):
    summary: OptimizationSummary
    assignments: List[TruckRoute]
    unassigned: List[StopDetail]


class RouteHistoryRead(BaseModel):
    id: int
    run_date: datetime
    execution_date: Optional[str]
    truck_assignments: List[TruckRoute]
    google_maps_links: List[str]

    class Config:
        from_attributes = True
