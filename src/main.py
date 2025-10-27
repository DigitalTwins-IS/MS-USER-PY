"""
MS-USER-PY - Microservicio de Gestión de Usuarios
FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from .routers import routes_router


from .config import settings

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Microservicio de gestión de usuarios para el Sistema Digital Twins.
    
    ## Funcionalidades
    
    * **Vendedores (Sellers)**: Registro, actualización, asignación a zonas
    * **Tenderos (Shopkeepers)**: Registro con geolocalización, gestión de coordenadas
    * **Asignaciones (Assignments)**: Asignar tenderos a vendedores, historial completo
    
    ## Historias de Usuario Implementadas
    
    * **HU2**: Como administrador, quiero registrar vendedores y asignarlos a zonas
    * **HU3**: Como administrador, quiero registrar tenderos con latitud/longitud
    * **HU4**: Como administrador, quiero actualizar datos de vendedores y tenderos
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar y configurar routers después de crear la app para evitar imports circulares
from .routers import sellers_router, shopkeepers_router, assignments_router, routes_router

# Incluir routers
app.include_router(
    sellers_router,
    prefix=settings.API_PREFIX,
    tags=["sellers"]
)

app.include_router(
    shopkeepers_router,
    prefix=settings.API_PREFIX,
    tags=["shopkeepers"]
)

app.include_router(
    assignments_router,
    prefix=settings.API_PREFIX,
    tags=["assignments"]
)

app.include_router(
    routes_router,
    prefix=settings.API_PREFIX,
    tags=["routes"]
)


@app.get("/", include_in_schema=False)
async def root():
    """Redireccionar a la documentación"""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
async def root_health():
    """Health check raíz"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Event handlers
@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} iniciado")
    print(f"📚 Documentación disponible en: http://{settings.SERVICE_HOST}:{settings.SERVICE_PORT}/docs")
    print(f"👥 Endpoints de usuarios en: {settings.API_PREFIX}")
    print(f"🔗 Integraciones: MS-GEO ({settings.MS_GEO_URL})")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre de la aplicación"""
    print(f"🛑 {settings.APP_NAME} detenido")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )

