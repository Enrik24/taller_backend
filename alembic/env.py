from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
from pathlib import Path

# Agregar app al path para importar modelos
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.database import Base
from app.modules.usuarios.models import Usuario, Cliente, Taller, Rol, Permiso, Tecnico, Vehiculo, Bitacora
from app.modules.solicitudes.models import Solicitud, Evidencia
from app.modules.pagos.models import Pago, Comision
from app.modules.notificaciones.models import NotificacionToken, PreferenciaNotificacion

# Alembic Config object
config = context.config

# Configurar logger
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Configurar URL de base de datos desde settings
config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)

# Metadata target para autogeneración
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecutar migraciones en modo offline"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True  # Para compatibilidad SQLite en tests
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecutar migraciones en modo online"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()