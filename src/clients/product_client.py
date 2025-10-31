"""
Cliente HTTP para comunicarse con el microservicio de Product
"""
import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class ProductClient:
    """Cliente para comunicarse con el microservicio de Product"""
    
    def __init__(self, base_url: str = "http://localhost:8005"):
        self.base_url = base_url.rstrip('/')
        self.timeout = 30.0
    
    async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtener un producto por ID desde el microservicio de Product
        
        Args:
            product_id: ID del producto a consultar
            
        Returns:
            Dict con la información del producto o None si no existe
            
        Raises:
            HTTPException: Si hay error en la comunicación
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/products/products/{product_id}")
                
                if response.status_code == 404:
                    return None
                elif response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Error al obtener producto {product_id}: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"Error al consultar el producto en el microservicio de Product: {response.status_code}"
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout al consultar producto {product_id}")
            raise HTTPException(
                status_code=504,
                detail="Timeout al consultar el microservicio de Product"
            )
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al consultar producto {product_id}: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Error de conexión con el microservicio de Product"
            )
    
    async def validate_product_exists(self, product_id: int) -> bool:
        """
        Validar si un producto existe en el microservicio de Product
        
        Args:
            product_id: ID del producto a validar
            
        Returns:
            True si el producto existe, False en caso contrario
        """
        product = await self.get_product(product_id)
        return product is not None
    
    async def get_products_by_category(self, category: str) -> list[Dict[str, Any]]:
        """
        Obtener productos por categoría desde el microservicio de Product
        
        Args:
            category: Categoría a consultar
            
        Returns:
            Lista de productos de la categoría
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/products/products",
                    params={"category": category}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Error al obtener productos por categoría {category}: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error al consultar productos por categoría {category}: {str(e)}")
            return []

# Instancia global del cliente
product_client = ProductClient()
