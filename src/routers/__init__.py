"""
Routers de la API
"""
from .sellers import router as sellers_router
from .shopkeepers import router as shopkeepers_router
from .assignments import router as assignments_router
from .routes import router as routes_router
from .inventory import router as inventory_router
from .visits import router as visits_router
from .seller_incidents import router as seller_incidents_router

__all__ = [
    "sellers_router",
    "shopkeepers_router",
    "assignments_router",
    "routes_router",
    "inventory_router",
    "visits_router",
    "seller_incidents_router"
]


