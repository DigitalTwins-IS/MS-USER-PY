"""
Router de Incidencias de Vendedor (SellerIncidents)
HU16: Registrar incidencias durante visitas
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from ..models import get_db, SellerIncident, Seller, Shopkeeper, Visit
from ..schemas.seller_incidents import (
    SellerIncidentCreate,
    SellerIncidentUpdate,
    SellerIncidentResponse,
    SellerIncidentDetailResponse
)
from ..utils.auth import get_current_user

router = APIRouter()


# ============================================================================
# LISTAR INCIDENCIAS
# ============================================================================

@router.get("/seller-incidents", response_model=List[SellerIncidentDetailResponse])
async def list_incidents(
    seller_id: Optional[int] = Query(None, description="Filtrar por vendedor"),
    visit_id: Optional[int] = Query(None, description="Filtrar por visita"),
    type: Optional[str] = Query(None, description="Filtrar por tipo (absence, delay, non_compliance)"),
    shopkeeper_id: Optional[int] = Query(None, description="Filtrar por tendero"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Listar incidencias de vendedores
    HU16: Permite ver todas las incidencias registradas, con filtros
    """
    query = db.query(SellerIncident)

    # Aplicar filtros
    if seller_id:
        query = query.filter(SellerIncident.seller_id == seller_id)
    
    if visit_id:
        query = query.filter(SellerIncident.visit_id == visit_id)
    
    if type:
        if type not in ["absence", "delay", "non_compliance"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de incidencia inválido. Debe ser: absence, delay o non_compliance"
            )
        query = query.filter(SellerIncident.type == type)
    
    if shopkeeper_id:
        query = query.filter(SellerIncident.shopkeeper_id == shopkeeper_id)

    incidents = query.order_by(SellerIncident.created_at.desc()).all()

    # Construir respuesta con información detallada
    response = []
    for incident in incidents:
        seller = db.query(Seller).filter(Seller.id == incident.seller_id).first()
        shopkeeper = None
        visit = None
        
        if incident.shopkeeper_id:
            shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == incident.shopkeeper_id).first()
        
        if incident.visit_id:
            visit = db.query(Visit).filter(Visit.id == incident.visit_id).first()

        response.append(SellerIncidentDetailResponse(
            id=incident.id,
            seller_id=incident.seller_id,
            seller_name=seller.name if seller else None,
            shopkeeper_id=incident.shopkeeper_id,
            shopkeeper_name=shopkeeper.name if shopkeeper else None,
            shopkeeper_business_name=shopkeeper.business_name if shopkeeper else None,
            visit_id=incident.visit_id,
            visit_scheduled_date=visit.scheduled_date if visit else None,
            visit_status=visit.status if visit else None,
            type=incident.type,
            description=incident.description,
            incident_date=incident.incident_date,
            created_at=incident.created_at,
            updated_at=incident.updated_at
        ))

    return response


# ============================================================================
# CREAR INCIDENCIA
# ============================================================================

@router.post("/seller-incidents", response_model=SellerIncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    data: SellerIncidentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Crear una nueva incidencia
    HU16: Permite registrar incidencias relacionadas con visitas
    
    Si se proporciona visit_id, se valida que la visita exista y se obtiene
    automáticamente el seller_id y shopkeeper_id de la visita si no se proporcionan.
    """
    # Preparar datos para la incidencia
    incident_data = data.dict()
    seller_id = incident_data.get("seller_id")
    shopkeeper_id = incident_data.get("shopkeeper_id")
    visit_id = incident_data.get("visit_id")
    
    # Si se proporciona visit_id, validar y obtener información de la visita
    if visit_id:
        visit = db.query(Visit).filter(Visit.id == visit_id).first()
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visita no encontrada"
            )
        
        # Si no se proporciona seller_id, obtenerlo de la visita
        if not seller_id:
            seller_id = visit.seller_id
            incident_data["seller_id"] = seller_id
        # Si se proporciona seller_id, validar que coincida con el de la visita
        elif seller_id != visit.seller_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El seller_id no coincide con el de la visita"
            )
        
        # Si no se proporciona shopkeeper_id, obtenerlo de la visita
        if not shopkeeper_id:
            shopkeeper_id = visit.shopkeeper_id
            incident_data["shopkeeper_id"] = shopkeeper_id
        # Si se proporciona shopkeeper_id, validar que coincida con el de la visita
        elif shopkeeper_id != visit.shopkeeper_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El shopkeeper_id no coincide con el de la visita"
            )
    
    # Validar que el vendedor existe (después de obtenerlo de la visita si es necesario)
    if not seller_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="seller_id es requerido. Proporciona seller_id o visit_id"
        )
    
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendedor no encontrado"
        )
    
    # Si se proporciona shopkeeper_id, validar que existe
    if shopkeeper_id:
        shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == shopkeeper_id).first()
        if not shopkeeper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tendero no encontrado"
            )
    
    # Crear la incidencia
    incident = SellerIncident(**incident_data)
    
    db.add(incident)
    db.commit()
    db.refresh(incident)
    
    return SellerIncidentResponse(
        id=incident.id,
        seller_id=incident.seller_id,
        shopkeeper_id=incident.shopkeeper_id,
        visit_id=incident.visit_id,
        type=incident.type,
        description=incident.description,
        incident_date=incident.incident_date,
        created_at=incident.created_at,
        updated_at=incident.updated_at
    )


# ============================================================================
# OBTENER INCIDENCIA POR ID
# ============================================================================

@router.get("/seller-incidents/{incident_id}", response_model=SellerIncidentDetailResponse)
async def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener una incidencia específica por ID"""
    incident = db.query(SellerIncident).filter(SellerIncident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidencia no encontrada"
        )

    seller = db.query(Seller).filter(Seller.id == incident.seller_id).first()
    shopkeeper = None
    visit = None
    
    if incident.shopkeeper_id:
        shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == incident.shopkeeper_id).first()
    
    if incident.visit_id:
        visit = db.query(Visit).filter(Visit.id == incident.visit_id).first()

    return SellerIncidentDetailResponse(
        id=incident.id,
        seller_id=incident.seller_id,
        seller_name=seller.name if seller else None,
        shopkeeper_id=incident.shopkeeper_id,
        shopkeeper_name=shopkeeper.name if shopkeeper else None,
        shopkeeper_business_name=shopkeeper.business_name if shopkeeper else None,
        visit_id=incident.visit_id,
        visit_scheduled_date=visit.scheduled_date if visit else None,
        visit_status=visit.status if visit else None,
        type=incident.type,
        description=incident.description,
        incident_date=incident.incident_date,
        created_at=incident.created_at,
        updated_at=incident.updated_at
    )


# ============================================================================
# ACTUALIZAR INCIDENCIA
# ============================================================================

@router.put("/seller-incidents/{incident_id}", response_model=SellerIncidentResponse)
async def update_incident(
    incident_id: int,
    data: SellerIncidentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Actualizar una incidencia existente"""
    incident = db.query(SellerIncident).filter(SellerIncident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidencia no encontrada"
        )
    
    # Validar visit_id si se proporciona
    if data.visit_id is not None:
        visit = db.query(Visit).filter(Visit.id == data.visit_id).first()
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visita no encontrada"
            )
        
        # Validar que el seller_id coincida
        seller_id = data.seller_id if data.seller_id is not None else incident.seller_id
        if seller_id != visit.seller_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El seller_id no coincide con el de la visita"
            )
    
    # Validar seller_id si se proporciona
    if data.seller_id is not None:
        seller = db.query(Seller).filter(Seller.id == data.seller_id).first()
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendedor no encontrado"
            )
    
    # Validar shopkeeper_id si se proporciona
    if data.shopkeeper_id is not None:
        shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == data.shopkeeper_id).first()
        if not shopkeeper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tendero no encontrado"
            )
    
    # Aplicar cambios
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)

    db.commit()
    db.refresh(incident)

    return SellerIncidentResponse(
        id=incident.id,
        seller_id=incident.seller_id,
        shopkeeper_id=incident.shopkeeper_id,
        visit_id=incident.visit_id,
        type=incident.type,
        description=incident.description,
        incident_date=incident.incident_date,
        created_at=incident.created_at,
        updated_at=incident.updated_at
    )


# ============================================================================
# ELIMINAR INCIDENCIA
# ============================================================================

@router.delete("/seller-incidents/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Eliminar una incidencia"""
    incident = db.query(SellerIncident).filter(SellerIncident.id == incident_id).first()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidencia no encontrada"
        )

    db.delete(incident)
    db.commit()
    return None


# ============================================================================
# OBTENER INCIDENCIAS DE UNA VISITA
# ============================================================================

@router.get("/visits/{visit_id}/incidents", response_model=List[SellerIncidentResponse])
async def get_visit_incidents(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener todas las incidencias relacionadas con una visita específica
    """
    # Validar que la visita existe
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visita no encontrada"
        )
    
    # Obtener incidencias de la visita
    incidents = db.query(SellerIncident).filter(
        SellerIncident.visit_id == visit_id
    ).order_by(SellerIncident.created_at.desc()).all()
    
    return [
        SellerIncidentResponse(
            id=incident.id,
            seller_id=incident.seller_id,
            shopkeeper_id=incident.shopkeeper_id,
            visit_id=incident.visit_id,
            type=incident.type,
            description=incident.description,
            incident_date=incident.incident_date,
            created_at=incident.created_at,
            updated_at=incident.updated_at
        )
        for incident in incidents
    ]
