from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    sku: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    category: Optional[str] = None
    brand: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    sku: str
    brand: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
