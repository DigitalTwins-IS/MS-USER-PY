"""
Cliente HTTP para comunicarse con el microservicio de Product
"""
import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class ProductClient:
    """Cliente para comunicarse con el microservicio de Product"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.MS_PRODUCT_URL).rstrip('/')
        self.timeout = 5.0  # Timeout más corto para no bloquear
    
    async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtener un producto por ID desde el microservicio de Product
        
        Args:
            product_id: ID del producto a consultar
            
        Returns:
            Dict con la información del producto o None si no existe o hay error
            (No lanza excepción para permitir fallback a datos locales)
        """
        url = f"{self.base_url}/api/v1/products/{product_id}"
        logger.info(f"Consultando producto {product_id} desde: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                
                logger.info(f"Respuesta del microservicio para producto {product_id}: status={response.status_code}")
                
                if response.status_code == 404:
                    logger.warning(f"Producto {product_id} no encontrado en el microservicio (404)")
                    return None
                elif response.status_code == 200:
                    product_data = response.json()
                    logger.info(f"Producto {product_id} obtenido: {product_data}")
                    return product_data
                else:
                    logger.warning(f"Error al obtener producto {product_id}: {response.status_code} - {response.text}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning(f"Timeout al consultar producto {product_id} desde {url} - usando datos locales")
            return None
        except httpx.RequestError as e:
            logger.warning(f"Error de conexión al consultar producto {product_id} desde {url}: {str(e)} - usando datos locales")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al consultar producto {product_id}: {str(e)}")
            return None
    
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
                    f"{self.base_url}/api/v1/products/",
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
