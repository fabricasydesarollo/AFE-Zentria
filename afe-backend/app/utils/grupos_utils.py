"""
Utilidades para Gestión de Grupos Multi-Tenant
===============================================

Helper functions para validación de acceso a grupos y permisos.

Nivel: Fortune 500 Enterprise Security
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException

from app.models.grupo import ResponsableGrupo
from app.models.usuario import Usuario


def get_grupos_usuario(usuario_id: int, db: Session) -> List[int]:
    """
    Obtiene lista de IDs de grupos a los que pertenece un usuario.

    Args:
        usuario_id: ID del usuario
        db: Sesión de base de datos

    Returns:
        Lista de IDs de grupos (puede estar vacía)

    Example:
        >>> grupos = get_grupos_usuario(123, db)
        >>> # [1, 5, 6, 7]
    """
    grupos = db.query(ResponsableGrupo.grupo_id).filter(
        ResponsableGrupo.responsable_id == usuario_id,
        ResponsableGrupo.activo == True
    ).all()

    return [g[0] for g in grupos]


def user_has_access_to_grupo(
    usuario_id: int,
    grupo_id: int,
    db: Session,
    rol: Optional[str] = None
) -> bool:
    """
    Verifica si un usuario tiene acceso a un grupo específico.

    Args:
        usuario_id: ID del usuario
        grupo_id: ID del grupo a validar
        db: Sesión de base de datos
        rol: Rol específico requerido (opcional: 'admin', 'responsable', etc.)

    Returns:
        True si tiene acceso, False si no

    Example:
        >>> if user_has_access_to_grupo(123, 1, db, rol="admin"):
        >>>     # Usuario es admin del grupo 1
    """
    query = db.query(ResponsableGrupo).filter(
        ResponsableGrupo.responsable_id == usuario_id,
        ResponsableGrupo.grupo_id == grupo_id,
        ResponsableGrupo.activo == True
    )

    if rol:
        query = query.filter(ResponsableGrupo.rol == rol)

    return query.first() is not None


def is_admin_or_superadmin(usuario: Usuario) -> bool:
    """
    Verifica si un usuario es admin o superadmin global.

    Args:
        usuario: Objeto Usuario

    Returns:
        True si es admin/superadmin, False si no

    Example:
        >>> if is_admin_or_superadmin(current_user):
        >>>     # Usuario tiene acceso total
    """
    return usuario.rol in ["admin", "superadmin"]


def validate_grupo_access(
    usuario: Usuario,
    grupo_id: int,
    db: Session,
    required_rol: Optional[str] = None
) -> None:
    """
    Valida acceso a grupo y lanza excepción si no tiene permiso.

    Args:
        usuario: Objeto Usuario
        grupo_id: ID del grupo a validar
        db: Sesión de base de datos
        required_rol: Rol específico requerido (opcional)

    Raises:
        HTTPException 403: Si no tiene acceso al grupo

    Example:
        >>> validate_grupo_access(current_user, 1, db, required_rol="admin")
        >>> # Si no es admin del grupo 1, lanza 403
    """
    # Admin global tiene acceso a todo
    if is_admin_or_superadmin(usuario):
        return

    # Validar acceso específico
    if not user_has_access_to_grupo(usuario.id, grupo_id, db, rol=required_rol):
        detail = f"Usuario no tiene acceso al grupo {grupo_id}"
        if required_rol:
            detail += f" con rol '{required_rol}'"
        raise HTTPException(status_code=403, detail=detail)


def get_grupos_usuario_con_detalles(usuario_id: int, db: Session) -> List[dict]:
    """
    Obtiene grupos del usuario con información detallada.

    Args:
        usuario_id: ID del usuario
        db: Sesión de base de datos

    Returns:
        Lista de diccionarios con información de grupos

    Example:
        >>> grupos = get_grupos_usuario_con_detalles(123, db)
        >>> # [
        >>> #   {"id": 1, "nombre": "AVIDANTI", "rol": "admin"},
        >>> #   {"id": 5, "nombre": "CAM", "rol": "responsable"}
        >>> # ]
    """
    result = db.execute(text("""
        SELECT
            g.id,
            g.nombre,
            g.codigo_corto,
            rg.rol
        FROM responsable_grupo rg
        JOIN grupos g ON rg.grupo_id = g.id
        WHERE rg.responsable_id = :usuario_id
        AND rg.activo = 1
        AND g.activo = 1
        ORDER BY g.nombre
    """), {"usuario_id": usuario_id})

    return [
        {
            "id": row[0],
            "nombre": row[1],
            "codigo_corto": row[2],
            "rol": row[3]
        }
        for row in result
    ]


def filter_query_by_grupos(
    query,
    usuario: Usuario,
    db: Session,
    grupo_id_column,
    grupo_id_filter: Optional[int] = None
):
    """
    Aplica filtro de grupos a una query SQLAlchemy.

    Args:
        query: Query de SQLAlchemy
        usuario: Objeto Usuario
        db: Sesión de base de datos
        grupo_id_column: Columna de grupo_id en el modelo (ej: Factura.grupo_id)
        grupo_id_filter: ID de grupo específico para filtrar (opcional)

    Returns:
        Query modificada con filtros aplicados

    Example:
        >>> query = db.query(Factura)
        >>> query = filter_query_by_grupos(
        >>>     query, current_user, db, Factura.grupo_id, grupo_id=1
        >>> )
    """
    # Admin global ve todo
    if is_admin_or_superadmin(usuario):
        if grupo_id_filter:
            query = query.filter(grupo_id_column == grupo_id_filter)
        return query

    # Usuario normal: solo sus grupos
    grupos_usuario = get_grupos_usuario(usuario.id, db)

    if not grupos_usuario:
        # Usuario sin grupos asignados: no ve nada (o solo NULL)
        query = query.filter(grupo_id_column.is_(None))
    else:
        # Filtrar por grupos del usuario
        query = query.filter(grupo_id_column.in_(grupos_usuario))

        # Si se especifica grupo_id, validar acceso y filtrar
        if grupo_id_filter:
            if grupo_id_filter not in grupos_usuario:
                raise HTTPException(
                    status_code=403,
                    detail=f"Usuario no tiene acceso al grupo {grupo_id_filter}"
                )
            query = query.filter(grupo_id_column == grupo_id_filter)

    return query
