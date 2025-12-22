# app/models/audit_log.py
from sqlalchemy import Column, BigInteger, String, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base
from sqlalchemy.orm import relationship

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    entidad = Column(String(64), nullable=False)
    entidad_id = Column(BigInteger, nullable=False)
    accion = Column(String(50), nullable=False)
    usuario = Column(String(100), nullable=False)
    detalle = Column(JSON, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
