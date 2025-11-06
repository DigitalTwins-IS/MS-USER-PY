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
import logging

from ..models import get_db, ShopkeeperInventory, Shopkeeper
from ..schemas.inventory import (
    InventoryCreate, InventoryUpdate, InventoryResponse,
    InventoryDetailResponse, StockAdjustment, InventorySummary
)
from ..utils import get_current_user
from ..clients.product_client import product_client

logger = logging.getLogger(__name__)
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
    
    # Obtener items del inventario con JOIN a la tabla products para obtener nombre y categoría
    # Usar SQL directo para hacer JOIN con la tabla products
    query_sql = text("""
        SELECT 
            i.id,
            i.shopkeeper_id,
            i.product_id,
            i.unit_price,
            i.current_stock,
            i.min_stock,
            i.max_stock,
            i.last_updated,
            COALESCE(i.product_name, p.name) as product_name,
            COALESCE(i.product_category, p.category) as product_category
        FROM inventories i
        LEFT JOIN products p ON i.product_id = p.id
        WHERE i.shopkeeper_id = :shopkeeper_id 
        AND i.is_active = TRUE
    """)
    
    if low_stock_only:
        query_sql = text("""
            SELECT 
                i.id,
                i.shopkeeper_id,
                i.product_id,
                i.unit_price,
                i.current_stock,
                i.min_stock,
                i.max_stock,
                i.last_updated,
                COALESCE(i.product_name, p.name) as product_name,
                COALESCE(i.product_category, p.category) as product_category
            FROM inventories i
            LEFT JOIN products p ON i.product_id = p.id
            WHERE i.shopkeeper_id = :shopkeeper_id 
            AND i.is_active = TRUE
            AND i.current_stock < i.min_stock
        """)
    
    result = db.execute(query_sql, {"shopkeeper_id": shopkeeper_id})
    rows = result.fetchall()
    
    inventory = []
    
    for row in rows:
        # Determinar estado del stock
        if row.current_stock < row.min_stock:
            stock_status = 'low'
        elif row.current_stock > row.max_stock:
            stock_status = 'high'
        else:
            stock_status = 'normal'
        
        # Intentar obtener información actualizada del producto desde el microservicio
        # Priorizar siempre el nombre del microservicio si está disponible
        product_name = row.product_name or f"Producto {row.product_id}"
        product_category = row.product_category or "Sin categoría"
        needs_update = False
        
        try:
            product = await product_client.get_product(row.product_id)
            if product:
                # Priorizar el nombre del microservicio sobre el almacenado
                new_product_name = product.get("name")
                new_product_category = product.get("category")
                
                logger.info(f"Producto {row.product_id} obtenido del microservicio: nombre={new_product_name}, categoría={new_product_category}")
                
                if new_product_name:
                    product_name = new_product_name
                    # Si el nombre cambió, actualizar en la BD
                    if row.product_name != new_product_name:
                        logger.info(f"Actualizando nombre del producto {row.product_id} de '{row.product_name}' a '{new_product_name}'")
                        needs_update = True
                else:
                    logger.warning(f"Producto {row.product_id} obtenido del microservicio pero sin nombre")
                
                if new_product_category:
                    product_category = new_product_category
                    # Si la categoría cambió, actualizar en la BD
                    if row.product_category != new_product_category:
                        needs_update = True
            else:
                logger.warning(f"Producto {row.product_id} no encontrado en el microservicio, usando nombre almacenado: '{row.product_name}'")
        except Exception as e:
            # Si falla, usar los datos almacenados en la BD
            logger.warning(f"No se pudo obtener producto {row.product_id} del microservicio: {e}")
        
        # Actualizar el nombre en la BD si cambió
        if needs_update:
            try:
                inventory_item = db.query(ShopkeeperInventory).filter(ShopkeeperInventory.id == row.id).first()
                if inventory_item:
                    inventory_item.product_name = product_name
                    inventory_item.product_category = product_category
                    db.commit()
            except Exception as e:
                logger.warning(f"Error al actualizar nombre del producto {row.product_id} en BD: {e}")
                db.rollback()
        
        inventory.append(InventoryDetailResponse(
            id=row.id,
            shopkeeper_id=row.shopkeeper_id,
            shopkeeper_name=shopkeeper.name,
            business_name=shopkeeper.business_name,
            product_id=row.product_id,
            product_name=product_name,
            category=product_category,
            price=float(row.unit_price),
            stock=float(row.current_stock),
            min_stock=float(row.min_stock),
            max_stock=float(row.max_stock),
            stock_status=stock_status,
            last_updated=row.last_updated
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
    Si el microservicio de Product no está disponible, se usan los datos proporcionados.
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
    
    # Intentar obtener información del producto desde el microservicio
    # Si no está disponible, usar los datos proporcionados en el request
    product = None
    product_name = None
    product_description = None
    product_category = None
    
    try:
        product = await product_client.get_product(inventory_data.product_id)
        if product:
            logger.info(f"Producto {inventory_data.product_id} obtenido del microservicio: {product}")
            product_name = product.get("name")
            product_description = product.get("description")
            product_category = product.get("category")
        else:
            logger.warning(f"Producto {inventory_data.product_id} no encontrado en el microservicio")
    except Exception as e:
        logger.warning(f"No se pudo obtener producto {inventory_data.product_id} del microservicio: {e}")
        # Continuar con los datos proporcionados en el request
    
    # Determinar el nombre del producto: priorizar microservicio, luego datos del request, luego fallback
    final_product_name = product_name or inventory_data.product_name or f"Producto {inventory_data.product_id}"
    final_product_description = product_description or inventory_data.product_description
    final_product_category = product_category or inventory_data.product_category
    
    logger.info(f"Creando inventario para producto {inventory_data.product_id} con nombre: '{final_product_name}'")
    
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
    
    # Asegurar que el stock sea un entero
    current_stock = int(round(float(inventory_data.current_stock or 0)))
    min_stock = int(round(float(inventory_data.min_stock or 10)))
    max_stock = int(round(float(inventory_data.max_stock or 100)))
    
    logger.info(f"Guardando stock: current_stock={current_stock}, min_stock={min_stock}, max_stock={max_stock}")
    
    # Crear nuevo item en el inventario usando la información del microservicio si está disponible,
    # sino usar los datos proporcionados en el request
    new_item = ShopkeeperInventory(
        shopkeeper_id=inventory_data.shopkeeper_id,
        product_id=inventory_data.product_id,
        unit_price=Decimal(str(inventory_data.unit_price)),
        current_stock=Decimal(str(current_stock)),
        min_stock=Decimal(str(min_stock)),
        max_stock=Decimal(str(max_stock)),
        product_name=final_product_name,
        product_description=final_product_description,
        product_category=final_product_category,
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
    
    # Intentar obtener información actualizada del producto desde el microservicio
    try:
        product = await product_client.get_product(item.product_id)
        if product:
            # Actualizar nombre y categoría si están disponibles en el microservicio
            if product.get("name"):
                item.product_name = product.get("name")
            if product.get("category"):
                item.product_category = product.get("category")
            if product.get("description"):
                item.product_description = product.get("description")
    except Exception as e:
        logger.warning(f"No se pudo obtener producto {item.product_id} del microservicio al actualizar: {e}")
    
    # Actualizar campos del request (asegurando que el stock sea entero)
    for field, value in inventory_data.model_dump(exclude_unset=True).items():
        if field == "current_stock" and value is not None:
            # Asegurar que el stock sea un entero
            setattr(item, field, Decimal(str(int(round(float(value))))))
        elif field in ["min_stock", "max_stock"] and value is not None:
            # Asegurar que min/max sean enteros
            setattr(item, field, Decimal(str(int(round(float(value))))))
        else:
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
    
    # Asegurar que la cantidad de ajuste sea un entero
    adjustment_quantity = int(round(float(adjustment.quantity or 0)))
    
    # Calcular nuevo stock (asegurando que sea entero)
    current_stock = int(round(float(item.current_stock or 0)))
    new_stock = current_stock + adjustment_quantity
    
    logger.info(f"Ajustando stock del producto {adjustment.product_id}: {current_stock} + {adjustment_quantity} = {new_stock}")
    
    # Validar que no quede negativo
    if new_stock < 0:
        raise HTTPException(
            400, 
            f"Stock insuficiente. Stock actual: {current_stock}, intentando reducir: {abs(adjustment_quantity)}"
        )
    
    # Actualizar stock (asegurando que sea entero)
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