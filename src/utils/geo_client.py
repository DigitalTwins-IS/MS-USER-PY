"""
Cliente HTTP para comunicarse con MS-GEO-PY
"""
import httpx
from fastapi import HTTPException, status
from ..config import settings


class GeoClient:
    """Cliente para interactuar con el microservicio MS-GEO-PY"""
    
    def __init__(self):
        self.base_url = settings.MS_GEO_URL
        self.timeout = 10.0
    
    async def verify_zone_exists(self, zone_id: int) -> dict:
        """
        Verifica que una zona existe en MS-GEO-PY
        
        Args:
            zone_id: ID de la zona a verificar
            
        Returns:
            dict: Información de la zona
            
        Raises:
            HTTPException: Si la zona no existe o hay error de conexión
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/geo/zones/{zone_id}")
                
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"La zona con ID {zone_id} no existe"
                    )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Error al comunicarse con el servicio geográfico"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo conectar con el servicio geográfico: {str(e)}"
            )
    
    async def get_zones_by_city(self, city_id: int) -> list:
        """
        Obtiene todas las zonas de una ciudad
        
        Args:
            city_id: ID de la ciudad
            
        Returns:
            list: Lista de zonas de la ciudad
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/geo/zones",
                    params={"city_id": city_id}
                )
                
                if response.status_code == 200:
                    return response.json()
                return []
                
        except httpx.RequestError:
            return []


# Instancia global del cliente
geo_client = GeoClient()

