# app/crud/audit.py
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from typing import Optional

def create_audit(db: Session, entidad: str, entidad_id: int, accion: str, usuario: str, detalle: Optional[dict] = None):
    log = AuditLog(entidad=entidad, entidad_id=entidad_id, accion=accion, usuario=usuario, detalle=detalle)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
