from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configurações da aplicação vindas de variáveis de ambiente"""

    # Aplicação
    APP_NAME: str = "AgentEscala"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Banco de dados
    DATABASE_URL: str

    # Segurança
    SECRET_KEY: str = "change-this-in-production"
    ADMIN_EMAIL: str = "admin@example.com"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
