"""
Modelo de Vendedor (Seller)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base


class Seller(Base):
    """Modelo de Vendedor - Representa a los vendedores del sistema"""
    
    __tablename__ = "sellers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    address = Column(String, nullable=True)
    # Referencias a entidades externas (MS-GEO: zones, MS-AUTH: users) se manejan sin FK
    zone_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Seller(id={self.id}, name={self.name}, email={self.email}, zone_id={self.zone_id})>"

