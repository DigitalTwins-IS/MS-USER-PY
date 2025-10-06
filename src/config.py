"""
Configuración del microservicio MS-USER-PY
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # API Configuration
    APP_NAME: str = "MS-USER-PY - User Management Service"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1/users"
    DEBUG: bool = False
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://dgt_user:dgt_pass@localhost:5437/digital_twins_db"
    
    # JWT Configuration
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    
    # CORS Configuration
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost"
    ]
    
    # Service Configuration
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 8000
    
    # External Services
    MS_GEO_URL: str = "http://ms-geo-py:8000"
    MS_AUTH_URL: str = "http://ms-auth-py:8000"
    
    # Business Rules
    MAX_SHOPKEEPERS_PER_SELLER: int = 80
    MAX_SELLERS_PER_ZONE: int = 10  # Recomendado, no hard limit
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

