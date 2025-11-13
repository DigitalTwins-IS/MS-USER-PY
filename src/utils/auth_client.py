"""
Cliente HTTP para comunicarse con MS-AUTH-PY
"""
import httpx
from typing import Optional, Dict
from ..config import settings
import logging

logger = logging.getLogger(__name__)


class AuthClient:
    """Cliente para interactuar con MS-AUTH-PY"""
    
    def __init__(self):
        self.base_url = settings.MS_AUTH_URL
        self.timeout = 10.0
    
    async def create_user(
        self,
        name: str,
        email: str,
        password: str,
        role: str = "VENDEDOR"
    ) -> Optional[Dict]:
        """
        Crear un nuevo usuario en MS-AUTH-PY
        
        Args:
            name: Nombre del usuario
            email: Email del usuario
            password: Contraseña del usuario
            role: Rol del usuario (default: VENDEDOR)
            
        Returns:
            Dict con los datos del usuario creado, o None si falla
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/register",
                    json={
                        "name": name,
                        "email": email,
                        "password": password,
                        "role": role
                    }
                )
                
                if response.status_code == 201:
                    user_data = response.json()
                    logger.info(f"Usuario creado exitosamente: {email}")
                    return user_data
                elif response.status_code == 400:
                    # Usuario ya existe, intentar obtenerlo
                    logger.warning(f"Usuario {email} ya existe, intentando obtenerlo")
                    return await self.get_user_by_email(email)
                else:
                    logger.error(
                        f"Error al crear usuario {email}: "
                        f"{response.status_code} - {response.text}"
                    )
                    return None
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout al crear usuario {email} en MS-AUTH-PY")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al crear usuario {email}: {str(e)}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Obtener usuario por email (requiere autenticación)
        Nota: Este método no está disponible en MS-AUTH-PY actualmente
        Se usa solo para logging
        
        Args:
            email: Email del usuario
            
        Returns:
            None (no implementado)
        """
        # MS-AUTH-PY no tiene endpoint público para obtener usuario por email
        # Este método es solo para logging
        return None


# Instancia global del cliente
auth_client = AuthClient()

