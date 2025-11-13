"""
Router de Tenderos (Shopkeepers) - HU3
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..models import get_db, Shopkeeper, Assignment, Seller
from ..schemas import (
    ShopkeeperCreate, ShopkeeperUpdate,
    ShopkeeperResponse, ShopkeeperWithSellerResponse
)
from ..utils import get_current_user

router = APIRouter()


@router.post("/shopkeepers", response_model=ShopkeeperResponse, status_code=status.HTTP_201_CREATED)
async def create_shopkeeper(
    shopkeeper_data: ShopkeeperCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """HU3: Crear tendero con coordenadas geográficas"""
    # Verificar email único si se proporciona
    if shopkeeper_data.email:
        if db.query(Shopkeeper).filter(Shopkeeper.email == shopkeeper_data.email).first():
            raise HTTPException(400, "El email ya está registrado")
    
    new_shopkeeper = Shopkeeper(**shopkeeper_data.model_dump())
    db.add(new_shopkeeper)
    db.commit()
    db.refresh(new_shopkeeper)
    return new_shopkeeper


@router.get("/shopkeepers", response_model=List[ShopkeeperWithSellerResponse])
async def list_shopkeepers(
    is_active: Optional[bool] = Query(True),
    seller_id: Optional[int] = Query(None),
    unassigned: Optional[bool] = Query(None, description="Filtrar por tenderos sin asignar"),
    assigned: Optional[bool] = Query(None, description="Filtrar por tenderos con vendedor asignado"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar tenderos con información de vendedor"""
    query = db.query(Shopkeeper)
    
    if is_active is not None:
        query = query.filter(Shopkeeper.is_active == is_active)
    
    shopkeepers = query.offset(skip).limit(limit).all()
    
    result = []
    for shopkeeper in shopkeepers:
        # Obtener asignación activa
        assignment = db.query(Assignment, Seller).join(
            Seller, Assignment.seller_id == Seller.id
        ).filter(
            Assignment.shopkeeper_id == shopkeeper.id,
            Assignment.is_active == True
        ).first()
        
        shopkeeper_dict = {**shopkeeper.__dict__}
        if assignment:
            shopkeeper_dict["seller_id"] = assignment.Seller.id
            shopkeeper_dict["seller_name"] = assignment.Seller.name
            shopkeeper_dict["seller_email"] = assignment.Seller.email
            shopkeeper_dict["assigned_at"] = assignment.Assignment.assigned_at
            shopkeeper_dict["zone_name"] = ""
        
        # Filtrar por seller_id si se especifica
        if seller_id and (not assignment or assignment.Seller.id != seller_id):
            continue
        
        # Filtrar no asignados si se especifica
        if unassigned is not None:
            if unassigned and assignment:
                continue
            if not unassigned and not assignment:
                continue
        
        # Filtrar asignados si se especifica
        if assigned is not None:
            if assigned and not assignment:
                continue
            if not assigned and assignment:
                continue
        
        result.append(ShopkeeperWithSellerResponse(**shopkeeper_dict))
    
    return result


@router.get("/shopkeepers/unassigned", response_model=List[ShopkeeperResponse])
async def list_unassigned_shopkeepers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar tenderos sin vendedor asignado"""
    # Subquery de tenderos con asignación activa
    assigned_ids = db.query(Assignment.shopkeeper_id).filter(
        Assignment.is_active == True
    ).subquery()
    
    shopkeepers = db.query(Shopkeeper).filter(
        Shopkeeper.is_active == True,
        ~Shopkeeper.id.in_(assigned_ids)
    ).all()
    
    return shopkeepers


@router.get("/shopkeepers/{shopkeeper_id}", response_model=ShopkeeperWithSellerResponse)
async def get_shopkeeper(
    shopkeeper_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener tendero por ID con información del vendedor"""
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == shopkeeper_id).first()
    if not shopkeeper:
        raise HTTPException(404, "Tendero no encontrado")
    
    # Obtener asignación activa
    assignment = db.query(Assignment, Seller).join(
        Seller, Assignment.seller_id == Seller.id
    ).filter(
        Assignment.shopkeeper_id == shopkeeper_id,
        Assignment.is_active == True
    ).first()
    
    shopkeeper_dict = {**shopkeeper.__dict__}
    if assignment:
        shopkeeper_dict["seller_id"] = assignment.Seller.id
        shopkeeper_dict["seller_name"] = assignment.Seller.name
        shopkeeper_dict["seller_email"] = assignment.Seller.email
        shopkeeper_dict["assigned_at"] = assignment.Assignment.assigned_at
        shopkeeper_dict["zone_name"] = ""
    
    return ShopkeeperWithSellerResponse(**shopkeeper_dict)


@router.put("/shopkeepers/{shopkeeper_id}", response_model=ShopkeeperResponse)
async def update_shopkeeper(
    shopkeeper_id: int,
    shopkeeper_data: ShopkeeperUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """HU4: Actualizar datos del tendero incluyendo coordenadas"""
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == shopkeeper_id).first()
    if not shopkeeper:
        raise HTTPException(404, "Tendero no encontrado")
    
    # Verificar email único si se cambia
    if shopkeeper_data.email and shopkeeper_data.email != shopkeeper.email:
        if db.query(Shopkeeper).filter(Shopkeeper.email == shopkeeper_data.email).first():
            raise HTTPException(400, "El email ya está registrado")
    
    # Actualizar campos
    for field, value in shopkeeper_data.model_dump(exclude_unset=True).items():
        setattr(shopkeeper, field, value)
    
    db.commit()
    db.refresh(shopkeeper)
    return shopkeeper


@router.delete("/shopkeepers/{shopkeeper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shopkeeper(
    shopkeeper_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Eliminar tendero (soft delete)"""
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == shopkeeper_id).first()
    if not shopkeeper:
        raise HTTPException(404, "Tendero no encontrado")
    
    shopkeeper.is_active = False
    db.commit()
    return None

