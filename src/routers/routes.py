"""
Router de Optimización de Rutas - HU13
Genera rutas optimizadas para vendedores visitando sus tenderos
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import math

from ..models import get_db, Seller, Shopkeeper, Assignment
from ..schemas import (
    OptimizedRouteResponse,
    RoutePoint,
    RouteStatistics
)
from ..utils import get_current_user

router = APIRouter()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distancia entre dos puntos usando fórmula de Haversine
    
    Returns:
        float: Distancia en kilómetros
    """
    R = 6371  # Radio de la Tierra en km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def nearest_neighbor_route(shopkeepers: List[Shopkeeper], 
                          start_lat: Optional[float] = None,
                          start_lon: Optional[float] = None) -> List[dict]:
    """
    Algoritmo Nearest Neighbor para optimizar ruta
    
    Args:
        shopkeepers: Lista de tenderos a visitar
        start_lat: Latitud punto de inicio (opcional)
        start_lon: Longitud punto de inicio (opcional)
        
    Returns:
        Lista ordenada de tenderos con distancias
    """
    if not shopkeepers:
        return []
    
    unvisited = [s for s in shopkeepers]
    route = []
    
    # Punto de inicio
    if start_lat and start_lon:
        current_lat, current_lon = start_lat, start_lon
    else:
        # Usar primer tendero como inicio
        first = unvisited.pop(0)
        route.append({
            'shopkeeper': first,
            'order': 1,
            'distance_from_previous': 0,
            'cumulative_distance': 0
        })
        current_lat = float(first.latitude)
        current_lon = float(first.longitude)
    
    cumulative_distance = 0
    
    # Algoritmo greedy: siempre elegir el más cercano
    while unvisited:
        nearest = None
        min_distance = float('inf')
        
        for shopkeeper in unvisited:
            dist = calculate_distance(
                current_lat, current_lon,
                float(shopkeeper.latitude),
                float(shopkeeper.longitude)
            )
            
            if dist < min_distance:
                min_distance = dist
                nearest = shopkeeper
        
        if nearest:
            unvisited.remove(nearest)
            cumulative_distance += min_distance
            
            route.append({
                'shopkeeper': nearest,
                'order': len(route) + 1,
                'distance_from_previous': round(min_distance, 2),
                'cumulative_distance': round(cumulative_distance, 2)
            })
            
            current_lat = float(nearest.latitude)
            current_lon = float(nearest.longitude)
    
    return route


@router.get(
    "/sellers/{seller_id}/optimized-route",
    response_model=OptimizedRouteResponse,
    summary="Generar ruta optimizada",
    description="HU13: Genera ruta optimizada visitando todos los tenderos del vendedor",
    tags=["Rutas"]
)
async def get_optimized_route(
    seller_id: int,
    start_latitude: Optional[float] = Query(None, description="Latitud punto de inicio"),
    start_longitude: Optional[float] = Query(None, description="Longitud punto de inicio"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    HU13: Genera ruta optimizada para un vendedor
    
    Algoritmo: Nearest Neighbor (greedy approach)
    - Siempre visita el tendero más cercano
    - Complejidad: O(n²)
    - Buena aproximación para <100 puntos
    
    Args:
        seller_id: ID del vendedor
        start_latitude: Latitud inicial (oficina, casa, etc)
        start_longitude: Longitud inicial
        
    Returns:
        Ruta optimizada con distancias y tiempos estimados
    """
    # Verificar vendedor existe
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(404, "Vendedor no encontrado")
    
    # Obtener tenderos asignados
    assignments = db.query(Assignment, Shopkeeper).join(
        Shopkeeper, Assignment.shopkeeper_id == Shopkeeper.id
    ).filter(
        Assignment.seller_id == seller_id,
        Assignment.is_active == True,
        Shopkeeper.is_active == True
    ).all()
    
    if not assignments:
        raise HTTPException(404, "El vendedor no tiene tenderos asignados")
    
    shopkeepers = [shopkeeper for _, shopkeeper in assignments]
    
    # Generar ruta optimizada
    optimized_route = nearest_neighbor_route(
        shopkeepers,
        start_latitude,
        start_longitude
    )
    
    # Construir respuesta
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
    
    # Calcular estadísticas
    total_distance = optimized_route[-1]['cumulative_distance'] if optimized_route else 0
    
    # Estimación de tiempo (velocidad promedio ciudad: 25 km/h)
    # + 10 minutos por cada visita
    avg_speed_kmh = 25
    visit_time_minutes = 10
    
    travel_time_hours = total_distance / avg_speed_kmh
    visit_time_hours = (len(route_points) * visit_time_minutes) / 60
    
    total_time_hours = travel_time_hours + visit_time_hours
    
    statistics = RouteStatistics(
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
    
    return OptimizedRouteResponse(
        seller_id=seller_id,
        seller_name=seller.name,
        route_points=route_points,
        statistics=statistics,
        algorithm_used="nearest_neighbor"
    )


@router.get(
    "/routes/compare-algorithms",
    summary="Comparar algoritmos de optimización",
    description="Compara diferentes algoritmos para generar rutas",
    tags=["Rutas"]
)
async def compare_route_algorithms(
    seller_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint provisional para comparar algoritmos de optimización.
    Retorna métricas básicas para el vendedor o un error si no existe.
    """
    # Verificar vendedor existe
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(404, "Vendedor no encontrado")

    # Obtener tenderos asignados
    assignments = db.query(Assignment, Shopkeeper).join(
        Shopkeeper, Assignment.shopkeeper_id == Shopkeeper.id
    ).filter(
        Assignment.seller_id == seller_id,
        Assignment.is_active == True,
        Shopkeeper.is_active == True
    ).all()

    shopkeepers = [shopkeeper for _, shopkeeper in assignments]

    # Implementación simplificada: comparar algoritmo nearest_neighbor con orden original
    nn_route = nearest_neighbor_route(shopkeepers)
    original_order = [{
        'shopkeeper_id': sk.id,
        'order': idx + 1
    } for idx, sk in enumerate(shopkeepers)]

    return {
        'seller_id': seller_id,
        'seller_name': seller.name,
        'algorithms': {
            'nearest_neighbor': {
                'num_stops': len(nn_route),
                'total_distance_km': round(nn_route[-1]['cumulative_distance'], 2) if nn_route else 0
            },
            'original_order': {
                'num_stops': len(original_order)
            }
        }
    }