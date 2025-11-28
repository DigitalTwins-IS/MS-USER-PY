# 🚀 HU18 - Cheat Sheet de Referencia Rápida
## Seguimiento en Tiempo Real - Guía de Bolsillo

---

## 📡 URLs de WebSocket

```bash
# Vendedor envía ubicación
ws://localhost:8000/api/v1/users/tracking/ws/send/{seller_id}

# Observar vendedor específico
ws://localhost:8000/api/v1/users/tracking/ws/watch/{seller_id}

# Observar todos (Admin)
ws://localhost:8000/api/v1/users/tracking/ws/watch-all
```

---

## 📤 Formato de Mensajes

### Vendedor → Servidor (Enviar ubicación)

```json
{
    "latitude": 4.6234,
    "longitude": -74.0654,
    "speed": 15.5,
    "battery": 85
}
```

### Servidor → Cliente (Actualización)

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

---

## 🔑 Códigos de Mensaje

| Type | Descripción | Quién lo envía |
|------|-------------|----------------|
| `connected` | Confirmación de conexión | Servidor |
| `location_received` | Ubicación procesada | Servidor |
| `location_update` | Nueva ubicación disponible | Servidor |
| `error` | Error en procesamiento | Servidor |
| `ping` | Keep-alive | Cliente |
| `pong` | Respuesta keep-alive | Servidor |

---

## 💻 Snippets de Código

### Python - Enviar Ubicación

```python
import asyncio
import websockets
import json

async def send_location(seller_id, lat, lon):
    uri = f"ws://localhost:8000/api/v1/users/tracking/ws/send/{seller_id}"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "latitude": lat,
            "longitude": lon,
            "speed": 25.0,
            "battery": 85
        }))
        response = await ws.recv()
        print(response)

asyncio.run(send_location(1, 4.6097, -74.0817))
```

### Python - Observar Vendedor

```python
import asyncio
import websockets
import json

async def watch_seller(seller_id):
    uri = f"ws://localhost:8000/api/v1/users/tracking/ws/watch/{seller_id}"
    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            if data['type'] == 'location_update':
                print(f"Ubicación: {data['data']}")

asyncio.run(watch_seller(1))
```

### JavaScript - Enviar Ubicación

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/users/tracking/ws/send/1');

ws.onopen = () => {
    // Enviar cada 10 segundos
    setInterval(() => {
        ws.send(JSON.stringify({
            latitude: 4.6097,
            longitude: -74.0817,
            speed: 25.0,
            battery: 85
        }));
    }, 10000);
};

ws.onmessage = (event) => {
    console.log('Servidor:', JSON.parse(event.data));
};
```

### JavaScript - Observar Vendedor

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/users/tracking/ws/watch/1');

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'location_update') {
        const loc = message.data;
        console.log(`${loc.seller_name}: ${loc.latitude}, ${loc.longitude}`);
        // Actualizar mapa
        updateMapMarker(loc.latitude, loc.longitude);
    }
};
```

### React Hook - Tracking

```jsx
import { useEffect, useState } from 'react';

function useSellerTracking(sellerId) {
    const [location, setLocation] = useState(null);
    const [status, setStatus] = useState('disconnected');

    useEffect(() => {
        const ws = new WebSocket(
            `ws://localhost:8000/api/v1/users/tracking/ws/watch/${sellerId}`
        );

        ws.onopen = () => setStatus('connected');
        ws.onclose = () => setStatus('disconnected');
        ws.onerror = () => setStatus('error');

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'location_update') {
                setLocation(msg.data);
            }
        };

        return () => ws.close();
    }, [sellerId]);

    return { location, status };
}

// Uso
function TrackingComponent() {
    const { location, status } = useSellerTracking(1);
    
    return (
        <div>
            <p>Estado: {status}</p>
            {location && (
                <p>
                    {location.seller_name}: 
                    {location.latitude}, {location.longitude}
                </p>
            )}
        </div>
    );
}
```

### React Native - GPS Tracking

```javascript
import Geolocation from 'react-native-geolocation-service';

class LocationService {
    constructor(sellerId) {
        this.sellerId = sellerId;
        this.ws = null;
    }

    start() {
        this.ws = new WebSocket(
            `ws://api.com/api/v1/users/tracking/ws/send/${this.sellerId}`
        );

        this.watchId = Geolocation.watchPosition(
            (position) => {
                if (this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        speed: position.coords.speed || 0
                    }));
                }
            },
            (error) => console.error(error),
            { 
                enableHighAccuracy: true,
                interval: 10000,
                distanceFilter: 50
            }
        );
    }

    stop() {
        Geolocation.clearWatch(this.watchId);
        this.ws?.close();
    }
}

// Uso
const service = new LocationService(1);
service.start();
```

---

## 🛠️ cURL y wscat

### REST Fallback - Obtener última ubicación

```bash
# Ubicación de vendedor específico
curl -X GET "http://localhost:8000/api/v1/users/tracking/location/1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Todas las ubicaciones (Admin)
curl -X GET "http://localhost:8000/api/v1/users/tracking/locations" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### wscat - Testing WebSocket

```bash
# Instalar wscat
npm install -g wscat

# Conectar como vendedor
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/send/1

# Enviar ubicación (escribir y presionar Enter)
> {"latitude": 4.6097, "longitude": -74.0817, "speed": 25, "battery": 85}

# Conectar como observador
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/watch/1
```

---

## 🔒 Permisos

| Acción | ADMIN | VENDEDOR | TENDERO |
|--------|-------|----------|---------|
| Enviar ubicación | ❌ | ✅ (solo su ID) | ❌ |
| Ver vendedor | ✅ | ❌ | ✅ (solo su vendedor) |
| Ver todos | ✅ | ❌ | ❌ |
| REST /location/{id} | ✅ | ✅ (solo su ID) | ✅ (solo su vendedor) |
| REST /locations | ✅ | ❌ | ❌ |

---

## ⚠️ Validaciones

### Coordenadas
- **Latitud**: -90 a 90 (Colombia: -5 a 13)
- **Longitud**: -180 a 180 (Colombia: -80 a -66)

### Campos Requeridos
- ✅ `latitude` (obligatorio)
- ✅ `longitude` (obligatorio)
- ⚪ `speed` (opcional)
- ⚪ `battery` (opcional)

### Límites
- **Frecuencia**: Máximo 6 actualizaciones/minuto
- **Tamaño mensaje**: Máximo 1KB
- **Conexiones simultáneas**: 100+ vendedores

---

## 🐛 Errores Comunes

### 1. Connection Failed

**Síntoma**: `WebSocket connection to 'ws://...' failed`

**Causas**:
- Servidor no está corriendo
- URL incorrecta (verificar http vs https, ws vs wss)
- Firewall bloqueando

**Solución**:
```bash
# Verificar servidor
curl http://localhost:8000/health

# Probar con wscat
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/watch/1
```

### 2. Unauthorized

**Síntoma**: HTTP 401 o 403

**Causa**: Token JWT inválido o rol incorrecto

**Solución**:
```bash
# Verificar token
curl http://localhost:8000/api/v1/users/sellers \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. latitude y longitude son requeridos

**Síntoma**: Error al enviar ubicación

**Causa**: Faltan campos obligatorios

**Solución**:
```javascript
// ❌ Incorrecto
ws.send(JSON.stringify({ speed: 25 }));

// ✅ Correcto
ws.send(JSON.stringify({
    latitude: 4.6097,
    longitude: -74.0817
}));
```

### 4. Conexión se cierra después de 30s

**Síntoma**: WebSocket desconecta automáticamente

**Causa**: Timeout del servidor/proxy

**Solución**: Enviar pings periódicos
```javascript
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 20000); // Cada 20 segundos
```

---

## 📊 Estados de WebSocket

| Estado | Valor | Descripción |
|--------|-------|-------------|
| CONNECTING | 0 | Conectando |
| OPEN | 1 | Conectado y listo |
| CLOSING | 2 | Cerrando conexión |
| CLOSED | 3 | Conexión cerrada |

```javascript
// Verificar estado
console.log(ws.readyState);

// Usar constantes
if (ws.readyState === WebSocket.OPEN) {
    ws.send(data);
}
```

---

## 🔄 Reconexión Automática

```javascript
class ReconnectingWebSocket {
    constructor(url, maxRetries = 5) {
        this.url = url;
        this.maxRetries = maxRetries;
        this.retries = 0;
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('✅ Conectado');
            this.retries = 0;
        };

        this.ws.onclose = () => {
            console.log('🔌 Desconectado');
            this.reconnect();
        };

        this.ws.onerror = (error) => {
            console.error('❌ Error:', error);
        };
    }

    reconnect() {
        if (this.retries < this.maxRetries) {
            this.retries++;
            const delay = Math.min(1000 * Math.pow(2, this.retries), 30000);
            console.log(`🔄 Reintentando en ${delay}ms...`);
            setTimeout(() => this.connect(), delay);
        } else {
            console.error('❌ Máximo de reintentos alcanzado');
        }
    }

    send(data) {
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(data);
        }
    }
}

// Uso
const ws = new ReconnectingWebSocket('ws://localhost:8000/...');
```

---

## 📦 Dependencias

### Backend
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
sqlalchemy==2.0.23
pydantic==2.5.0
```

### Frontend Web
```bash
npm install react-leaflet leaflet
```

### Frontend Mobile
```bash
npm install react-native-geolocation-service
npm install @react-native-community/netinfo
```

---

## 🧪 Testing Rápido

### Test 1: Enviar y Recibir

**Terminal 1 (Vendedor)**:
```bash
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/send/1
> {"latitude": 4.6097, "longitude": -74.0817}
```

**Terminal 2 (Observador)**:
```bash
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/watch/1
# Debe mostrar la ubicación enviada en Terminal 1
```

### Test 2: REST Fallback

```bash
# Terminal 1: Enviar ubicación via WebSocket
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/send/1
> {"latitude": 4.6097, "longitude": -74.0817}

# Terminal 2: Obtener via REST
curl http://localhost:8000/api/v1/users/tracking/location/1
```

---

## 📈 Métricas Clave

| Métrica | Valor Esperado |
|---------|----------------|
| Latencia | < 200ms |
| Frecuencia actualización | 10 segundos |
| Tamaño mensaje | ~200 bytes |
| Conexiones simultáneas | 100+ vendedores |
| Observadores por vendedor | Ilimitado |
| Tiempo de reconexión | < 5 segundos |

---

## 🎯 Casos de Uso

### Caso 1: Tendero ve cuando llegará su vendedor

```javascript
// Frontend del tendero
const { location } = useSellerTracking(myAssignedSellerId);

if (location) {
    const distance = calculateDistance(
        myLocation, 
        [location.latitude, location.longitude]
    );
    const eta = distance / location.speed * 60; // minutos
    
    showNotification(`Vendedor llegará en ${eta.toFixed(0)} minutos`);
}
```

### Caso 2: Admin monitorea flota completa

```javascript
// Dashboard administrativo
const ws = new WebSocket('ws://.../tracking/ws/watch-all');

ws.onmessage = (event) => {
    const { data } = JSON.parse(event.data);
    
    // Actualizar mapa con todos los vendedores
    Object.values(data).forEach(seller => {
        updateMarker(seller.seller_id, seller.latitude, seller.longitude);
    });
    
    // Calcular estadísticas
    const moving = Object.values(data).filter(s => s.speed > 0).length;
    updateStats({ total: Object.keys(data).length, moving });
};
```

### Caso 3: Vendedor en campo

```javascript
// App móvil del vendedor
const service = new LocationService(mySellerId);

// Iniciar al comenzar la jornada
service.start();

// Detener al finalizar
service.stop();
```

---

## 📱 Permisos Móviles

### iOS (Info.plist)

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Necesitamos tu ubicación para rastrear tus visitas</string>

<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>Necesitamos tu ubicación en segundo plano</string>
```

### Android (AndroidManifest.xml)

```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
```

---

## 🔗 Enlaces Útiles

- **Documentación completa**: `DOCUMENTACION_API_HU18.md`
- **Swagger UI**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health
- **OpenStreetMap**: https://www.openstreetmap.org/

---

## 🆘 Ayuda Rápida

```bash
# Ver logs del servidor
docker logs -f ms-user-py

# Ver conexiones activas
netstat -an | grep 8000

# Reiniciar servidor
docker restart ms-user-py

# Probar conectividad
curl http://localhost:8000/health
```

---

**Última actualización**: Noviembre 28, 2025  
**Versión**: 1.0.0

---

💡 **Tip**: Guarda este documento como favorito para acceso rápido durante el desarrollo.
