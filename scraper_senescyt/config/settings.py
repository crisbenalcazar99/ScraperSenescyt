# settings.py — Prefijos de conexión del scraper Senescyt.
#
# Estos valores se pasan directamente a get_session_maker() y get_engine()
# de zaly_toolkits. Para cambiar de base de datos solo se edita aquí.

# BD desde donde el Refiller lee las cédulas a procesar
BASE_ORIGEN  = "TRAN"

# BD donde el Worker escribe los resultados extraídos
BASE_DESTINO = "SENESCYT"

# Instancia Redis que gestiona la cola (ver redis_client.py)
BASE_REDIS   = "default"