"""
Modelo de Asignación (Assignment)
Tabla intermedia N:M entre Sellers y Shopkeepers con historial completo
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from .database import Base


class Assignment(Base):
    """
    Modelo de Asignación - Relaciona vendedores con tenderos
    Esta es la ÚNICA fuente de verdad para la relación seller-shopkeeper
    """
    
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True)
    shopkeeper_id = Column(Integer, ForeignKey("shopkeepers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Timestamps de asignación/desasignación
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    unassigned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Auditoría - quién hizo los cambios
    # Referencias a usuarios de MS-AUTH se almacenan sin FK por ser externas
    assigned_by = Column(Integer, nullable=True, index=True)
    unassigned_by = Column(Integer, nullable=True, index=True)
    
    # Notas sobre la asignación
    notes = Column(Text, nullable=True)
    
    # Estado activo
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps de auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Assignment(id={self.id}, seller={self.seller_id}, shopkeeper={self.shopkeeper_id}, active={self.is_active})>"

