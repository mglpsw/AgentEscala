from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .settings import settings

engine = create_engine(settings.DATABASE_URL)
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
