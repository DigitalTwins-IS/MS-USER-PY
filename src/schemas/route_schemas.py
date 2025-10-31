"""
Schemas para Optimización de Rutas - HU13
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class RoutePoint(BaseModel):
    """Punto individual en la ruta"""
    shopkeeper_id: int = Field(..., description="ID del tendero")
    shopkeeper_name: str = Field(..., description="Nombre del tendero")
    business_name: Optional[str] = Field(None, description="Nombre del negocio")
    address: str = Field(..., description="Dirección")
    latitude: float = Field(..., description="Latitud")
    longitude: float = Field(..., description="Longitud")
    order: int = Field(..., description="Orden de visita (1, 2, 3...)")
    distance_from_previous_km: float = Field(..., description="Distancia desde punto anterior (km)")
    cumulative_distance_km: float = Field(..., description="Distancia acumulada (km)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shopkeeper_id": 1,
                "shopkeeper_name": "Tienda La Esperanza",
                "business_name": "Supermercado La Esperanza",
                "address": "Calle 80 #12-34",
                "latitude": 4.6097100,
                "longitude": -74.0817500,
                "order": 1,
                "distance_from_previous_km": 0.0,
                "cumulative_distance_km": 0.0
            }
        }


class RouteStatistics(BaseModel):
    """Estadísticas de la ruta"""
    total_shopkeepers: int = Field(..., description="Total de tenderos en ruta")
    total_distance_km: float = Field(..., description="Distancia total (km)")
    estimated_travel_time_hours: float = Field(..., description="Tiempo de viaje estimado (horas)")
    estimated_visit_time_hours: float = Field(..., description="Tiempo de visitas estimado (horas)")
    estimated_total_time_hours: float = Field(..., description="Tiempo total estimado (horas)")
    average_distance_between_stops_km: float = Field(..., description="Distancia promedio entre paradas (km)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_shopkeepers": 45,
                "total_distance_km": 78.5,
                "estimated_travel_time_hours": 3.14,
                "estimated_visit_time_hours": 7.5,
                "estimated_total_time_hours": 10.64,
                "average_distance_between_stops_km": 1.74
            }
        }


class OptimizedRouteResponse(BaseModel):
    """Respuesta completa de ruta optimizada"""
    seller_id: int = Field(..., description="ID del vendedor")
    seller_name: str = Field(..., description="Nombre del vendedor")
    route_points: List[RoutePoint] = Field(..., description="Puntos de la ruta ordenados")
    statistics: RouteStatistics = Field(..., description="Estadísticas de la ruta")
    algorithm_used: str = Field(..., description="Algoritmo utilizado")
    
    class Config:
        json_schema_extra = {
            "example": {
                "seller_id": 1,
                "seller_name": "Juan Pérez",
                "route_points": [
                    {
                        "shopkeeper_id": 1,
                        "shopkeeper_name": "Tienda 1",
                        "business_name": "Supermercado 1",
                        "address": "Calle 1",
                        "latitude": 4.6097,
                        "longitude": -74.0817,
                        "order": 1,
                        "distance_from_previous_km": 0.0,
                        "cumulative_distance_km": 0.0
                    }
                ],
                "statistics": {
                    "total_shopkeepers": 45,
                    "total_distance_km": 78.5,
                    "estimated_travel_time_hours": 3.14,
                    "estimated_visit_time_hours": 7.5,
                    "estimated_total_time_hours": 10.64,
                    "average_distance_between_stops_km": 1.74
                },
                "algorithm_used": "nearest_neighbor"
            }
        }


class RouteVisualizationRequest(BaseModel):
    """Solicitud para visualizar ruta en mapa"""
    seller_id: int = Field(..., description="ID del vendedor")
    start_latitude: Optional[float] = Field(None, description="Latitud inicio")
    start_longitude: Optional[float] = Field(None, description="Longitud inicio")
    show_distances: bool = Field(True, description="Mostrar distancias")
    show_order: bool = Field(True, description="Mostrar orden de visita")
    
    class Config:
        json_schema_extra = {
            "example": {
                "seller_id": 1,
                "start_latitude": 4.6097,
                "start_longitude": -74.0817,
                "show_distances": True,
                "show_order": True
            }
        }