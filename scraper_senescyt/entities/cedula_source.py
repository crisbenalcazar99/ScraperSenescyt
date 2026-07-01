from sqlalchemy import Column, String, BigInteger

from scraper_senescyt.entities.models.base import Base


class CedulaSource(Base):
    __tablename__  = 'cedulas'
    __table_args__ = {"schema": "senescyt_schema"}

    id     = Column(BigInteger, primary_key=True, autoincrement=True)
    cedula = Column(String(20), unique=True, nullable=False)