import httpx
import asyncio
from typing import Optional, Dict, List
from datetime import datetime


class NominatimClient:
    """
    Cliente para Nominatim API
    
    CRÍTICO:
    - Máximo 1 request/segundo
    - User-Agent obligatorio con info de contacto
    - Uso educativo/investigación permitido
    
    Funcionalidades:
    - Geocoding: Dirección → Coordenadas
    - Reverse Geocoding: Coordenadas → Dirección
    - Search: Buscar lugares por nombre
    """
    
    BASE_URL = "https://nominatim.openstreetmap.org"
    
    def __init__(self, user_agent: str = "DigitalTwins-UniversityProject/1.0"):
        """
        Args:
            user_agent: OBLIGATORIO - Identificación de tu aplicación
                       Incluye email en producción
        """
        self.headers = {
            "User-Agent": user_agent,
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8"
        }
        self._last_request_time = 0
        self._request_count = 0
    
    async def _rate_limit(self):
        """
        Respeta el límite de 1 request/segundo
        
        ⚠️ NO MODIFICAR - O serás bloqueado permanentemente
        """
        current_time = datetime.now().timestamp()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < 1.0:
            sleep_time = 1.0 - time_since_last
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = datetime.now().timestamp()
        self._request_count += 1
    
    async def geocode(
        self,
        address: str,
        city: str = "Bogotá",
        country: str = "Colombia",
        limit: int = 1
    ) -> Optional[Dict]:
        """
        Convertir dirección en coordenadas
        
        Args:
            address: "Calle 72 #10-34"
            city: "Bogotá"
            country: "Colombia"
            limit: Número máximo de resultados
        
        Returns:
            {
                'latitude': 4.6533,
                'longitude': -74.0602,
                'display_name': 'Calle 72 #10-34, Chapinero, Bogotá...',
                'confidence': 0.9,
                'address': {...}
            }
        
        Example:
            >>> result = await client.geocode("Calle 72 #10-34", "Bogotá")
            >>> print(result['latitude'])
            4.6533
        """
        await self._rate_limit()
        
        full_query = f"{address}, {city}, {country}"
        
        params = {
            "q": full_query,
            "format": "json",
            "limit": limit,
            "addressdetails": 1,
            "dedupe": 1
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params=params,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    results = response.json()
                    
                    if results and len(results) > 0:
                        best_result = results[0]
                        
                        return {
                            "latitude": float(best_result["lat"]),
                            "longitude": float(best_result["lon"]),
                            "display_name": best_result.get("display_name", ""),
                            "address": best_result.get("address", {}),
                            "confidence": self._calculate_confidence(best_result),
                            "osm_type": best_result.get("osm_type", ""),
                            "place_id": best_result.get("place_id", "")
                        }
                    else:
                        print(f"⚠️ Nominatim: No resultados para '{full_query}'")
                        return None
                
                elif response.status_code == 429:
                    print("❌ Nominatim: Rate limit excedido")
                    await asyncio.sleep(60)
                    return None
                
                else:
                    print(f"❌ Nominatim error {response.status_code}: {response.text[:100]}")
                    return None
                    
        except httpx.TimeoutException:
            print(f"⏱️ Nominatim: Timeout para '{address}'")
            return None
        except Exception as e:
            print(f"❌ Nominatim error: {e}")
            return None
    
    def _calculate_confidence(self, result: Dict) -> float:
        """
        Calcular confianza del resultado (0.0 - 1.0)
        
        Nominatim no provee score directo, lo estimamos por:
        - Tipo de resultado (node > way > relation)
        - Nivel de detalle en address
        """
        osm_type = result.get("osm_type", "")
        address = result.get("address", {})
        
        # Score base por tipo de objeto
        type_scores = {
            "node": 0.9,      # Punto específico (edificio)
            "way": 0.7,       # Vía (calle)
            "relation": 0.5   # Área (barrio, zona)
        }
        score = type_scores.get(osm_type, 0.3)
        
        # Bonus por detalles
        if "house_number" in address:
            score += 0.1
        if "road" in address:
            score += 0.05
        
        return min(score, 1.0)
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 18
    ) -> Optional[Dict]:
        """
        Convertir coordenadas en dirección
        
        Args:
            latitude: 4.6533
            longitude: -74.0602
            zoom: Nivel de detalle (18=edificio, 16=calle, 10=ciudad)
        
        Returns:
            {
                'address': 'Calle 72 #10-34, Chapinero, Bogotá',
                'street': 'Calle 72',
                'house_number': '10-34',
                'neighbourhood': 'Chapinero',
                'city': 'Bogotá',
                'country': 'Colombia'
            }
        
        Example:
            >>> result = await client.reverse_geocode(4.6533, -74.0602)
            >>> print(result['address'])
            'Calle 72 #10-34, Chapinero, Bogotá, Colombia'
        """
        await self._rate_limit()
        
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "zoom": zoom,
            "addressdetails": 1
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/reverse",
                    params=params,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if "error" not in result:
                        address_parts = result.get("address", {})
                        
                        return {
                            "address": result.get("display_name", "Dirección desconocida"),
                            "street": address_parts.get("road", ""),
                            "house_number": address_parts.get("house_number", ""),
                            "neighbourhood": address_parts.get("neighbourhood", ""),
                            "suburb": address_parts.get("suburb", ""),
                            "city": address_parts.get("city", address_parts.get("town", "")),
                            "state": address_parts.get("state", ""),
                            "country": address_parts.get("country", "Colombia"),
                            "postcode": address_parts.get("postcode", "")
                        }
                    else:
                        print(f"⚠️ Nominatim: Sin dirección en {latitude}, {longitude}")
                        return None
                
                else:
                    print(f"❌ Nominatim error {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Nominatim reverse error: {e}")
            return None
    
    async def search_place(
        self,
        query: str,
        city: str = "Bogotá",
        limit: int = 5
    ) -> List[Dict]:
        """
        Buscar lugares (negocios, puntos de interés)
        
        Args:
            query: "Hospital San Ignacio"
            city: "Bogotá"
            limit: Máximo de resultados
        
        Returns:
            [
                {
                    'name': 'Hospital Universitario San Ignacio',
                    'latitude': 4.6279,
                    'longitude': -74.0648,
                    'type': 'hospital'
                },
                ...
            ]
        
        Example:
            >>> results = await client.search_place("Universidad Nacional")
            >>> print(results[0]['name'])
            'Universidad Nacional de Colombia'
        """
        await self._rate_limit()
        
        full_query = f"{query}, {city}, Colombia"
        
        params = {
            "q": full_query,
            "format": "json",
            "limit": limit,
            "addressdetails": 1
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params=params,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    results = response.json()
                    
                    places = []
                    for result in results:
                        places.append({
                            "name": result.get("display_name", "").split(",")[0],
                            "full_address": result.get("display_name", ""),
                            "latitude": float(result["lat"]),
                            "longitude": float(result["lon"]),
                            "type": result.get("type", ""),
                            "place_id": result.get("place_id", "")
                        })
                    
                    return places
                
                else:
                    print(f"❌ Nominatim search error {response.status_code}")
                    return []
                    
        except Exception as e:
            print(f"❌ Nominatim search error: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas de uso"""
        return {
            "total_requests": self._request_count,
            "rate_limit": "1 request/segundo",
            "service": "Nominatim OSM"
        }


# Instancia global
nominatim_client = NominatimClient(
    user_agent="DigitalTwins-IS/1.0 (University Project; Contact: vale@university.edu)"
)
