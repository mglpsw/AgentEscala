import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from .settings import DEFAULT_DATABASE_URL, settings

logger = logging.getLogger("agentescala.database")
DATABASE_URL = settings.database_url_resolved

if DATABASE_URL == DEFAULT_DATABASE_URL:
    logger.warning(
        "DATABASE_URL não definido; usando fallback local %s para ambiente de desenvolvimento.",
        DEFAULT_DATABASE_URL,
    )

engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependência para sessões de banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializar tabelas do banco de dados"""
    # Garante que os modelos estejam registrados antes de criar as tabelas
    from .. import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
