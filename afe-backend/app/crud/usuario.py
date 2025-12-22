from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import and_

from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioUpdate


# -----------------------------------------------------
# Obtener usuario por ID
# -----------------------------------------------------
def get_usuario_by_id(db: Session, usuario_id: int) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


# -----------------------------------------------------
# Obtener usuario por nombre de usuario
# -----------------------------------------------------
def get_usuario_by_usuario(db: Session, usuario: str) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.usuario == usuario).first()


# -----------------------------------------------------
# Autenticar usuario
# -----------------------------------------------------
def authenticate(db: Session, usuario: str, password: str) -> Optional[Usuario]:
    from app.core.security import verify_password
    user = get_usuario_by_usuario(db, usuario)
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# -----------------------------------------------------
# Crear usuario
# -----------------------------------------------------
def create_usuario(db: Session, data) -> Usuario:
    from app.core.security import hash_password
    create_data = data.dict()

    # Hash the password if provided
    if "password" in create_data and create_data["password"]:
        create_data["hashed_password"] = hash_password(create_data.pop("password"))

    obj = Usuario(**create_data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# -----------------------------------------------------
# Actualizar usuario
# -----------------------------------------------------
def update_usuario(db: Session, u_id: int, data: UsuarioUpdate) -> Optional[Usuario]:
    from app.core.security import hash_password
    usuario = get_usuario_by_id(db, u_id)
    if not usuario:
        return None

    update_data = data.dict(exclude_unset=True)

    # Validar que el nuevo nombre de usuario no esté duplicado
    if "usuario" in update_data and update_data["usuario"] != usuario.usuario:
        existing = get_usuario_by_usuario(db, update_data["usuario"])
        if existing:
            raise ValueError(f"El usuario '{update_data['usuario']}' ya existe en el sistema")

    if "password" in update_data and update_data["password"]:
        usuario.hashed_password = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(usuario, field, value)

    db.commit()
    db.refresh(usuario)
    return usuario


def delete_usuario(db: Session, u_id: int) -> bool:
    """
    Desactiva un usuario en lugar de eliminarlo físicamente.

    Esto evita problemas con foreign keys en asignacion_nit_responsable
    y mantiene la integridad referencial del sistema.
    """
    usuario = get_usuario_by_id(db, u_id)
    if not usuario:
        return False

    # Soft delete: desactivar en lugar de eliminar
    usuario.activo = False
    db.commit()
    return True


# -----------------------------------------------------
# Funciones adicionales para automatización
# -----------------------------------------------------
def get_usuario(db: Session, usuario_id: int) -> Optional[Usuario]:
    """Alias de get_usuario_by_id para compatibilidad"""
    return get_usuario_by_id(db, usuario_id)


def get_usuarios_activos(db: Session) -> List[Usuario]:
    """Obtiene todos los usuarios activos"""
    return (
        db.query(Usuario)
        .filter(Usuario.activo == True)
        .all()
    )


def get_usuarios_por_rol(db: Session, rol_nombre: str) -> List[Usuario]:
    """
    Obtiene usuarios por rol específico
    NOTA: Esta función requiere que el modelo tenga relación con roles
    """
    # Implementación básica - ajustar según estructura de roles
    return (
        db.query(Usuario)
        .filter(
            and_(
                Usuario.activo == True,
                # Aquí iría la lógica de filtrado por rol
                # Por ahora devolvemos usuarios activos
            )
        )
        .all()
    )

