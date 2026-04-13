from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Adiciona o diretório do app ao path
app_path = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, app_path)

# Importa models e settings
from backend.config.database import Base
from backend.config.settings import settings
from backend.models import models  # Import all models

# Objeto de configuração do Alembic, que dá acesso aos valores do .ini em uso
config = context.config

# Sobrescreve sqlalchemy.url com o DATABASE_URL das configurações
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpreta o arquivo de configuração para logging do Python.
# Esta linha basicamente configura os loggers.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Adicione aqui o objeto MetaData do seu modelo
# para suportar 'autogenerate'
target_metadata = Base.metadata

# Outros valores da configuração, definidos pelas necessidades do env.py,
# podem ser obtidos:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Executa migrações no modo 'offline'.

    Configura o contexto apenas com a URL e não com um Engine,
    embora um Engine também seja aceitável aqui. Ao pular a criação
    do Engine nem mesmo precisamos que um DBAPI esteja disponível.

    Chamadas a context.execute() aqui emitem a string informada para
    a saída do script.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrações no modo 'online'.

    Neste cenário precisamos criar um Engine
    e associar uma conexão ao contexto.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
