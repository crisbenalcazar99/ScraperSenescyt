# db.py — Punto de entrada principal para crear engines y sessions.
#
# Mantiene un cache por prefijo para no crear múltiples engines en el mismo proceso.
# El flujo completo es:
#
#   setting.py  →  connection.py  →  get_engine()  →  get_session_maker()
#
# Desde código de negocio NO se debe importar este módulo directamente;
# usar session_manager.py::get_session() que agrega el context manager.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from zaly_toolkits.common.connection import build_connection_url
from zaly_toolkits.config.setting import get_db_config

_engine_cache: dict = {}
_session_cache: dict = {}

# Argumentos de conexión específicos por BD que no encajan en la URL
_CONNECT_ARGS = {
    "QUANTA": {"connect_args": {"options": "-c TimeZone=America/Guayaquil"}},
}


def get_engine(prefix: str):
    """Devuelve el engine SQLAlchemy para el prefijo dado, creándolo si no existe en caché.

    El engine es compartido por todo el proceso (singleton por prefijo).
    Prefijos disponibles: LOCAL, PORTAL, PORTAL_GK, FENIX, CAMUNDA, LATINUM, QUANTA.
    """
    if prefix not in _engine_cache:
        config = get_db_config(prefix)
        url = build_connection_url(config)
        extra = _CONNECT_ARGS.get(prefix, {})
        _engine_cache[prefix] = create_engine(url, echo=False, hide_parameters=True, **extra)
    return _engine_cache[prefix]


def get_session_maker(prefix: str):
    """Devuelve la clase Session (sessionmaker) para el prefijo dado.

    Úsalo cuando necesites instanciar sesiones manualmente.
    Para la mayoría de los casos prefiere session_manager.py::get_session().
    """
    if prefix not in _session_cache:
        _session_cache[prefix] = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine(prefix)
        )
    return _session_cache[prefix]


