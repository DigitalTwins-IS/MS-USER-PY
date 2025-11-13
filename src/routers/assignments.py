"""
Router de Asignaciones (Assignments)
Gestiona la relación entre vendedores y tenderos
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from ..cache import route_cache

from ..models import get_db, Assignment, Seller, Shopkeeper
from ..schemas import (
    AssignmentCreate, ReassignmentRequest,
    AssignmentDetailResponse, AssignmentHistoryResponse
)
from ..utils import get_current_user
from ..config import settings

router = APIRouter()


@router.post("/assign", response_model=AssignmentDetailResponse, status_code=status.HTTP_201_CREATED)
async def assign_shopkeeper(
    assignment_data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Asignar tendero a vendedor"""
    # Verificar vendedor existe
    seller = db.query(Seller).filter(Seller.id == assignment_data.seller_id).first()
    if not seller:
        raise HTTPException(404, "Vendedor no encontrado")
    
    # Verificar tendero existe
    shopkeeper = db.query(Shopkeeper).filter(
        Shopkeeper.id == assignment_data.shopkeeper_id
    ).first()
    if not shopkeeper:
        raise HTTPException(404, "Tendero no encontrado")
    
    # Verificar que no esté ya asignado
    existing = db.query(Assignment).filter(
        Assignment.shopkeeper_id == assignment_data.shopkeeper_id,
        Assignment.is_active == True
    ).first()
    if existing:
        raise HTTPException(400, "El tendero ya está asignado a otro vendedor")
    
    # Verificar límite de tenderos (solo advertencia)
    count = db.query(Assignment).filter(
        Assignment.seller_id == assignment_data.seller_id,
        Assignment.is_active == True
    ).count()
    
    if count >= settings.MAX_SHOPKEEPERS_PER_SELLER:
        print(f"⚠️  WARNING: Vendedor {seller.id} supera límite de {settings.MAX_SHOPKEEPERS_PER_SELLER} tenderos")
    
    # Crear asignación
    new_assignment = Assignment(
        seller_id=assignment_data.seller_id,
        shopkeeper_id=assignment_data.shopkeeper_id,
        notes=assignment_data.notes,
        assigned_by=1,  # TODO: Obtener del current_user
        is_active=True
    )
    
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    route_cache.invalidate_seller(assignment_data.seller_id) 
    
    # Preparar respuesta con nombres
    response_data = {
        **new_assignment.__dict__,
        "seller_name": seller.name,
        "shopkeeper_name": shopkeeper.name,
        "assigned_by_name": "Admin",
        "unassigned_by_name": None
    }
    
    return AssignmentDetailResponse(**response_data)


@router.post("/reassign", response_model=AssignmentDetailResponse)
async def reassign_shopkeeper(
    reassignment_data: ReassignmentRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Reasignar tendero a otro vendedor"""
    # Obtener asignación actual
    current_assignment = db.query(Assignment).filter(
        Assignment.shopkeeper_id == reassignment_data.shopkeeper_id,
        Assignment.is_active == True
    ).first()
    
    if not current_assignment:
        raise HTTPException(404, "El tendero no tiene asignación activa")
    
    # Verificar nuevo vendedor existe
    new_seller = db.query(Seller).filter(
        Seller.id == reassignment_data.new_seller_id
    ).first()
    if not new_seller:
        raise HTTPException(404, "El nuevo vendedor no existe")
    
    shopkeeper = db.query(Shopkeeper).filter(
        Shopkeeper.id == reassignment_data.shopkeeper_id
    ).first()
    
    # Desactivar asignación actual
    current_assignment.is_active = False
    current_assignment.unassigned_by = 1  # TODO: Obtener del current_user
    
    # Crear nueva asignación
    new_assignment = Assignment(
        seller_id=reassignment_data.new_seller_id,
        shopkeeper_id=reassignment_data.shopkeeper_id,
        notes=reassignment_data.notes,
        assigned_by=1,
        is_active=True
    )
    
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    route_cache.invalidate_seller(current_assignment.seller_id)
    route_cache.invalidate_seller(reassignment_data.new_seller_id)
    
    response_data = {
        **new_assignment.__dict__,
        "seller_name": new_seller.name,
        "shopkeeper_name": shopkeeper.name,
        "assigned_by_name": "Admin",
        "unassigned_by_name": None
    }
    
    return AssignmentDetailResponse(**response_data)


@router.get("/assignments", response_model=List[AssignmentDetailResponse])
async def list_assignments(
    is_active: bool = Query(True),
    seller_id: int = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar asignaciones con información detallada"""
    query = db.query(Assignment, Seller, Shopkeeper).join(
        Seller, Assignment.seller_id == Seller.id
    ).join(
        Shopkeeper, Assignment.shopkeeper_id == Shopkeeper.id
    )
    
    if is_active is not None:
        query = query.filter(Assignment.is_active == is_active)
    
    if seller_id:
        query = query.filter(Assignment.seller_id == seller_id)
    
    assignments = query.offset(skip).limit(limit).all()
    
    result = []
    for assignment, seller, shopkeeper in assignments:
        response_data = {
            **assignment.__dict__,
            "seller_name": seller.name,
            "shopkeeper_name": shopkeeper.name,
            "assigned_by_name": "Admin",
            "unassigned_by_name": None
        }
        result.append(AssignmentDetailResponse(**response_data))
    
    return result


@router.get("/assignments/history/{shopkeeper_id}", response_model=AssignmentHistoryResponse)
async def get_assignment_history(
    shopkeeper_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener historial completo de asignaciones de un tendero"""
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == shopkeeper_id).first()
    if not shopkeeper:
        raise HTTPException(404, "Tendero no encontrado")
    
    # Obtener todas las asignaciones (activas e inactivas)
    assignments = db.query(Assignment, Seller).join(
        Seller, Assignment.seller_id == Seller.id
    ).filter(
        Assignment.shopkeeper_id == shopkeeper_id
    ).order_by(Assignment.assigned_at.desc()).all()
    
    assignments_list = []
    for assignment, seller in assignments:
        response_data = {
            **assignment.__dict__,
            "seller_name": seller.name,
            "shopkeeper_name": shopkeeper.name,
            "assigned_by_name": "Admin",
            "unassigned_by_name": None
        }
        assignments_list.append(AssignmentDetailResponse(**response_data))
    
    return AssignmentHistoryResponse(
        shopkeeper_id=shopkeeper_id,
        shopkeeper_name=shopkeeper.name,
        assignments=assignments_list,
        total_assignments=len(assignments_list)
    )


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_shopkeeper(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Desactivar asignación (desasignar tendero)"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Asignación no encontrada")
    
    assignment.is_active = False
    assignment.unassigned_by = 1  # TODO: Obtener del current_user
    
    db.commit()
    route_cache.invalidate_seller(seller_id)
    return None

