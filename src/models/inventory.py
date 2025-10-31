from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, String, Boolean
from sqlalchemy.sql import func
from .database import Base

class ShopkeeperInventory(Base):
    __tablename__ = "inventories"
    
    id = Column(Integer, primary_key=True, index=True)
    shopkeeper_id = Column(Integer, ForeignKey("shopkeepers.id"), nullable=False, index=True)
    product_id = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    min_stock = Column(Numeric(10, 2), default=10)
    max_stock = Column(Numeric(10, 2), default=100)
    current_stock = Column(Numeric(10, 2), nullable=False, default=0)
    product_name = Column(String(255), nullable=True)
    product_description = Column(String(500), nullable=True)
    product_category = Column(String(100), nullable=True)
    product_brand = Column(String(100), nullable=True)
    is_validated = Column(Boolean, default=False)
    validated_by = Column(Integer, nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    assigned_by = Column(Integer, nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # Alias para compatibilidad
    @property
    def stock(self):
        return self.current_stock
    
    @property
    def product_sku(self):
        # Para compatibilidad, devolvemos el ID como string
        return str(self.product_id)
