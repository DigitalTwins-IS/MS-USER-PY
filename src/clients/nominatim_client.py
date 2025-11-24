"""
Cliente Nominatim - OpenStreetMap Geocoding
100% Gratis, sin API key, sin registro
Rate limit: 1 request/segundo
"""
import httpx
import asyncio
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import get_db


class NominatimClient:
    """
    Cliente para Nominatim (OSM Geocoding)
    
    Docs: https://nominatim.org/release-docs/latest/api/
    
    IMPORTANTE:
    - SIEMPRE incluir User-Agent válido
    - Máximo 1 request/segundo
    - Uso educativo permitido
    """
    
    BASE_URL = "https://nominatim.openstreetmap.org"
    
    def __init__(self, user_agent: str = "DigitalTwins-University/1.0 (Educational Project)"):
        self.headers = {
            "User-Agent": user_agent,
            "Accept-Language": "es-CO,es;q=0.9",
            "Accept": "application/json"
        }
        self._last_request = 0
        self._cache_enabled = True
    
    async def _rate_limit(self):
        """Respeta límite de 1 req/segundo"""
        now = datetime.now().timestamp()
        elapsed = now - self._last_request
        
        if elapsed < 1.0:
            wait_time = 1.0 - elapsed
            print(f"⏳ Rate limit: esperando {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        self._last_request = datetime.now().timestamp()
    
    async def _get_from_cache(self, address: str, city: str, db: Session) -> Optional[Dict]:
        """Busca en caché de base de datos"""
        if not self._cache_enabled:
            return None
        
        try:
            from ..models.geocoding_cache import GeocodingCache
            
            cached = db.query(GeocodingCache).filter(
                GeocodingCache.address == address,
                GeocodingCache.city == city
            ).first()
            
            if cached:
                print(f"✅ Geocoding CACHE HIT: {address}, {city}")
                # Actualizar contador de uso
                cached.last_used = datetime.now()
                cached.usage_count += 1
                db.commit()
                
                return {
                    "latitude": float(cached.latitude),
                    "longitude": float(cached.longitude),
                    "display_name": cached.display_name,
                    "confidence": float(cached.confidence) if cached.confidence else 0.8,
                    "from_cache": True
                }
            
            return None
        except Exception as e:
            print(f"⚠️ Error leyendo caché: {e}")
            return None
    
    async def _save_to_cache(self, address: str, city: str, result: Dict, db: Session):
        """Guarda resultado en caché"""
        try:
            from ..models.geocoding_cache import GeocodingCache
            
            cached = GeocodingCache(
                address=address,
                city=city,
                country="Colombia",
                latitude=result["latitude"],
                longitude=result["longitude"],
                display_name=result.get("display_name", ""),
                confidence=result.get("confidence", 0.8),
                provider="nominatim"
            )
            
            db.add(cached)
            db.commit()
            print(f"💾 Geocoding guardado en caché: {address}, {city}")
            
        except Exception as e:
            print(f"⚠️ Error guardando en caché: {e}")
            db.rollback()
    
    async def geocode(
        self,
        address: str,
        city: str = "Bogotá",
        country: str = "Colombia",
        db: Session = None,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Convierte dirección en coordenadas
        
        Args:
            address: "Calle 72 #10-34"
            city: "Bogotá"
            country: "Colombia"
            db: Sesión de base de datos (para caché)
            use_cache: Usar caché si está disponible
        
        Returns:
            {
                'latitude': 4.6533,
                'longitude': -74.0602,
                'display_name': 'Calle 72 #10-34, Bogotá...',
                'confidence': 0.9,
                'from_cache': False
            }
        """
        # Intentar obtener del caché
        if use_cache and db:
            cached = await self._get_from_cache(address, city, db)
            if cached:
                return cached
        
        # Rate limiting
        await self._rate_limit()
        
        # Construir query
        full_query = f"{address}, {city}, {country}"
        
        params = {
            "q": full_query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
            "dedupe": 1
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params=params,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    results = response.json()
                    
                    if results and len(results) > 0:
                        best = results[0]
                        
                        result = {
                            "latitude": float(best["lat"]),
                            "longitude": float(best["lon"]),
                            "display_name": best.get("display_name", ""),
                            "address_parts": best.get("address", {}),
                            "confidence": self._calc_confidence(best),
                            "osm_type": best.get("osm_type", ""),
                            "place_id": best.get("place_id", ""),
                            "from_cache": False
                        }
                        
                        # Guardar en caché
                        if db:
                            await self._save_to_cache(address, city, result, db)
                        
                        return result
                    
                    print(f"❌ No se encontró: {full_query}")
                    return None
                
                elif response.status_code == 429:
                    print("❌ Rate limit excedido - Esperando 60s")
                    await asyncio.sleep(60)
                    return None
                
                else:
                    print(f"❌ Error {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error geocoding: {e}")
            return None
    
    def _calc_confidence(self, result: Dict) -> float:
        """Calcula score de confianza (0.0 - 1.0)"""
        osm_type = result.get("osm_type", "")
        address = result.get("address", {})
        
        type_scores = {
            "node": 0.9,
            "way": 0.7,
            "relation": 0.5
        }
        score = type_scores.get(osm_type, 0.3)
        
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
        Convierte coordenadas en dirección
        
        Args:
            latitude: 4.6533
            longitude: -74.0602
            zoom: Nivel de detalle (18=edificio, 10=ciudad)
        
        Returns:
            {
                'address': 'Calle 72 #10-34, Chapinero, Bogotá',
                'street': 'Calle 72',
                'neighbourhood': 'Chapinero',
                'city': 'Bogotá'
            }
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
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/reverse",
                    params=params,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if "error" not in result:
                        addr = result.get("address", {})
                        
                        return {
                            "address": result.get("display_name", ""),
                            "street": addr.get("road", ""),
                            "house_number": addr.get("house_number", ""),
                            "neighbourhood": addr.get("neighbourhood", addr.get("suburb", "")),
                            "city": addr.get("city", addr.get("town", "")),
                            "state": addr.get("state", ""),
                            "country": addr.get("country", "Colombia"),
                            "postcode": addr.get("postcode", "")
                        }
                    
                    return None
                
                return None
                
        except Exception as e:
            print(f"❌ Error reverse geocoding: {e}")
            return None


# Instancia global
nominatim_client = NominatimClient()