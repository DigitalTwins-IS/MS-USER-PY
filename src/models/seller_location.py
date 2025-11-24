"""
Modelo para ubicaciones de vendedores
HU18: Tracking en tiempo real
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base


class SellerLocation(Base):
    """Ubicaciones históricas de vendedores"""
    __tablename__ = "seller_locations"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True)
    latitude = Column(Numeric(10, 8), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=False)
    accuracy = Column(Numeric(10, 2))
    speed = Column(Numeric(10, 2))
    heading = Column(Numeric(5, 2))
    status = Column(String(20), default="active", index=True)
    battery_level = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación
    seller = relationship("Seller", back_populates="locations")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive', 'offline')", name="check_status"),
        CheckConstraint("battery_level BETWEEN 0 AND 100", name="check_battery"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="check_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="check_longitude"),
    )