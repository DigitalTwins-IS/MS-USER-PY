"""
Modelo de Visita (Visit)
HU21: Agendar visitas basadas en inventario
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.sql import func
from .database import Base


class Visit(Base):
    """
    Modelo de Visita - Representa una visita agendada de un vendedor a un tendero
    HU21: Permite agendar visitas basadas en el estado del inventario
    """
    
    __tablename__ = "visits"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True)
    shopkeeper_id = Column(Integer, ForeignKey("shopkeepers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Fecha y hora programada de la visita
    scheduled_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Estado de la visita (pending, completed, cancelled)
    status = Column(String(20), default="pending", nullable=False, index=True)
    
    # Constraint para validar el status
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed', 'cancelled')", name="check_visit_status"),
    )
    
    # Motivo y notas de la visita
    reason = Column(String(255), default="reabastecimiento", nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps de completado y cancelación
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_reason = Column(Text, nullable=True)
    
    # Timestamps de auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Visit(id={self.id}, seller={self.seller_id}, shopkeeper={self.shopkeeper_id}, status={self.status}, scheduled_date={self.scheduled_date})>"

