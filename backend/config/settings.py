import os
from typing import List

from pydantic_settings import BaseSettings

DEFAULT_DATABASE_URL = "sqlite:///./agentescala.db"


class Settings(BaseSettings):
    """Configurações da aplicação vindas de variáveis de ambiente"""

    # Aplicação
    APP_NAME: str = "AgentEscala"
    APP_VERSION: str = "1.5.1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    CORS_ALLOW_ORIGINS: str = ""
    METRICS_ENABLED: bool = True
    OCR_API_BASE_URL: str = "https://api.ks-sm.net:9443"
    OCR_API_TIMEOUT_SECONDS: float = 20.0
    OCR_API_ENABLED: bool = True
    OCR_API_VERIFY_SSL: bool = True

    SCHEDULE_MAX_DAILY_HOURS: float = 12.0
    SCHEDULE_MAX_WEEKLY_HOURS: float = 60.0

    # Banco de dados
    DATABASE_URL: str = DEFAULT_DATABASE_URL

    # Segurança
    SECRET_KEY: str = "change-this-in-production"
    ADMIN_EMAIL: str = "admin@example.com"

    @property
    def cors_allow_origins_list(self) -> List[str]:
        if not self.CORS_ALLOW_ORIGINS:
            return ["*"] if self.DEBUG else []

        return [
            origin.strip()
            for origin in self.CORS_ALLOW_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def database_url_resolved(self) -> str:
        """Retorna DATABASE_URL com fallback previsível para execução local."""
        env_url = os.getenv("DATABASE_URL", "").strip()
        configured = (self.DATABASE_URL or "").strip()
        return env_url or configured or DEFAULT_DATABASE_URL

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Ignora variáveis de infra do .env (ex.: portas Docker) não declaradas no Settings
        extra = "ignore"


settings = Settings()
