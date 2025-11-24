"""
WebSocket Router - Tracking de Vendedores en Tiempo Real
HU18: Seguimiento en vivo de ubicación de vendedores

PERMISOS:
- VENDEDOR: Puede enviar su ubicación GPS
- TENDERO: Puede ver la ubicación de su vendedor asignado
- ADMIN: Puede ver todos los vendedores
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Set, Optional
import json
from datetime import datetime

from ..models import get_db, Seller, Shopkeeper, Assignment
from ..utils import get_current_user

router = APIRouter()

# ============================================================================
# GESTOR DE CONEXIONES WEBSOCKET
# ============================================================================

class ConnectionManager:
    """
    Maneja las conexiones WebSocket activas.
    
    Estructura:
    - active_connections: {seller_id: Set[WebSocket]} - Conexiones de observadores
    - seller_locations: {seller_id: {lat, lng, timestamp, speed, battery}}
    """
    
    def __init__(self):
        # Conexiones activas por seller_id (observadores viendo a ese vendedor)
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        
        # Ubicaciones actuales de vendedores
        self.seller_locations: Dict[int, dict] = {}
    
    async def connect(self, websocket: WebSocket, seller_id: int):
        """Conecta un observador para ver a un vendedor específico"""
        await websocket.accept()
        
        if seller_id not in self.active_connections:
            self.active_connections[seller_id] = set()
        
        self.active_connections[seller_id].add(websocket)
        
        # Enviar ubicación actual si existe
        if seller_id in self.seller_locations:
            await websocket.send_json({
                "type": "location_update",
                "data": self.seller_locations[seller_id]
            })
    
    def disconnect(self, websocket: WebSocket, seller_id: int):
        """Desconecta un observador"""
        if seller_id in self.active_connections:
            self.active_connections[seller_id].discard(websocket)
            
            # Limpiar si no hay más conexiones
            if not self.active_connections[seller_id]:
                del self.active_connections[seller_id]
    
    async def update_location(self, seller_id: int, location_data: dict):
        """
        Actualiza la ubicación de un vendedor y notifica a todos los observadores
        
        Args:
            seller_id: ID del vendedor
            location_data: {latitude, longitude, speed, battery, timestamp}
        """
        # Guardar ubicación actual
        self.seller_locations[seller_id] = {
            **location_data,
            "seller_id": seller_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Broadcast a todos los observadores de este vendedor
        if seller_id in self.active_connections:
            message = {
                "type": "location_update",
                "data": self.seller_locations[seller_id]
            }
            
            disconnected = set()
            for connection in self.active_connections[seller_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)
            
            # Limpiar conexiones muertas
            for conn in disconnected:
                self.active_connections[seller_id].discard(conn)
    
    def get_location(self, seller_id: int) -> Optional[dict]:
        """Obtiene la última ubicación conocida de un vendedor"""
        return self.seller_locations.get(seller_id)
    
    def get_all_locations(self) -> Dict[int, dict]:
        """Obtiene todas las ubicaciones activas (para ADMIN)"""
        return self.seller_locations.copy()


# Instancia global del gestor
manager = ConnectionManager()


# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@router.websocket("/ws/send/{seller_id}")
async def websocket_send_location(
    websocket: WebSocket,
    seller_id: int,
    db: Session = Depends(get_db)
):
    """
    WebSocket para que un VENDEDOR envíe su ubicación GPS.
    
    El vendedor conecta y envía mensajes con formato:
    {
        "latitude": 4.6234,
        "longitude": -74.0654,
        "speed": 15.5,  // km/h (opcional)
        "battery": 85   // % (opcional)
    }
    """
    await websocket.accept()
    
    try:
        # Validar que el vendedor existe
        seller = db.query(Seller).filter(Seller.id == seller_id).first()
        if not seller:
            await websocket.send_json({
                "type": "error",
                "message": f"Vendedor {seller_id} no encontrado"
            })
            await websocket.close()
            return
        
        print(f"📡 Vendedor {seller.name} (ID: {seller_id}) conectado para enviar ubicación")
        
        # Confirmación de conexión
        await websocket.send_json({
            "type": "connected",
            "message": f"Conectado como {seller.name}",
            "seller_id": seller_id
        })
        
        # Loop para recibir ubicaciones
        while True:
            data = await websocket.receive_json()
            
            # Validar datos recibidos
            if "latitude" not in data or "longitude" not in data:
                await websocket.send_json({
                    "type": "error",
                    "message": "latitude y longitude son requeridos"
                })
                continue
            
            # Actualizar ubicación y notificar observadores
            location_data = {
                "latitude": float(data["latitude"]),
                "longitude": float(data["longitude"]),
                "speed": float(data.get("speed", 0)),
                "battery": int(data.get("battery", 100)),
                "seller_name": seller.name
            }
            
            await manager.update_location(seller_id, location_data)
            
            # Confirmar recepción
            await websocket.send_json({
                "type": "location_received",
                "timestamp": datetime.now().isoformat()
            })
            
            print(f"📍 Ubicación actualizada: {seller.name} - {location_data['latitude']}, {location_data['longitude']}")
    
    except WebSocketDisconnect:
        print(f"❌ Vendedor {seller_id} desconectado")
    except Exception as e:
        print(f"❌ Error en WebSocket send: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/watch/{seller_id}")
async def websocket_watch_location(
    websocket: WebSocket,
    seller_id: int,
    db: Session = Depends(get_db)
):
    """
    WebSocket para que TENDERO/ADMIN vean la ubicación de un vendedor.
    
    El cliente recibe mensajes con formato:
    {
        "type": "location_update",
        "data": {
            "seller_id": 1,
            "seller_name": "Juan Pérez",
            "latitude": 4.6234,
            "longitude": -74.0654,
            "speed": 15.5,
            "battery": 85,
            "timestamp": "2025-11-22T20:30:00"
        }
    }
    """
    await manager.connect(websocket, seller_id)
    
    try:
        # Validar que el vendedor existe
        seller = db.query(Seller).filter(Seller.id == seller_id).first()
        if not seller:
            await websocket.send_json({
                "type": "error",
                "message": f"Vendedor {seller_id} no encontrado"
            })
            await websocket.close()
            return
        
        print(f"👀 Observador conectado para ver vendedor {seller.name} (ID: {seller_id})")
        
        # Confirmación de conexión
        await websocket.send_json({
            "type": "connected",
            "message": f"Observando a {seller.name}",
            "seller_id": seller_id
        })
        
        # Mantener conexión abierta
        while True:
            # Esperar mensajes del cliente (ping/pong)
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except:
                break
    
    except WebSocketDisconnect:
        print(f"❌ Observador desconectado de vendedor {seller_id}")
    except Exception as e:
        print(f"❌ Error en WebSocket watch: {e}")
    finally:
        manager.disconnect(websocket, seller_id)
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/watch-all")
async def websocket_watch_all_locations(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    WebSocket para que ADMIN vea TODOS los vendedores activos.
    
    El cliente recibe mensajes con formato:
    {
        "type": "all_locations",
        "data": {
            "1": {...},
            "2": {...}
        }
    }
    """
    await websocket.accept()
    
    # TODO: Validar que el usuario es ADMIN
    # (requiere implementar autenticación en WebSocket)
    
    print(f"👑 ADMIN conectado para ver todos los vendedores")
    
    try:
        # Enviar ubicaciones iniciales
        all_locations = manager.get_all_locations()
        await websocket.send_json({
            "type": "all_locations",
            "data": all_locations
        })
        
        # Mantener conexión y enviar actualizaciones
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                # Enviar todas las ubicaciones actuales
                all_locations = manager.get_all_locations()
                await websocket.send_json({
                    "type": "all_locations",
                    "data": all_locations
                })
    
    except WebSocketDisconnect:
        print(f"❌ ADMIN desconectado")
    except Exception as e:
        print(f"❌ Error en WebSocket watch-all: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass


# ============================================================================
# REST ENDPOINTS (fallback)
# ============================================================================

@router.get("/location/{seller_id}")
async def get_seller_location(
    seller_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene la última ubicación conocida de un vendedor (fallback HTTP).
    
    PERMISOS:
    - ADMIN: Puede ver cualquier vendedor
    - VENDEDOR: Solo su propia ubicación
    - TENDERO: Solo su vendedor asignado
    """
    # TODO: Implementar validación de permisos similar a routes_router
    
    location = manager.get_location(seller_id)
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay ubicación disponible para vendedor {seller_id}"
        )
    
    return location


@router.get("/locations")
async def get_all_locations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene todas las ubicaciones activas (solo ADMIN).
    """
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver todas las ubicaciones"
        )
    
    return manager.get_all_locations()