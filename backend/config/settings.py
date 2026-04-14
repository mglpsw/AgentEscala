from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da aplicação vindas de variáveis de ambiente"""

    # Aplicação
    APP_NAME: str = "AgentEscala"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    CORS_ALLOW_ORIGINS: str = ""
    METRICS_ENABLED: bool = True

    # Banco de dados
    DATABASE_URL: str

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

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Ignora variáveis de infra do .env (ex.: portas Docker) não declaradas no Settings
        extra = "ignore"


settings = Settings()
