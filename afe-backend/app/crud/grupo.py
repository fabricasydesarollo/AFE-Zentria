"""
CRUD de Grupos - Multi-Tenant con Jerarquía

Operaciones de acceso a datos para grupos con soporte jerárquico.

Características:
- CRUD completo (Create, Read, Update, Soft Delete)
- Soporte para jerarquía de grupos
- Filtrado por múltiples criterios
- Validaciones de integridad jerárquica
- Soft delete


"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.grupo import Grupo
from app.schemas.grupo import GrupoCreate, GrupoUpdate, GrupoFilter

logger = logging.getLogger(__name__)


# ================================================================================
# OPERACIONES DE LECTURA
# ================================================================================

def get_grupo(db: Session, grupo_id: int, include_deleted: bool = False) -> Optional[Grupo]:
    """
    Obtiene un grupo por ID.

    Args:
        db: Sesión de base de datos
        grupo_id: ID del grupo
        include_deleted: Si True, incluye grupos eliminados

    Returns:
        Grupo o None
    """
    query = db.query(Grupo).filter(Grupo.id == grupo_id)

    if not include_deleted:
        query = query.filter(Grupo.eliminado == False)

    return query.first()


def get_grupo_by_codigo(db: Session, codigo_corto: str, include_deleted: bool = False) -> Optional[Grupo]:
    """
    Obtiene un grupo por código corto.

    Args:
        db: Sesión de base de datos
        codigo_corto: Código único del grupo
        include_deleted: Si True, incluye grupos eliminados

    Returns:
        Grupo o None
    """
    query = db.query(Grupo).filter(Grupo.codigo_corto == codigo_corto)

    if not include_deleted:
        query = query.filter(Grupo.eliminado == False)

    return query.first()


def list_grupos(
    db: Session,
    filtros: Optional[GrupoFilter] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[Grupo], int]:
    """
    Lista grupos con filtros opcionales.

    Args:
        db: Sesión de base de datos
        filtros: Filtros a aplicar
        skip: Offset para paginación
        limit: Límite de resultados

    Returns:
        Tupla (lista de grupos, total)
    """
    query = db.query(Grupo)

    # Aplicar filtros
    if filtros:
        if filtros.activo is not None:
            query = query.filter(Grupo.activo == filtros.activo)

        if filtros.eliminado is not None:
            query = query.filter(Grupo.eliminado == filtros.eliminado)

        if filtros.grupo_padre_id is not None:
            query = query.filter(Grupo.grupo_padre_id == filtros.grupo_padre_id)

        if filtros.nivel is not None:
            query = query.filter(Grupo.nivel == filtros.nivel)

        if filtros.codigo_corto:
            query = query.filter(Grupo.codigo_corto == filtros.codigo_corto)
    else:
        # Por defecto, no mostrar eliminados
        query = query.filter(Grupo.eliminado == False)

    # Ordenar por jerarquía
    query = query.order_by(Grupo.ruta_jerarquica)

    total = query.count()
    grupos = query.offset(skip).limit(limit).all()

    return grupos, total


def get_grupos_raiz(db: Session, activos_only: bool = True) -> List[Grupo]:
    """
    Obtiene todos los grupos raíz (sin padre).

    Args:
        db: Sesión de base de datos
        activos_only: Si True, solo devuelve grupos activos

    Returns:
        Lista de grupos raíz
    """
    query = db.query(Grupo).filter(Grupo.grupo_padre_id == None, Grupo.eliminado == False)

    if activos_only:
        query = query.filter(Grupo.activo == True)

    return query.order_by(Grupo.nombre).all()


def get_hijos(db: Session, grupo_padre_id: int, activos_only: bool = True) -> List[Grupo]:
    """
    Obtiene todos los hijos de un grupo.

    Args:
        db: Sesión de base de datos
        grupo_padre_id: ID del grupo padre
        activos_only: Si True, solo devuelve grupos activos

    Returns:
        Lista de grupos hijos
    """
    query = db.query(Grupo).filter(
        Grupo.grupo_padre_id == grupo_padre_id,
        Grupo.eliminado == False
    )

    if activos_only:
        query = query.filter(Grupo.activo == True)

    return query.order_by(Grupo.nombre).all()


def get_arbol_jerarquico(db: Session, grupo_id: Optional[int] = None) -> List[Grupo]:
    """
    Obtiene el árbol jerárquico completo o desde un grupo específico.

    Args:
        db: Sesión de base de datos
        grupo_id: ID del grupo raíz (None para todo el árbol)

    Returns:
        Lista de grupos ordenados jerárquicamente
    """
    query = db.query(Grupo).filter(Grupo.eliminado == False, Grupo.activo == True)

    if grupo_id:
        # Obtener el grupo y sus descendientes
        grupo = get_grupo(db, grupo_id)
        if grupo and grupo.ruta_jerarquica:
            query = query.filter(
                or_(
                    Grupo.id == grupo_id,
                    Grupo.ruta_jerarquica.like(f"{grupo.ruta_jerarquica}/%")
                )
            )

    return query.order_by(Grupo.ruta_jerarquica).all()


# ================================================================================
# OPERACIONES DE ESCRITURA
# ================================================================================

def create_grupo(db: Session, grupo_data: GrupoCreate, creado_por: str = "SYSTEM") -> Grupo:
    """
    Crea un nuevo grupo.

    Args:
        db: Sesión de base de datos
        grupo_data: Datos del grupo a crear
        creado_por: Usuario que crea el grupo

    Returns:
        Grupo creado

    Raises:
        ValueError: Si hay errores de validación
    """
    # Validar código único
    existing = get_grupo_by_codigo(db, grupo_data.codigo_corto, include_deleted=True)
    if existing:
        raise ValueError(f"Ya existe un grupo con código '{grupo_data.codigo_corto}'")

    # Validar grupo padre si existe
    # Nivel por defecto = 1 (Sede)
    # Nota: Para crear un grupo Corporativo (nivel 0), debe establecerse manualmente
    nivel = 1
    ruta_jerarquica = None

    if grupo_data.grupo_padre_id:
        padre = get_grupo(db, grupo_data.grupo_padre_id)
        if not padre:
            raise ValueError(f"Grupo padre {grupo_data.grupo_padre_id} no existe")

        if not padre.puede_tener_hijos():
            raise ValueError(f"El grupo padre '{padre.nombre}' no permite subsedes o ha alcanzado el nivel máximo")

        nivel = padre.nivel + 1

    # Crear grupo
    nuevo_grupo = Grupo(
        nombre=grupo_data.nombre,
        codigo_corto=grupo_data.codigo_corto,
        descripcion=grupo_data.descripcion,
        grupo_padre_id=grupo_data.grupo_padre_id,
        nivel=nivel,
        correos_corporativos=grupo_data.correos_corporativos or [],
        permite_subsedes=grupo_data.permite_subsedes,
        max_nivel_subsedes=grupo_data.max_nivel_subsedes,
        activo=grupo_data.activo,
        creado_por=creado_por
    )

    db.add(nuevo_grupo)
    db.flush()  # Para obtener el ID

    # Construir ruta jerárquica
    if grupo_data.grupo_padre_id:
        padre = get_grupo(db, grupo_data.grupo_padre_id)
        nuevo_grupo.ruta_jerarquica = f"{padre.ruta_jerarquica}/{nuevo_grupo.id}"
    else:
        nuevo_grupo.ruta_jerarquica = str(nuevo_grupo.id)

    db.commit()
    db.refresh(nuevo_grupo)

    logger.info(f"Grupo creado: {nuevo_grupo.codigo_corto} (ID: {nuevo_grupo.id})")

    return nuevo_grupo


def update_grupo(
    db: Session,
    grupo_id: int,
    grupo_data: GrupoUpdate,
    actualizado_por: str
) -> Optional[Grupo]:
    """
    Actualiza un grupo existente.

    Args:
        db: Sesión de base de datos
        grupo_id: ID del grupo a actualizar
        grupo_data: Datos a actualizar
        actualizado_por: Usuario que actualiza

    Returns:
        Grupo actualizado o None si no existe

    Raises:
        ValueError: Si hay errores de validación
    """
    grupo = get_grupo(db, grupo_id)
    if not grupo:
        return None

    # Validar código único si se está cambiando
    if grupo_data.codigo_corto and grupo_data.codigo_corto != grupo.codigo_corto:
        existing = get_grupo_by_codigo(db, grupo_data.codigo_corto, include_deleted=True)
        if existing:
            raise ValueError(f"Ya existe un grupo con código '{grupo_data.codigo_corto}'")

    # Actualizar campos
    update_data = grupo_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(grupo, field, value)

    grupo.actualizado_por = actualizado_por

    db.commit()
    db.refresh(grupo)

    logger.info(f"Grupo actualizado: {grupo.codigo_corto} (ID: {grupo.id})")

    return grupo


def soft_delete_grupo(db: Session, grupo_id: int, eliminado_por: str) -> Optional[Grupo]:
    """
    Realiza soft delete de un grupo.

    Args:
        db: Sesión de base de datos
        grupo_id: ID del grupo a eliminar
        eliminado_por: Usuario que elimina

    Returns:
        Grupo eliminado o None si no existe

    Raises:
        ValueError: Si el grupo tiene hijos activos
    """
    grupo = get_grupo(db, grupo_id)
    if not grupo:
        return None

    # Verificar que no tenga hijos activos
    hijos = get_hijos(db, grupo_id, activos_only=True)
    if hijos:
        raise ValueError(f"No se puede eliminar el grupo '{grupo.nombre}' porque tiene {len(hijos)} subsedes activas")

    # Realizar soft delete
    grupo.soft_delete(eliminado_por)

    db.commit()
    db.refresh(grupo)

    logger.info(f"Grupo eliminado (soft delete): {grupo.codigo_corto} (ID: {grupo.id})")

    return grupo


def restore_grupo(db: Session, grupo_id: int, restaurado_por: str) -> Optional[Grupo]:
    """
    Restaura un grupo eliminado.

    Args:
        db: Sesión de base de datos
        grupo_id: ID del grupo a restaurar
        restaurado_por: Usuario que restaura

    Returns:
        Grupo restaurado o None si no existe
    """
    grupo = get_grupo(db, grupo_id, include_deleted=True)
    if not grupo or not grupo.eliminado:
        return None

    grupo.eliminado = False
    grupo.activo = True
    grupo.fecha_eliminacion = None
    grupo.eliminado_por = None
    grupo.actualizado_por = restaurado_por

    db.commit()
    db.refresh(grupo)

    logger.info(f"Grupo restaurado: {grupo.codigo_corto} (ID: {grupo.id})")

    return grupo


# ================================================================================
# OPERACIONES AUXILIARES
# ================================================================================

def count_grupos(db: Session, activos_only: bool = True) -> int:
    """
    Cuenta el total de grupos.

    Args:
        db: Sesión de base de datos
        activos_only: Si True, solo cuenta grupos activos

    Returns:
        Número total de grupos
    """
    query = db.query(Grupo).filter(Grupo.eliminado == False)

    if activos_only:
        query = query.filter(Grupo.activo == True)

    return query.count()


def grupo_tiene_facturas(db: Session, grupo_id: int) -> bool:
    """
    Verifica si un grupo tiene facturas asociadas.

    Args:
        db: Sesión de base de datos
        grupo_id: ID del grupo

    Returns:
        True si tiene facturas
    """
    from app.models.factura import Factura
    return db.query(Factura).filter(Factura.grupo_id == grupo_id).count() > 0


# ================================================================================
# OPERACIONES DE RESPONSABLE_GRUPO (Asignación Usuarios-Grupos)
# ================================================================================

def asignar_responsable_a_grupo(
    db: Session,
    responsable_id: int,
    grupo_id: int,
    asignado_por: str,
    activo: bool = True
) -> Optional['ResponsableGrupo']:
    """
    Asigna un usuario responsable a un grupo.

    Args:
        db: Sesión de base de datos
        responsable_id: ID del usuario
        grupo_id: ID del grupo
        asignado_por: Usuario que realiza la asignación
        activo: Estado inicial de la asignación

    Returns:
        ResponsableGrupo creado o None si ya existe

    Raises:
        ValueError: Si el grupo o usuario no existen
    """
    from app.models.grupo import ResponsableGrupo
    from app.models.usuario import Usuario

    # Validar que el grupo existe
    grupo = get_grupo(db, grupo_id)
    if not grupo:
        raise ValueError(f"Grupo {grupo_id} no encontrado")

    # Validar que el usuario existe
    usuario = db.query(Usuario).filter(Usuario.id == responsable_id).first()
    if not usuario:
        raise ValueError(f"Usuario {responsable_id} no encontrado")

    # Verificar si ya existe la asignación
    asignacion_existente = db.query(ResponsableGrupo).filter(
        ResponsableGrupo.responsable_id == responsable_id,
        ResponsableGrupo.grupo_id == grupo_id
    ).first()

    if asignacion_existente:
        # Si existe pero está inactiva, reactivarla
        if not asignacion_existente.activo and activo:
            asignacion_existente.activo = True
            asignacion_existente.actualizado_por = asignado_por
            db.commit()
            db.refresh(asignacion_existente)
            logger.info(f"Asignación reactivada: Usuario {responsable_id} → Grupo {grupo_id}")
            return asignacion_existente

        logger.warning(f"Asignación ya existe: Usuario {responsable_id} → Grupo {grupo_id}")
        return asignacion_existente

    # Crear nueva asignación
    nueva_asignacion = ResponsableGrupo(
        responsable_id=responsable_id,
        grupo_id=grupo_id,
        activo=activo,
        asignado_por=asignado_por
    )

    db.add(nueva_asignacion)
    db.commit()
    db.refresh(nueva_asignacion)

    logger.info(f"Usuario {responsable_id} asignado a Grupo {grupo_id} por {asignado_por}")

    return nueva_asignacion


def remover_responsable_de_grupo(
    db: Session,
    responsable_id: int,
    grupo_id: int,
    actualizado_por: str
) -> bool:
    """
    Desactiva la asignación de un usuario a un grupo.

    Args:
        db: Sesión de base de datos
        responsable_id: ID del usuario
        grupo_id: ID del grupo
        actualizado_por: Usuario que realiza la acción

    Returns:
        True si se desactivó exitosamente
    """
    from app.models.grupo import ResponsableGrupo

    asignacion = db.query(ResponsableGrupo).filter(
        ResponsableGrupo.responsable_id == responsable_id,
        ResponsableGrupo.grupo_id == grupo_id
    ).first()

    if not asignacion:
        logger.warning(f"Asignación no encontrada: Usuario {responsable_id} → Grupo {grupo_id}")
        return False

    asignacion.activo = False
    asignacion.actualizado_por = actualizado_por

    db.commit()

    logger.info(f"Usuario {responsable_id} removido de Grupo {grupo_id} por {actualizado_por}")

    return True


def listar_responsables_de_grupo(
    db: Session,
    grupo_id: int,
    activos_only: bool = True
) -> List['ResponsableGrupo']:
    """
    Lista todos los responsables asignados a un grupo.

    Args:
        db: Sesión de base de datos
        grupo_id: ID del grupo
        activos_only: Si True, solo devuelve asignaciones activas

    Returns:
        Lista de ResponsableGrupo
    """
    from app.models.grupo import ResponsableGrupo

    query = db.query(ResponsableGrupo).filter(ResponsableGrupo.grupo_id == grupo_id)

    if activos_only:
        query = query.filter(ResponsableGrupo.activo == True)

    return query.all()


def listar_grupos_de_responsable(
    db: Session,
    responsable_id: int,
    activos_only: bool = True
) -> List['ResponsableGrupo']:
    """
    Lista todos los grupos asignados a un responsable.

    Args:
        db: Sesión de base de datos
        responsable_id: ID del usuario
        activos_only: Si True, solo devuelve asignaciones activas

    Returns:
        Lista de ResponsableGrupo
    """
    from app.models.grupo import ResponsableGrupo

    query = db.query(ResponsableGrupo).filter(ResponsableGrupo.responsable_id == responsable_id)

    if activos_only:
        query = query.filter(ResponsableGrupo.activo == True)

    return query.all()


def get_asignacion_responsable_grupo(
    db: Session,
    asignacion_id: int
) -> Optional['ResponsableGrupo']:
    """
    Obtiene una asignación específica por ID.

    Args:
        db: Sesión de base de datos
        asignacion_id: ID de la asignación

    Returns:
        ResponsableGrupo o None
    """
    from app.models.grupo import ResponsableGrupo

    return db.query(ResponsableGrupo).filter(ResponsableGrupo.id == asignacion_id).first()


def actualizar_estado_asignacion(
    db: Session,
    asignacion_id: int,
    activo: bool,
    actualizado_por: str
) -> Optional['ResponsableGrupo']:
    """
    Actualiza el estado de una asignación.

    Args:
        db: Sesión de base de datos
        asignacion_id: ID de la asignación
        activo: Nuevo estado
        actualizado_por: Usuario que realiza la actualización

    Returns:
        ResponsableGrupo actualizado o None si no existe
    """
    from app.models.grupo import ResponsableGrupo

    asignacion = db.query(ResponsableGrupo).filter(ResponsableGrupo.id == asignacion_id).first()

    if not asignacion:
        return None

    asignacion.activo = activo
    asignacion.actualizado_por = actualizado_por

    db.commit()
    db.refresh(asignacion)

    logger.info(f"Asignación {asignacion_id} actualizada a activo={activo} por {actualizado_por}")

    return asignacion
