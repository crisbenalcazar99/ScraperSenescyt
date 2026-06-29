# setting.py — Fuente única de configuración de conexiones.
#
# Cada base de datos se identifica por un PREFIJO (ej. "LOCAL", "QUANTA").
# Las credenciales se leen de variables de entorno con el patrón:
#
#   DB_HOST_LOCAL, DB_PORT_LOCAL, DB_USER_LOCAL, DB_PASSWORD_LOCAL ...
#   DB_HOST_QUANTA, DB_PORT_QUANTA, DB_USER_QUANTA ...
#
# Para agregar una nueva base de datos solo hay que definir las variables
# de entorno con el nuevo prefijo y llamar get_db_config("NUEVO_PREFIJO").
# No es necesario modificar ningún otro archivo.

import os
from dotenv import load_dotenv

load_dotenv()  # carga el .env de la raíz del proyecto si existe


# ── PostgreSQL / SQL Server ───────────────────────────────────────────────────

def get_db_config(prefix: str = "DB") -> dict:
    """Devuelve un dict con las credenciales de la BD identificada por `prefix`.

    Prefijos disponibles: LOCAL, PORTAL, PORTAL_GK, FENIX, CAMUNDA, LATINUM, QUANTA.
    Cada clave del dict es consumida por connection.py::build_connection_url().
    """
    return {
        'engine':      os.environ.get(f"DB_ENGINE_{prefix}"),
        'driver':      os.environ.get(f"DB_DRIVER_{prefix}"),
        'host':        os.environ.get(f"DB_HOST_{prefix}"),
        'port':        os.environ.get(f"DB_PORT_{prefix}"),
        'user':        os.environ.get(f"DB_USER_{prefix}"),
        'password':    os.environ.get(f"DB_PASSWORD_{prefix}"),
        'database':    os.environ.get(f"DB_NAME_{prefix}", ""),
        'odbc_driver': os.environ.get(f"DB_ODBC_DRIVER_{prefix}"),
    }


# ── Redis ─────────────────────────────────────────────────────────────────────

def get_redis_config() -> dict:
    """Devuelve la configuración de Redis leída de variables de entorno.

    Variables: REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD.
    Consumida por zaly_toolkits/common/redis_db.py::get_redis().
    """
    return {
        'host':     os.environ.get('REDIS_HOST', 'localhost'),
        'port':     int(os.environ.get('REDIS_PORT', '6379')),
        'db':       int(os.environ.get('REDIS_DB', '0')),
        'password': os.environ.get('REDIS_PASSWORD'),
    }
