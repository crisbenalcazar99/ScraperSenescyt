from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, func, BigInteger
from sqlalchemy.dialects.postgresql import JSONB

from scraper_senescyt.entities.models.base import Base


class SenescytConsulta(Base):
    __tablename__ = 'senescyt_consulta'
    __table_args__ = {"schema": "senescyt_schema"}

    id_consulta = Column(BigInteger, primary_key=True)
    cedula          = Column(String(20),  unique=True)
    nombres         = Column(String(200))
    genero          = Column(String(50))
    nacionalidad    = Column(String(50))
    sin_resultados  = Column(Boolean, default=False)
    certificaciones = Column(JSONB)
    fecha_creacion = Column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False
    )

    fecha_actualizacion = Column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
        onupdate=func.now()
    )