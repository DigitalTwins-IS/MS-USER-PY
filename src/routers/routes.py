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
from typing import List, Optional, Dict, Tuple
import math

import importlib

from ..models import get_db, Seller, Shopkeeper, Assignment
from ..schemas import (
    OptimizedRouteResponse,
    RoutePoint,
    RouteStatistics,
    CacheStats
)
from ..utils import get_current_user
from ..config import settings

try:
    from ..cache.route_cache import route_cache
except ImportError:
    route_cache = None
    print("⚠️  Route cache no disponible")

router = APIRouter()


def _get_openroute_client():
    """Obtiene la instancia global inicializada en main.py."""
    if not settings.OPENROUTE_ENABLED or not settings.OPENROUTE_API_KEY:
        return None
    try:
        module = importlib.import_module("src.clients.openroute_client")
    except ImportError:
        return None
    return getattr(module, "openroute_client", None)


# ============================================================================
# SRP: CLASE PARA GESTIÓN DE PERMISOS
# ============================================================================

class RoutePermissionManager:
    """Gestiona permisos de acceso a rutas (SRP)"""
    
    @staticmethod
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
    
    @staticmethod
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
    
    @staticmethod
    def resolve_seller_id(
        seller_id: Optional[int],
        shopkeeper_id: Optional[int],
        current_user: dict,
        db: Session
    ) -> Tuple[int, str]:
        """Resuelve el seller_id basado en permisos y parámetros"""
        user_role = current_user.get("role")
        user_id = current_user.get("id")
        
        # Tendero: Solo puede ver ruta de su vendedor
        if user_role == "TENDERO":
            resolved_seller_id = RoutePermissionManager.get_seller_id_for_shopkeeper(user_id, db)
            if not resolved_seller_id:
                raise HTTPException(status_code=404, detail="No tienes vendedor asignado")
            return resolved_seller_id, "TENDERO"
        
        # Vendedor: Solo su propia ruta
        elif user_role == "VENDEDOR":
            if not seller_id:
                seller = db.query(Seller).filter(Seller.user_id == user_id).first()
                if not seller:
                    raise HTTPException(status_code=404, detail="No tienes perfil de vendedor")
                resolved_seller_id = seller.id
            else:
                resolved_seller_id = seller_id
            
            RoutePermissionManager.validate_route_permissions(resolved_seller_id, current_user, db)
            return resolved_seller_id, "VENDEDOR"
        
        # Admin: Cualquier ruta pero necesita seller_id
        elif user_role == "ADMIN":
            if not seller_id:
                raise HTTPException(status_code=400, detail="Proporcione seller_id")
            RoutePermissionManager.validate_route_permissions(seller_id, current_user, db)
            return seller_id, "ADMIN"
        
        else:
            raise HTTPException(status_code=403, detail="No tienes permisos")


# ============================================================================
# SRP: ALGORITMOS DE OPTIMIZACIÓN
# ============================================================================

class GeoDistanceCalculator:
    """Utilidades para calcular distancias geográficas"""
    
    EARTH_RADIUS_KM = 6371
    
    @staticmethod
    def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distancia entre dos puntos en kilómetros"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return GeoDistanceCalculator.EARTH_RADIUS_KM * c
    
class OpenRouteServiceOptimizer:
    """Optimizador usando OpenRouteService API (OCP: Extensible)"""
    
    MAX_POINTS = 50  # Límite de OpenRouteService gratuito
    
    @staticmethod
    async def calculate_optimized_route(
        shopkeepers: List[Shopkeeper],
        start_lat: Optional[float] = None,
        start_lon: Optional[float] = None
    ) -> Tuple[List[dict], str, Optional[dict]]:
        """
        Calcula ruta optimizada usando OpenRouteService API.
        Primero optimiza el orden de visita (TSP) y luego obtiene la geometría real.
        """
        
        # Verificar si OpenRouteService está habilitado y configurado
        client = _get_openroute_client()
        if not settings.OPENROUTE_ENABLED or not client:
            print(f"⚠️ OpenRouteService optimizer sin cliente (enabled={settings.OPENROUTE_ENABLED}, client={client})")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenRouteService no está configurado en el servidor"
            )
        
        try:
            # Limitar puntos si es necesario
            if len(shopkeepers) > OpenRouteServiceOptimizer.MAX_POINTS:
                print(f"⚠️  Limitando ruta a {OpenRouteServiceOptimizer.MAX_POINTS} puntos")
                shopkeepers = shopkeepers[:OpenRouteServiceOptimizer.MAX_POINTS]
            
            # PASO 1: Preparar coordenadas (incluyendo punto de inicio)
            locations = [[float(sk.longitude), float(sk.latitude)] for sk in shopkeepers]
            start_location = [start_lon, start_lat] if start_lat and start_lon else None
            
            # PASO 2: Intentar optimizar orden usando matriz de distancias (considera tráfico y rutas reales)
            optimized_indices = None
            try:
                print(f"🚀 Optimizando orden con TSP basado en distancias reales (considera tráfico) para {len(locations)} puntos...")
                optimized_indices = await client.optimize_route_order(
                    locations=locations,
                    start_location=start_location,
                    profile="driving-car"
                )
            except Exception as e:
                print(f"⚠️ Error en optimización TSP: {e}, usando orden original")
                import traceback
                traceback.print_exc()
            
            if not optimized_indices:
                print("⚠️ No se pudo optimizar orden, usando orden original")
                optimized_indices = list(range(len(shopkeepers)))
            
            # PASO 3: Construir ruta optimizada
            optimized_route = []
            for idx, original_idx in enumerate(optimized_indices):
                sk = shopkeepers[original_idx]
                optimized_route.append({
                    "shopkeeper": sk,
                    "order": idx + 1
                })
            
            # PASO 4: Obtener ruta real con geometría usando Directions API
            # La API de OpenRouteService considera tráfico, rutas reales y devuelve geometría detallada
            route_coordinates = []
            if start_location:
                route_coordinates.append(start_location)
            for item in optimized_route:
                sk = item['shopkeeper']
                route_coordinates.append([float(sk.longitude), float(sk.latitude)])
            
            print(f"📍 Obteniendo ruta real con tráfico para {len(route_coordinates)} puntos...")
            print(f"   🔍 Coordenadas: {route_coordinates[:3]}... (mostrando primeras 3)")
            
            try:
                route_data = await client.get_route(
                    coordinates=route_coordinates,
                    profile="driving-car"  # Considera tráfico en tiempo real
                )
            except Exception as e:
                print(f"❌ Error al llamar get_route: {e}")
                import traceback
                traceback.print_exc()
                route_data = None
            
            if not route_data:
                error_msg = "OpenRouteService no pudo calcular la ruta con tráfico"
                print(f"❌ {error_msg}")
                print(f"   🔍 Verificar: API key configurada, coordenadas válidas, límites de API")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=error_msg
                )
            
            # PASO 5: Extraer datos de la API (incluye geometría para mostrar en mapa)
            api_data = {
                "total_distance_km": route_data.get('distance_km', 0),
                "total_duration_minutes": route_data.get('duration_minutes', 0),
                "geometry": route_data.get('geometry', '')  # Polyline para mostrar en mapa
            }
            
            # Actualizar distancias en la ruta optimizada
            optimized_route = OpenRouteServiceOptimizer._calculate_route_distances(
                optimized_route, start_lat, start_lon
            )
            
            print(f"✅ Ruta OPTIMIZADA: {api_data['total_distance_km']} km, {api_data['total_duration_minutes']:.1f} min")
            print(f"   📊 Geometría: {len(api_data.get('geometry', ''))} caracteres")
            
            return optimized_route, "openrouteservice", api_data
            
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            print(f"❌ Error con OpenRouteService API: {e}")
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo obtener la ruta desde OpenRouteService"
            )
    
    @staticmethod
    def _calculate_route_distances(
        optimized_route: List[Dict],
        start_lat: Optional[float] = None,
        start_lon: Optional[float] = None
    ) -> List[Dict]:
        """Calcula distancias entre puntos en la ruta optimizada"""
        cumulative_distance = 0
        prev_lat = start_lat
        prev_lon = start_lon
        
        for item in optimized_route:
            sk = item['shopkeeper']
            
            # Calcular distancia desde punto anterior
            if prev_lat and prev_lon:
                segment_distance = GeoDistanceCalculator.distance_km(
                    prev_lat, prev_lon,
                    float(sk.latitude), float(sk.longitude)
                )
            else:
                segment_distance = 0
            
            cumulative_distance += segment_distance
            
            item['distance_from_previous'] = round(segment_distance, 2)
            item['cumulative_distance'] = round(cumulative_distance, 2)
            
            prev_lat = float(sk.latitude)
            prev_lon = float(sk.longitude)
        
        return optimized_route
    
    @staticmethod
    async def _get_route_geometry(
        optimized_route: List[Dict],
        start_lat: Optional[float],
        start_lon: Optional[float],
        client
    ) -> str:
        """
        Obtiene la geometría real de la ruta usando get_route.
        Conecta todos los puntos en orden optimizado (incluyendo punto de inicio si existe).
        """
        try:
            # Construir lista de coordenadas en orden optimizado
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
            
            print(f"📍 Obteniendo geometría para {len(coordinates)} puntos en orden optimizado...")
            
            # Llamar a get_route con el orden optimizado
            route_result = await client.get_route(
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
    
    


# ============================================================================
# SRP: CONSTRUCTOR DE RESPUESTAS
# ============================================================================

class RouteResponseBuilder:
    """Construye respuestas de rutas optimizadas (SRP)"""
    
    AVG_SPEED_KMH = 25  # Velocidad promedio en ciudad
    VISIT_TIME_MINUTES = 10  # Tiempo estimado por visita
    
    @staticmethod
    def build_route_response(
        optimized_route: List[dict],
        seller_id: int,
        seller_name: str,
        algorithm_used: str,
        api_data: Optional[dict] = None
    ) -> Dict:
        """Construye respuesta completa de ruta optimizada"""
        
        # Construir puntos de ruta
        route_points = RouteResponseBuilder._build_route_points(optimized_route)
        
        # Calcular estadísticas
        statistics = RouteResponseBuilder._calculate_statistics(optimized_route, route_points)
        
        # Construir respuesta base
        response_data = OptimizedRouteResponse(
            seller_id=seller_id,
            seller_name=seller_name,
            route_points=route_points,
            statistics=statistics,
            algorithm_used=algorithm_used
        )
        
        # Convertir a dict y agregar campos extras
        response_dict = response_data.model_dump()
        response_dict["from_cache"] = False
        
        response_dict["api_data"] = api_data or {
            "total_distance_km": 0,
            "total_duration_minutes": 0,
            "geometry": ""
        }
        
        if not api_data:
            print("⚠️ RouteResponseBuilder - api_data vacío, se usará geometría simple en el frontend")
        else:
            print(f"🔍 RouteResponseBuilder - geometry length: {len(api_data.get('geometry', ''))}")
        
        return response_dict
    
    @staticmethod
    def _build_route_points(optimized_route: List[dict]) -> List[RoutePoint]:
        """Construye lista de RoutePoint a partir de la ruta optimizada"""
        route_points = []
        for item in optimized_route:
            sk = item['shopkeeper']
            route_points.append(RoutePoint(
                shopkeeper_id=sk.id,
                shopkeeper_name=sk.name,
                business_name=sk.business_name,
                address=sk.address,
                latitude=float(sk.latitude),
                longitude=float(sk.longitude),
                order=item['order'],
                distance_from_previous_km=item['distance_from_previous'],
                cumulative_distance_km=item['cumulative_distance']
            ))
        return route_points
    
    @staticmethod
    def _calculate_statistics(
        optimized_route: List[dict],
        route_points: List[RoutePoint]
    ) -> RouteStatistics:
        """Calcula estadísticas de la ruta"""
        total_distance = optimized_route[-1]['cumulative_distance'] if optimized_route else 0
        
        # Estimación de tiempo
        travel_time_hours = total_distance / RouteResponseBuilder.AVG_SPEED_KMH
        visit_time_hours = (len(route_points) * RouteResponseBuilder.VISIT_TIME_MINUTES) / 60
        total_time_hours = travel_time_hours + visit_time_hours
        
        return RouteStatistics(
            total_shopkeepers=len(route_points),
            total_distance_km=round(total_distance, 2),
            estimated_travel_time_hours=round(travel_time_hours, 2),
            estimated_visit_time_hours=round(visit_time_hours, 2),
            estimated_total_time_hours=round(total_time_hours, 2),
            average_distance_between_stops_km=round(
                total_distance / len(route_points) if route_points else 0,
                2
            )
        )
    


# ============================================================================
# ENDPOINTS PRINCIPALES
# ============================================================================

@router.get("/routes/optimize", response_model=OptimizedRouteResponse, tags=["Rutas"])
async def optimize_route(
    seller_id: Optional[int] = Query(None),
    shopkeeper_id: Optional[int] = Query(None, description="ID del tendero (para ver ruta de su vendedor)"),
    start_latitude: Optional[float] = Query(None, ge=-90, le=90),
    start_longitude: Optional[float] = Query(None, ge=-180, le=180),
    use_api: bool = Query(True, description="Usar OpenRouteService API"),
    force_recalculate: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Genera ruta optimizada con control de permisos y principios SOLID"""
    
    # 1. Resolver seller_id basado en permisos
    resolved_seller_id, user_role = RoutePermissionManager.resolve_seller_id(
        seller_id, shopkeeper_id, current_user, db
    )
    
    # 2. Verificar que el vendedor existe
    seller = db.query(Seller).filter(Seller.id == resolved_seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    
    # 3. Obtener tenderos asignados
    assignments = db.query(Assignment, Shopkeeper).join(
        Shopkeeper, Assignment.shopkeeper_id == Shopkeeper.id
    ).filter(
        Assignment.seller_id == resolved_seller_id,
        Assignment.is_active == True,
        Shopkeeper.is_active == True
    ).all()
    
    if not assignments:
        raise HTTPException(status_code=404, detail="El vendedor no tiene tenderos asignados")
    
    shopkeepers = [shopkeeper for _, shopkeeper in assignments]
    
    print(f"📊 Generando ruta para vendedor {seller.name} ({len(shopkeepers)} tenderos) - Usuario: {user_role}")
    
    # 4. Generar ruta usando OpenRouteService (obligatorio)
    if not use_api:
        raise HTTPException(status_code=400, detail="El optimizador solo soporta OpenRouteService")
    client = _get_openroute_client()
    if not settings.OPENROUTE_ENABLED or not client:
        print(f"⚠️ OpenRouteService no disponible (enabled={settings.OPENROUTE_ENABLED}, client={client})")
        raise HTTPException(status_code=503, detail="OpenRouteService no está configurado")
    
    optimized_route, algorithm_used, api_data = await OpenRouteServiceOptimizer.calculate_optimized_route(
        shopkeepers, start_latitude, start_longitude
    )
    
    # 5. Construir respuesta
    response_dict = RouteResponseBuilder.build_route_response(
        optimized_route, resolved_seller_id, seller.name, algorithm_used, api_data
    )
    
    # DEBUG: Verificar respuesta final
    print(f"🔍 BACKEND DEBUG - Respuesta final:")
    print(f"   - api_data presente: {bool(api_data)}")
    print(f"   - geometry en api_data: {bool(api_data.get('geometry') if api_data else False)}")
    print(f"   - geometry length: {len(api_data.get('geometry', '')) if api_data else 0}")
    
    return response_dict


@router.get("/routes/cache/stats", response_model=CacheStats, tags=["Rutas"])
async def get_cache_stats(current_user: dict = Depends(get_current_user)):
    """Estadísticas de caché - Solo ADMIN"""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores")
    if not route_cache:
        raise HTTPException(status_code=503, detail="Caché no disponible")
    return route_cache.stats()


@router.post("/routes/cache/clear", tags=["Rutas"])
async def clear_cache(current_user: dict = Depends(get_current_user)):
    """Limpiar caché - Solo ADMIN"""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores")
    if not route_cache:
        raise HTTPException(status_code=503, detail="Caché no disponible")
    route_cache.clear()
    return {"message": "Caché limpiado", "stats": route_cache.stats()}