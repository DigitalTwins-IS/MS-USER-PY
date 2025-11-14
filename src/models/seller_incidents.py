from sqlalchemy import Column, Integer, Text, Date, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from .database import Base

class SellerIncident(Base):
    __tablename__ = "seller_incidents"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    shopkeeper_id = Column(Integer, ForeignKey("shopkeepers.id", ondelete="SET NULL"))

    type = Column(String(30), nullable=False)
    description = Column(Text)
    incident_date = Column(Date, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())