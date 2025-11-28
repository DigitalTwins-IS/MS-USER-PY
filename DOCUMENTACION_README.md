# 📚 Documentación Completa - MS-USER-PY

## Índice de Documentación

Este repositorio contiene la documentación técnica completa del microservicio MS-USER-PY, con énfasis especial en la **Historia de Usuario 18 (HU18): Seguimiento en Tiempo Real**.

---

## 📖 Documentos Disponibles

### 1. Documentación Técnica Completa
**Archivo**: [`DOCUMENTACION_API_HU18.md`](./DOCUMENTACION_API_HU18.md)

**Contenido**:
- ✅ Descripción completa del microservicio
- ✅ Arquitectura y estructura de módulos
- ✅ **HU18**: Documentación detallada del sistema de seguimiento en tiempo real
- ✅ APIs públicas de todos los módulos (Sellers, Shopkeepers, Routes, Visits, Inventory, etc.)
- ✅ Modelos de datos y schemas
- ✅ Ejemplos de uso completos en Python y JavaScript
- ✅ Integración con frontend (React, React Native)
- ✅ Guía de troubleshooting

**Audiencia**: Desarrolladores, Arquitectos de Software, DevOps

**Páginas**: ~150 páginas estimadas en Confluence

---

### 2. Resumen Ejecutivo HU18
**Archivo**: [`HU18_RESUMEN_EJECUTIVO.md`](./HU18_RESUMEN_EJECUTIVO.md)

**Contenido**:
- ✅ Descripción general de HU18
- ✅ Objetivos de negocio
- ✅ Arquitectura técnica simplificada
- ✅ Endpoints WebSocket principales
- ✅ Implementación móvil y web (código listo para usar)
- ✅ Seguridad y permisos
- ✅ Métricas de rendimiento
- ✅ Troubleshooting rápido
- ✅ Roadmap futuro

**Audiencia**: Product Managers, Desarrolladores Frontend, QA Testers

**Páginas**: ~20 páginas estimadas en Confluence

---

## 🚀 Inicio Rápido

### Prerrequisitos

```bash
# Python 3.11+
python --version

# PostgreSQL con PostGIS
psql --version

# Node.js (para ejemplos de frontend)
node --version
```

### Instalación

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd workspace

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp env.example .env
# Editar .env con tus valores

# 5. Iniciar servidor
uvicorn src.main:app --reload --port 8000
```

### Verificar Instalación

```bash
# Health check
curl http://localhost:8000/health

# Documentación interactiva
open http://localhost:8000/docs
```

---

## 🎯 HU18: Seguimiento en Tiempo Real

### Descripción Breve

**HU18** representa una **mejora y evolución** de **HU13 (Rutas Optimizadas)**. Mientras HU13 proporciona rutas planificadas estáticas, HU18 agrega **seguimiento GPS en tiempo real** usando WebSockets.

**Mejoras implementadas sobre HU13**:
- **Tracking en tiempo real**: Ubicación GPS actualizada cada 10 segundos
- **Sistema de observadores**: Múltiples usuarios observando en vivo
- **WebSocket bidireccional**: Comunicación instantánea
- **Panel administrativo**: Monitoreo de toda la flota
- **Datos enriquecidos**: Velocidad, batería, timestamps

**Funcionalidades**:
- **Vendedores**: Envían su ubicación mientras ejecutan la ruta (HU13)
- **Tenderos**: Ven la ubicación real del vendedor en mapa interactivo
- **Administradores**: Monitorean todos los vendedores simultáneamente
- **Comparación**: Ruta planificada (HU13) vs ruta real (HU18)

### Diagrama de Flujo

```
┌─────────────────┐
│  Vendedor       │
│  (App Móvil)    │
│                 │
│  📱 GPS activo  │
└────────┬────────┘
         │
         │ WebSocket
         │ ws://api/tracking/ws/send/1
         ▼
┌─────────────────┐
│  MS-USER-PY     │
│  (Backend)      │
│                 │
│  ConnectionMgr  │
└────────┬────────┘
         │
         │ Broadcast
         │
         ├────────────────────┬────────────────────┐
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Tendero 1  │      │  Tendero 2  │      │   Admin     │
│  (Web App)  │      │  (Web App)  │      │  (Dashboard)│
│             │      │             │      │             │
│  🗺️ Mapa    │      │  🗺️ Mapa    │      │  🗺️ Todos   │
└─────────────┘      └─────────────┘      └─────────────┘
```

### Endpoints Principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/ws/send/{seller_id}` | WebSocket | Vendedor envía GPS |
| `/ws/watch/{seller_id}` | WebSocket | Observar vendedor |
| `/ws/watch-all` | WebSocket | Observar todos (Admin) |
| `/location/{seller_id}` | GET | Última ubicación conocida |
| `/locations` | GET | Todas las ubicaciones (Admin) |

### Ejemplo Rápido (Python)

```python
import asyncio
import websockets
import json

async def send_location():
    uri = "ws://localhost:8000/api/v1/users/tracking/ws/send/1"
    
    async with websockets.connect(uri) as ws:
        # Enviar ubicación
        location = {
            "latitude": 4.6097,
            "longitude": -74.0817,
            "speed": 25.0,
            "battery": 85
        }
        await ws.send(json.dumps(location))
        
        # Recibir confirmación
        response = await ws.recv()
        print(f"Servidor: {response}")

asyncio.run(send_location())
```

### Ejemplo Rápido (JavaScript)

```javascript
// Observar vendedor
const ws = new WebSocket('ws://localhost:8000/api/v1/users/tracking/ws/watch/1');

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'location_update') {
        console.log('Ubicación:', message.data);
        // Actualizar mapa
        updateMarker(message.data.latitude, message.data.longitude);
    }
};
```

---

## 🏗️ Arquitectura del Sistema

### Microservicios

```
┌──────────────────┐
│   MS-USER-PY     │  ← Este microservicio
│   (Usuarios)     │
└────────┬─────────┘
         │
         ├─────────────────┐
         │                 │
┌────────▼────────┐ ┌──────▼─────────┐
│   MS-AUTH-PY    │ │   MS-GEO-PY    │
│ (Autenticación) │ │  (Geografía)   │
└─────────────────┘ └────────────────┘
         │
         │
┌────────▼────────┐
│ MS-PRODUCT-PY   │
│  (Productos)    │
└─────────────────┘
```

### Stack Tecnológico

- **Framework**: FastAPI 0.104.1
- **Base de datos**: PostgreSQL + PostGIS + GeoAlchemy2
- **ORM**: SQLAlchemy 2.0
- **Validación**: Pydantic 2.5
- **WebSockets**: FastAPI WebSocket
- **Geocoding**: Nominatim
- **Routing**: OpenRouteService API
- **Testing**: Pytest

---

## 📊 Estructura del Proyecto

```
/workspace/
├── src/
│   ├── main.py                 # Aplicación FastAPI
│   ├── config.py              # Configuración
│   │
│   ├── models/                # Modelos de base de datos
│   │   ├── seller.py
│   │   ├── shopkeeper.py
│   │   ├── assignment.py
│   │   ├── visit.py
│   │   └── inventory.py
│   │
│   ├── routers/               # Endpoints de API
│   │   ├── sellers.py
│   │   ├── shopkeepers.py
│   │   ├── assignments.py
│   │   ├── routes.py
│   │   ├── tracking.py        ⭐ HU18
│   │   ├── visits.py
│   │   ├── inventory.py
│   │   └── seller_incidents.py
│   │
│   ├── schemas/               # Validación Pydantic
│   │   ├── seller.py
│   │   ├── shopkeeper.py
│   │   ├── tracking.py        ⭐ HU18
│   │   └── ...
│   │
│   ├── clients/              # Clientes externos
│   │   ├── openroute_client.py
│   │   ├── nominatim_client.py
│   │   └── product_client.py
│   │
│   ├── cache/                # Sistema de caché
│   │   └── route_cache.py
│   │
│   └── utils/                # Utilidades
│       ├── auth.py
│       └── geo_client.py
│
├── tests/                    # Tests unitarios
│   └── test_users.py
│
├── requirements.txt          # Dependencias Python
├── pytest.ini               # Configuración Pytest
├── Dockerfile              # Contenedor Docker
├── .env.example           # Variables de entorno
│
└── DOCUMENTACION/         # 📚 Documentación
    ├── DOCUMENTACION_API_HU18.md
    ├── HU18_RESUMEN_EJECUTIVO.md
    └── DOCUMENTACION_README.md (este archivo)
```

---

## 🔧 Configuración

### Variables de Entorno Principales

```bash
# Aplicación
APP_NAME=MS-USER-PY
APP_VERSION=1.0.0
API_PREFIX=/api/v1/users
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000

# Base de datos
DATABASE_URL=postgresql://dgt_user:dgt_pass@localhost:5437/digital_twins_db

# OpenRouteService (para rutas)
OPENROUTE_API_KEY=tu_api_key_aqui
OPENROUTE_ENABLED=true

# Nominatim (para geocoding)
NOMINATIM_ENABLED=true
NOMINATIM_USER_AGENT=DigitalTwins-IS/1.0

# Microservicios externos
MS_AUTH_URL=http://ms-auth-py:8000
MS_GEO_URL=http://ms-geo-py:8000
MS_PRODUCT_URL=http://ms-product-py:8000

# Reglas de negocio
MAX_SHOPKEEPERS_PER_SELLER=80
MAX_SELLERS_PER_ZONE=10

# Cache
ROUTE_CACHE_TTL_HOURS=24
ROUTE_CACHE_MAX_SIZE=1000
```

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Con cobertura
pytest --cov=src --cov-report=html

# Test específico
pytest tests/test_users.py::test_create_seller
```

### Tests de WebSocket

```bash
# Instalar wscat
npm install -g wscat

# Probar conexión vendedor
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/send/1

# Enviar ubicación
> {"latitude": 4.6097, "longitude": -74.0817, "speed": 25, "battery": 85}

# Probar conexión observador
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/watch/1
```

---

## 📖 Documentación Adicional

### Swagger UI (Interactiva)
```
http://localhost:8000/docs
```

### ReDoc (Alternativa)
```
http://localhost:8000/redoc
```

### OpenAPI Schema (JSON)
```
http://localhost:8000/openapi.json
```

---

## 🐳 Docker

### Construir Imagen

```bash
docker build -t ms-user-py:latest .
```

### Ejecutar Contenedor

```bash
docker run -d \
  --name ms-user-py \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  ms-user-py:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  ms-user-py:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://dgt_user:dgt_pass@db:5432/digital_twins_db
      - OPENROUTE_API_KEY=${OPENROUTE_API_KEY}
    depends_on:
      - db

  db:
    image: postgis/postgis:15-3.3
    environment:
      - POSTGRES_DB=digital_twins_db
      - POSTGRES_USER=dgt_user
      - POSTGRES_PASSWORD=dgt_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 📊 Monitoreo

### Health Checks

```bash
# Health básico
curl http://localhost:8000/health

# Status detallado
curl http://localhost:8000/status
```

**Respuesta esperada**:
```json
{
    "status": "healthy",
    "service": "MS-USER-PY",
    "version": "1.0.0",
    "features": {
        "openroute_service": true,
        "nominatim_geocoding": true,
        "route_caching": true,
        "real_time_tracking": true
    },
    "endpoints": {
        "sellers": "/api/v1/users/sellers",
        "shopkeepers": "/api/v1/users/shopkeepers",
        "routes": "/api/v1/users/routes",
        "tracking": "/api/v1/users/tracking"
    }
}
```

---

## 🔒 Seguridad

### Autenticación

Todos los endpoints REST requieren autenticación JWT:

```bash
curl http://localhost:8000/api/v1/users/sellers \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Roles

- **ADMIN**: Acceso completo a todos los recursos
- **VENDEDOR**: Solo sus propios datos y rutas
- **TENDERO**: Solo puede ver su vendedor asignado

### WebSocket Security (Roadmap)

Actualmente los WebSockets no requieren autenticación. En producción se implementará:

```javascript
const ws = new WebSocket(
    `ws://api.com/tracking/ws/watch/1?token=${jwt_token}`
);
```

---

## 🐛 Troubleshooting

### Problema: Error de conexión a base de datos

```bash
# Verificar conexión
psql -h localhost -U dgt_user -d digital_twins_db

# Verificar extensión PostGIS
psql -d digital_twins_db -c "SELECT PostGIS_version();"
```

### Problema: OpenRouteService no funciona

```bash
# Verificar API key
curl "https://api.openrouteservice.org/v2/health" \
  -H "Authorization: YOUR_API_KEY"

# Deshabilitar temporalmente
export OPENROUTE_ENABLED=false
```

### Problema: WebSocket no conecta

```bash
# Verificar si el puerto está abierto
netstat -an | grep 8000

# Probar con wscat
wscat -c ws://localhost:8000/api/v1/users/tracking/ws/watch/1
```

---

## 📈 Roadmap

### Q4 2025 ✅
- [x] APIs básicas (Sellers, Shopkeepers, Assignments)
- [x] Sistema de rutas optimizadas
- [x] WebSocket tracking en tiempo real
- [x] Sistema de visitas
- [x] Gestión de inventario

### Q1 2026
- [ ] Autenticación en WebSockets
- [ ] Persistencia de trazas GPS
- [ ] Notificaciones push
- [ ] Dashboard de analytics

### Q2 2026
- [ ] Machine Learning para predicción de tiempos
- [ ] Geofencing automático
- [ ] Optimización de rutas con tráfico en tiempo real
- [ ] App móvil nativa

---

## 👥 Equipo

### Desarrolladores
- Backend: MS-USER-PY Team
- Frontend: Digital Twins UI Team
- DevOps: Infrastructure Team

### Contacto
- **Slack**: #ms-user-py
- **Email**: dev@digitaltwins.com
- **Jira**: DTWIN-USER

---

## 📝 Licencia

Propiedad de Digital Twins IS. Todos los derechos reservados.

---

## 🙏 Agradecimientos

- **OpenRouteService**: Por su excelente API de routing
- **Nominatim**: Por el servicio de geocoding
- **FastAPI**: Por el framework increíble
- **Leaflet**: Por la librería de mapas

---

## 📚 Referencias Externas

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL + PostGIS](https://postgis.net/)
- [OpenRouteService API](https://openrouteservice.org/dev/#/api-docs)
- [Nominatim API](https://nominatim.org/release-docs/latest/api/Overview/)
- [WebSocket Protocol (RFC 6455)](https://datatracker.ietf.org/doc/html/rfc6455)
- [Leaflet Maps](https://leafletjs.com/)
- [React Leaflet](https://react-leaflet.js.org/)

---

**Última actualización**: Noviembre 28, 2025  
**Versión de documentación**: 1.0.0  
**Mantenido por**: MS-USER-PY Development Team

---

## 🚀 Siguientes Pasos

1. **Para Desarrolladores Backend**: Leer [`DOCUMENTACION_API_HU18.md`](./DOCUMENTACION_API_HU18.md) completo
2. **Para Desarrolladores Frontend**: Empezar con [`HU18_RESUMEN_EJECUTIVO.md`](./HU18_RESUMEN_EJECUTIVO.md)
3. **Para Product Managers**: Revisar sección de HU18 y roadmap
4. **Para QA Testers**: Familiarizarse con los ejemplos de testing

---

¿Tienes preguntas? Consulta la documentación completa o contacta al equipo de desarrollo.
