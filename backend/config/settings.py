"""
Configuración centralizada del backend usando pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import List, Optional

# Obtener la ruta del archivo .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Configuración del sistema"""
    
    # Odoo - URL y DB son requeridos, credenciales son opcionales
    # (las credenciales las proporciona cada usuario en el login)
    ODOO_URL: str = "https://riofuturo.server98c6e.oerpondemand.net"
    ODOO_DB: str = "riofuturo-master"
    ODOO_USER: Optional[str] = None
    ODOO_PASSWORD: Optional[str] = None
    
    # API
    API_URL: str = "http://127.0.0.1:8000"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Permisos
    PERMISSION_ADMINS: List[str] = ["mvalladares@riofuturo.cl", "frios@riofuturo.cl"]
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding='utf-8',
        extra='ignore'
    )


# Singleton de configuración
settings = Settings()
