"""
Utilidades de autenticación JWT
Valida tokens generados por MS-AUTH-PY
"""
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..config import settings

# HTTP Bearer scheme para el header Authorization (más simple para Swagger)
http_bearer = HTTPBearer(auto_error=False)


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT
    
    Args:
        token: Token JWT a decodificar
        
    Returns:
        dict: Datos extraídos del token
        
    Raises:
        HTTPException: Si el token es inválido
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role", "").upper()  # Normalizar a mayúsculas
        user_id: int = payload.get("user_id")
        
        if email is None:
            raise credentials_exception
            
        return {
            "email": email, 
            "role": role,
            "user_id": user_id
        }
        
    except JWTError:
        raise credentials_exception


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> dict:
    """
    Obtiene el usuario actual desde el token JWT
    
    Args:
        credentials: Credenciales HTTP Bearer del header Authorization
        
    Returns:
        dict: Información del usuario (email, role)
        
    Raises:
        HTTPException: Si el token es inválido o no está presente
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    user_data = decode_token(token)
    return user_data


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Verifica que el usuario actual sea un administrador
    
    Args:
        current_user: Usuario actual
        
    Returns:
        dict: Usuario administrador
        
    Raises:
        HTTPException: Si el usuario no es administrador
    """
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    return current_user

