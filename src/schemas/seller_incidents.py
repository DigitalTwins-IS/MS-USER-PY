"""
Schemas de Incidencias de Vendedor (SellerIncident)
HU16: Registrar incidencias durante visitas
"""
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from datetime import date, datetime


class SellerIncidentBase(BaseModel):
    """Schema base para incidencias"""
    seller_id: Optional[int] = Field(None, gt=0, description="ID del vendedor (opcional si se proporciona visit_id)")
    shopkeeper_id: Optional[int] = Field(None, gt=0, description="ID del tendero (opcional si se proporciona visit_id)")
    visit_id: Optional[int] = Field(None, gt=0, description="ID de la visita relacionada (opcional)")
    type: Literal["absence", "delay", "non_compliance"] = Field(..., description="Tipo de incidencia")
    description: Optional[str] = Field(None, description="Descripción detallada de la incidencia")
    incident_date: date = Field(..., description="Fecha de la incidencia")
    
    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validar que se proporcione seller_id o visit_id"""
        if not self.seller_id and not self.visit_id:
            raise ValueError("Se debe proporcionar seller_id o visit_id")
        return self
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "seller_id": 1,
                "shopkeeper_id": 5,
                "visit_id": 10,
                "type": "delay",
                "description": "El vendedor llegó 30 minutos tarde a la visita",
                "incident_date": "2025-11-15"
            }
        }


class SellerIncidentCreate(SellerIncidentBase):
    """Schema para crear una incidencia"""
    pass


class SellerIncidentUpdate(BaseModel):
    """Schema para actualizar una incidencia"""
    seller_id: Optional[int] = Field(None, gt=0, description="ID del vendedor")
    shopkeeper_id: Optional[int] = Field(None, gt=0, description="ID del tendero")
    visit_id: Optional[int] = Field(None, gt=0, description="ID de la visita relacionada")
    type: Optional[Literal["absence", "delay", "non_compliance"]] = Field(None, description="Tipo de incidencia")
    description: Optional[str] = Field(None, description="Descripción detallada de la incidencia")
    incident_date: Optional[date] = Field(None, description="Fecha de la incidencia")
    
    class Config:
        from_attributes = True


class SellerIncidentResponse(SellerIncidentBase):
    """Schema para respuesta de incidencia"""
    id: int = Field(..., description="ID de la incidencia")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Última actualización")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "seller_id": 1,
                "shopkeeper_id": 5,
                "visit_id": 10,
                "type": "delay",
                "description": "El vendedor llegó 30 minutos tarde a la visita",
                "incident_date": "2025-11-15",
                "created_at": "2025-11-15T10:30:00Z",
                "updated_at": "2025-11-15T10:30:00Z"
            }
        }


class SellerIncidentDetailResponse(SellerIncidentResponse):
    """Schema para respuesta detallada con nombres"""
    seller_name: Optional[str] = Field(None, description="Nombre del vendedor")
    shopkeeper_name: Optional[str] = Field(None, description="Nombre del tendero")
    shopkeeper_business_name: Optional[str] = Field(None, description="Nombre del negocio")
    visit_scheduled_date: Optional[datetime] = Field(None, description="Fecha programada de la visita relacionada")
    visit_status: Optional[str] = Field(None, description="Estado de la visita relacionada")
    
    class Config:
        from_attributes = True