"""
Modelo de Incidencia de Vendedor (SellerIncident)
HU16: Registrar incidencias durante visitas
"""
from sqlalchemy import Column, Integer, Text, Date, String, ForeignKey, TIMESTAMP, CheckConstraint
from sqlalchemy.sql import func
from .database import Base


class SellerIncident(Base):
    """
    Modelo de Incidencia de Vendedor - Representa incidencias registradas durante visitas
    HU16: Permite registrar incidencias (ausencia, retraso, incumplimiento) relacionadas con visitas
    """
    __tablename__ = "seller_incidents"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True)
    shopkeeper_id = Column(Integer, ForeignKey("shopkeepers.id", ondelete="SET NULL"), nullable=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="SET NULL"), nullable=True, index=True)

    type = Column(String(30), nullable=False)
    description = Column(Text)
    incident_date = Column(Date, nullable=False)

    # Constraint para validar el tipo
    __table_args__ = (
        CheckConstraint("type IN ('absence', 'delay', 'non_compliance')", name="check_incident_type"),
    )

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SellerIncident(id={self.id}, seller={self.seller_id}, visit={self.visit_id}, type={self.type})>"