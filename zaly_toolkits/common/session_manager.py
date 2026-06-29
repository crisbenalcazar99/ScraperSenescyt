# session_manager.py — Context manager de sesiones para código de negocio.
#
# Es la única interfaz que los módulos externos deben importar para
# interactuar con la base de datos. Garantiza commit, rollback y cierre
# automático sin que el llamador tenga que gestionar el ciclo de vida.
#
# Para agregar una nueva BD basta con definir sus variables de entorno
# (DB_HOST_NUEVA, etc.) — no hay que modificar este archivo.
#
# Uso:
#   with get_session("QUANTA") as session:
#       session.execute(...)

from contextlib import contextmanager
from zaly_toolkits.common.db import get_session_maker


@contextmanager
def get_session(db_alias: str = "LOCAL"):
    """Context manager que entrega una sesión SQLAlchemy lista para usar.

    Hace commit al salir sin error, rollback si hay excepción, y siempre cierra.
    db_alias es el prefijo de la BD: LOCAL, PORTAL, PORTAL_GK, FENIX,
    CAMUNDA, LATINUM, QUANTA, o cualquier prefijo nuevo definido en .env.
    """
    session = get_session_maker(db_alias)()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
