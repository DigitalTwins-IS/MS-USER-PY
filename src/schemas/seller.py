"""
Schemas de Vendedor (Seller)
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class SellerBase(BaseModel):
    """Schema base de Vendedor"""
    name: str = Field(..., min_length=3, max_length=255, description="Nombre del vendedor")
    email: EmailStr = Field(..., description="Email del vendedor")
    phone: Optional[str] = Field(None, max_length=20, description="Teléfono")
    address: Optional[str] = Field(None, description="Dirección")
    zone_id: int = Field(..., gt=0, description="ID de la zona asignada")


class SellerCreate(SellerBase):
    """Schema para crear vendedor"""
    user_id: Optional[int] = Field(None, description="ID del usuario del sistema (opcional, si no se proporciona se crea automáticamente)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Juan Pérez",
                "email": "juan.perez@vendedor.com",
                "phone": "3001234567",
                "address": "Calle 80 #12-34, Bogotá",
                "zone_id": 1
            }
        }


class SellerUpdate(BaseModel):
    """Schema para actualizar vendedor"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    zone_id: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None


class SellerResponse(SellerBase):
    """Schema para respuesta de vendedor"""
    id: int = Field(..., description="ID del vendedor")
    user_id: Optional[int] = Field(None, description="ID del usuario")
    is_active: bool = Field(..., description="Estado activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: Optional[datetime] = Field(None, description="Última actualización")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Juan Pérez",
                "email": "juan.perez@vendedor.com",
                "phone": "3001234567",
                "address": "Calle 80 #12-34, Bogotá",
                "zone_id": 1,
                "user_id": 1,
                "is_active": True,
                "created_at": "2025-10-02T00:00:00Z",
                "updated_at": "2025-10-02T00:00:00Z"
            }
        }


class SellerWithZoneResponse(SellerResponse):
    """Schema de vendedor con información de zona"""
    zone_name: str = Field(..., description="Nombre de la zona")
    zone_color: str = Field(..., description="Color de la zona")
    city_name: str = Field(..., description="Nombre de la ciudad")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Juan Pérez",
                "email": "juan.perez@vendedor.com",
                "phone": "3001234567",
                "address": "Calle 80 #12-34",
                "zone_id": 1,
                "zone_name": "Norte",
                "zone_color": "#E74C3C",
                "city_name": "Bogotá",
                "user_id": 1,
                "is_active": True,
                "created_at": "2025-10-02T00:00:00Z",
                "updated_at": "2025-10-02T00:00:00Z"
            }
        }


class SellerWithShopkeepersResponse(SellerResponse):
    """Schema de vendedor con sus tenderos asignados"""
    total_shopkeepers: int = Field(..., description="Total de tenderos asignados")
    zone_name: str = Field(..., description="Nombre de la zona")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Juan Pérez",
                "email": "juan.perez@vendedor.com",
                "phone": "3001234567",
                "address": "Calle 80 #12-34",
                "zone_id": 1,
                "zone_name": "Norte",
                "user_id": 1,
                "is_active": True,
                "total_shopkeepers": 15,
                "created_at": "2025-10-02T00:00:00Z",
                "updated_at": "2025-10-02T00:00:00Z"
            }
        }


class ChangeZoneRequest(BaseModel):
    """Schema para cambiar zona de vendedor"""
    new_zone_id: int = Field(..., gt=0, description="ID de la nueva zona")
    notes: Optional[str] = Field(None, description="Notas sobre el cambio")
    
    class Config:
        json_schema_extra = {
            "example": {
                "new_zone_id": 2,
                "notes": "Cambio por redistribución territorial"
            }
        }

