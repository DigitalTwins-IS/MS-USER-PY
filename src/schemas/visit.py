"""
Schemas de Visita (Visit)
HU21: Agendar visitas basadas en inventario
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class VisitCreate(BaseModel):
    """Schema para crear una visita"""
    shopkeeper_id: int = Field(..., gt=0, description="ID del tendero a visitar")
    scheduled_date: datetime = Field(..., description="Fecha y hora programada de la visita")
    reason: Optional[str] = Field("reabastecimiento", max_length=255, description="Motivo de la visita")
    notes: Optional[str] = Field(None, description="Notas adicionales sobre la visita")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "shopkeeper_id": 1,
                "scheduled_date": "2025-11-15T10:00:00Z",
                "reason": "reabastecimiento",
                "notes": "Productos con bajo stock: Arroz, Aceite, Azúcar"
            }
        }


class VisitUpdate(BaseModel):
    """Schema para actualizar una visita"""
    scheduled_date: Optional[datetime] = Field(None, description="Nueva fecha y hora programada")
    reason: Optional[str] = Field(None, max_length=255, description="Nuevo motivo de la visita")
    notes: Optional[str] = Field(None, description="Nuevas notas adicionales")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "scheduled_date": "2025-11-16T14:00:00Z",
                "reason": "reabastecimiento urgente",
                "notes": "Actualización: Agregar productos lácteos"
            }
        }


class VisitCancelRequest(BaseModel):
    """Schema para cancelar una visita"""
    cancelled_reason: Optional[str] = Field(None, description="Razón de la cancelación")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "cancelled_reason": "Tendero no disponible en esa fecha"
            }
        }


class VisitResponse(BaseModel):
    """Schema para respuesta de visita"""
    id: int = Field(..., description="ID de la visita")
    seller_id: int = Field(..., description="ID del vendedor")
    shopkeeper_id: int = Field(..., description="ID del tendero")
    scheduled_date: datetime = Field(..., description="Fecha y hora programada")
    status: str = Field(..., description="Estado de la visita (pending, completed, cancelled)")
    reason: Optional[str] = Field(None, description="Motivo de la visita")
    notes: Optional[str] = Field(None, description="Notas adicionales")
    completed_at: Optional[datetime] = Field(None, description="Fecha de completado")
    cancelled_at: Optional[datetime] = Field(None, description="Fecha de cancelación")
    cancelled_reason: Optional[str] = Field(None, description="Razón de cancelación")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Última actualización")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "seller_id": 1,
                "shopkeeper_id": 1,
                "scheduled_date": "2025-11-15T10:00:00Z",
                "status": "pending",
                "reason": "reabastecimiento",
                "notes": "Productos con bajo stock: Arroz, Aceite, Azúcar",
                "completed_at": None,
                "cancelled_at": None,
                "cancelled_reason": None,
                "created_at": "2025-11-10T08:00:00Z",
                "updated_at": "2025-11-10T08:00:00Z"
            }
        }


class VisitDetailResponse(VisitResponse):
    """Schema para respuesta detallada de visita con información del tendero"""
    shopkeeper_name: str = Field(..., description="Nombre del tendero")
    shopkeeper_business_name: Optional[str] = Field(None, description="Nombre del negocio")
    shopkeeper_address: str = Field(..., description="Dirección del tendero")
    shopkeeper_phone: Optional[str] = Field(None, description="Teléfono del tendero")
    shopkeeper_email: Optional[str] = Field(None, description="Email del tendero")
    seller_name: str = Field(..., description="Nombre del vendedor")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "seller_id": 1,
                "seller_name": "Juan Pérez",
                "shopkeeper_id": 1,
                "shopkeeper_name": "María González",
                "shopkeeper_business_name": "Tienda El Buen Sabor",
                "shopkeeper_address": "Calle 80 #12-34, Bogotá",
                "shopkeeper_phone": "3001234567",
                "shopkeeper_email": "maria@tienda.com",
                "scheduled_date": "2025-11-15T10:00:00Z",
                "status": "pending",
                "reason": "reabastecimiento",
                "notes": "Productos con bajo stock: Arroz, Aceite, Azúcar",
                "completed_at": None,
                "cancelled_at": None,
                "cancelled_reason": None,
                "created_at": "2025-11-10T08:00:00Z",
                "updated_at": "2025-11-10T08:00:00Z"
            }
        }


class ShopkeeperLowStockResponse(BaseModel):
    """Schema para tenderos con bajo stock"""
    shopkeeper_id: int = Field(..., description="ID del tendero")
    shopkeeper_name: str = Field(..., description="Nombre del tendero")
    shopkeeper_business_name: Optional[str] = Field(None, description="Nombre del negocio")
    shopkeeper_address: str = Field(..., description="Dirección del tendero")
    shopkeeper_phone: Optional[str] = Field(None, description="Teléfono del tendero")
    shopkeeper_email: Optional[str] = Field(None, description="Email del tendero")
    low_stock_count: int = Field(..., description="Cantidad de productos con bajo stock")
    total_products: int = Field(..., description="Total de productos en inventario")
    last_updated: Optional[datetime] = Field(None, description="Última actualización del inventario")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "shopkeeper_id": 1,
                "shopkeeper_name": "María González",
                "shopkeeper_business_name": "Tienda El Buen Sabor",
                "shopkeeper_address": "Calle 80 #12-34, Bogotá",
                "shopkeeper_phone": "3001234567",
                "shopkeeper_email": "maria@tienda.com",
                "low_stock_count": 5,
                "total_products": 20,
                "last_updated": "2025-11-10T08:00:00Z"
            }
        }


class VisitListResponse(BaseModel):
    """Schema para lista de visitas con filtros"""
    visits: List[VisitDetailResponse] = Field(..., description="Lista de visitas")
    total: int = Field(..., description="Total de visitas")
    pending: int = Field(..., description="Cantidad de visitas pendientes")
    completed: int = Field(..., description="Cantidad de visitas completadas")
    cancelled: int = Field(..., description="Cantidad de visitas canceladas")
    
    class Config:
        from_attributes = True

