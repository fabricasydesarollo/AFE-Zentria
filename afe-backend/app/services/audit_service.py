# app/services/audit_service.py
from sqlalchemy.orm import Session
from app.crud.audit import create_audit

class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(self, entidad: str, entidad_id: int, accion: str, usuario: str, detalle: dict | None = None):
        return create_audit(self.db, entidad, entidad_id, accion, usuario, detalle)
