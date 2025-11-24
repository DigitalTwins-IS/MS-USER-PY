"""
Modelo para caché de geocodificación
HU18: Reduce llamadas a APIs externas
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, UniqueConstraint
from sqlalchemy.sql import func

from .database import Base


class GeocodingCache(Base):
    """Caché de resultados de geocodificación"""
    __tablename__ = "geocoding_cache"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), default="Colombia")
    latitude = Column(Numeric(10, 8), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=False)
    display_name = Column(Text)
    confidence = Column(Numeric(3, 2))
    provider = Column(String(50), default="nominatim")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), server_default=func.now())
    usage_count = Column(Integer, default=1)
    
    __table_args__ = (
        UniqueConstraint('address', 'city', 'country', name='uq_address_city_country'),
    )