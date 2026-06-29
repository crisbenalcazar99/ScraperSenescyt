from zaly_toolkits.common.db import get_engine
from sqlalchemy import text

with get_engine("SENESCYT").connect() as conn:
    result = conn.execute(text("""
                               SELECT COUNT(*)
                               FROM information_schema.tables
                               WHERE table_schema = 'senescyt'
                                 AND table_name = 'senescyt_consulta'
                               """))
    print("Tabla existe:", result.scalar() == 1)