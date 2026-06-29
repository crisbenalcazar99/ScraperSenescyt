# redis_db.py — Punto de entrada para conexiones Redis.
#
# Paralelo a db.py para bases relacionales: obtiene la configuración
# de setting.py y mantiene una instancia cacheada por proceso.

import redis
from zaly_toolkits.config.setting import get_redis_config

_redis_cache: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Devuelve la instancia Redis compartida del proceso, creándola si no existe.

    La conexión se configura con las variables de entorno
    REDIS_HOST, REDIS_PORT, REDIS_DB y REDIS_PASSWORD definidas en setting.py.
    """
    global _redis_cache
    if _redis_cache is None:
        config = get_redis_config()
        _redis_cache = redis.Redis(decode_responses=True, **config)
    return _redis_cache