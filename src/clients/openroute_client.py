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
    
    def _encode_polyline(self, coordinates: List[List[float]]) -> str:
        """
        Codifica coordenadas GeoJSON a polyline (algoritmo de Google).
        Coordinates vienen en formato [lon, lat] de GeoJSON.
        """
        if not coordinates:
            return ""
        
        # DEBUG: Ver primeras coordenadas
        if len(coordinates) > 0:
            print(f"🔍 DEBUG ENCODE: Primera coordenada GeoJSON: {coordinates[0]}")
            print(f"🔍 DEBUG ENCODE: Segunda coordenada GeoJSON: {coordinates[1] if len(coordinates) > 1 else 'N/A'}")
        
        def encode_value(value):
            # value is already the delta in 1e5 scale, just encode it
            value = ~(value << 1) if value < 0 else (value << 1)
            chunks = []
            while value >= 0x20:
                chunks.append((0x20 | (value & 0x1f)) + 63)
                value >>= 5
            chunks.append(value + 63)
            return ''.join(chr(chunk) for chunk in chunks)
        
        encoded = []
        prev_lat = 0
        prev_lng = 0
        
        for coord in coordinates:
            # GeoJSON format is [longitude, latitude]
            lng, lat = coord[0], coord[1]
            
            dlat = int(round(lat * 1e5)) - prev_lat
            dlng = int(round(lng * 1e5)) - prev_lng
            
            # Polyline encoding standard: encode latitude first, then longitude
            encoded.append(encode_value(dlat))
            encoded.append(encode_value(dlng))
            
            prev_lat = int(round(lat * 1e5))
            prev_lng = int(round(lng * 1e5))
        
        # DEBUG: Ver primeros valores codificados
        print(f"🔍 DEBUG ENCODE: Primer prev_lat final: {prev_lat}, primer prev_lng final: {prev_lng}")
        
        return ''.join(encoded)
    
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
                'geometry': "encoded_polyline_string",  # Polyline para mapa
                'bbox': [...]
            }
        
        Example:
            >>> coords = [[-74.0817, 4.6097], [-74.0723, 4.6533]]
            >>> route = await client.get_route(coords)
            >>> print(f"{route['distance_km']} km, {route['duration_minutes']} min")
        """
        if not self.api_key:
            print("❌ OpenRouteService: API key no configurada")
            return None
        
        # Use GeoJSON endpoint to get full geometry
        url = f"{self.BASE_URL}/v2/directions/{profile}/geojson"
        
        payload = {
            "coordinates": coordinates,
            "elevation": False,
            "instructions": False,
            "preference": "fastest",  # Considera tráfico y rutas más rápidas
            "units": "m"
        }
        
        # Remove Accept header to avoid 406 error
        request_headers = self.headers.copy()
        if "Accept" in request_headers:
            del request_headers["Accept"]
        
        try:
            print(f"🔍 Llamando OpenRouteService Directions API: {len(coordinates)} puntos")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=request_headers)
                
                print(f"🔍 OpenRouteService response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    self._request_count += 1
                    
                    if "features" in data and len(data["features"]) > 0:
                        feature = data["features"][0]
                        geometry = feature.get("geometry", {})
                        properties = feature.get("properties", {})
                        summary = properties.get("summary", {})
                        
                        # Extract GeoJSON coordinates and encode to polyline
                        geojson_coords = geometry.get("coordinates", [])
                        encoded_geometry = self._encode_polyline(geojson_coords)
                        
                        print(f"✅ Ruta obtenida: {summary.get('distance', 0)/1000:.2f} km")
                        print(f"   📍 {len(geojson_coords)} puntos de geometría")
                        print(f"   🔐 Polyline: {len(encoded_geometry)} caracteres")
                        
                        return {
                            "distance_km": round(summary.get("distance", 0) / 1000, 2),
                            "duration_minutes": round(summary.get("duration", 0) / 60, 1),
                            "geometry": encoded_geometry,
                            "bbox": feature.get("bbox", [])
                        }
                    else:
                        print(f"⚠️ OpenRouteService: Sin rutas en respuesta. Data keys: {list(data.keys()) if isinstance(data, dict) else 'No es dict'}")
                        if isinstance(data, dict) and "error" in data:
                            print(f"   Error details: {data.get('error')}")
                        return None
                
                elif response.status_code == 401:
                    error_text = response.text[:500]
                    print(f"❌ OpenRouteService: API key inválida. Response: {error_text}")
                    return None
                
                elif response.status_code == 429:
                    print("❌ OpenRouteService: Límite de requests excedido")
                    return None
                
                else:
                    error_text = response.text[:500]
                    print(f"❌ OpenRouteService error {response.status_code}: {error_text}")
                    return None
                    
        except httpx.TimeoutException:
            print("⏱️ OpenRouteService: Timeout después de 30 segundos")
            return None
        except Exception as e:
            print(f"❌ OpenRouteService error: {e}")
            import traceback
            traceback.print_exc()
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
    
    async def optimize_route_order(
        self,
        locations: List[List[float]],
        start_location: Optional[List[float]] = None,
        profile: str = "driving-car"
    ) -> Optional[List[int]]:
        """
        Optimiza el orden de visita usando matriz de distancias y algoritmo TSP simple (Nearest Neighbor).
        
        Args:
            locations: Lista de [longitude, latitude] para cada punto
            start_location: [longitude, latitude] del punto de inicio (opcional)
            profile: Perfil de transporte
        
        Returns:
            Lista de índices en orden optimizado, ej: [2, 0, 1, 3]
        """
        if not self.api_key:
            print("❌ OpenRouteService: API key no configurada")
            return None
        
        if len(locations) < 2:
            return list(range(len(locations)))
        
        try:
            # Construir lista completa de ubicaciones (inicio + puntos)
            all_locations = []
            if start_location:
                all_locations.append(start_location)
            all_locations.extend(locations)
            
            # Obtener matriz de distancias
            matrix = await self.get_distance_matrix(all_locations, profile)
            if not matrix:
                print("⚠️ No se pudo obtener matriz de distancias, usando orden original")
                return list(range(len(locations)))
            
            distances = matrix["distances_km"]
            
            # Algoritmo Nearest Neighbor TSP
            n = len(locations)
            start_idx = 0 if start_location else None
            visited = set()
            route = []
            
            # Si hay punto de inicio, empezar desde ahí
            if start_idx is not None:
                current = 0  # Índice del punto de inicio en la matriz
                visited.add(0)
            else:
                # Empezar desde el punto más cercano al primer punto
                current = 0
                visited.add(0)
            
            # Para cada punto de destino (excluyendo el inicio si existe)
            for _ in range(n):
                best_next = None
                best_distance = float('inf')
                
                # Buscar el punto no visitado más cercano
                for j in range(1 if start_location else 0, len(all_locations)):
                    if j not in visited:
                        dist = distances[current][j]
                        if dist < best_distance:
                            best_distance = dist
                            best_next = j
                
                if best_next is not None:
                    visited.add(best_next)
                    # Ajustar índice para excluir el punto de inicio
                    route.append(best_next - (1 if start_location else 0))
                    current = best_next
                else:
                    break
            
            # Si faltan puntos, agregarlos en orden
            for i in range(len(locations)):
                if i not in route:
                    route.append(i)
            
            return route
            
        except Exception as e:
            print(f"⚠️ Error en optimización TSP: {e}")
            # Fallback: orden original
            return list(range(len(locations)))
    
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
"""
Router de Optimización de Rutas - HU13
Genera rutas optimizadas para vendedores visitando sus tenderos asignados

CONTROL DE PERMISOS:
- ADMIN: Puede generar rutas de cualquier vendedor
- VENDEDOR: Solo puede generar su propia ruta
- TENDERO: Solo puede VER la ruta de su vendedor asignado
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from ..models import get_db, Seller, Shopkeeper, Assignment
from ..schemas import (
    OptimizedRouteResponse,
    RoutePoint,
    RouteStatistics,
    CacheStats
)
from ..utils import get_current_user
from ..config import settings

# Importar clientes
try:
    from ..clients.openroute_client import openroute_client
except ImportError:
    openroute_client = None
    print("⚠️  OpenRouteService client no disponible")

try:
    from ..cache.route_cache import route_cache
except ImportError:
    route_cache = None
    print("⚠️  Route cache no disponible")

router = APIRouter()


# ============================================================================
# FUNCIONES DE VALIDACIÓN DE PERMISOS
# ============================================================================

def validate_route_permissions(
    seller_id: int,
    current_user: dict,
    db: Session
) -> None:
    """Valida permisos para generar/ver ruta"""
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    
    if user_role == "ADMIN":
        return
    
    if user_role == "VENDEDOR":
        seller = db.query(Seller).filter(Seller.user_id == user_id).first()
        if not seller or seller.id != seller_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes generar tu propia ruta"
            )
        return
    
    if user_role == "TENDERO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los tenderos no pueden generar rutas"
        )
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para acceder a rutas"
    )


def get_seller_id_for_shopkeeper(shopkeeper_user_id: int, db: Session) -> Optional[int]:
    """Obtiene el seller_id asignado a un tendero"""
    shopkeeper = db.query(Shopkeeper).filter(
        Shopkeeper.user_id == shopkeeper_user_id
    ).first()
    
    if not shopkeeper:
        return None
    
    assignment = db.query(Assignment).filter(
        Assignment.shopkeeper_id == shopkeeper.id,
        Assignment.is_active == True
    ).first()
    
    return assignment.seller_id if assignment else None


# ============================================================================
# ALGORITMO - OPENROUTESERVICE CON GEOMETRÍA
# ============================================================================

async def calculate_optimized_route(
    shopkeepers: List[Shopkeeper],
    start_lat: Optional[float] = None,
    start_lon: Optional[float] = None
) -> tuple[List[dict], dict]:
    """
    Calcula ruta optimizada usando OpenRouteService.
    1. Optimization API para orden óptimo
    2. Directions API para geometría real por calles
    """
    
    if not settings.OPENROUTE_ENABLED or not openroute_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenRouteService no está configurado"
        )
    
    try:
        # PASO 1: Optimizar orden de visitas
        jobs = _build_optimization_jobs(shopkeepers)
        vehicles = _build_vehicle_config(start_lat, start_lon, len(jobs))
        
        print(f"🚀 Optimizando orden con Vroom TSP para {len(jobs)} puntos...")
        optimization_result = await openroute_client.optimize_route(
            jobs=jobs,
            vehicles=vehicles,
            profile="driving-car"
        )
        
        if not optimization_result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error en Optimization API"
            )
        
        # PASO 2: Procesar orden optimizado
        optimized_route = _process_optimization_result(optimization_result, shopkeepers)
        
        # PASO 3: Obtener geometría real usando Directions API
        geometry = await _get_route_geometry(optimized_route, start_lat, start_lon)
        
        # PASO 4: Extraer datos de la API
        api_data = _extract_api_data(optimization_result, geometry)
        
        print(f"✅ Ruta OPTIMIZADA: {api_data['total_distance_km']} km, {api_data['total_duration_minutes']:.1f} min")
        print(f"   📊 Geometría: {len(geometry)} caracteres")
        
        return optimized_route, api_data
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error al optimizar ruta: {str(e)}"
        )


async def _get_route_geometry(
    optimized_route: List[Dict],
    start_lat: Optional[float],
    start_lon: Optional[float]
) -> str:
    """
    Obtiene la geometría real de la ruta usando get_route.
    Conecta todos los puntos en orden (incluyendo punto de inicio si existe).
    """
    try:
        # Construir lista de coordenadas en orden
        coordinates = []
        
        # Agregar punto de inicio si existe
        if start_lat and start_lon:
            coordinates.append([start_lon, start_lat])
        
        # Agregar todos los tenderos en orden optimizado
        for item in optimized_route:
            sk = item['shopkeeper']
            coordinates.append([float(sk.longitude), float(sk.latitude)])
        
        if len(coordinates) < 2:
            return ""
        
        print(f"📍 Obteniendo geometría para {len(coordinates)} puntos...")
        
        # Llamar a get_route (que ya funciona)
        route_result = await openroute_client.get_route(
            coordinates=coordinates,
            profile="driving-car"
        )
        
        if not route_result or 'geometry' not in route_result:
            print("⚠️ No se obtuvo geometría de get_route")
            return ""
        
        # Extraer geometría (polyline codificada)
        geometry = route_result.get('geometry', '')
        print(f"✅ Geometría obtenida: {len(geometry)} caracteres")
        
        return geometry
        
    except Exception as e:
        print(f"⚠️ Error obteniendo geometría: {e}")
        import traceback
        traceback.print_exc()
        return ""


def _build_optimization_jobs(shopkeepers: List[Shopkeeper]) -> List[Dict]:
    """Construye lista de jobs para el optimizador"""
    jobs = [
        {
            "id": idx + 1,
            "location": [float(sk.longitude), float(sk.latitude)],
            "service": 600
        }
        for idx, sk in enumerate(shopkeepers)
    ]
    
    if len(jobs) > 100:
        print(f"⚠️ Limitando a 100 puntos")
        return jobs[:100]
    
    return jobs


def _build_vehicle_config(
    start_lat: Optional[float],
    start_lon: Optional[float],
    job_count: int
) -> Optional[List[Dict]]:
    """Construye configuración del vehículo"""
    if not start_lat or not start_lon:
        return None
    
    return [{
        "id": 1,
        "profile": "driving-car",
        "start": [start_lon, start_lat],
        "end": [start_lon, start_lat]  # Volver al inicio
    }]


def _process_optimization_result(
    optimization_result: Dict,
    shopkeepers: List[Shopkeeper]
) -> List[Dict]:
    """Procesa resultado y construye ruta ordenada"""
    route = optimization_result["routes"][0]
    steps = route["steps"]
    shopkeeper_dict = {idx + 1: sk for idx, sk in enumerate(shopkeepers)}
    
    optimized_route = []
    
    for step in steps:
        if step["type"] != "job":
            continue
            
        job_id = step["job"]
        sk = shopkeeper_dict.get(job_id)
        
        if sk:
            optimized_route.append({
                "shopkeeper": sk,
                "order": len(optimized_route) + 1
            })
    
    return optimized_route


def _extract_api_data(optimization_result: Dict, geometry: str) -> Dict:
    """Extrae datos relevantes"""
    route = optimization_result["routes"][0]
    
    unassigned = optimization_result.get("summary", {}).get("unassigned", [])
    unassigned_count = len(unassigned) if isinstance(unassigned, list) else unassigned
    
    return {
        "total_distance_km": round(route["distance"] / 1000, 2),
        "total_duration_minutes": round(route["duration"] / 60, 2),
        "geometry": geometry,  # Geometría real de Directions API
        "optimization_cost": optimization_result.get("summary", {}).get("cost", 0),
        "unassigned_jobs": unassigned_count
    }


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/routes/optimize", response_model=OptimizedRouteResponse, tags=["Rutas"])
async def optimize_route(
    seller_id: Optional[int] = Query(None),
    start_latitude: Optional[float] = Query(None, ge=-90, le=90),
    start_longitude: Optional[float] = Query(None, ge=-180, le=180),
    force_recalculate: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Genera ruta optimizada con geometría real"""
    
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    
    # Validar permisos y obtener seller_id
    if user_role == "TENDERO":
        seller_id = get_seller_id_for_shopkeeper(user_id, db)
        if not seller_id:
            raise HTTPException(status_code=404, detail="Sin vendedor asignado")
    elif user_role == "VENDEDOR":
        if not seller_id:
            seller = db.query(Seller).filter(Seller.user_id == user_id).first()
            if not seller:
                raise HTTPException(status_code=404, detail="Sin perfil de vendedor")
            seller_id = seller.id
        validate_route_permissions(seller_id, current_user, db)
    elif user_role == "ADMIN":
        if not seller_id:
            raise HTTPException(status_code=400, detail="Proporcione seller_id")
        validate_route_permissions(seller_id, current_user, db)
    else:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    # Verificar vendedor
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    
    # Obtener tenderos
    assignments = db.query(Assignment, Shopkeeper).join(
        Shopkeeper, Assignment.shopkeeper_id == Shopkeeper.id
    ).filter(
        Assignment.seller_id == seller_id,
        Assignment.is_active == True,
        Shopkeeper.is_active == True
    ).all()
    
    if not assignments:
        raise HTTPException(status_code=404, detail="Sin tenderos asignados")
    
    shopkeepers = [shopkeeper for _, shopkeeper in assignments]
    shopkeeper_ids = [sk.id for sk in shopkeepers]
    
    # Intentar caché (TEMPORALMENTE DESHABILITADO)
    # if route_cache and not force_recalculate:
    #     start_coords = (start_latitude, start_longitude) if start_latitude and start_longitude else None
    #     cached_route = route_cache.get(seller_id, shopkeeper_ids, start_coords)
    #     if cached_route:
    #         cached_route["from_cache"] = True
    #         return cached_route
    
    # Generar ruta
    optimized_route, api_data = await calculate_optimized_route(
        shopkeepers, start_latitude, start_longitude
    )
    
    # Construir respuesta
    route_points = []
    for idx, item in enumerate(optimized_route):
        sk = item['shopkeeper']
        route_points.append(RoutePoint(
            shopkeeper_id=sk.id,
            shopkeeper_name=sk.name,
            business_name=sk.business_name,
            address=sk.address,
            latitude=float(sk.latitude),
            longitude=float(sk.longitude),
            order=item['order'],
            distance_from_previous_km=0,
            cumulative_distance_km=0
        ))
    
    statistics = RouteStatistics(
        total_shopkeepers=len(route_points),
        total_distance_km=api_data['total_distance_km'],
        estimated_travel_time_hours=round(api_data['total_duration_minutes'] / 60, 2),
        estimated_visit_time_hours=round(len(route_points) * 10 / 60, 2),
        estimated_total_time_hours=round((api_data['total_duration_minutes'] + len(route_points) * 10) / 60, 2),
        average_distance_between_stops_km=round(api_data['total_distance_km'] / len(route_points), 2) if route_points else 0
    )
    
    # Crear objeto de respuesta validado
    response_data = OptimizedRouteResponse(
        seller_id=seller_id,
        seller_name=seller.name,
        route_points=route_points,
        statistics=statistics,
        algorithm_used="openrouteservice",
        api_data=api_data
    )
    
    # DEBUG: Verificar api_data
    print(f"🔍 DEBUG final response:")
    print(f"   - api_data presente: {response_data.api_data is not None}")
    if response_data.api_data:
        print(f"   - Geometry length: {len(response_data.api_data.get('geometry', ''))}")
    
    # Guardar en caché (TEMPORALMENTE DESHABILITADO)
    # if route_cache:
    #     start_coords = (start_latitude, start_longitude) if start_latitude and start_longitude else None
    #     route_cache.set(seller_id, shopkeeper_ids, response_data.model_dump(), start_coords)
    
    return response_data


@router.get("/routes/cache/stats", tags=["Rutas"])
async def get_cache_stats(current_user: dict = Depends(get_current_user)):
    if not route_cache:
        raise HTTPException(status_code=503, detail="Caché no disponible")
    return route_cache.stats()


@router.post("/routes/cache/clear", tags=["Rutas"])
async def clear_cache(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo admin")
    if not route_cache:
        raise HTTPException(status_code=503, detail="Caché no disponible")
    route_cache.clear()
    return {"message": "Caché limpiado", "stats": route_cache.stats()}