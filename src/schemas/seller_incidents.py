from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class SellerIncidentBase(BaseModel):
    seller_id: int
    shopkeeper_id: Optional[int] = None
    type: str
    description: Optional[str] = None
    incident_date: date

class SellerIncidentCreate(SellerIncidentBase):
    pass

class SellerIncidentUpdate(BaseModel):
    seller_id: Optional[int] = None     
    shopkeeper_id: Optional[int] = None  
    type: Optional[str] = None
    description: Optional[str] = None
    incident_date: Optional[date] = None

class SellerIncidentResponse(SellerIncidentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        rom_attributes = True