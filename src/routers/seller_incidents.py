from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.models.database import get_db
from src.models.seller_incidents import SellerIncident
from src.schemas.seller_incidents import (
    SellerIncidentCreate, SellerIncidentUpdate, SellerIncidentResponse
)
from src.models.seller import Seller
from src.models.shopkeeper import Shopkeeper
from src.utils.auth import get_current_user

router = APIRouter(prefix="/seller-incidents", tags=["Seller Incidents"])

# ============================================================
# LISTAR INCIDENCIAS CON NOMBRES
# ============================================================

@router.get("/")
def list_incidents(
    seller_id: int = None,
    type: str = None,
    shopkeeper_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(SellerIncident)

    if seller_id:
        query = query.filter(SellerIncident.seller_id == seller_id)

    if type:
        query = query.filter(SellerIncident.type == type)

    if shopkeeper_id:
        query = query.filter(SellerIncident.shopkeeper_id == shopkeeper_id)

    incidents = query.order_by(SellerIncident.created_at.desc()).all()

    response = []
    for i in incidents:
        seller = db.query(Seller).filter(Seller.id == i.seller_id).first()
        shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == i.shopkeeper_id).first()

        response.append({
            "id": i.id,
            "seller_id": i.seller_id,
            "seller_name": seller.name if seller else None,
            "shopkeeper_id": i.shopkeeper_id,
            "shopkeeper_name": shopkeeper.name if shopkeeper else None,
            "type": i.type,
            "description": i.description,
            "incident_date": i.incident_date,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
        })

    return response


# ============================================================
# CREAR INCIDENCIA
# ============================================================

@router.post("/")
def create_incident(
    data: SellerIncidentCreate,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = SellerIncident(**data.dict())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


# ============================================================
# OBTENER UNA INCIDENCIA POR ID CON NOMBRES
# ============================================================

@router.get("/{incident_id}")
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db)
):
    i = db.query(SellerIncident).filter(SellerIncident.id == incident_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    seller = db.query(Seller).filter(Seller.id == i.seller_id).first()
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == i.shopkeeper_id).first()

    return {
        "id": i.id,
        "seller_id": i.seller_id,
        "seller_name": seller.name if seller else None,
        "shopkeeper_id": i.shopkeeper_id,
        "shopkeeper_name": shopkeeper.name if shopkeeper else None,
        "type": i.type,
        "description": i.description,
        "incident_date": i.incident_date,
        "created_at": i.created_at,
        "updated_at": i.updated_at,
    }


# ============================================================
# EDITAR INCIDENCIA
# ============================================================

@router.put("/{incident_id}")
def update_incident(
    incident_id: int,
    data: SellerIncidentUpdate,
    db: Session = Depends(get_db)
):
    incident = db.query(SellerIncident).filter(SellerIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    # Aplicar cambios
    for field, value in data.dict(exclude_unset=True).items():
        setattr(incident, field, value)

    db.commit()
    db.refresh(incident)

    # Obtener nombres actualizados
    seller = db.query(Seller).filter(Seller.id == incident.seller_id).first()
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == incident.shopkeeper_id).first()

    return {
        "id": incident.id,
        "seller_id": incident.seller_id,
        "seller_name": seller.name if seller else None,
        "shopkeeper_id": incident.shopkeeper_id,
        "shopkeeper_name": shopkeeper.name if shopkeeper else None,
        "type": incident.type,
        "description": incident.description,
        "incident_date": incident.incident_date,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at,
    }

    # ============================================================
# ELIMINAR INCIDENCIA
# ============================================================

@router.delete("/{incident_id}", status_code=204)
def delete_incident(
    incident_id: int,
    db: Session = Depends(get_db)
):
    incident = db.query(SellerIncident).filter(SellerIncident.id == incident_id).first()

    if not incident:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    db.delete(incident)
    db.commit()
    return