"""
Cliente para OpenRouteService API
Optimización de rutas y cálculo de distancias reales

Docs: https://openrouteservice.org/dev/#/api-docs
Límite gratis: 2,000 requests/día, 40 req/minuto
"""
import httpx
from typing import List, Dict, Optional


class OpenRouteServiceClient:
    """
    Cliente para OpenRouteService
    
    Servicios:
    - Directions: Rutas optimizadas entre puntos
    - Matrix: Matriz de distancias entre múltiples puntos
    - Isochrones: Áreas alcanzables en X tiempo
    
    Límites:
    - 2,000 requests/día
    - 40 requests/minuto
    - Máximo 50 puntos en matriz
    """
    
    BASE_URL = "https://api.openrouteservice.org"
    
    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: API key de OpenRouteService
                    Obtener en: https://openrouteservice.org/dev/#/signup
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self._request_count = 0
    
    async def get_route(
        self,
        coordinates: List[List[float]],
        profile: str = "driving-car"
    ) -> Optional[Dict]:
        """
        Obtiene ruta optimizada entre múltiples puntos
        
        Args:
            coordinates: Lista de [longitude, latitude]
                        ⚠️ ORDEN: [lon, lat] (al revés de lo común)
            profile: 'driving-car', 'driving-hgv', 'cycling-regular', 'foot-walking'
        
        Returns:
            {
                'distance_km': 15.3,
                'duration_minutes': 28.5,
                'geometry': {...},  # Polyline para mapa
                'steps': [...]      # Instrucciones turn-by-turn
            }
        
        Example:
            >>> coords = [[-74.0817, 4.6097], [-74.0723, 4.6533]]
            >>> route = await client.get_route(coords)
            >>> print(f"{route['distance_km']} km, {route['duration_minutes']} min")
        """
        if not self.api_key:
            print("❌ OpenRouteService: API key no configurada")
            return None
        
        url = f"{self.BASE_URL}/v2/directions/{profile}"
        
        payload = {
            "coordinates": coordinates,
            "format": "json",
            "instructions": True,
            "elevation": False,
            "geometry": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self._request_count += 1
                    
                    if "routes" in data and len(data["routes"]) > 0:
                        route = data["routes"][0]
                        summary = route["summary"]
                        
                        return {
                            "distance_km": round(summary["distance"] / 1000, 2),
                            "duration_minutes": round(summary["duration"] / 60, 1),
                            "geometry": route.get("geometry", None),
                            "steps": route.get("segments", []),
                            "bbox": route.get("bbox", [])
                        }
                    else:
                        print("⚠️ OpenRouteService: Sin rutas en respuesta")
                        return None
                
                elif response.status_code == 401:
                    print("❌ OpenRouteService: API key inválida")
                    return None
                
                elif response.status_code == 429:
                    print("❌ OpenRouteService: Límite de requests excedido")
                    return None
                
                else:
                    print(f"❌ OpenRouteService error {response.status_code}: {response.text[:200]}")
                    return None
                    
        except httpx.TimeoutException:
            print("⏱️ OpenRouteService: Timeout")
            return None
        except Exception as e:
            print(f"❌ OpenRouteService error: {e}")
            return None
    
    async def get_distance_matrix(
        self,
        locations: List[List[float]],
        profile: str = "driving-car"
    ) -> Optional[Dict]:
        """
        Calcula matriz de distancias entre múltiples puntos
        
        ⚠️ Límite: 50 puntos máximo
        
        Args:
            locations: Lista de [longitude, latitude]
            profile: Perfil de transporte
        
        Returns:
            {
                'distances_km': [[0, 1.5, 2.3], [1.5, 0, 0.8], ...],
                'durations_min': [[0, 3, 4], [3, 0, 2], ...]
            }
        
        Example:
            >>> locs = [[-74.08, 4.61], [-74.07, 4.65], [-74.09, 4.62]]
            >>> matrix = await client.get_distance_matrix(locs)
            >>> print(matrix['distances_km'][0][1])  # Distancia 0→1
            1.5
        """
        if not self.api_key:
            print("❌ OpenRouteService: API key no configurada")
            return None
        
        if len(locations) > 50:
            print(f"⚠️ OpenRouteService: Máximo 50 puntos (tienes {len(locations)})")
            return None
        
        url = f"{self.BASE_URL}/v2/matrix/{profile}"
        
        payload = {
            "locations": locations,
            "metrics": ["distance", "duration"]
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self._request_count += 1
                    
                    # Convertir a km y minutos
                    distances_km = [
                        [round(d / 1000, 2) for d in row]
                        for row in data.get("distances", [])
                    ]
                    
                    durations_min = [
                        [round(t / 60, 1) for t in row]
                        for row in data.get("durations", [])
                    ]
                    
                    return {
                        "distances_km": distances_km,
                        "durations_min": durations_min
                    }
                
                else:
                    print(f"❌ OpenRouteService matrix error {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ OpenRouteService matrix error: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas de uso"""
        return {
            "total_requests": self._request_count,
            "daily_limit": 2000,
            "minute_limit": 40,
            "service": "OpenRouteService"
        }


# Instancia global (se inicializa con key de settings)
openroute_client = None

def init_openroute_client(api_key: str):
    """Inicializar cliente con API key"""
    global openroute_client
    openroute_client = OpenRouteServiceClient(api_key)
    return openroute_client
