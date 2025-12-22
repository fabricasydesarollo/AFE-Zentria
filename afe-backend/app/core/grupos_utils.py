"""
Utilidades para manejo de grupos y permisos multi-tenant.

Este módulo contiene funciones helper para:
- Obtener grupos de un usuario
- Validar acceso a grupos
- Aplicar filtros por grupo en queries

Nivel: Fortune 500 Enterprise Security
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.grupo import ResponsableGrupo, Grupo
from app.models.usuario import Usuario


def get_grupos_usuario(usuario_id: int, db: Session, incluir_descendientes: bool = True) -> List[int]:
    """
    Obtiene lista de IDs de grupos a los que pertenece un usuario.

    ARQUITECTURA JERÁRQUICA:
    - Si el usuario está asignado a un grupo padre (ej: AVIDANTI)
    - Incluye automáticamente todos los grupos hijos (CAM, CAI, CASM, ADC, etc.)
    - Esto permite que Admins de sede tengan acceso a todas sus subsedes

    Args:
        usuario_id: ID del usuario
        db: Sesión de SQLAlchemy
        incluir_descendientes: Si True, incluye todos los grupos hijos (default: True)

    Returns:
        Lista de IDs de grupos (puede estar vacía)

    Ejemplo:
        >>> grupos = get_grupos_usuario(5, db)
        >>> print(grupos)
        [1, 2, 5, 6, 7, 8]  # AVIDANTI + CAM + CAI + CASM + ADC + DSZF + CAA
    """
    # Obtener grupos directamente asignados
    grupos_asignados = (
        db.query(ResponsableGrupo.grupo_id)
        .filter(
            ResponsableGrupo.responsable_id == usuario_id,
            ResponsableGrupo.activo == True
        )
        .all()
    )

    grupos_ids = [grupo_id[0] for grupo_id in grupos_asignados]

    if not incluir_descendientes:
        return grupos_ids

    # Incluir todos los descendientes de cada grupo asignado
    todos_los_grupos = set(grupos_ids)

    for grupo_id in grupos_ids:
        descendientes = obtener_descendientes_grupo(grupo_id, db)
        todos_los_grupos.update(descendientes)

    return list(todos_los_grupos)


def get_grupos_usuario_con_detalles(usuario_id: int, db: Session) -> List[dict]:
    """
    Obtiene lista de grupos con detalles completos para un usuario.

    Args:
        usuario_id: ID del usuario
        db: Sesión de SQLAlchemy

    Returns:
        Lista de diccionarios con información de grupos

    Ejemplo:
        >>> grupos = get_grupos_usuario_con_detalles(5, db)
        >>> print(grupos[0])
        {
            'id': 1,
            'nombre': 'AVIDANTI',
            'codigo_corto': 'AVID',
            'nivel': 1,
            'activo': True
        }
    """
    grupos = (
        db.query(Grupo)
        .join(ResponsableGrupo, Grupo.id == ResponsableGrupo.grupo_id)
        .filter(
            ResponsableGrupo.responsable_id == usuario_id,
            ResponsableGrupo.activo == True,
            Grupo.activo == True,
            Grupo.eliminado == False
        )
        .all()
    )

    return [
        {
            'id': grupo.id,
            'nombre': grupo.nombre,
            'codigo_corto': grupo.codigo_corto,
            'nivel': grupo.nivel,
            'activo': grupo.activo
        }
        for grupo in grupos
    ]


def usuario_tiene_acceso_grupo(usuario_id: int, grupo_id: int, db: Session) -> bool:
    """
    Verifica si un usuario tiene acceso a un grupo específico.

    Args:
        usuario_id: ID del usuario
        grupo_id: ID del grupo a verificar
        db: Sesión de SQLAlchemy

    Returns:
        True si tiene acceso, False si no

    Ejemplo:
        >>> tiene_acceso = usuario_tiene_acceso_grupo(5, 1, db)
        >>> print(tiene_acceso)
        True
    """
    grupos_usuario = get_grupos_usuario(usuario_id, db)
    return grupo_id in grupos_usuario


def usuario_es_admin(usuario: Usuario) -> bool:
    """
    Verifica si un usuario tiene rol de superadministrador.

    IMPORTANTE: Solo SuperAdmin retorna True.
    - superadmin = True (acceso total sin restricciones)
    - admin = False (debe usar responsable_grupo)
    - otros roles = False

    Args:
        usuario: Objeto Usuario

    Returns:
        True si es superadmin, False para admin y otros roles

    Ejemplo:
        >>> es_admin = usuario_es_admin(usuario)
        >>> print(es_admin)
        False
    """
    if not usuario.role:
        return False
    return usuario.role.nombre == "superadmin"


def aplicar_filtro_grupos(query, modelo_clase, usuario: Usuario, db: Session, grupo_id_solicitado: Optional[int] = None):
    """
    Aplica filtro de grupos a un query de SQLAlchemy.

    Lógica:
    - Si usuario es admin: no aplica filtro (ve todo)
    - Si grupo_id_solicitado: filtra por ese grupo (si tiene acceso)
    - Si no: filtra por todos los grupos del usuario

    Args:
        query: Query de SQLAlchemy
        modelo_clase: Clase del modelo (ej: Factura)
        usuario: Usuario actual
        db: Sesión de SQLAlchemy
        grupo_id_solicitado: Grupo específico solicitado (opcional)

    Returns:
        Query con filtro aplicado

    Raises:
        ValueError: Si usuario no tiene acceso al grupo solicitado

    Ejemplo:
        >>> query = db.query(Factura)
        >>> query = aplicar_filtro_grupos(query, Factura, usuario, db)
        >>> facturas = query.all()
    """
    from fastapi import HTTPException

    # Admin puede ver todo
    if usuario_es_admin(usuario):
        if grupo_id_solicitado:
            return query.filter(modelo_clase.grupo_id == grupo_id_solicitado)
        return query

    # Obtener grupos del usuario
    grupos_usuario = get_grupos_usuario(usuario.id, db)

    # Si no tiene grupos asignados, no ve nada
    if not grupos_usuario:
        # Filtro imposible (siempre False)
        return query.filter(modelo_clase.grupo_id == -1)

    # Si se solicita un grupo específico
    if grupo_id_solicitado:
        if grupo_id_solicitado not in grupos_usuario:
            raise HTTPException(
                status_code=403,
                detail=f"Usuario no tiene acceso al grupo {grupo_id_solicitado}"
            )
        return query.filter(modelo_clase.grupo_id == grupo_id_solicitado)

    # Filtrar por todos los grupos del usuario
    return query.filter(modelo_clase.grupo_id.in_(grupos_usuario))


def get_grupos_raiz_usuario(usuario: Usuario, db: Session) -> List[Grupo]:
    """
    Obtiene solo los grupos raíz (nivel 1) accesibles por el usuario.

    Útil para:
    - Mostrar selector de grupo en frontend
    - Dashboard con vista por organización principal

    Args:
        usuario: Usuario actual
        db: Sesión de SQLAlchemy

    Returns:
        Lista de grupos raíz

    Ejemplo:
        >>> grupos_raiz = get_grupos_raiz_usuario(usuario, db)
        >>> print([g.nombre for g in grupos_raiz])
        ['AVIDANTI', 'ADC']
    """
    # Admin ve todos los grupos raíz
    if usuario_es_admin(usuario):
        return (
            db.query(Grupo)
            .filter(
                Grupo.nivel == 1,
                Grupo.activo == True,
                Grupo.eliminado == False
            )
            .all()
        )

    # Usuario normal: solo grupos raíz de sus grupos
    grupos_usuario = get_grupos_usuario(usuario.id, db)

    if not grupos_usuario:
        return []

    # Obtener grupos raíz de los grupos asignados
    grupos = (
        db.query(Grupo)
        .filter(
            Grupo.id.in_(grupos_usuario),
            Grupo.nivel == 1,
            Grupo.activo == True,
            Grupo.eliminado == False
        )
        .all()
    )

    return grupos


def contar_facturas_por_grupo(usuario: Usuario, db: Session) -> dict:
    """
    Cuenta facturas por grupo para el usuario.

    Útil para dashboard y estadísticas.

    Args:
        usuario: Usuario actual
        db: Sesión de SQLAlchemy

    Returns:
        Diccionario {grupo_id: cantidad}

    Ejemplo:
        >>> stats = contar_facturas_por_grupo(usuario, db)
        >>> print(stats)
        {1: 171, 2: 166, 3: 14}
    """
    from app.models.factura import Factura
    from sqlalchemy import func

    query = db.query(
        Factura.grupo_id,
        func.count(Factura.id).label('total')
    )

    # Aplicar filtro de grupos
    query = aplicar_filtro_grupos(query, Factura, usuario, db)

    resultados = query.group_by(Factura.grupo_id).all()

    return {row[0]: row[1] for row in resultados if row[0] is not None}


def validar_acceso_crear_factura(usuario: Usuario, grupo_id: int, db: Session) -> bool:
    """
    Valida si un usuario puede crear una factura en un grupo específico.

    Args:
        usuario: Usuario actual
        grupo_id: Grupo donde se quiere crear la factura
        db: Sesión de SQLAlchemy

    Returns:
        True si puede crear, False si no

    Raises:
        HTTPException: Si no tiene acceso

    Ejemplo:
        >>> puede_crear = validar_acceso_crear_factura(usuario, 1, db)
    """
    from fastapi import HTTPException

    # Admin puede crear en cualquier grupo
    if usuario_es_admin(usuario):
        # Verificar que grupo existe
        grupo = db.query(Grupo).filter(Grupo.id == grupo_id).first()
        if not grupo:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        return True

    # Usuario normal: solo en sus grupos
    if not usuario_tiene_acceso_grupo(usuario.id, grupo_id, db):
        raise HTTPException(
            status_code=403,
            detail=f"No tiene permiso para crear facturas en el grupo {grupo_id}"
        )

    return True


def obtener_jerarquia_grupo(grupo_id: int, db: Session) -> List[int]:
    """
    Obtiene la jerarquía completa de un grupo (padre, abuelo, etc.).

    Útil para permisos heredados.

    Args:
        grupo_id: ID del grupo
        db: Sesión de SQLAlchemy

    Returns:
        Lista de IDs desde grupo hasta raíz

    Ejemplo:
        >>> jerarquia = obtener_jerarquia_grupo(5, db)  # CAM (hijo de AVIDANTI)
        >>> print(jerarquia)
        [5, 1]  # CAM → AVIDANTI
    """
    jerarquia = []
    grupo_actual = db.query(Grupo).filter(Grupo.id == grupo_id).first()

    while grupo_actual:
        jerarquia.append(grupo_actual.id)
        if grupo_actual.grupo_padre_id:
            grupo_actual = db.query(Grupo).filter(
                Grupo.id == grupo_actual.grupo_padre_id
            ).first()
        else:
            break

    return jerarquia


def obtener_descendientes_grupo(grupo_id: int, db: Session) -> List[int]:
    """
    Obtiene TODOS los descendientes de un grupo (hijos, nietos, bisnietos, etc.).

    Útil para permisos jerárquicos donde el admin de un grupo padre
    tiene acceso automático a todos los grupos hijos.

    Args:
        grupo_id: ID del grupo padre
        db: Sesión de SQLAlchemy

    Returns:
        Lista de IDs de todos los descendientes (NO incluye el grupo_id original)

    Ejemplo:
        >>> descendientes = obtener_descendientes_grupo(1, db)  # AVIDANTI
        >>> print(descendientes)
        [2, 5, 6, 7, 8, 9, 10]  # ADC, CAM, CAI, CASM, DSZF, CAA, etc.
    """
    descendientes = []

    # Obtener hijos directos
    hijos = db.query(Grupo.id).filter(
        Grupo.grupo_padre_id == grupo_id,
        Grupo.activo == True,
        Grupo.eliminado == False
    ).all()

    for hijo in hijos:
        hijo_id = hijo[0]
        descendientes.append(hijo_id)
        # Recursivamente obtener descendientes del hijo
        descendientes.extend(obtener_descendientes_grupo(hijo_id, db))

    return descendientes
