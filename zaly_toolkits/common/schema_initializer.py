# schema_initializer.py — Creación de tablas en base de datos.
#
# Usa Base.metadata (el registro de todos los modelos ORM declarados)
# para emitir los CREATE TABLE que falten. Es idempotente: no destruye
# tablas existentes ni modifica columnas; solo crea lo que no existe.

from zaly_toolkits.common.db import get_engine
from scraper_senescyt.entities.models.base import Base

# Los modelos deben importarse para que SQLAlchemy los registre en Base.metadata.
# Sin este import, create_all no sabe que existen y no crea ninguna tabla.
import scraper_senescyt.entities.senescyt_consulta  # noqa: F401


def create_schema(db_alias: str = "LOCAL"):
    """Crea todas las tablas declaradas en los modelos ORM si no existen.

    db_alias: prefijo de la BD destino (por defecto LOCAL).
    Llamar una vez al inicio de la aplicación o en scripts de migración.
    """
    tablas = list(Base.metadata.tables.keys())
    print(f"Tablas registradas en metadata: {tablas}")
    try:
        Base.metadata.create_all(get_engine(db_alias))
        print(f"Esquema creado exitosamente en '{db_alias}' ({len(tablas)} tabla/s).")
    except Exception as e:
        print(f"Error al crear el esquema de base de datos: {e}")
        raise
