"""
Schemas para servicios de geocodificación
HU18: Integración con Nominatim
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class GeocodeRequest(BaseModel):
    """Solicitud de geocodificación"""
    address: str = Field(..., min_length=3, description="Dirección a buscar")
    city: str = Field("Bogotá", description="Ciudad")
    country: str = Field("Colombia", description="País")
    use_cache: bool = Field(True, description="Usar caché si está disponible")
    
    class Config:
        json_schema_extra = {
            "example": {
                "address": "Calle 72 #10-34",
                "city": "Bogotá",
                "country": "Colombia",
                "use_cache": True
            }
        }


class GeocodeResponse(BaseModel):
    """Respuesta de geocodificación"""
    address: str = Field(..., description="Dirección buscada")
    city: str
    coordinates: Dict[str, float] = Field(..., description="{'latitude': ..., 'longitude': ...}")
    full_address: str = Field(..., description="Dirección completa formateada")
    confidence: float = Field(..., ge=0, le=1, description="Confianza del resultado (0-1)")
    from_cache: bool = Field(False, description="Si el resultado viene del caché")
    details: Optional[Dict] = Field(None, description="Detalles adicionales de la dirección")
    
    class Config:
        json_schema_extra = {
            "example": {
                "address": "Calle 72 #10-34",
                "city": "Bogotá",
                "coordinates": {
                    "latitude": 4.6533,
                    "longitude": -74.0602
                },
                "full_address": "Calle 72 #10-34, Chapinero, Bogotá, Colombia",
                "confidence": 0.9,
                "from_cache": False,
                "details": {
                    "neighbourhood": "Chapinero",
                    "postcode": "110221"
                }
            }
        }


class ReverseGeocodeResponse(BaseModel):
    """Respuesta de geocodificación inversa"""
    coordinates: Dict[str, float]
    address: str = Field(..., description="Dirección completa")
    street: str = Field("", description="Nombre de la calle")
    house_number: str = Field("", description="Número de casa")
    neighbourhood: str = Field("", description="Barrio")
    city: str = Field("", description="Ciudad")
    state: str = Field("", description="Departamento/Estado")
    country: str = Field("Colombia", description="País")
    postcode: str = Field("", description="Código postal")
    
    class Config:
        json_schema_extra = {
            "example": {
                "coordinates": {"latitude": 4.6533, "longitude": -74.0602},
                "address": "Calle 72 #10-34, Chapinero, Bogotá, Colombia",
                "street": "Calle 72",
                "house_number": "10-34",
                "neighbourhood": "Chapinero",
                "city": "Bogotá",
                "state": "Cundinamarca",
                "country": "Colombia",
                "postcode": "110221"
            }
        }


class PlaceSearchResult(BaseModel):
    """Resultado de búsqueda de lugar"""
    name: str
    full_address: str
    latitude: float
    longitude: float
    type: str = Field("", description="Tipo de lugar (hospital, university, etc)")
    place_id: str = Field("", description="ID del lugar en OSM")


class PlaceSearchResponse(BaseModel):
    """Respuesta de búsqueda de lugares"""
    query: str
    city: str
    total_results: int
    places: List[PlaceSearchResult]
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Hospital San Ignacio",
                "city": "Bogotá",
                "total_results": 2,
                "places": [
                    {
                        "name": "Hospital Universitario San Ignacio",
                        "full_address": "Carrera 7 #40-62, Bogotá",
                        "latitude": 4.6279,
                        "longitude": -74.0648,
                        "type": "hospital",
                        "place_id": "123456"
                    }
                ]
            }
        }