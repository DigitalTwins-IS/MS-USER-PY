# Documentación Técnica Completa - MS-USER-PY
## Historia de Usuario 18: Seguimiento en Tiempo Real

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Arquitectura General](#arquitectura-general)
3. [HU18: Sistema de Seguimiento en Tiempo Real](#hu18-sistema-de-seguimiento-en-tiempo-real)
4. [APIs Públicas por Módulo](#apis-públicas-por-módulo)
5. [Modelos de Datos](#modelos-de-datos)
6. [Ejemplos de Uso](#ejemplos-de-uso)
7. [Integración con Frontend](#integración-con-frontend)
8. [Guía de Troubleshooting](#guía-de-troubleshooting)

---

## 1. Introducción

### 1.1 Descripción General

**MS-USER-PY** es un microservicio de gestión de usuarios para el Sistema Digital Twins, desarrollado con FastAPI. Proporciona funcionalidades completas para la gestión de vendedores, tenderos, rutas optimizadas y **seguimiento en tiempo real** de ubicaciones GPS.

### 1.2 Características Principales

- ✅ **HU18**: **Seguimiento en tiempo real de vendedores con WebSockets**
  - WebSocket para envío de ubicación GPS por vendedores
  - WebSocket para observación en tiempo real por tenderos
  - Panel administrativo para monitoreo de todos los vendedores
  - APIs REST de fallback para consulta de ubicaciones
  - Sistema de broadcast automático a observadores
  - Gestión eficiente de conexiones con ConnectionManager

### 1.3 Tecnologías

- **Framework**: FastAPI 0.104.1
- **Base de datos**: PostgreSQL con SQLAlchemy
- **Geoespacial**: GeoAlchemy2, Shapely
- **Comunicación en tiempo real**: WebSockets
- **Enrutamiento**: OpenRouteService API
- **Geocodificación**: Nominatim

### 1.4 Configuración

```bash
# Variables de entorno principales
APP_NAME=MS-USER-PY
API_PREFIX=/api/v1/users
DATABASE_URL=postgresql://usuario:password@localhost:5437/digital_twins_db
SERVICE_PORT=8000

# OpenRouteService (para rutas optimizadas)
OPENROUTE_API_KEY=tu_api_key_aqui
OPENROUTE_ENABLED=true

# Servicios externos
MS_AUTH_URL=http://ms-auth-py:8000
MS_GEO_URL=http://ms-geo-py:8000
MS_PRODUCT_URL=http://ms-product-py:8000
```

---

## 2. Arquitectura General

### 2.1 Estructura de Módulos

```
src/
├── main.py                 # Aplicación FastAPI principal
├── config.py              # Configuración global
├── models/                # Modelos de base de datos
│   ├── seller.py
│   ├── shopkeeper.py
│   ├── assignment.py
│   ├── visit.py
│   └── inventory.py
├── routers/               # Endpoints de API
│   ├── sellers.py
│   ├── shopkeepers.py
│   ├── assignments.py
│   ├── routes.py
│   ├── tracking.py        # ⭐ HU18: WebSockets
│   ├── visits.py
│   └── inventory.py
├── schemas/               # Validación con Pydantic
│   ├── tracking.py        # ⭐ HU18: Schemas
│   └── ...
├── clients/              # Clientes de servicios externos
│   ├── openroute_client.py
│   └── nominatim_client.py
└── utils/                # Utilidades
    └── auth.py
```

### 2.2 Diagrama de Flujo - HU18

```
┌─────────────┐          WebSocket          ┌──────────────┐
│  Vendedor   │ ════════════════════════════> │  MS-USER-PY  │
│  (Mobile)   │   Envía coordenadas GPS      │   (Backend)  │
└─────────────┘                              └──────────────┘
                                                     │
                                                     │ Broadcast
                                                     ▼
                                              ┌──────────────┐
                                              │   Tenderos   │
                                              │  (Web/App)   │
                                              └──────────────┘
```

---

## 3. HU18: Sistema de Seguimiento en Tiempo Real

### 3.1 Descripción

La **Historia de Usuario 18** implementa un sistema de seguimiento en tiempo real que permite:

- **Vendedores**: Enviar su ubicación GPS en tiempo real
- **Tenderos**: Ver la ubicación actual del vendedor asignado en un mapa
- **Administradores**: Monitorear todos los vendedores activos simultáneamente

### 3.2 Arquitectura WebSocket

#### 3.2.1 Gestor de Conexiones

```python
class ConnectionManager:
    """
    Maneja las conexiones WebSocket activas.
    
    Estructura de datos:
    - active_connections: {seller_id: Set[WebSocket]} 
    - seller_locations: {seller_id: {lat, lng, timestamp, speed, battery}}
    """
    
    async def connect(websocket, seller_id)
    async def disconnect(websocket, seller_id)
    async def update_location(seller_id, location_data)
    def get_location(seller_id) -> dict
    def get_all_locations() -> dict
```

#### 3.2.2 Endpoints WebSocket

| Endpoint | Rol | Descripción |
|----------|-----|-------------|
| `/ws/send/{seller_id}` | **VENDEDOR** | Enviar ubicación GPS |
| `/ws/watch/{seller_id}` | **TENDERO/ADMIN** | Observar vendedor |
| `/ws/watch-all` | **ADMIN** | Observar todos |

---

### 3.3 API WebSocket Detallada

#### 3.3.1 WS Send Location (Vendedor Envía Ubicación)

**Endpoint**: `ws://api.example.com/api/v1/users/tracking/ws/send/{seller_id}`

**Método**: WebSocket

**Rol requerido**: VENDEDOR

**Descripción**: El vendedor conecta a este endpoint y envía actualizaciones periódicas de su ubicación GPS.

##### Flujo de Conexión

```javascript
// 1. Establecer conexión
const ws = new WebSocket('ws://localhost:8000/api/v1/users/tracking/ws/send/1');

// 2. Escuchar confirmación
ws.onopen = () => {
    console.log('Conectado como vendedor');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Mensaje del servidor:', data);
    // Tipos: "connected", "location_received", "error"
};
```

##### Formato de Mensaje (Cliente → Servidor)

```json
{
    "latitude": 4.6234,
    "longitude": -74.0654,
    "speed": 15.5,
    "battery": 85
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `latitude` | float | ✅ Sí | Latitud GPS (-90 a 90) |
| `longitude` | float | ✅ Sí | Longitud GPS (-180 a 180) |
| `speed` | float | ❌ No | Velocidad en km/h |
| `battery` | int | ❌ No | Nivel de batería (0-100) |

##### Formato de Respuesta (Servidor → Cliente)

**Mensaje de Confirmación:**
```json
{
    "type": "connected",
    "message": "Conectado como Juan Pérez",
    "seller_id": 1
}
```

**Confirmación de Ubicación:**
```json
{
    "type": "location_received",
    "timestamp": "2025-11-28T14:30:00"
}
```

**Error:**
```json
{
    "type": "error",
    "message": "latitude y longitude son requeridos"
}
```

##### Ejemplo Completo en Python

```python
import asyncio
import websockets
import json
import random

async def send_location(seller_id: int):
    """Simula un vendedor enviando su ubicación"""
    uri = f"ws://localhost:8000/api/v1/users/tracking/ws/send/{seller_id}"
    
    async with websockets.connect(uri) as websocket:
        # Recibir confirmación de conexión
        response = await websocket.recv()
        print(f"Servidor: {response}")
        
        # Enviar ubicaciones cada 5 segundos
        base_lat = 4.6097
        base_lon = -74.0817
        
        for i in range(10):
            # Simular movimiento
            location = {
                "latitude": base_lat + random.uniform(-0.01, 0.01),
                "longitude": base_lon + random.uniform(-0.01, 0.01),
                "speed": random.uniform(0, 40),
                "battery": 100 - i * 5
            }
            
            await websocket.send(json.dumps(location))
            print(f"Enviado: {location}")
            
            # Esperar confirmación
            response = await websocket.recv()
            print(f"Confirmación: {response}")
            
            await asyncio.sleep(5)

# Ejecutar
asyncio.run(send_location(seller_id=1))
```

##### Ejemplo en JavaScript (React Native / Mobile)

```javascript
class SellerLocationService {
    constructor(sellerId) {
        this.sellerId = sellerId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        const url = `ws://api.example.com/api/v1/users/tracking/ws/send/${this.sellerId}`;
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('✅ Conexión establecida');
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch(data.type) {
                case 'connected':
                    console.log('✅', data.message);
                    this.startSendingLocation();
                    break;
                case 'location_received':
                    console.log('📍 Ubicación confirmada');
                    break;
                case 'error':
                    console.error('❌', data.message);
                    break;
            }
        };

        this.ws.onerror = (error) => {
            console.error('❌ Error WebSocket:', error);
        };

        this.ws.onclose = () => {
            console.log('🔌 Conexión cerrada');
            this.attemptReconnect();
        };
    }

    startSendingLocation() {
        // Enviar ubicación cada 10 segundos
        this.locationInterval = setInterval(() => {
            this.getCurrentPosition();
        }, 10000);
    }

    getCurrentPosition() {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const location = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    speed: position.coords.speed || 0,
                    battery: this.getBatteryLevel()
                };
                
                this.sendLocation(location);
            },
            (error) => {
                console.error('Error obteniendo GPS:', error);
            }
        );
    }

    sendLocation(location) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(location));
            console.log('📍 Ubicación enviada:', location);
        }
    }

    getBatteryLevel() {
        // Implementar según plataforma
        return 100; // Placeholder
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`🔄 Reintentando conexión (${this.reconnectAttempts})...`);
                this.connect();
            }, 3000 * this.reconnectAttempts);
        }
    }

    disconnect() {
        if (this.locationInterval) {
            clearInterval(this.locationInterval);
        }
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Uso
const service = new SellerLocationService(1);
service.connect();
```

---

#### 3.3.2 WS Watch Location (Observar Vendedor)

**Endpoint**: `ws://api.example.com/api/v1/users/tracking/ws/watch/{seller_id}`

**Método**: WebSocket

**Rol requerido**: TENDERO, ADMIN

**Descripción**: Permite observar la ubicación en tiempo real de un vendedor específico.

##### Flujo de Conexión

```javascript
// 1. Conectar al vendedor
const ws = new WebSocket('ws://localhost:8000/api/v1/users/tracking/ws/watch/1');

// 2. Recibir actualizaciones automáticas
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'location_update') {
        updateMapMarker(message.data);
    }
};

// 3. Enviar ping para mantener conexión
setInterval(() => {
    ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

##### Formato de Mensaje (Servidor → Cliente)

**Actualización de Ubicación:**
```json
{
    "type": "location_update",
    "data": {
        "seller_id": 1,
        "seller_name": "Juan Pérez",
        "latitude": 4.6234,
        "longitude": -74.0654,
        "speed": 15.5,
        "battery": 85,
        "timestamp": "2025-11-28T14:30:00"
    }
}
```

**Confirmación de Conexión:**
```json
{
    "type": "connected",
    "message": "Observando a Juan Pérez",
    "seller_id": 1
}
```

##### Ejemplo Completo en React

```jsx
import React, { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';

function SellerTrackingMap({ sellerId }) {
    const [location, setLocation] = useState(null);
    const [status, setStatus] = useState('Desconectado');
    const wsRef = useRef(null);

    useEffect(() => {
        // Conectar WebSocket
        const ws = new WebSocket(
            `ws://localhost:8000/api/v1/users/tracking/ws/watch/${sellerId}`
        );
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('✅ Conectado al tracking');
            setStatus('Conectado');
        };

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);

            switch(message.type) {
                case 'connected':
                    console.log(message.message);
                    break;

                case 'location_update':
                    console.log('📍 Ubicación actualizada:', message.data);
                    setLocation(message.data);
                    setStatus('Recibiendo datos');
                    break;

                case 'error':
                    console.error('❌ Error:', message.message);
                    setStatus('Error');
                    break;
            }
        };

        ws.onerror = (error) => {
            console.error('❌ Error WebSocket:', error);
            setStatus('Error de conexión');
        };

        ws.onclose = () => {
            console.log('🔌 Conexión cerrada');
            setStatus('Desconectado');
        };

        // Ping cada 30 segundos
        const pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);

        // Cleanup
        return () => {
            clearInterval(pingInterval);
            ws.close();
        };
    }, [sellerId]);

    if (!location) {
        return (
            <div className="tracking-loading">
                <p>Estado: {status}</p>
                <p>Esperando ubicación del vendedor...</p>
            </div>
        );
    }

    return (
        <div className="tracking-container">
            <div className="tracking-header">
                <h2>Seguimiento: {location.seller_name}</h2>
                <span className={`status ${status.toLowerCase()}`}>
                    {status}
                </span>
            </div>

            <div className="tracking-info">
                <div className="info-item">
                    <span>🔋 Batería:</span>
                    <strong>{location.battery}%</strong>
                </div>
                <div className="info-item">
                    <span>🚗 Velocidad:</span>
                    <strong>{location.speed.toFixed(1)} km/h</strong>
                </div>
                <div className="info-item">
                    <span>🕐 Última actualización:</span>
                    <strong>{new Date(location.timestamp).toLocaleTimeString()}</strong>
                </div>
            </div>

            <MapContainer
                center={[location.latitude, location.longitude]}
                zoom={15}
                style={{ height: '500px', width: '100%' }}
            >
                <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; OpenStreetMap contributors'
                />
                <Marker position={[location.latitude, location.longitude]}>
                    <Popup>
                        <div>
                            <strong>{location.seller_name}</strong>
                            <p>Velocidad: {location.speed} km/h</p>
                            <p>Batería: {location.battery}%</p>
                        </div>
                    </Popup>
                </Marker>
            </MapContainer>
        </div>
    );
}

export default SellerTrackingMap;
```

---

#### 3.3.3 WS Watch All (Administrador: Todos los Vendedores)

**Endpoint**: `ws://api.example.com/api/v1/users/tracking/ws/watch-all`

**Método**: WebSocket

**Rol requerido**: ADMIN

**Descripción**: Permite al administrador ver todos los vendedores activos simultáneamente.

##### Formato de Mensaje

```json
{
    "type": "all_locations",
    "data": {
        "1": {
            "seller_id": 1,
            "seller_name": "Juan Pérez",
            "latitude": 4.6234,
            "longitude": -74.0654,
            "speed": 15.5,
            "battery": 85,
            "timestamp": "2025-11-28T14:30:00"
        },
        "2": {
            "seller_id": 2,
            "seller_name": "María González",
            "latitude": 4.6100,
            "longitude": -74.0700,
            "speed": 20.0,
            "battery": 90,
            "timestamp": "2025-11-28T14:29:55"
        }
    }
}
```

##### Ejemplo en React (Dashboard Administrativo)

```jsx
import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';

function AdminTrackingDashboard() {
    const [sellers, setSellers] = useState({});
    const [stats, setStats] = useState({ total: 0, active: 0 });

    useEffect(() => {
        const ws = new WebSocket(
            'ws://localhost:8000/api/v1/users/tracking/ws/watch-all'
        );

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);

            if (message.type === 'all_locations') {
                setSellers(message.data);
                
                // Calcular estadísticas
                const total = Object.keys(message.data).length;
                const active = Object.values(message.data).filter(
                    s => s.speed > 0
                ).length;
                
                setStats({ total, active });
            }
        };

        // Ping periódico para recibir actualizaciones
        const pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 10000); // Cada 10 segundos

        return () => {
            clearInterval(pingInterval);
            ws.close();
        };
    }, []);

    return (
        <div className="admin-dashboard">
            <h1>Panel de Seguimiento - Todos los Vendedores</h1>
            
            <div className="stats-bar">
                <div className="stat-card">
                    <h3>Total Vendedores</h3>
                    <p className="stat-value">{stats.total}</p>
                </div>
                <div className="stat-card">
                    <h3>En Movimiento</h3>
                    <p className="stat-value">{stats.active}</p>
                </div>
            </div>

            <MapContainer
                center={[4.6097, -74.0817]}
                zoom={12}
                style={{ height: '600px', width: '100%' }}
            >
                <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                
                {Object.values(sellers).map(seller => (
                    <Marker
                        key={seller.seller_id}
                        position={[seller.latitude, seller.longitude]}
                    >
                        <Popup>
                            <div>
                                <strong>{seller.seller_name}</strong>
                                <p>🚗 {seller.speed.toFixed(1)} km/h</p>
                                <p>🔋 {seller.battery}%</p>
                                <p>🕐 {new Date(seller.timestamp).toLocaleTimeString()}</p>
                            </div>
                        </Popup>
                    </Marker>
                ))}
            </MapContainer>

            <div className="sellers-list">
                <h2>Lista de Vendedores Activos</h2>
                {Object.values(sellers).map(seller => (
                    <div key={seller.seller_id} className="seller-card">
                        <h3>{seller.seller_name}</h3>
                        <p>Velocidad: {seller.speed} km/h</p>
                        <p>Batería: {seller.battery}%</p>
                        <p>Última actualización: {new Date(seller.timestamp).toLocaleString()}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default AdminTrackingDashboard;
```

---

### 3.4 APIs REST (Fallback HTTP)

Además de WebSockets, se proporcionan endpoints REST para obtener la última ubicación conocida:

#### 3.4.1 Obtener Ubicación de Vendedor

```http
GET /api/v1/users/tracking/location/{seller_id}
```

**Headers:**
```
Authorization: Bearer {token}
```

**Respuesta:**
```json
{
    "seller_id": 1,
    "seller_name": "Juan Pérez",
    "latitude": 4.6234,
    "longitude": -74.0654,
    "speed": 15.5,
    "battery": 85,
    "timestamp": "2025-11-28T14:30:00"
}
```

**Ejemplo cURL:**
```bash
curl -X GET "http://localhost:8000/api/v1/users/tracking/location/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 3.4.2 Obtener Todas las Ubicaciones (Solo ADMIN)

```http
GET /api/v1/users/tracking/locations
```

**Respuesta:**
```json
{
    "1": {
        "seller_id": 1,
        "seller_name": "Juan Pérez",
        "latitude": 4.6234,
        "longitude": -74.0654,
        "speed": 15.5,
        "battery": 85,
        "timestamp": "2025-11-28T14:30:00"
    },
    "2": { ... }
}
```

---

### 3.5 Control de Permisos

| Endpoint | ADMIN | VENDEDOR | TENDERO |
|----------|-------|----------|---------|
| `ws/send/{seller_id}` | ❌ | ✅ (solo su ID) | ❌ |
| `ws/watch/{seller_id}` | ✅ | ❌ | ✅ (solo su vendedor) |
| `ws/watch-all` | ✅ | ❌ | ❌ |
| `GET /location/{seller_id}` | ✅ | ✅ (solo su ID) | ✅ (solo su vendedor) |
| `GET /locations` | ✅ | ❌ | ❌ |

---

## 4. APIs de Tracking en Tiempo Real (HU18)

### 4.1 WebSocket: Enviar Ubicación (Vendedor)

**Endpoint**: `ws://api.example.com/api/v1/users/tracking/ws/send/{seller_id}`

**Método**: WebSocket

**Descripción**: Permite al vendedor enviar su ubicación GPS en tiempo real.

**Request (Cliente → Servidor)**:
```json
{
    "latitude": 4.6234,
    "longitude": -74.0654,
    "speed": 15.5,
    "battery": 85
}
```

**Response (Servidor → Cliente)**:
```json
{
    "type": "location_received",
    "timestamp": "2025-11-28T14:30:00Z"
}
```

---

### 4.2 WebSocket: Observar Vendedor

**Endpoint**: `ws://api.example.com/api/v1/users/tracking/ws/watch/{seller_id}`

**Método**: WebSocket

**Descripción**: Permite observar la ubicación en tiempo real de un vendedor específico.

**Response (Servidor → Cliente)**:
```json
{
    "type": "location_update",
    "data": {
        "seller_id": 1,
        "seller_name": "Juan Pérez",
        "latitude": 4.6234,
        "longitude": -74.0654,
        "speed": 15.5,
        "battery": 85,
        "timestamp": "2025-11-28T14:30:00Z"
    }
}
```

---

### 4.3 WebSocket: Observar Todos (Admin)

**Endpoint**: `ws://api.example.com/api/v1/users/tracking/ws/watch-all`

**Método**: WebSocket

**Descripción**: Permite al administrador observar todos los vendedores activos.

**Response (Servidor → Cliente)**:
```json
{
    "type": "all_locations",
    "data": {
        "1": {
            "seller_id": 1,
            "seller_name": "Juan Pérez",
            "latitude": 4.6234,
            "longitude": -74.0654,
            "speed": 15.5,
            "battery": 85,
            "timestamp": "2025-11-28T14:30:00Z"
        }
    }
}
```

---

### 4.4 REST: Obtener Última Ubicación

**Endpoint**: `GET /api/v1/users/tracking/location/{seller_id}`

**Método**: GET (HTTP REST)

**Descripción**: Obtiene la última ubicación conocida de un vendedor (fallback HTTP).

**Response (200 OK)**:
```json
{
    "seller_id": 1,
    "seller_name": "Juan Pérez",
    "latitude": 4.6234,
    "longitude": -74.0654,
    "speed": 15.5,
    "battery": 85,
    "timestamp": "2025-11-28T14:30:00Z"
}
```

---

### 4.5 REST: Obtener Todas las Ubicaciones

**Endpoint**: `GET /api/v1/users/tracking/locations`

**Método**: GET (HTTP REST)

**Descripción**: Obtiene todas las ubicaciones activas (solo administradores).

**Response (200 OK)**:
```json
{
    "1": {
        "seller_id": 1,
        "seller_name": "Juan Pérez",
        "latitude": 4.6234,
        "longitude": -74.0654,
        "speed": 15.5,
        "battery": 85,
        "timestamp": "2025-11-28T14:30:00Z"
    }
}

---

## 5. Modelos de Datos

### 5.1 Modelo: Seller (Vendedor)

```python
class Seller(Base):
    __tablename__ = "sellers"
    
    id: int                    # PK
    user_id: int               # FK a MS-AUTH
    name: str                  # Nombre completo
    email: str                 # Email único
    phone: str                 # Teléfono
    address: str               # Dirección
    zone_id: int               # FK a zona
    is_active: bool            # Estado
    created_at: datetime
    updated_at: datetime
```

### 5.2 Modelo: Shopkeeper (Tendero)

```python
class Shopkeeper(Base):
    __tablename__ = "shopkeepers"
    
    id: int
    name: str                  # Nombre del tendero
    business_name: str         # Nombre del negocio
    address: str               # Dirección física
    phone: str
    email: str
    latitude: Decimal          # -5 a 13 (Colombia)
    longitude: Decimal         # -80 a -66 (Colombia)
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 5.3 Modelo: Assignment (Asignación)

```python
class Assignment(Base):
    __tablename__ = "assignments"
    
    id: int
    seller_id: int             # FK a Seller
    shopkeeper_id: int         # FK a Shopkeeper
    assigned_at: datetime
    assigned_by: int           # FK a User
    is_active: bool
    unassigned_by: int         # FK a User (si se desasigna)
    notes: str
```

### 5.4 Modelo: Visit (Visita)

```python
class Visit(Base):
    __tablename__ = "visits"
    
    id: int
    seller_id: int
    shopkeeper_id: int
    scheduled_date: datetime   # Fecha agendada (timezone-aware)
    status: str                # pending, completed, cancelled
    reason: str                # Motivo de visita
    notes: str
    completed_at: datetime
    cancelled_at: datetime
    cancelled_reason: str
    created_at: datetime
    updated_at: datetime
```

### 5.5 Modelo: ShopkeeperInventory

```python
class ShopkeeperInventory(Base):
    __tablename__ = "inventories"
    
    id: int
    shopkeeper_id: int
    product_id: int            # FK a MS-PRODUCT
    product_name: str          # Cache del nombre
    product_category: str
    unit_price: Decimal
    current_stock: Decimal
    min_stock: Decimal
    max_stock: Decimal
    is_active: bool
    last_updated: datetime
```

### 5.6 Modelo: SellerIncident (Incidencia)

```python
class SellerIncident(Base):
    __tablename__ = "seller_incidents"
    
    id: int
    seller_id: int
    shopkeeper_id: int
    visit_id: int              # Opcional
    type: str                  # absence, delay, non_compliance
    description: str
    incident_date: date
    created_at: datetime
    updated_at: datetime
```

---

## 6. Ejemplos de Uso

### 6.1 Flujo Completo: Crear Vendedor y Asignar Tenderos

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/users"
TOKEN = "your_bearer_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. Crear vendedor
seller_data = {
    "name": "María González",
    "email": "maria.gonzalez@vendedor.com",
    "phone": "3009876543",
    "address": "Carrera 7 #50-20",
    "zone_id": 2
}

response = requests.post(f"{BASE_URL}/sellers", json=seller_data, headers=headers)
seller = response.json()
print(f"✅ Vendedor creado: ID {seller['id']}")

# 2. Crear tenderos
shopkeepers_data = [
    {
        "name": "Tienda Don Pedro",
        "business_name": "Minimercado Don Pedro",
        "address": "Calle 60 #8-15",
        "phone": "6011234567",
        "latitude": 4.6500,
        "longitude": -74.0900
    },
    {
        "name": "Tienda La Esquina",
        "business_name": "Tienda La Esquina",
        "address": "Carrera 10 #65-30",
        "phone": "6017654321",
        "latitude": 4.6600,
        "longitude": -74.0850
    }
]

shopkeeper_ids = []
for shop_data in shopkeepers_data:
    response = requests.post(f"{BASE_URL}/shopkeepers", json=shop_data, headers=headers)
    shop = response.json()
    shopkeeper_ids.append(shop['id'])
    print(f"✅ Tendero creado: ID {shop['id']}")

# 3. Asignar tenderos al vendedor
for shop_id in shopkeeper_ids:
    assignment_data = {
        "seller_id": seller['id'],
        "shopkeeper_id": shop_id,
        "notes": "Asignación inicial"
    }
    response = requests.post(f"{BASE_URL}/assign", json=assignment_data, headers=headers)
    print(f"✅ Asignación creada: Vendedor {seller['id']} → Tendero {shop_id}")

print(f"\n✅ Proceso completo: Vendedor {seller['name']} tiene {len(shopkeeper_ids)} tenderos asignados")
```

### 6.2 Flujo: Generar Ruta y Seguimiento en Tiempo Real

```python
import asyncio
import websockets
import requests
import json

# 1. Generar ruta optimizada
response = requests.get(
    "http://localhost:8000/api/v1/users/routes/optimize",
    params={
        "seller_id": 1,
        "start_latitude": 4.6097,
        "start_longitude": -74.0817
    },
    headers={"Authorization": f"Bearer {TOKEN}"}
)

route = response.json()
print(f"📍 Ruta generada: {route['statistics']['total_shopkeepers']} puntos")
print(f"📏 Distancia total: {route['statistics']['total_distance_km']} km")
print(f"⏱️  Tiempo estimado: {route['statistics']['estimated_total_time_hours']} horas")

# 2. Iniciar seguimiento en tiempo real
async def track_seller():
    uri = "ws://localhost:8000/api/v1/users/tracking/ws/watch/1"
    
    async with websockets.connect(uri) as websocket:
        print("📡 Conectado al tracking")
        
        async for message in websocket:
            data = json.loads(message)
            
            if data['type'] == 'location_update':
                loc = data['data']
                print(f"📍 Vendedor: {loc['seller_name']}")
                print(f"   📍 Ubicación: {loc['latitude']}, {loc['longitude']}")
                print(f"   🚗 Velocidad: {loc['speed']} km/h")
                print(f"   🔋 Batería: {loc['battery']}%")

asyncio.run(track_seller())
```

### 6.3 Flujo: Agendar Visita por Bajo Stock

```python
# 1. Obtener tenderos con bajo stock
response = requests.get(
    f"{BASE_URL}/visits/shopkeepers/low-stock",
    params={"seller_id": 1},
    headers=headers
)

low_stock_shopkeepers = response.json()
print(f"⚠️  {len(low_stock_shopkeepers)} tenderos con bajo stock")

# 2. Agendar visitas prioritarias
for shop in low_stock_shopkeepers[:5]:  # Top 5
    visit_data = {
        "shopkeeper_id": shop['shopkeeper_id'],
        "scheduled_date": "2025-11-29T10:00:00-05:00",
        "reason": "reabastecimiento",
        "notes": f"Bajo stock: {shop['low_stock_count']} productos"
    }
    
    response = requests.post(
        f"{BASE_URL}/visits",
        json=visit_data,
        headers=headers
    )
    
    visit = response.json()
    print(f"✅ Visita agendada: {shop['shopkeeper_name']} - {visit['scheduled_date']}")
```

---

## 7. Integración con Frontend

### 7.1 React Component: Tracking en Vivo

```jsx
// TrackingPage.jsx
import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL;
const WS_BASE_URL = process.env.REACT_APP_WS_URL;

function TrackingPage({ sellerId }) {
    const [sellerLocation, setSellerLocation] = useState(null);
    const [route, setRoute] = useState(null);
    const [ws, setWs] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState('Desconectado');

    // Cargar ruta optimizada
    useEffect(() => {
        loadRoute();
    }, [sellerId]);

    // Conectar WebSocket
    useEffect(() => {
        const websocket = new WebSocket(`${WS_BASE_URL}/tracking/ws/watch/${sellerId}`);
        
        websocket.onopen = () => {
            setConnectionStatus('Conectado');
        };

        websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'location_update') {
                setSellerLocation(message.data);
            }
        };

        websocket.onerror = () => {
            setConnectionStatus('Error');
        };

        websocket.onclose = () => {
            setConnectionStatus('Desconectado');
        };

        setWs(websocket);

        return () => {
            if (websocket) {
                websocket.close();
            }
        };
    }, [sellerId]);

    const loadRoute = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/routes/optimize`, {
                params: { seller_id: sellerId }
            });
            setRoute(response.data);
        } catch (error) {
            console.error('Error cargando ruta:', error);
        }
    };

    if (!sellerLocation || !route) {
        return (
            <div className="loading">
                <p>Estado: {connectionStatus}</p>
                <p>Cargando mapa...</p>
            </div>
        );
    }

    return (
        <div className="tracking-page">
            <header className="tracking-header">
                <h1>Seguimiento: {sellerLocation.seller_name}</h1>
                <div className="stats">
                    <span className="stat">🔋 {sellerLocation.battery}%</span>
                    <span className="stat">🚗 {sellerLocation.speed} km/h</span>
                    <span className="stat">📍 {connectionStatus}</span>
                </div>
            </header>

            <MapContainer
                center={[sellerLocation.latitude, sellerLocation.longitude]}
                zoom={13}
                style={{ height: '600px', width: '100%' }}
            >
                <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; OpenStreetMap contributors'
                />

                {/* Marcador del vendedor */}
                <Marker position={[sellerLocation.latitude, sellerLocation.longitude]}>
                    <Popup>
                        <div>
                            <strong>{sellerLocation.seller_name}</strong>
                            <p>Velocidad: {sellerLocation.speed} km/h</p>
                            <p>Última actualización: {new Date(sellerLocation.timestamp).toLocaleTimeString()}</p>
                        </div>
                    </Popup>
                </Marker>

                {/* Marcadores de tenderos en la ruta */}
                {route.route_points.map(point => (
                    <Marker
                        key={point.shopkeeper_id}
                        position={[point.latitude, point.longitude]}
                    >
                        <Popup>
                            <div>
                                <strong>#{point.order}. {point.shopkeeper_name}</strong>
                                <p>{point.business_name}</p>
                                <p>{point.address}</p>
                                <p>Distancia: {point.distance_from_previous_km} km</p>
                            </div>
                        </Popup>
                    </Marker>
                ))}
            </MapContainer>

            <div className="route-info">
                <h2>Información de Ruta</h2>
                <div className="route-stats">
                    <div className="stat-card">
                        <h3>Total Clientes</h3>
                        <p>{route.statistics.total_shopkeepers}</p>
                    </div>
                    <div className="stat-card">
                        <h3>Distancia Total</h3>
                        <p>{route.statistics.total_distance_km} km</p>
                    </div>
                    <div className="stat-card">
                        <h3>Tiempo Estimado</h3>
                        <p>{route.statistics.estimated_total_time_hours} hrs</p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default TrackingPage;
```

---

## 8. Guía de Troubleshooting

### 8.1 WebSocket: Problemas Comunes

#### Problema: "WebSocket connection failed"

**Posibles causas:**
- Servidor no está ejecutándose
- URL incorrecta (ws:// vs wss://)
- Firewall bloqueando conexión

**Solución:**
```bash
# Verificar que el servidor esté corriendo
curl http://localhost:8000/health

# Probar WebSocket con wscat
npm install -g wscat
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/watch/1
```

#### Problema: "Unauthorized" en WebSocket

**Causa**: Autenticación no implementada en WebSocket

**Solución temporal**: Las conexiones WebSocket actualmente no requieren autenticación. En producción, implementar autenticación via token en query params:

```javascript
const ws = new WebSocket(`ws://api.com/tracking/ws/watch/1?token=${auth_token}`);
```

#### Problema: Conexión se cierra después de 30 segundos

**Causa**: Timeout de proxy/load balancer

**Solución**: Enviar pings periódicos
```javascript
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 20000); // Cada 20 segundos
```

### 8.2 Rutas: Problemas Comunes

#### Problema: "OpenRouteService no está configurado"

**Causa**: `OPENROUTE_API_KEY` no configurada

**Solución:**
```bash
# .env
OPENROUTE_API_KEY=tu_api_key_aqui
OPENROUTE_ENABLED=true
```

Obtener API key en: https://openrouteservice.org/dev/#/signup

#### Problema: Ruta no se genera para más de 50 puntos

**Causa**: Límite de OpenRouteService gratuito

**Solución**: Automáticamente se limita a 50 puntos. Para más puntos, actualizar a plan pagado.

### 8.3 Permisos: Errores 403

#### Problema: "No tienes permisos para..."

**Causa**: Token JWT no tiene el rol correcto

**Solución**: Verificar el rol en el token
```python
import jwt

token = "tu_token_aqui"
decoded = jwt.decode(token, options={"verify_signature": False})
print(f"Rol: {decoded.get('role')}")
```

---

## 9. Conclusión

Esta documentación cubre todas las APIs públicas del microservicio MS-USER-PY, con énfasis especial en la **Historia de Usuario 18** (HU18) - Sistema de Seguimiento en Tiempo Real.

### 9.1 Características Destacadas

✅ **Seguimiento en tiempo real** con WebSockets  
✅ **Rutas optimizadas** con OpenRouteService API  
✅ **Gestión completa** de vendedores y tenderos  
✅ **Sistema de visitas** basado en inventario  
✅ **Control de permisos** granular por rol  

### 9.2 Próximos Pasos

Para implementar el frontend completo:
1. Implementar componente de mapa con React Leaflet
2. Integrar WebSockets para seguimiento en vivo
3. Crear dashboard administrativo con estadísticas
4. Implementar notificaciones push para tenderos
5. Agregar autenticación en WebSockets

### 9.3 Soporte

Para más información o soporte técnico, contactar al equipo de desarrollo.

---

**Última actualización**: Noviembre 28, 2025  
**Versión**: 1.0.0  
**Autor**: MS-USER-PY Development Team
