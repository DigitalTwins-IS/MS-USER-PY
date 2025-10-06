"""
Router de Vendedores (Sellers) - HU2
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from ..models import get_db, Seller, Assignment
from ..schemas import (
    SellerCreate, SellerUpdate, SellerResponse,
    SellerWithShopkeepersResponse, ChangeZoneRequest, HealthResponse
)
from ..utils import get_current_user, geo_client

router = APIRouter()


@router.post("/sellers", response_model=SellerResponse, status_code=status.HTTP_201_CREATED)
async def create_seller(
    seller_data: SellerCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """HU2: Crear vendedor y asignarlo a zona"""
    # Verificar zona existe
    await geo_client.verify_zone_exists(seller_data.zone_id)
    
    # Verificar email único
    if db.query(Seller).filter(Seller.email == seller_data.email).first():
        raise HTTPException(400, "El email ya está registrado")
    
    new_seller = Seller(**seller_data.model_dump())
    db.add(new_seller)
    db.commit()
    db.refresh(new_seller)
    return new_seller


@router.get("/sellers", response_model=List[SellerWithShopkeepersResponse])
async def list_sellers(
    zone_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar vendedores con conteo de tenderos"""
    query = db.query(Seller)
    
    if zone_id:
        query = query.filter(Seller.zone_id == zone_id)
    if is_active is not None:
        query = query.filter(Seller.is_active == is_active)
    
    sellers = query.offset(skip).limit(limit).all()
    
    # Agregar conteo de tenderos
    result = []
    for seller in sellers:
        count = db.query(Assignment).filter(
            Assignment.seller_id == seller.id,
            Assignment.is_active == True
        ).count()
        
        seller_dict = {**seller.__dict__, "total_shopkeepers": count, "zone_name": ""}
        result.append(SellerWithShopkeepersResponse(**seller_dict))
    
    return result


@router.get("/sellers/{seller_id}", response_model=SellerResponse)
async def get_seller(
    seller_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener vendedor por ID"""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(404, "Vendedor no encontrado")
    return seller


@router.put("/sellers/{seller_id}", response_model=SellerResponse)
async def update_seller(
    seller_id: int,
    seller_data: SellerUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """HU4: Actualizar datos del vendedor"""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(404, "Vendedor no encontrado")
    
    # Verificar zona si se cambia
    if seller_data.zone_id:
        await geo_client.verify_zone_exists(seller_data.zone_id)
    
    # Verificar email único si se cambia
    if seller_data.email and seller_data.email != seller.email:
        if db.query(Seller).filter(Seller.email == seller_data.email).first():
            raise HTTPException(400, "El email ya está registrado")
    
    # Actualizar campos
    for field, value in seller_data.model_dump(exclude_unset=True).items():
        setattr(seller, field, value)
    
    db.commit()
    db.refresh(seller)
    return seller


@router.delete("/sellers/{seller_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seller(
    seller_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Eliminar vendedor (soft delete)"""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(404, "Vendedor no encontrado")
    
    seller.is_active = False
    db.commit()
    return None


@router.post("/sellers/{seller_id}/change-zone", response_model=SellerResponse)
async def change_seller_zone(
    seller_id: int,
    zone_data: ChangeZoneRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cambiar zona de vendedor"""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(404, "Vendedor no encontrado")
    
    # Verificar nueva zona existe
    await geo_client.verify_zone_exists(zone_data.new_zone_id)
    
    seller.zone_id = zone_data.new_zone_id
    db.commit()
    db.refresh(seller)
    return seller


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check"""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        service="MS-USER-PY",
        version="1.0.0",
        database=db_status
    )

