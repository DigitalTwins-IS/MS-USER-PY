# src/routers/inventory.py
"""
Router de Inventario
Gestiona el INVENTARIO de productos de cada tendero
(qué productos tiene cada tendero y en qué cantidad)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Optional
from decimal import Decimal
import httpx

from ..models import get_db, ShopkeeperInventory, Shopkeeper
from ..schemas.inventory import (
    InventoryCreate, InventoryUpdate, InventoryResponse,
    InventoryDetailResponse, StockAdjustment, InventorySummary
)
from ..utils import get_current_user
from ..clients.product_client import product_client

router = APIRouter()


# ============================================================================
# HEALTH CHECK Y PRUEBAS
# ============================================================================

@router.get("/inventory/health")
async def inventory_health_check():
    """
    Health check del servicio de inventario
    Verifica la conectividad con el microservicio de Product
    """
    try:
        # Probar conectividad con el microservicio de Product
        test_product = await product_client.get_product(1)
        return {
            "status": "healthy",
            "product_service": "connected",
            "test_product": test_product is not None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "product_service": "disconnected",
            "error": str(e)
        }


@router.post("/inventory/debug")
async def debug_inventory_data(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint de debug para verificar los datos que se están enviando
    """
    return {
        "received_data": inventory_data.model_dump(),
        "data_types": {
            "shopkeeper_id": type(inventory_data.shopkeeper_id).__name__,
            "product_id": type(inventory_data.product_id).__name__,
            "unit_price": type(inventory_data.unit_price).__name__,
            "current_stock": type(inventory_data.current_stock).__name__,
            "min_stock": type(inventory_data.min_stock).__name__,
            "max_stock": type(inventory_data.max_stock).__name__,
        },
        "validation_errors": []
    }


@router.post("/inventory/test", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def test_add_inventory_item(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint de prueba para agregar producto al inventario (sin autenticación)
    """
    # Verificar que el tendero existe
    shopkeeper = db.query(Shopkeeper).filter(
        Shopkeeper.id == inventory_data.shopkeeper_id
    ).first()
    if not shopkeeper:
        raise HTTPException(404, "Tendero no encontrado")
    
    # Validar que el ID del producto sea válido
    if inventory_data.product_id <= 0:
        raise HTTPException(400, f"ID de producto '{inventory_data.product_id}' no es válido")
    
    # Validar que el producto existe en el microservicio de Product
    product = await product_client.get_product(inventory_data.product_id)
    if not product:
        raise HTTPException(
            404, 
            f"El producto con ID '{inventory_data.product_id}' no existe en el catálogo de productos"
        )
    
    # Verificar que no existe ya este producto en el inventario
    existing = db.query(ShopkeeperInventory).filter(
        ShopkeeperInventory.shopkeeper_id == inventory_data.shopkeeper_id,
        ShopkeeperInventory.product_id == inventory_data.product_id
    ).first()
    
    if existing:
        raise HTTPException(
            400, 
            f"El producto con ID '{inventory_data.product_id}' ya existe en el inventario de este tendero"
        )
    
    # Crear nuevo item en el inventario usando la información del microservicio de Product
    new_item = ShopkeeperInventory(
        shopkeeper_id=inventory_data.shopkeeper_id,
        product_id=inventory_data.product_id,
        unit_price=inventory_data.unit_price,
        current_stock=inventory_data.current_stock,
        min_stock=inventory_data.min_stock,
        max_stock=inventory_data.max_stock,
        product_name=inventory_data.product_name or product.get("name"),
        product_description=inventory_data.product_description or product.get("description"),
        product_category=inventory_data.product_category or product.get("category"),
        product_brand=inventory_data.product_brand,
        is_validated=True,
        validated_by=1,  # Usuario de prueba
        validated_at=func.now()
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return new_item


@router.get("/inventory/products/available")
async def get_available_products(
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener productos disponibles desde el microservicio de Product
    Útil para seleccionar productos al agregar al inventario
    """
    try:
        if category:
            products = await product_client.get_products_by_category(category)
        else:
            # Obtener todos los productos
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{product_client.base_url}/api/v1/products/products")
                if response.status_code == 200:
                    products = response.json()
                else:
                    products = []
        
        return {
            "products": products,
            "total": len(products)
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error al obtener productos: {str(e)}"
        )


# ============================================================================
# CONSULTAS DE INVENTARIO
# ============================================================================

@router.get("/inventory/{shopkeeper_id}", response_model=List[InventoryDetailResponse])
async def get_shopkeeper_inventory(
    shopkeeper_id: int,
    low_stock_only: bool = Query(False, description="Solo mostrar items con stock bajo"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener inventario completo de un tendero
    
    Retorna todos los productos que tiene el tendero con:
    - Información del producto (nombre, precio, categoría)
    - Stock actual, mínimo y máximo
    - Estado del stock (low/normal/high)
    """
    # Verificar que el tendero existe
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == shopkeeper_id).first()
    if not shopkeeper:
        raise HTTPException(404, "Tendero no encontrado")
    
    # Obtener items del inventario usando el nuevo esquema
    query = db.query(ShopkeeperInventory).filter(
        ShopkeeperInventory.shopkeeper_id == shopkeeper_id,
        ShopkeeperInventory.is_active == True
    )
    
    if low_stock_only:
        query = query.filter(ShopkeeperInventory.current_stock < ShopkeeperInventory.min_stock)
    
    inventory_items = query.all()
    inventory = []
    
    for item in inventory_items:
        # Obtener información actualizada del producto desde el microservicio
        product_info = await product_client.get_product(item.product_id)
        
        # Determinar estado del stock
        if item.current_stock < item.min_stock:
            stock_status = 'low'
        elif item.current_stock > item.max_stock:
            stock_status = 'high'
        else:
            stock_status = 'normal'
        
        # Usar información del microservicio de Product si está disponible, sino usar la local
        product_name = product_info.get("name") if product_info else item.product_name or f"Producto {item.product_id}"
        product_category = product_info.get("category") if product_info else item.product_category or "Sin categoría"
        
        inventory.append(InventoryDetailResponse(
            id=item.id,
            shopkeeper_id=item.shopkeeper_id,
            shopkeeper_name=shopkeeper.name,
            business_name=shopkeeper.business_name,
            product_id=item.product_id,
            product_name=product_name,
            category=product_category,
            price=float(item.unit_price),
            stock=float(item.current_stock),
            min_stock=float(item.min_stock),
            max_stock=float(item.max_stock),
            stock_status=stock_status,
            last_updated=item.last_updated
        ))
    
    return inventory


@router.get("/inventory/{shopkeeper_id}/summary", response_model=InventorySummary)
async def get_inventory_summary(
    shopkeeper_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener resumen del inventario de un tendero
    
    Incluye:
    - Total de productos diferentes
    - Cantidad de items con stock bajo
    - Valor total del inventario (stock * precio)
    """
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == shopkeeper_id).first()
    if not shopkeeper:
        raise HTTPException(404, "Tendero no encontrado")
    
    # Obtener todos los items del inventario usando el nuevo esquema
    inventory_items = db.query(ShopkeeperInventory).filter(
        ShopkeeperInventory.shopkeeper_id == shopkeeper_id,
        ShopkeeperInventory.is_active == True
    ).all()
    
    total_products = len(inventory_items)
    low_stock_items = sum(1 for item in inventory_items if item.current_stock < item.min_stock)
    
    # Calcular valor total del inventario
    total_value = 0
    for item in inventory_items:
        total_value += float(item.current_stock * item.unit_price)
    
    last_updated = max([item.last_updated for item in inventory_items]) if inventory_items else None
    
    return InventorySummary(
        shopkeeper_id=shopkeeper_id,
        shopkeeper_name=shopkeeper.name,
        total_products=total_products,
        low_stock_items=low_stock_items,
        total_value=total_value,
        last_updated=last_updated
    )


# ============================================================================
# GESTIÓN DE ITEMS DEL INVENTARIO
# ============================================================================

@router.post("/inventory", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def add_inventory_item(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Agregar un producto al inventario de un tendero
    
    **Nota**: Un tendero no puede tener el mismo producto duplicado.
    El producto debe existir en el microservicio de Product.
    """
    # Verificar que el tendero existe
    shopkeeper = db.query(Shopkeeper).filter(
        Shopkeeper.id == inventory_data.shopkeeper_id
    ).first()
    if not shopkeeper:
        raise HTTPException(404, "Tendero no encontrado")
    
    # Validar que el ID del producto sea válido
    if inventory_data.product_id <= 0:
        raise HTTPException(400, f"ID de producto '{inventory_data.product_id}' no es válido")
    
    # Validar que el producto existe en el microservicio de Product
    product = await product_client.get_product(inventory_data.product_id)
    if not product:
        raise HTTPException(
            404, 
            f"El producto con ID '{inventory_data.product_id}' no existe en el catálogo de productos"
        )
    
    # Verificar que no existe ya este producto en el inventario
    existing = db.query(ShopkeeperInventory).filter(
        ShopkeeperInventory.shopkeeper_id == inventory_data.shopkeeper_id,
        ShopkeeperInventory.product_id == inventory_data.product_id
    ).first()
    
    if existing:
        raise HTTPException(
            400, 
            f"El producto con ID '{inventory_data.product_id}' ya existe en el inventario de este tendero"
        )
    
    # Crear nuevo item en el inventario usando la información del microservicio de Product
    new_item = ShopkeeperInventory(
        shopkeeper_id=inventory_data.shopkeeper_id,
        product_id=inventory_data.product_id,
        unit_price=inventory_data.unit_price,
        current_stock=inventory_data.current_stock,
        min_stock=inventory_data.min_stock,
        max_stock=inventory_data.max_stock,
        product_name=inventory_data.product_name or product.get("name"),
        product_description=inventory_data.product_description or product.get("description"),
        product_category=inventory_data.product_category or product.get("category"),
        product_brand=inventory_data.product_brand,
        is_validated=True,
        validated_by=current_user.get("user_id"),
        validated_at=func.now()
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return new_item


@router.put("/inventory/{inventory_id}", response_model=InventoryResponse)
async def update_inventory_item(
    inventory_id: int,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualizar un item del inventario
    
    Permite cambiar:
    - Stock actual
    - Stock mínimo
    - Stock máximo
    """
    item = db.query(ShopkeeperInventory).filter(
        ShopkeeperInventory.id == inventory_id
    ).first()
    
    if not item:
        raise HTTPException(404, "Item de inventario no encontrado")
    
    # Actualizar campos
    for field, value in inventory_data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    return item


@router.delete("/inventory/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Eliminar un producto del inventario de un tendero
    
    **Nota**: Esto es una eliminación permanente (no soft delete)
    """
    item = db.query(ShopkeeperInventory).filter(
        ShopkeeperInventory.id == inventory_id
    ).first()
    
    if not item:
        raise HTTPException(404, "Item de inventario no encontrado")
    
    db.delete(item)
    db.commit()
    return None


# ============================================================================
# AJUSTES DE STOCK
# ============================================================================

@router.post("/inventory/{shopkeeper_id}/adjust-stock")
async def adjust_stock(
    shopkeeper_id: int,
    adjustment: StockAdjustment,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Ajustar stock de un producto (entrada o salida)
    
    - **quantity positiva**: Entrada de mercancía (ej: +10)
    - **quantity negativa**: Salida/venta (ej: -5)
    
    Ejemplo:
    ```json
    {
        "product_id": 1,
        "quantity": 10,
        "notes": "Compra a proveedor"
    }
    ```
    """
    # Buscar el item en el inventario
    item = db.query(ShopkeeperInventory).filter(
        ShopkeeperInventory.shopkeeper_id == shopkeeper_id,
        ShopkeeperInventory.product_id == adjustment.product_id
    ).first()
    
    if not item:
        raise HTTPException(
            404, 
            "Este producto no existe en el inventario. Primero debe agregarlo."
        )
    
    # Calcular nuevo stock
    new_stock = float(item.stock) + adjustment.quantity
    
    # Validar que no quede negativo
    if new_stock < 0:
        raise HTTPException(
            400, 
            f"Stock insuficiente. Stock actual: {item.stock}, intentando reducir: {abs(adjustment.quantity)}"
        )
    
    # Actualizar stock
    item.current_stock = Decimal(str(new_stock))
    db.commit()
    db.refresh(item)
    
    # Obtener info del producto para la respuesta desde el microservicio
    product_info = await product_client.get_product(adjustment.product_id)
    
    return {
        "success": True,
        "message": f"Stock ajustado: {adjustment.quantity:+.2f}",
        "product_name": product_info.get("name") if product_info else item.product_name or "Producto",
        "previous_stock": float(item.current_stock) - adjustment.quantity,
        "new_stock": float(item.current_stock),
        "notes": adjustment.notes
    }


# ============================================================================
# OPERACIONES MASIVAS
# ============================================================================

@router.get("/inventory/low-stock/all", response_model=List[InventoryDetailResponse])
async def get_all_low_stock_items(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener todos los items con stock bajo de TODOS los tenderos
    
    Útil para generar reportes de reabastecimiento
    """
    query = text("""
        SELECT * FROM v_shopkeeper_inventory
        WHERE stock_status = 'low'
        ORDER BY shopkeeper_name, product_name
    """)
    
    result = db.execute(query)
    inventory = []
    
    for row in result:
        inventory.append(InventoryDetailResponse(
            id=row.id,
            shopkeeper_id=row.shopkeeper_id,
            shopkeeper_name=row.shopkeeper_name,
            business_name=row.business_name,
            product_id=row.product_id,
            product_name=row.product_name,
            category=row.category,
            price=float(row.price),
            stock=float(row.stock),
            min_stock=float(row.min_stock),
            max_stock=float(row.max_stock),
            stock_status=row.stock_status,
            last_updated=row.last_updated
        ))
    
    return inventory