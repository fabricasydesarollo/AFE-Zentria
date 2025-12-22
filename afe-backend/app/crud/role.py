# app/crud/role.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.role import Role
from typing import List, Optional


def get_role(db: Session, role_id: int) -> Optional[Role]:
    """Obtiene un rol por su ID"""
    return db.query(Role).filter(Role.id == role_id).first()


def get_role_by_name(db: Session, nombre: str) -> Optional[Role]:
    """Obtiene un rol por su nombre (insensible a mayúsculas/minúsculas)"""
    return (
        db.query(Role)
        .filter(func.lower(Role.nombre) == nombre.lower().strip())
        .first()
    )


def list_roles(db: Session, skip: int = 0, limit: int = 100) -> List[Role]:
    """Lista todos los roles con paginación"""
    return (
        db.query(Role)
        .order_by(Role.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
