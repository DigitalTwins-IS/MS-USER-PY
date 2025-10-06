"""
Schemas de Tendero (Shopkeeper)
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class ShopkeeperBase(BaseModel):
    """Schema base de Tendero"""
    name: str = Field(..., min_length=3, max_length=255, description="Nombre del tendero")
    business_name: Optional[str] = Field(None, max_length=255, description="Nombre del negocio")
    address: str = Field(..., min_length=5, description="Dirección del establecimiento")
    phone: Optional[str] = Field(None, max_length=20, description="Teléfono")
    email: Optional[EmailStr] = Field(None, description="Email")
    latitude: float = Field(..., ge=-90, le=90, description="Latitud (-90 a 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitud (-180 a 180)")
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude_colombia(cls, v):
        """Valida que la latitud esté dentro del rango de Colombia"""
        if not (-5 <= v <= 13):
            raise ValueError('La latitud debe estar entre -5 y 13 (rango de Colombia)')
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude_colombia(cls, v):
        """Valida que la longitud esté dentro del rango de Colombia"""
        if not (-80 <= v <= -66):
            raise ValueError('La longitud debe estar entre -80 y -66 (rango de Colombia)')
        return v


class ShopkeeperCreate(ShopkeeperBase):
    """Schema para crear tendero"""
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Tienda La Esperanza",
                "business_name": "Supermercado La Esperanza",
                "address": "Calle 80 #12-34, Chapinero",
                "phone": "6012345678",
                "email": "laesperanza@tienda.com",
                "latitude": 4.6097100,
                "longitude": -74.0817500
            }
        }


class ShopkeeperUpdate(BaseModel):
    """Schema para actualizar tendero"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    business_name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, min_length=5)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_active: Optional[bool] = None
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude_colombia(cls, v):
        if v is not None and not (-5 <= v <= 13):
            raise ValueError('La latitud debe estar entre -5 y 13 (rango de Colombia)')
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude_colombia(cls, v):
        if v is not None and not (-80 <= v <= -66):
            raise ValueError('La longitud debe estar entre -80 y -66 (rango de Colombia)')
        return v


class ShopkeeperResponse(ShopkeeperBase):
    """Schema para respuesta de tendero"""
    id: int = Field(..., description="ID del tendero")
    is_active: bool = Field(..., description="Estado activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: Optional[datetime] = Field(None, description="Última actualización")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Tienda La Esperanza",
                "business_name": "Supermercado La Esperanza",
                "address": "Calle 80 #12-34, Chapinero",
                "phone": "6012345678",
                "email": "laesperanza@tienda.com",
                "latitude": 4.6097100,
                "longitude": -74.0817500,
                "is_active": True,
                "created_at": "2025-10-02T00:00:00Z",
                "updated_at": "2025-10-02T00:00:00Z"
            }
        }


class ShopkeeperWithSellerResponse(ShopkeeperResponse):
    """Schema de tendero con información del vendedor actual"""
    seller_id: Optional[int] = Field(None, description="ID del vendedor asignado")
    seller_name: Optional[str] = Field(None, description="Nombre del vendedor")
    seller_email: Optional[str] = Field(None, description="Email del vendedor")
    zone_name: Optional[str] = Field(None, description="Nombre de la zona")
    assigned_at: Optional[datetime] = Field(None, description="Fecha de asignación")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Tienda La Esperanza",
                "business_name": "Supermercado La Esperanza",
                "address": "Calle 80 #12-34",
                "phone": "6012345678",
                "email": "laesperanza@tienda.com",
                "latitude": 4.6097100,
                "longitude": -74.0817500,
                "is_active": True,
                "seller_id": 1,
                "seller_name": "Juan Pérez",
                "seller_email": "juan@vendedor.com",
                "zone_name": "Norte",
                "assigned_at": "2025-10-02T00:00:00Z",
                "created_at": "2025-10-02T00:00:00Z",
                "updated_at": "2025-10-02T00:00:00Z"
            }
        }

