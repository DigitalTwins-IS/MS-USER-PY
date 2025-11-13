"""
Clientes para comunicación con otros microservicios y APIs externas
"""
from .product_client import product_client
from .nominatim_client import nominatim_client
from .openroute_client import openroute_client, init_openroute_client

__all__ = [
    "product_client",
    "nominatim_client",
    "openroute_client",
    "init_openroute_client"
]