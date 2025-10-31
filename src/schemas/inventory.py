from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InventoryCreate(BaseModel):
    shopkeeper_id: int
    product_id: int
    unit_price: float = Field(..., gt=0)
    current_stock: float = Field(..., ge=0)
    min_stock: Optional[float] = 10
    max_stock: Optional[float] = 100
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_category: Optional[str] = None
    product_brand: Optional[str] = None
    
    class Config:
        from_attributes = True

class InventoryUpdate(BaseModel):
    current_stock: Optional[float] = None
    min_stock: Optional[float] = None
    max_stock: Optional[float] = None
    unit_price: Optional[float] = None
    
    class Config:
        from_attributes = True

class StockAdjustment(BaseModel):
    product_id: int
    quantity: float
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True

class InventoryResponse(BaseModel):
    id: int
    shopkeeper_id: int
    product_id: int
    unit_price: float
    current_stock: float
    min_stock: float
    max_stock: float
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_category: Optional[str] = None
    product_brand: Optional[str] = None
    is_validated: bool
    validated_by: Optional[int] = None
    validated_at: Optional[datetime] = None
    is_active: bool
    last_updated: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class InventoryDetailResponse(BaseModel):
    id: int
    shopkeeper_id: int
    shopkeeper_name: str
    business_name: Optional[str]
    product_id: int
    product_name: str
    category: Optional[str]
    price: float
    stock: float
    min_stock: float
    max_stock: float
    stock_status: str
    last_updated: datetime
    
    class Config:
        from_attributes = True

class InventorySummary(BaseModel):
    shopkeeper_id: int
    shopkeeper_name: str
    total_products: int
    low_stock_items: int
    total_value: float
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True
