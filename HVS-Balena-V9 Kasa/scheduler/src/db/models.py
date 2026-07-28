"""
Modelos ORM (SQLAlchemy) usados por el scheduler para leer los intentos.

Espejo de los del contenedor `app` (ambos códigos son separados). Mapean las
tablas que crea db/init/01_schema.sql; no crean el esquema.
"""
from sqlalchemy import (
    Column, Integer, SmallInteger, String, DateTime, Date, ForeignKey
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MandatoryAssembly(Base):
    __tablename__ = "mandatory_assemblies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    type = Column(Integer, nullable=False)
    enable = Column(SmallInteger, nullable=False, default=1)


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    is_bad = Column(SmallInteger, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    date = Column(Date, nullable=False)


class BadAssembly(Base):
    __tablename__ = "bad_assemblies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False)
    type = Column(Integer, ForeignKey("mandatory_assemblies.id"), nullable=False)
    bad_assembly = Column(SmallInteger, nullable=False, default=1)
