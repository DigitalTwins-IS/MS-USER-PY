"""
Modelo de Tendero (Shopkeeper)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from .database import Base


class Shopkeeper(Base):
    """
    Modelo de Tendero - Representa tiendas con ubicación geográfica
    NOTA: La relación con sellers se maneja a través de la tabla 'assignments'
    """
    
    __tablename__ = "shopkeepers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=True)
    address = Column(String, nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Coordenadas geográficas
    latitude = Column(Numeric(10, 8), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=False)
    location = Column(Geometry('POINT', srid=4326), nullable=True)  # PostGIS
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Shopkeeper(id={self.id}, name={self.name}, business={self.business_name})>"

