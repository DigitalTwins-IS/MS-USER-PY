"""
Schemas para sistema de tracking en tiempo real
HU18: Rastreo de Pedido en Mapa con WebSockets
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime


class SellerLocationCreate(BaseModel):
    """Schema para crear nueva ubicación de vendedor"""
    seller_id: int = Field(..., description="ID del vendedor")
    latitude: float = Field(..., ge=-90, le=90, description="Latitud")
    longitude: float = Field(..., ge=-180, le=180, description="Longitud")
    accuracy: Optional[float] = Field(None, ge=0, description="Precisión GPS en metros")
    speed: Optional[float] = Field(None, ge=0, description="Velocidad en km/h")
    status: Literal["active", "inactive", "offline"] = Field("active", description="Estado del vendedor")
    battery_level: Optional[int] = Field(None, ge=0, le=100, description="Nivel de batería")
    
    class Config:
        json_schema_extra = {
            "example": {
                "seller_id": 1,
                "latitude": 4.6097,
                "longitude": -74.0817,
                "accuracy": 10.5,
                "speed": 25.0,
                "heading": 180.0,
                "status": "active",
                "battery_level": 85
            }
        }


class SellerLocationResponse(BaseModel):
    """Schema para respuesta de ubicación"""
    id: int
    seller_id: int
    seller_name: str
    latitude: float
    longitude: float
    accuracy: Optional[float]
    speed: Optional[float]
    heading: Optional[float]
    status: str
    battery_level: Optional[int]
    timestamp: datetime
    zone_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class TrackingInfo(BaseModel):
    """Información adicional de tracking"""
    distance_to_shopkeeper_km: float = Field(..., description="Distancia al tendero en km")
    estimated_arrival_minutes: int = Field(..., description="Tiempo estimado de llegada en minutos")
    last_update: datetime = Field(..., description="Última actualización")
    is_moving: bool = Field(..., description="Indica si el vendedor está en movimiento")


class WebSocketMessage(BaseModel):
    """Mensaje WebSocket para cliente"""
    type: Literal["location_update", "connection_status", "error"]
    location: Optional[SellerLocationResponse] = None
    tracking: Optional[TrackingInfo] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "location_update",
                "location": {
                    "id": 1,
                    "seller_id": 1,
                    "seller_name": "Juan Pérez",
                    "latitude": 4.6097,
                    "longitude": -74.0817,
                    "speed": 25.0,
                    "status": "active",
                    "battery_level": 85,
                    "timestamp": "2024-01-15T10:30:00Z"
                },
                "tracking": {
                    "distance_to_shopkeeper_km": 2.5,
                    "estimated_arrival_minutes": 8,
                    "last_update": "2024-01-15T10:30:00Z",
                    "is_moving": True
                }
            }
        }