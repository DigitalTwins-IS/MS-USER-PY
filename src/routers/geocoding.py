"""
Router de Geocodificación
HU18: Integración con Nominatim para convertir direcciones ↔ coordenadas
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..models import get_db
from ..schemas import (
    GeocodeRequest,
    GeocodeResponse,
    ReverseGeocodeResponse,
    PlaceSearchResponse
)
from ..clients.nominatim_client import nominatim_client
from ..utils import get_current_user

router = APIRouter()


@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_address(
    request: GeocodeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    HU14: Convertir dirección en coordenadas
    
    Usa Nominatim (OpenStreetMap) - Gratis, sin API key
    Incluye caché en base de datos para reducir llamadas
    
    Example:
        POST /geocode
        {
            "address": "Calle 72 #10-34",
            "city": "Bogotá",
            "use_cache": true
        }
    
    Returns:
        {
            "address": "Calle 72 #10-34",
            "coordinates": {"latitude": 4.6533, "longitude": -74.0602},
            "confidence": 0.9,
            "from_cache": false
        }
    """
    result = await nominatim_client.geocode(
        address=request.address,
        city=request.city,
        country=request.country,
        db=db if request.use_cache else None,
        use_cache=request.use_cache
    )
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró la dirección: {request.address}, {request.city}"
        )
    
    return GeocodeResponse(
        address=request.address,
        city=request.city,
        coordinates={
            "latitude": result["latitude"],
            "longitude": result["longitude"]
        },
        full_address=result["display_name"],
        confidence=result["confidence"],
        from_cache=result.get("from_cache", False),
        details=result.get("address_parts", {})
    )


@router.get("/geocode/simple", response_model=GeocodeResponse)
async def geocode_address_simple(
    address: str = Query(..., min_length=3, description="Dirección a buscar"),
    city: str = Query("Bogotá", description="Ciudad"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    HU14: Geocodificación simple con query params (más fácil para frontend)
    
    Example:
        GET /geocode/simple?address=Calle 72 #10-34&city=Bogotá
    """
    result = await nominatim_client.geocode(
        address=address,
        city=city,
        db=db,
        use_cache=True
    )
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró la dirección: {address}, {city}"
        )
    
    return GeocodeResponse(
        address=address,
        city=city,
        coordinates={
            "latitude": result["latitude"],
            "longitude": result["longitude"]
        },
        full_address=result["display_name"],
        confidence=result["confidence"],
        from_cache=result.get("from_cache", False),
        details=result.get("address_parts", {})
    )


@router.get("/reverse-geocode", response_model=ReverseGeocodeResponse)
async def reverse_geocode_location(
    latitude: float = Query(..., ge=-90, le=90, description="Latitud"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitud"),
    zoom: int = Query(18, ge=1, le=18, description="Nivel de detalle (18=edificio, 10=ciudad)"),
    current_user: dict = Depends(get_current_user)
):
    """
    HU14: Convertir coordenadas en dirección
    
    Example:
        GET /reverse-geocode?latitude=4.6533&longitude=-74.0602
    
    Returns:
        {
            "coordinates": {"latitude": 4.6533, "longitude": -74.0602},
            "address": "Calle 72 #10-34, Chapinero, Bogotá",
            "street": "Calle 72",
            "neighbourhood": "Chapinero"
        }
    """
    result = await nominatim_client.reverse_geocode(
        latitude=latitude,
        longitude=longitude,
        zoom=zoom
    )
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró dirección en: {latitude}, {longitude}"
        )
    
    return ReverseGeocodeResponse(
        coordinates={
            "latitude": latitude,
            "longitude": longitude
        },
        **result
    )


@router.get("/search-place", response_model=PlaceSearchResponse)
async def search_nearby_place(
    query: str = Query(..., min_length=3, description="Nombre del lugar"),
    city: str = Query("Bogotá", description="Ciudad"),
    limit: int = Query(5, ge=1, le=10, description="Número máximo de resultados"),
    current_user: dict = Depends(get_current_user)
):
    """
    HU14: Buscar lugares (hospitales, universidades, puntos de interés)
    
    Example:
        GET /search-place?query=Hospital San Ignacio&city=Bogotá&limit=5
    
    Returns:
        {
            "query": "Hospital San Ignacio",
            "city": "Bogotá",
            "total_results": 2,
            "places": [...]
        }
    """
    from ..clients.nominatim_client import nominatim_client
    
    # Reutilizar método geocode para búsqueda
    results = []
    result = await nominatim_client.geocode(query, city)
    
    if result:
        results.append({
            "name": query,
            "full_address": result["display_name"],
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "type": result.get("osm_type", ""),
            "place_id": str(result.get("place_id", ""))
        })
    
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron lugares: {query} en {city}"
        )
    
    return PlaceSearchResponse(
        query=query,
        city=city,
        total_results=len(results),
        places=results
    )


@router.get("/cache/stats")
async def get_geocoding_cache_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    HU14: Estadísticas del caché de geocodificación
    
    Returns:
        {
            "total_entries": 150,
            "most_used": [...],
            "cache_size_mb": 0.5
        }
    """
    from ..models.geocoding_cache import GeocodingCache
    from sqlalchemy import func
    
    total = db.query(func.count(GeocodingCache.id)).scalar()
    
    most_used = db.query(
        GeocodingCache.address,
        GeocodingCache.city,
        GeocodingCache.usage_count
    ).order_by(
        GeocodingCache.usage_count.desc()
    ).limit(10).all()
    
    return {
        "total_entries": total,
        "most_used": [
            {
                "address": addr,
                "city": city,
                "usage_count": count
            }
            for addr, city, count in most_used
        ]
    }


@router.delete("/cache/clear")
async def clear_geocoding_cache(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    HU14: Limpiar caché de geocodificación
    
    Útil para mantenimiento o cuando los datos están obsoletos
    """
    from ..models.geocoding_cache import GeocodingCache
    
    deleted = db.query(GeocodingCache).delete()
    db.commit()
    
    return {
        "message": "Caché limpiado exitosamente",
        "deleted_entries": deleted
    }