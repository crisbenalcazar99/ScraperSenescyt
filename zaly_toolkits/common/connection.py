# connection.py — Construcción de URLs de conexión para SQLAlchemy.
#
# Soporta PostgreSQL (psycopg2) y SQL Server (pyodbc via ODBC).
# Es llamado exclusivamente por db.py::get_engine(); no debe usarse directo.


def build_connection_url(config: dict) -> str:
    """Construye el string de conexión SQLAlchemy a partir del dict de credenciales.

    Para PostgreSQL produce:  postgresql+psycopg2://user:pass@host:port/db
    Para SQL Server produce:  mssql+pyodbc://user:pass@host:port/db?driver=...&TrustServerCertificate=yes

    El dict `config` es el que devuelve setting.py::get_db_config().
    """
    engine = config.get('engine', 'postgresql')
    driver = config.get('driver', 'psycopg2')
    user = config['user']
    password = config['password']
    host = config['host']
    port = config['port']
    db = config.get('database', '')
    odbc_driver = config.get('odbc_driver')  # solo SQL Server lo usa

    if not engine or not driver:
        raise ValueError("Faltan parámetros obligatorios: 'engine' o 'driver'")

    url = f"{engine}+{driver}://{user}:{password}@{host}:{port}"

    # SQL Server requiere el nombre del driver ODBC y deshabilitar verificación TLS
    if engine.lower() == "mssql":
        if not odbc_driver:
            raise ValueError("Para SQL Server debes definir DB_ODBC_DRIVER_LATINUM en tu .env")
        odbc_driver_encoded = odbc_driver.replace(" ", "+")
        return f"{url}/{db}?driver={odbc_driver_encoded}&TrustServerCertificate=yes"

    return f"{url}/{db}" if db else url
