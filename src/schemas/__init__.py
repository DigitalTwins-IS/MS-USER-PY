"""
Schemas Pydantic para validación
"""
from .seller import (
    SellerCreate,
    SellerUpdate,
    SellerResponse,
    SellerWithZoneResponse,
    SellerWithShopkeepersResponse,
    ChangeZoneRequest
)
from .shopkeeper import (
    ShopkeeperCreate,
    ShopkeeperUpdate,
    ShopkeeperResponse,
    ShopkeeperWithSellerResponse
)
from .assignment import (
    AssignmentCreate,
    ReassignmentRequest,
    AssignmentResponse,
    AssignmentDetailResponse,
    AssignmentHistoryResponse,
    HealthResponse
)
from .product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse
)
from .inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
    InventoryDetailResponse,
    StockAdjustment,
    InventorySummary
)
from .visit import (
    VisitCreate,
    VisitUpdate,
    VisitCancelRequest,
    VisitResponse,
    VisitDetailResponse,
    ShopkeeperLowStockResponse,
    VisitListResponse
)

from .seller_incidents import (
    SellerIncidentCreate,
    SellerIncidentUpdate,
    SellerIncidentResponse
)

from .route_schemas import (
    RoutePoint,
    RouteStatistics,
    OptimizedRouteResponse,
    RouteVisualizationRequest
)

__all__ = [
    # Seller
    "SellerCreate",
    "SellerUpdate",
    "SellerResponse",
    "SellerWithZoneResponse",
    "SellerWithShopkeepersResponse",
    "ChangeZoneRequest",
    # Shopkeeper
    "ShopkeeperCreate",
    "ShopkeeperUpdate",
    "ShopkeeperResponse",
    "ShopkeeperWithSellerResponse",
    # Assignment
    "AssignmentCreate",
    "ReassignmentRequest",
    "AssignmentResponse",
    "AssignmentDetailResponse",
    "AssignmentHistoryResponse",
    "HealthResponse",
    # Product
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    # Inventory
    "InventoryCreate",
    "InventoryUpdate",
    "InventoryResponse",
    "InventoryDetailResponse",
    "StockAdjustment",
    "InventorySummary",
    "HealthResponse",
    # Visit
    "VisitCreate",
    "VisitUpdate",
    "VisitCancelRequest",
    "VisitResponse",
    "VisitDetailResponse",
    "ShopkeeperLowStockResponse",
    "VisitListResponse",
    # Seller Incidents
    "SellerIncidentCreate",
    "SellerIncidentUpdate",
    "SellerIncidentResponse",
    # Route
    "RoutePoint",
    "RouteStatistics",
    "OptimizedRouteResponse",
    "RouteVisualizationRequest"
]