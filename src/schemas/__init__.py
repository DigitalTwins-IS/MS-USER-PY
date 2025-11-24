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
    VisitStatusUpdate,
    VisitResponse,
    VisitDetailResponse,
    ShopkeeperLowStockResponse,
    VisitListResponse
)

from .seller_incidents import (
    SellerIncidentCreate,
    SellerIncidentUpdate,
    SellerIncidentResponse,
    SellerIncidentDetailResponse
)

from .tracking import (
    SellerLocationCreate,
    SellerLocationResponse,
    TrackingInfo,
    WebSocketMessage
)

from .geocoding import (
    GeocodeRequest,
    GeocodeResponse,
    ReverseGeocodeResponse,
    PlaceSearchResult,
    PlaceSearchResponse
)

from .route_schemas import (
    RouteOptimizationRequest,
    CacheStats,
    OptimizedRouteResponse,
    RoutePoint,
    RouteStatistics
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
    "VisitStatusUpdate",
    "VisitResponse",
    "VisitDetailResponse",
    "ShopkeeperLowStockResponse",
    "VisitListResponse",
    # Seller Incidents
    "SellerIncidentCreate",
    "SellerIncidentUpdate",
    "SellerIncidentResponse",
    # Tracking
    "SellerLocationCreate",
    "SellerLocationResponse",
    "TrackingInfo",
    "WebSocketMessage",
    # Geocoding
    "GeocodeRequest",
    "GeocodeResponse",
    "ReverseGeocodeResponse",
    "PlaceSearchResult",
    "PlaceSearchResponse",
    # Routes
    "RouteOptimizationRequest",
    "CacheStats",
    "OptimizedRouteResponse",
    "RoutePoint",
    "RouteStatistics"
]