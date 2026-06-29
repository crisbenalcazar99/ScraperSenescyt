# Guía de conexiones — zaly_toolkits

## Arquitectura de capas

```
config/setting.py          → lee credenciales (variables de entorno)
common/connection.py       → construye el URL de SQLAlchemy
common/db.py               → crea y cachea el engine / sessionmaker
common/session_manager.py  → context manager para código de negocio  ← único punto de entrada
common/schema_initializer.py → crea tablas en la BD
```

Cada capa tiene una sola responsabilidad. **El código de negocio solo debe importar `session_manager.py`.**

---

## Flujo de llamadas por caso de uso

### Caso 1 — Uso normal (ORM, queries, inserciones)

```
tu_codigo.py
    │
    └─► get_session("LOCAL")                ← session_manager.py
            │
            └─► get_session_maker("LOCAL")  ← db.py
                    │
                    └─► get_engine("LOCAL") ← db.py
                              │
                              ├─► get_db_config("LOCAL")       ← setting.py
                              └─► build_connection_url(config)  ← connection.py
```

### Caso 2 — Engine directo (pandas, create_all, migraciones)

```
tu_codigo.py
    │
    └─► get_engine("LOCAL")                 ← db.py  (mismo engine cacheado)
              │
              ├─► get_db_config("LOCAL")       ← setting.py
              └─► build_connection_url(config)  ← connection.py
```

> El cache de `db.py` garantiza que ambos casos usan el **mismo engine en memoria** —
> no se abren dos conexiones aunque se llamen `get_session` y `get_engine` al mismo tiempo.

---

## Cuándo usar cada función

| Necesito... | Usar |
|---|---|
| Hacer queries ORM / insertar registros | `get_session("ALIAS")` |
| `pd.read_sql` / `pd.to_sql` con pandas | `get_engine("ALIAS")` |
| Crear tablas (`create_all`) | `create_schema("ALIAS")` |
| Worker que controla su sesión manualmente | `get_session_maker("ALIAS")()` |

---

## Bases de datos disponibles

| Alias | Motor | Descripción |
|---|---|---|
| `LOCAL` | PostgreSQL | BD principal del proyecto (default) |
| `PORTAL` | PostgreSQL | Portal de gestión |
| `PORTAL_GK` | PostgreSQL | Portal GK |
| `FENIX` | PostgreSQL | Sistema Fénix |
| `CAMUNDA` | PostgreSQL | Motor de procesos Camunda |
| `QUANTA` | PostgreSQL | DWH Quanta (zona horaria Guayaquil) |
| `LATINUM` | SQL Server | ERP Latinum (requiere driver ODBC) |

---

## Uso normal — context manager
get_session es un context manager — un bloque with que gestiona automáticamente el ciclo de vida de la sesión. 
 El with ejecuta automáticamente el commit, el rollback si falla, y el close al salir — sin que lo escribas.  
```python
from zaly_toolkits.common.session_manager import get_session

# Commit automático al salir; rollback automático si hay excepción
with get_session("QUANTA") as session:
    resultado = session.execute(text("SELECT 1")).fetchall()

# Sin alias usa LOCAL por defecto
with get_session() as session:
    session.add(mi_objeto)
```

---

## Uso avanzado — sesión manual

Útil para workers de larga duración que necesitan controlar el ciclo de vida.

```python
from zaly_toolkits.common.db import get_session_maker

SessionLocal = get_session_maker("LOCAL")
session = SessionLocal()

try:
    session.execute(...)
    session.commit()
except Exception:
    session.rollback()
    raise
finally:
    session.close()
```

---

## Uso del engine directo

Solo para operaciones que necesitan el engine de SQLAlchemy (pandas, migraciones, etc.).

```python
from zaly_toolkits.common.db import get_engine
import pandas as pd

engine = get_engine("PORTAL")
df = pd.read_sql("SELECT * FROM tabla", engine)
```

---

## Crear tablas (inicialización)

```python
from zaly_toolkits.common.schema_initializer import create_schema

create_schema("LOCAL")   # crea todas las tablas declaradas en los modelos ORM
```

---

## Configuración de credenciales

Las credenciales se definen como variables de entorno con el patrón `DB_{CAMPO}_{PREFIJO}`.

### Ejemplo para LOCAL (PostgreSQL)

```env
DB_ENGINE_LOCAL=postgresql
DB_DRIVER_LOCAL=psycopg2
DB_HOST_LOCAL=localhost
DB_PORT_LOCAL=5432
DB_USER_LOCAL=postgres
DB_PASSWORD_LOCAL=mi_password
DB_NAME_LOCAL=senescyt
```

### Ejemplo para LATINUM (SQL Server)

```env
DB_ENGINE_LATINUM=mssql
DB_DRIVER_LATINUM=pyodbc
DB_HOST_LATINUM=192.168.1.10
DB_PORT_LATINUM=1433
DB_USER_LATINUM=sa
DB_PASSWORD_LATINUM=mi_password
DB_NAME_LATINUM=latinum
DB_ODBC_DRIVER_LATINUM=ODBC Driver 17 for SQL Server
```

### Agregar una nueva base de datos

No se modifica ningún archivo Python. Solo se definen las variables de entorno con el nuevo prefijo y se usa ese prefijo como alias:

```env
DB_ENGINE_NUEVA=postgresql
DB_HOST_NUEVA=10.0.0.5
DB_PORT_NUEVA=5432
DB_USER_NUEVA=app_user
DB_PASSWORD_NUEVA=secret
DB_NAME_NUEVA=mi_base
```

```python
with get_session("NUEVA") as session:
    ...
```

---

## Redis

La configuración de Redis se lee de:

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=          # dejar vacío si no tiene contraseña
```

```python
from scraper_senescyt.queue.redis_client import get_redis

r = get_redis()
r.set("clave", "valor")
```