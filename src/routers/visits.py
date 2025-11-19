"""
Router de Visitas (Visits) - HU21
Agendar visitas basadas en inventario
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, time, timedelta, timezone

from ..models import (
    get_db, Visit, Seller, Shopkeeper, Assignment, ShopkeeperInventory, SellerIncident
)
from ..schemas.visit import (
    VisitCreate, VisitUpdate, VisitCancelRequest, VisitStatusUpdate,
    VisitResponse, VisitDetailResponse, ShopkeeperLowStockResponse,
    VisitListResponse
)
from ..utils import get_current_user

router = APIRouter()


def get_seller_by_user(db: Session, user_email: str, user_role: str, user_id: Optional[int] = None) -> Optional[Seller]:
    """
    Obtener el vendedor asociado al usuario autenticado
    Busca por user_id (más confiable) o por email (fallback)
    """
    # Si el usuario es VENDEDOR, buscar por user_id primero (más confiable)
    if user_role == "VENDEDOR":
        # Buscar por user_id si está disponible (más confiable)
        if user_id:
            seller = db.query(Seller).filter(Seller.user_id == user_id).first()
            if seller:
                return seller
        
        # Fallback: buscar por email
        if user_email:
            seller = db.query(Seller).filter(Seller.email == user_email).first()
            if seller:
                return seller
    
    # Si el usuario es ADMIN, no puede agendar visitas directamente
    # Necesitaríamos un seller_id en el request
    return None


def validate_scheduled_date(scheduled_date: datetime) -> None:
    """
    Validar que la fecha/hora de la visita sea futura y en horario laboral
    Horario laboral: 8:00 AM - 6:00 PM (hora local del usuario)
    
    """
    # Si la fecha tiene timezone, extraer la hora en su zona horaria original
    # Esto es lo que el usuario seleccionó (hora local)
    if scheduled_date.tzinfo is not None:
        # La hora local es la hora del datetime en su zona horaria original
        # No convertimos a UTC para validar, porque queremos validar la hora que el usuario ve
        visit_time_local = scheduled_date.time()
        
        # Para validar si es futura, convertimos a UTC para comparar
        date_utc = scheduled_date.astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)
        
        # Validar que la fecha sea futura (con margen de 1 minuto)
        if date_utc <= (now_utc - timedelta(minutes=1)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha y hora de la visita debe ser futura"
            )
        
        # Validar horario laboral usando la hora LOCAL (la que el usuario seleccionó)
        visit_time = visit_time_local
    else:
        # Si no tiene timezone, asumir que es hora local (formato legacy)
        visit_time = scheduled_date.time()
        
        # Validar que la fecha sea futura (menos preciso sin timezone)
        now_local = datetime.now()
        if scheduled_date <= (now_local - timedelta(minutes=1)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha y hora de la visita debe ser futura"
            )
    
    # Validar horario laboral (8:00 AM - 6:00 PM) en hora LOCAL
    visit_hour = visit_time.hour
    visit_minute = visit_time.minute
    
    # Convertir a minutos desde medianoche para comparación precisa
    visit_minutes = visit_hour * 60 + visit_minute
    work_start_minutes = 8 * 60   # 8:00 AM = 480 minutos
    work_end_minutes = 18 * 60    # 6:00 PM = 1080 minutos (incluye exactamente 6:00 PM)
    
    # Validar rango: 8:00 AM - 6:00 PM (incluyendo exactamente 6:00 PM)
    if visit_minutes < work_start_minutes or visit_minutes > work_end_minutes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La visita debe programarse en horario laboral (8:00 AM - 6:00 PM). Hora recibida: {visit_time.strftime('%I:%M %p')} (hora local)"
        )


def verify_shopkeeper_assigned_to_seller(
    db: Session, seller_id: int, shopkeeper_id: int
) -> bool:
    """
    Verificar que el tendero esté asignado al vendedor
    """
    assignment = db.query(Assignment).filter(
        Assignment.seller_id == seller_id,
        Assignment.shopkeeper_id == shopkeeper_id,
        Assignment.is_active == True
    ).first()
    
    return assignment is not None


# ============================================================================
# ENDPOINTS DE VISITAS
# ============================================================================

@router.get("/visits", response_model=VisitListResponse)
async def list_visits(
    status_filter: Optional[str] = Query(None, description="Filtrar por estado (pending, completed, cancelled)"),
    shopkeeper_id: Optional[int] = Query(None, description="Filtrar por tendero"),
    seller_id: Optional[int] = Query(None, description="Filtrar por vendedor (solo para ADMIN)"),
    start_date: Optional[datetime] = Query(None, description="Fecha de inicio"),
    end_date: Optional[datetime] = Query(None, description="Fecha de fin"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Listar visitas
    HU21: El vendedor puede ver todas sus visitas agendadas
    ADMIN puede ver todas las visitas
    TENDERO no tiene acceso a visitas (solo visualización si es necesario)
    """
    user_role = current_user.get("role")
    
    # TENDERO no tiene acceso a visitas
    if user_role == "TENDERO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver visitas"
        )
    
    # Construir query base
    query = db.query(
        Visit, Seller, Shopkeeper
    ).join(
        Seller, Visit.seller_id == Seller.id
    ).join(
        Shopkeeper, Visit.shopkeeper_id == Shopkeeper.id
    )
    
    # Aplicar filtros según el rol
    seller = None
    if user_role == "VENDEDOR":
        # Vendedor solo ve sus propias visitas
        seller = get_seller_by_user(
            db, 
            current_user.get("email"), 
            user_role,
            current_user.get("user_id")
        )
        if not seller:
            # Si no hay vendedor asociado, retornar lista vacía en lugar de error
            # Esto permite que el vendedor vea la página aunque no tenga vendedor asociado todavía
            return VisitListResponse(
                visits=[],
                total=0,
                pending=0,
                completed=0,
                cancelled=0
            )
        query = query.filter(Visit.seller_id == seller.id)
    elif user_role == "ADMIN":
        # ADMIN puede ver todas las visitas, pero puede filtrar por vendedor
        if seller_id:
            query = query.filter(Visit.seller_id == seller_id)
    
    # Aplicar filtros adicionales
    if status_filter:
        query = query.filter(Visit.status == status_filter)
    
    if shopkeeper_id:
        query = query.filter(Visit.shopkeeper_id == shopkeeper_id)
    
    if start_date:
        query = query.filter(Visit.scheduled_date >= start_date)
    
    if end_date:
        query = query.filter(Visit.scheduled_date <= end_date)
    
    # Calcular estadísticas usando la misma query base
    base_query = db.query(Visit)
    if user_role == "VENDEDOR" and seller:
        base_query = base_query.filter(Visit.seller_id == seller.id)
    elif user_role == "ADMIN" and seller_id:
        base_query = base_query.filter(Visit.seller_id == seller_id)
    
    # Aplicar los mismos filtros a las estadísticas
    if status_filter:
        base_query = base_query.filter(Visit.status == status_filter)
    if shopkeeper_id:
        base_query = base_query.filter(Visit.shopkeeper_id == shopkeeper_id)
    if start_date:
        base_query = base_query.filter(Visit.scheduled_date >= start_date)
    if end_date:
        base_query = base_query.filter(Visit.scheduled_date <= end_date)
    
    # Calcular estadísticas
    pending_count = base_query.filter(Visit.status == "pending").count()
    completed_count = base_query.filter(Visit.status == "completed").count()
    cancelled_count = base_query.filter(Visit.status == "cancelled").count()
    total = base_query.count()
    
    # Aplicar paginación
    results = query.order_by(Visit.scheduled_date.asc()).offset(skip).limit(limit).all()
    
    # Construir respuesta
    visits = []
    for visit, seller_obj, shopkeeper in results:
        visits.append(VisitDetailResponse(
            id=visit.id,
            seller_id=visit.seller_id,
            seller_name=seller_obj.name,
            shopkeeper_id=visit.shopkeeper_id,
            shopkeeper_name=shopkeeper.name,
            shopkeeper_business_name=shopkeeper.business_name,
            shopkeeper_address=shopkeeper.address,
            shopkeeper_phone=shopkeeper.phone,
            shopkeeper_email=shopkeeper.email,
            scheduled_date=visit.scheduled_date,
            status=visit.status,
            reason=visit.reason,
            notes=visit.notes,
            completed_at=visit.completed_at,
            cancelled_at=visit.cancelled_at,
            cancelled_reason=visit.cancelled_reason,
            created_at=visit.created_at,
            updated_at=visit.updated_at
        ))
    
    return VisitListResponse(
        visits=visits,
        total=total,
        pending=pending_count,
        completed=completed_count,
        cancelled=cancelled_count
    )


@router.get("/visits/{visit_id}", response_model=VisitDetailResponse)
async def get_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener detalle de una visita
    HU21: El vendedor puede ver el detalle de sus visitas
    ADMIN y TENDERO pueden ver cualquier visita
    """
    user_role = current_user.get("role")
    
    # Obtener la visita
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visita no encontrada"
        )
    
    # Si es VENDEDOR, verificar que la visita sea suya
    if user_role == "VENDEDOR":
        seller = get_seller_by_user(
            db, 
            current_user.get("email"), 
            user_role,
            current_user.get("user_id")
        )
        if not seller or visit.seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para ver esta visita"
            )
    
    # Obtener información del vendedor y tendero
    seller_obj = db.query(Seller).filter(Seller.id == visit.seller_id).first()
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == visit.shopkeeper_id).first()
    
    # Contar incidencias relacionadas con esta visita
    incidents_count = db.query(SellerIncident).filter(
        SellerIncident.visit_id == visit_id
    ).count()
    
    return VisitDetailResponse(
        id=visit.id,
        seller_id=visit.seller_id,
        seller_name=seller_obj.name,
        shopkeeper_id=visit.shopkeeper_id,
        shopkeeper_name=shopkeeper.name,
        shopkeeper_business_name=shopkeeper.business_name,
        shopkeeper_address=shopkeeper.address,
        shopkeeper_phone=shopkeeper.phone,
        shopkeeper_email=shopkeeper.email,
        scheduled_date=visit.scheduled_date,
        status=visit.status,
        reason=visit.reason,
        notes=visit.notes,
        completed_at=visit.completed_at,
        cancelled_at=visit.cancelled_at,
        cancelled_reason=visit.cancelled_reason,
        created_at=visit.created_at,
        updated_at=visit.updated_at,
        incidents_count=incidents_count
    )


@router.post("/visits", response_model=VisitResponse, status_code=status.HTTP_201_CREATED)
async def create_visit(
    visit_data: VisitCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Agendar nueva visita
    HU21: El vendedor puede agendar visitas a tenderos asignados
    """
    user_role = current_user.get("role")
    user_email = current_user.get("email")
    user_id = current_user.get("user_id")
    
    # Verificar que el usuario sea VENDEDOR
    if user_role != "VENDEDOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los vendedores pueden agendar visitas"
        )
    
    # Obtener el vendedor asociado al usuario
    seller = get_seller_by_user(db, user_email, user_role, user_id)
    
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No se encontró un vendedor asociado a tu cuenta. Email: {user_email}, User ID: {user_id}, Role: {user_role}"
        )
    
    # Verificar que el tendero existe
    shopkeeper = db.query(Shopkeeper).filter(
        Shopkeeper.id == visit_data.shopkeeper_id
    ).first()
    
    if not shopkeeper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tendero no encontrado"
        )
    
    # Verificar que el tendero esté asignado al vendedor
    if not verify_shopkeeper_assigned_to_seller(db, seller.id, visit_data.shopkeeper_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El tendero no está asignado a ti"
        )
    
    # Validar fecha/hora de la visita
    validate_scheduled_date(visit_data.scheduled_date)
    
    # Crear la visita
    new_visit = Visit(
        seller_id=seller.id,
        shopkeeper_id=visit_data.shopkeeper_id,
        scheduled_date=visit_data.scheduled_date,
        status="pending",
        reason=visit_data.reason or "reabastecimiento",
        notes=visit_data.notes
    )
    
    db.add(new_visit)
    db.commit()
    db.refresh(new_visit)
    
    return VisitResponse(
        id=new_visit.id,
        seller_id=new_visit.seller_id,
        shopkeeper_id=new_visit.shopkeeper_id,
        scheduled_date=new_visit.scheduled_date,
        status=new_visit.status,
        reason=new_visit.reason,
        notes=new_visit.notes,
        completed_at=new_visit.completed_at,
        cancelled_at=new_visit.cancelled_at,
        cancelled_reason=new_visit.cancelled_reason,
        created_at=new_visit.created_at,
        updated_at=new_visit.updated_at
    )


@router.put("/visits/{visit_id}", response_model=VisitResponse)
async def update_visit(
    visit_id: int,
    visit_data: VisitUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualizar visita
    HU21: El vendedor puede actualizar visitas pendientes
    """
    user_role = current_user.get("role")
    user_email = current_user.get("email")
    user_id = current_user.get("user_id")
    
    # Obtener el vendedor asociado al usuario
    seller = get_seller_by_user(db, user_email, user_role, user_id)
    
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se encontró un vendedor asociado a tu cuenta"
        )
    
    # Obtener la visita
    visit = db.query(Visit).filter(
        Visit.id == visit_id,
        Visit.seller_id == seller.id
    ).first()
    
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visita no encontrada"
        )
    
    # Solo se pueden actualizar visitas pendientes
    if visit.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede actualizar una visita {visit.status}"
        )
    
    # Actualizar campos
    if visit_data.scheduled_date:
        validate_scheduled_date(visit_data.scheduled_date)
        visit.scheduled_date = visit_data.scheduled_date
    
    if visit_data.reason is not None:
        visit.reason = visit_data.reason
    
    if visit_data.notes is not None:
        visit.notes = visit_data.notes
    
    db.commit()
    db.refresh(visit)
    
    return VisitResponse(
        id=visit.id,
        seller_id=visit.seller_id,
        shopkeeper_id=visit.shopkeeper_id,
        scheduled_date=visit.scheduled_date,
        status=visit.status,
        reason=visit.reason,
        notes=visit.notes,
        completed_at=visit.completed_at,
        cancelled_at=visit.cancelled_at,
        cancelled_reason=visit.cancelled_reason,
        created_at=visit.created_at,
        updated_at=visit.updated_at
    )


@router.patch("/visits/{visit_id}/cancel", response_model=VisitResponse)
async def cancel_visit(
    visit_id: int,
    cancel_data: VisitCancelRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cancelar visita
    HU21: El vendedor puede cancelar visitas pendientes
    """
    user_role = current_user.get("role")
    user_email = current_user.get("email")
    user_id = current_user.get("user_id")
    
    # Obtener el vendedor asociado al usuario
    seller = get_seller_by_user(db, user_email, user_role, user_id)
    
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se encontró un vendedor asociado a tu cuenta"
        )
    
    # Obtener la visita
    visit = db.query(Visit).filter(
        Visit.id == visit_id,
        Visit.seller_id == seller.id
    ).first()
    
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visita no encontrada"
        )
    
    # Permitir cancelar visitas en cualquier estado (flexibilidad)
    # Si ya está cancelada, solo actualizar la razón si se proporciona
    if visit.status == "cancelled" and cancel_data.cancelled_reason:
        visit.cancelled_reason = cancel_data.cancelled_reason
        db.commit()
        db.refresh(visit)
        return VisitResponse(
            id=visit.id,
            seller_id=visit.seller_id,
            shopkeeper_id=visit.shopkeeper_id,
            scheduled_date=visit.scheduled_date,
            status=visit.status,
            reason=visit.reason,
            notes=visit.notes,
            completed_at=visit.completed_at,
            cancelled_at=visit.cancelled_at,
            cancelled_reason=visit.cancelled_reason,
            created_at=visit.created_at,
            updated_at=visit.updated_at
        )
    
    # Cancelar la visita
    visit.status = "cancelled"
    visit.cancelled_at = datetime.now(timezone.utc)
    visit.cancelled_reason = cancel_data.cancelled_reason
    # Limpiar completed_at si existía
    visit.completed_at = None
    
    db.commit()
    db.refresh(visit)
    
    return VisitResponse(
        id=visit.id,
        seller_id=visit.seller_id,
        shopkeeper_id=visit.shopkeeper_id,
        scheduled_date=visit.scheduled_date,
        status=visit.status,
        reason=visit.reason,
        notes=visit.notes,
        completed_at=visit.completed_at,
        cancelled_at=visit.cancelled_at,
        cancelled_reason=visit.cancelled_reason,
        created_at=visit.created_at,
        updated_at=visit.updated_at
    )


@router.patch("/visits/{visit_id}/complete", response_model=VisitResponse)
async def complete_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Marcar visita como completada
    HU21: El vendedor puede marcar visitas como completadas
    """
    user_role = current_user.get("role")
    user_email = current_user.get("email")
    user_id = current_user.get("user_id")
    
    # Obtener el vendedor asociado al usuario
    seller = get_seller_by_user(db, user_email, user_role, user_id)
    
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se encontró un vendedor asociado a tu cuenta"
        )
    
    # Obtener la visita
    visit = db.query(Visit).filter(
        Visit.id == visit_id,
        Visit.seller_id == seller.id
    ).first()
    
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visita no encontrada"
        )
    
    # Permitir completar visitas en cualquier estado (flexibilidad)
    # Si ya está completada, solo actualizar el timestamp
    if visit.status == "completed":
        visit.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(visit)
        return VisitResponse(
            id=visit.id,
            seller_id=visit.seller_id,
            shopkeeper_id=visit.shopkeeper_id,
            scheduled_date=visit.scheduled_date,
            status=visit.status,
            reason=visit.reason,
            notes=visit.notes,
            completed_at=visit.completed_at,
            cancelled_at=visit.cancelled_at,
            cancelled_reason=visit.cancelled_reason,
            created_at=visit.created_at,
            updated_at=visit.updated_at
        )
    
    # Completar la visita
    visit.status = "completed"
    visit.completed_at = datetime.now(timezone.utc)
    # Limpiar datos de cancelación si existían
    visit.cancelled_at = None
    visit.cancelled_reason = None
    
    db.commit()
    db.refresh(visit)
    
    return VisitResponse(
        id=visit.id,
        seller_id=visit.seller_id,
        shopkeeper_id=visit.shopkeeper_id,
        scheduled_date=visit.scheduled_date,
        status=visit.status,
        reason=visit.reason,
        notes=visit.notes,
        completed_at=visit.completed_at,
        cancelled_at=visit.cancelled_at,
        cancelled_reason=visit.cancelled_reason,
        created_at=visit.created_at,
        updated_at=visit.updated_at
    )


# ============================================================================
# CAMBIAR ESTADO DE VISITA
# ============================================================================

@router.patch("/visits/{visit_id}/status", response_model=VisitResponse)
async def update_visit_status(
    visit_id: int,
    status_data: VisitStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cambiar el estado de una visita
    Permite cambiar el estado entre: pending, completed, cancelled
    
    Reglas de negocio:
    - Solo el vendedor propietario o ADMIN pueden cambiar el estado
    - Se puede cambiar de cualquier estado a cualquier otro (flexibilidad)
    - Si se cancela, se requiere cancelled_reason
    - Si se completa, se registra completed_at automáticamente
    - Si se vuelve a pending, se limpian completed_at y cancelled_at
    """
    user_role = current_user.get("role")
    user_email = current_user.get("email")
    user_id = current_user.get("user_id")
    
    # Obtener la visita
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visita no encontrada"
        )
    
    # Verificar permisos: ADMIN puede cambiar cualquier visita, VENDEDOR solo las suyas
    if user_role != "ADMIN":
        seller = get_seller_by_user(db, user_email, user_role, user_id)
        if not seller or visit.seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para cambiar el estado de esta visita"
            )
    
    # Validar transiciones de estado
    current_status = visit.status
    new_status = status_data.status
    
    # Si el estado no cambia, solo actualizar notas si se proporcionan
    if current_status == new_status:
        if status_data.notes:
            visit.notes = status_data.notes
        db.commit()
        db.refresh(visit)
        return VisitResponse(
            id=visit.id,
            seller_id=visit.seller_id,
            shopkeeper_id=visit.shopkeeper_id,
            scheduled_date=visit.scheduled_date,
            status=visit.status,
            reason=visit.reason,
            notes=visit.notes,
            completed_at=visit.completed_at,
            cancelled_at=visit.cancelled_at,
            cancelled_reason=visit.cancelled_reason,
            created_at=visit.created_at,
            updated_at=visit.updated_at
        )
    
    # Cambiar estado según el nuevo valor
    if new_status == "completed":
        visit.status = "completed"
        visit.completed_at = datetime.now(timezone.utc)
        # Limpiar datos de cancelación si existían
        visit.cancelled_at = None
        visit.cancelled_reason = None
    
    elif new_status == "cancelled":
        visit.status = "cancelled"
        visit.cancelled_at = datetime.now(timezone.utc)
        visit.cancelled_reason = status_data.cancelled_reason
        # Limpiar datos de completado si existían
        visit.completed_at = None
    
    elif new_status == "pending":
        visit.status = "pending"
        # Limpiar datos de completado y cancelación
        visit.completed_at = None
        visit.cancelled_at = None
        visit.cancelled_reason = None
    
    # Actualizar notas si se proporcionan
    if status_data.notes:
        visit.notes = status_data.notes
    
    db.commit()
    db.refresh(visit)
    
    return VisitResponse(
        id=visit.id,
        seller_id=visit.seller_id,
        shopkeeper_id=visit.shopkeeper_id,
        scheduled_date=visit.scheduled_date,
        status=visit.status,
        reason=visit.reason,
        notes=visit.notes,
        completed_at=visit.completed_at,
        cancelled_at=visit.cancelled_at,
        cancelled_reason=visit.cancelled_reason,
        created_at=visit.created_at,
        updated_at=visit.updated_at
    )


# ============================================================================
# ENDPOINTS DE TENDEROS CON BAJO STOCK
# ============================================================================

@router.get("/visits/shopkeepers/low-stock", response_model=List[ShopkeeperLowStockResponse])
async def list_shopkeepers_with_low_stock(
    seller_id: Optional[int] = Query(None, description="Filtrar por vendedor (solo para ADMIN)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Listar tenderos con bajo stock
    HU21: El vendedor puede ver tenderos con productos de bajo stock
    ADMIN puede ver todos los tenderos con bajo stock
    TENDERO no tiene acceso a esta funcionalidad
    """
    user_role = current_user.get("role")
    seller = None
    
    # Solo VENDEDOR y ADMIN tienen acceso
    if user_role == "TENDERO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver tenderos con bajo stock"
        )
    
    # Obtener el vendedor asociado al usuario según el rol
    if user_role == "VENDEDOR":
        seller = get_seller_by_user(
            db, 
            current_user.get("email"), 
            user_role,
            current_user.get("user_id")
        )
        if not seller:
            # Si no hay vendedor asociado, retornar lista vacía
            return []
    elif user_role == "ADMIN" and seller_id:
        # ADMIN puede filtrar por vendedor específico
        seller = db.query(Seller).filter(Seller.id == seller_id).first()
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendedor no encontrado"
            )
    
    # Obtener todos los tenderos asignados al vendedor (si aplica)
    shopkeeper_ids = []
    if seller:
        assignments = db.query(Assignment).filter(
            Assignment.seller_id == seller.id,
            Assignment.is_active == True
        ).all()
        shopkeeper_ids = [assignment.shopkeeper_id for assignment in assignments]
        
        if not shopkeeper_ids:
            return []
    else:
        # ADMIN puede ver todos los tenderos con bajo stock
        if user_role == "ADMIN":
            all_shopkeepers = db.query(Shopkeeper).filter(Shopkeeper.is_active == True).all()
            shopkeeper_ids = [sk.id for sk in all_shopkeepers]
            
            if not shopkeeper_ids:
                return []
        else:
            return []
    
    # Obtener tenderos con bajo stock
    # Un tendero tiene bajo stock si tiene al menos un producto con current_stock < min_stock
    low_stock_inventories = db.query(
        ShopkeeperInventory.shopkeeper_id,
        func.count(ShopkeeperInventory.id).label('low_stock_count'),
        func.max(ShopkeeperInventory.last_updated).label('last_updated')
    ).filter(
        ShopkeeperInventory.shopkeeper_id.in_(shopkeeper_ids),
        ShopkeeperInventory.is_active == True,
        ShopkeeperInventory.current_stock < ShopkeeperInventory.min_stock
    ).group_by(
        ShopkeeperInventory.shopkeeper_id
    ).all()
    
    # Obtener total de productos por tendero
    total_products = db.query(
        ShopkeeperInventory.shopkeeper_id,
        func.count(ShopkeeperInventory.id).label('total_count')
    ).filter(
        ShopkeeperInventory.shopkeeper_id.in_(shopkeeper_ids),
        ShopkeeperInventory.is_active == True
    ).group_by(
        ShopkeeperInventory.shopkeeper_id
    ).all()
    
    # Crear diccionario de totales
    total_dict = {shopkeeper_id: count for shopkeeper_id, count in total_products}
    
    # Obtener información de los tenderos
    result = []
    for shopkeeper_id, low_stock_count, last_updated in low_stock_inventories:
        shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == shopkeeper_id).first()
        
        if shopkeeper:
            result.append(ShopkeeperLowStockResponse(
                shopkeeper_id=shopkeeper.id,
                shopkeeper_name=shopkeeper.name,
                shopkeeper_business_name=shopkeeper.business_name,
                shopkeeper_address=shopkeeper.address,
                shopkeeper_phone=shopkeeper.phone,
                shopkeeper_email=shopkeeper.email,
                low_stock_count=low_stock_count,
                total_products=total_dict.get(shopkeeper_id, 0),
                last_updated=last_updated
            ))
    
    # Ordenar por cantidad de productos con bajo stock (mayor a menor)
    result.sort(key=lambda x: x.low_stock_count, reverse=True)
    
    return result


@router.get("/visits/shopkeepers/{shopkeeper_id}/inventory-summary")
async def get_shopkeeper_inventory_summary(
    shopkeeper_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener resumen de inventario del tendero
    HU21: El vendedor puede ver el resumen del inventario al agendar una visita
    ADMIN puede ver el resumen de cualquier tendero
    TENDERO no tiene acceso a esta funcionalidad
    """
    user_role = current_user.get("role")
    
    # TENDERO no tiene acceso
    if user_role == "TENDERO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver resumen de inventario"
        )
    
    # Si es VENDEDOR, verificar que el tendero esté asignado
    if user_role == "VENDEDOR":
        seller = get_seller_by_user(
            db, 
            current_user.get("email"), 
            user_role,
            current_user.get("user_id")
        )
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No se encontró un vendedor asociado a tu cuenta. Contacta al administrador."
            )
        
        # Verificar que el tendero esté asignado al vendedor
        if not verify_shopkeeper_assigned_to_seller(db, seller.id, shopkeeper_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El tendero no está asignado a ti"
            )
    
    # Obtener el tendero
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.id == shopkeeper_id).first()
    
    if not shopkeeper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tendero no encontrado"
        )
    
    # Obtener inventario con bajo stock
    low_stock_items = db.query(ShopkeeperInventory).filter(
        ShopkeeperInventory.shopkeeper_id == shopkeeper_id,
        ShopkeeperInventory.is_active == True,
        ShopkeeperInventory.current_stock < ShopkeeperInventory.min_stock
    ).all()
    
    # Obtener todos los productos del inventario
    all_items = db.query(ShopkeeperInventory).filter(
        ShopkeeperInventory.shopkeeper_id == shopkeeper_id,
        ShopkeeperInventory.is_active == True
    ).all()
    
    # Construir respuesta
    low_stock_products = []
    for item in low_stock_items:
        low_stock_products.append({
            "product_id": item.product_id,
            "product_name": item.product_name,
            "current_stock": float(item.current_stock),
            "min_stock": float(item.min_stock),
            "max_stock": float(item.max_stock),
            "unit_price": float(item.unit_price),
            "stock_status": "low"
        })
    
    return {
        "shopkeeper_id": shopkeeper.id,
        "shopkeeper_name": shopkeeper.name,
        "shopkeeper_business_name": shopkeeper.business_name,
        "total_products": len(all_items),
        "low_stock_count": len(low_stock_items),
        "low_stock_products": low_stock_products,
        "last_updated": max([item.last_updated for item in all_items]) if all_items else None
    }


@router.get("/visits/generate-sample/status")
async def check_sample_visits_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Verificar estado para generar visitas de muestra
    Solo accesible para ADMIN
    """
    user_role = current_user.get("role")
    
    if user_role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver este estado"
        )
    
    sellers_count = db.query(Seller).filter(Seller.is_active == True).count()
    shopkeepers_count = db.query(Shopkeeper).filter(Shopkeeper.is_active == True).count()
    assignments_count = db.query(Assignment).filter(Assignment.is_active == True).count()
    existing_visits_count = db.query(Visit).count()
    
    return {
        "sellers_available": sellers_count,
        "shopkeepers_available": shopkeepers_count,
        "assignments_available": assignments_count,
        "existing_visits": existing_visits_count,
        "can_generate": sellers_count > 0 and shopkeepers_count > 0,
        "message": "OK" if (sellers_count > 0 and shopkeepers_count > 0) else "Faltan vendedores o tenderos"
    }


@router.post("/visits/generate-sample", status_code=status.HTTP_201_CREATED)
async def generate_sample_visits(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Generar visitas de muestra para demostración
    Solo accesible para ADMIN
    Crea visitas con diferentes estados para diferentes vendedores
    """
    user_role = current_user.get("role")
    
    # Solo ADMIN puede generar visitas de muestra
    if user_role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden generar visitas de muestra"
        )
    
    # Obtener todos los vendedores activos
    sellers = db.query(Seller).filter(Seller.is_active == True).all()
    
    if not sellers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay vendedores activos en el sistema. Por favor, crea al menos un vendedor primero."
        )
    
    # Obtener todos los tenderos activos
    all_shopkeepers = db.query(Shopkeeper).filter(Shopkeeper.is_active == True).all()
    
    if not all_shopkeepers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay tenderos activos en el sistema. Por favor, crea al menos un tendero primero."
        )
    
    # Obtener todas las asignaciones activas
    assignments = db.query(Assignment).filter(Assignment.is_active == True).all()
    
    # Crear un diccionario de vendedor -> tenderos asignados
    seller_shopkeepers = {}
    for assignment in assignments:
        if assignment.seller_id not in seller_shopkeepers:
            seller_shopkeepers[assignment.seller_id] = []
        seller_shopkeepers[assignment.seller_id].append(assignment.shopkeeper_id)
    
    # Si no hay asignaciones, asignar tenderos a vendedores de forma circular
    if not seller_shopkeepers:
        # Asignar tenderos a vendedores de forma circular
        for i, seller in enumerate(sellers[:min(10, len(sellers))]):
            seller_shopkeepers[seller.id] = [all_shopkeepers[i % len(all_shopkeepers)].id]
    
    created_visits = []
    now = datetime.now(timezone.utc)
    
    # Para cada vendedor, crear visitas con diferentes estados
    for seller in sellers[:min(10, len(sellers))]:  # Máximo 10 vendedores
        shopkeeper_ids = seller_shopkeepers.get(seller.id, [])
        
        if not shopkeeper_ids:
            # Si aún no tiene tenderos, usar el primer tendero disponible
            if all_shopkeepers:
                shopkeeper_ids = [all_shopkeepers[0].id]
            else:
                continue
        
        # Crear visitas con diferentes porcentajes de cumplimiento
        # Vendedor 1: 90% cumplimiento (9 completadas, 1 pendiente)
        # Vendedor 2: 75% cumplimiento (6 completadas, 2 pendientes)
        # Vendedor 3: 50% cumplimiento (5 completadas, 5 pendientes)
        # Vendedor 4: 95% cumplimiento (19 completadas, 1 pendiente)
        # Vendedor 5: 60% cumplimiento (3 completadas, 2 pendientes)
        # etc.
        
        seller_index = sellers.index(seller) % 5
        compliance_patterns = [
            (9, 1, 0),   # 90% cumplimiento
            (6, 2, 0),   # 75% cumplimiento
            (5, 5, 0),   # 50% cumplimiento
            (19, 1, 0),  # 95% cumplimiento
            (3, 2, 0),   # 60% cumplimiento
        ]
        
        completed_count, pending_count, cancelled_count = compliance_patterns[seller_index]
        total_visits = completed_count + pending_count + cancelled_count
        
        # Crear visitas completadas
        for i in range(completed_count):
            shopkeeper_id = shopkeeper_ids[i % len(shopkeeper_ids)]
            # Fechas en el pasado (últimos 30 días)
            days_ago = (total_visits - i) % 30
            scheduled_date = now - timedelta(days=days_ago, hours=9 + (i % 8))
            completed_at = scheduled_date + timedelta(hours=1)
            
            visit = Visit(
                seller_id=seller.id,
                shopkeeper_id=shopkeeper_id,
                scheduled_date=scheduled_date,
                status="completed",
                reason="reabastecimiento",
                notes=f"Visita completada - Productos entregados",
                completed_at=completed_at
            )
            db.add(visit)
            created_visits.append(visit)
        
        # Crear visitas pendientes
        for i in range(pending_count):
            shopkeeper_id = shopkeeper_ids[(completed_count + i) % len(shopkeeper_ids)]
            # Fechas futuras (próximos 7 días)
            days_ahead = (i % 7) + 1
            scheduled_date = now + timedelta(days=days_ahead, hours=9 + (i % 8))
            
            visit = Visit(
                seller_id=seller.id,
                shopkeeper_id=shopkeeper_id,
                scheduled_date=scheduled_date,
                status="pending",
                reason="reabastecimiento",
                notes=f"Visita programada - Pendiente de realizar"
            )
            db.add(visit)
            created_visits.append(visit)
        
        # Crear visitas canceladas
        for i in range(cancelled_count):
            shopkeeper_id = shopkeeper_ids[(completed_count + pending_count + i) % len(shopkeeper_ids)]
            # Fechas en el pasado
            days_ago = (total_visits - i) % 30
            scheduled_date = now - timedelta(days=days_ago, hours=9 + (i % 8))
            cancelled_at = scheduled_date + timedelta(hours=0.5)
            
            visit = Visit(
                seller_id=seller.id,
                shopkeeper_id=shopkeeper_id,
                scheduled_date=scheduled_date,
                status="cancelled",
                reason="reabastecimiento",
                notes=f"Visita cancelada",
                cancelled_at=cancelled_at,
                cancelled_reason="Tendero no disponible"
            )
            db.add(visit)
            created_visits.append(visit)
    
    if not created_visits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudieron crear visitas. Verifica que haya vendedores con tenderos asignados."
        )
    
    try:
        db.commit()
        
        # Refrescar todas las visitas creadas
        for visit in created_visits:
            db.refresh(visit)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar las visitas: {str(e)}"
        )
    
    return {
        "message": f"Se crearon {len(created_visits)} visitas de muestra exitosamente",
        "total_created": len(created_visits),
        "sellers_processed": len(set(v.seller_id for v in created_visits)),
        "shopkeepers_used": len(set(v.shopkeeper_id for v in created_visits)),
        "visits": [
            {
                "id": visit.id,
                "seller_id": visit.seller_id,
                "shopkeeper_id": visit.shopkeeper_id,
                "status": visit.status,
                "scheduled_date": visit.scheduled_date.isoformat()
            }
            for visit in created_visits[:20]  # Mostrar solo las primeras 20
        ]
    }