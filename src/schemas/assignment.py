"""
Schemas de Asignación (Assignment)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AssignmentCreate(BaseModel):
    """Schema para crear asignación"""
    seller_id: int = Field(..., gt=0, description="ID del vendedor")
    shopkeeper_id: int = Field(..., gt=0, description="ID del tendero")
    notes: Optional[str] = Field(None, description="Notas sobre la asignación")
    
    class Config:
        json_schema_extra = {
            "example": {
                "seller_id": 1,
                "shopkeeper_id": 1,
                "notes": "Asignación inicial por cercanía geográfica"
            }
        }


class ReassignmentRequest(BaseModel):
    """Schema para reasignar tendero a otro vendedor"""
    shopkeeper_id: int = Field(..., gt=0, description="ID del tendero")
    new_seller_id: int = Field(..., gt=0, description="ID del nuevo vendedor")
    notes: Optional[str] = Field(None, description="Motivo de la reasignación")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shopkeeper_id": 1,
                "new_seller_id": 2,
                "notes": "Reasignación por optimización de rutas"
            }
        }


class AssignmentResponse(BaseModel):
    """Schema para respuesta de asignación"""
    id: int = Field(..., description="ID de la asignación")
    seller_id: int = Field(..., description="ID del vendedor")
    shopkeeper_id: int = Field(..., description="ID del tendero")
    assigned_at: datetime = Field(..., description="Fecha de asignación")
    unassigned_at: Optional[datetime] = Field(None, description="Fecha de desasignación")
    assigned_by: Optional[int] = Field(None, description="ID del usuario que asignó")
    unassigned_by: Optional[int] = Field(None, description="ID del usuario que desasignó")
    notes: Optional[str] = Field(None, description="Notas")
    is_active: bool = Field(..., description="Estado activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "seller_id": 1,
                "shopkeeper_id": 1,
                "assigned_at": "2025-10-02T00:00:00Z",
                "unassigned_at": None,
                "assigned_by": 1,
                "unassigned_by": None,
                "notes": "Asignación inicial",
                "is_active": True,
                "created_at": "2025-10-02T00:00:00Z"
            }
        }


class AssignmentDetailResponse(AssignmentResponse):
    """Schema detallado de asignación con nombres"""
    seller_name: str = Field(..., description="Nombre del vendedor")
    shopkeeper_name: str = Field(..., description="Nombre del tendero")
    assigned_by_name: Optional[str] = Field(None, description="Nombre de quien asignó")
    unassigned_by_name: Optional[str] = Field(None, description="Nombre de quien desasignó")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "seller_id": 1,
                "seller_name": "Juan Pérez",
                "shopkeeper_id": 1,
                "shopkeeper_name": "Tienda La Esperanza",
                "assigned_at": "2025-10-02T00:00:00Z",
                "unassigned_at": None,
                "assigned_by": 1,
                "assigned_by_name": "Admin",
                "unassigned_by": None,
                "unassigned_by_name": None,
                "notes": "Asignación inicial",
                "is_active": True,
                "created_at": "2025-10-02T00:00:00Z"
            }
        }


class AssignmentHistoryResponse(BaseModel):
    """Schema para historial de asignaciones de un tendero"""
    shopkeeper_id: int = Field(..., description="ID del tendero")
    shopkeeper_name: str = Field(..., description="Nombre del tendero")
    assignments: list[AssignmentDetailResponse] = Field(..., description="Lista de asignaciones")
    total_assignments: int = Field(..., description="Total de asignaciones")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shopkeeper_id": 1,
                "shopkeeper_name": "Tienda La Esperanza",
                "assignments": [
                    {
                        "id": 2,
                        "seller_id": 2,
                        "seller_name": "María García",
                        "shopkeeper_id": 1,
                        "shopkeeper_name": "Tienda La Esperanza",
                        "assigned_at": "2025-10-10T00:00:00Z",
                        "unassigned_at": None,
                        "is_active": True
                    },
                    {
                        "id": 1,
                        "seller_id": 1,
                        "seller_name": "Juan Pérez",
                        "shopkeeper_id": 1,
                        "shopkeeper_name": "Tienda La Esperanza",
                        "assigned_at": "2025-10-01T00:00:00Z",
                        "unassigned_at": "2025-10-10T00:00:00Z",
                        "is_active": False
                    }
                ],
                "total_assignments": 2
            }
        }


class HealthResponse(BaseModel):
    """Schema para health check"""
    status: str = Field(..., description="Estado del servicio")
    service: str = Field(..., description="Nombre del servicio")
    version: str = Field(..., description="Versión del servicio")
    database: str = Field(..., description="Estado de la base de datos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "MS-USER-PY",
                "version": "1.0.0",
                "database": "connected"
            }
        }

