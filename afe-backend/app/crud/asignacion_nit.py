# app/crud/asignacion_nit.py
"""
CRUD operations para AsignacionNitResponsable.

Centraliza la lógica de mapeo NIT → Grupo para evitar duplicación de código.


"""

from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.grupo import Grupo
import logging

logger = logging.getLogger(__name__)


def get_grupo_id_por_nit(
    db: Session,
    nit: str,
    responsable_id: Optional[int] = None
) -> Optional[int]:
    """
    Obtiene el grupo_id al que pertenece un NIT.

    Esta es la función CENTRALIZADA para mapear NIT → Grupo.
    Usada por:
    - invoice_service.py (clasificación automática de facturas)
    - workflow_automatico.py (asignación de responsables)
    - Scripts de migración

    Lógica:
    1. Buscar en asignacion_nit_responsable con grupo_id específico
    2. Si hay múltiples coincidencias y se provee responsable_id, filtrar por responsable
    3. Si no hay resultados o grupo_id es NULL, retornar None

    Args:
        db: Sesión de base de datos
        nit: NIT del proveedor (limpio, sin puntos ni guiones)
        responsable_id: ID del responsable (opcional, para desambiguar)

    Returns:
        grupo_id si se encuentra, None si no existe o es NULL

    Example:
        >>> get_grupo_id_por_nit(db, "900123456")
        5  # CAM - Manizales

        >>> get_grupo_id_por_nit(db, "900999999")
        None  # NIT no configurado
    """
    try:
        # Query base: buscar asignaciones activas con grupo_id no NULL
        query = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.nit == nit,
            AsignacionNitResponsable.activo == True,
            AsignacionNitResponsable.grupo_id.isnot(None)  # Excluir asignaciones globales
        )

        # Si se provee responsable_id, filtrar por responsable
        if responsable_id is not None:
            query = query.filter(AsignacionNitResponsable.responsable_id == responsable_id)

        # Obtener primera coincidencia (puede haber múltiples si NIT compartido)
        asignacion = query.first()

        if asignacion:
            logger.debug(
                f"Grupo encontrado para NIT",
                extra={
                    "nit": nit,
                    "grupo_id": asignacion.grupo_id,
                    "responsable_id": asignacion.responsable_id
                }
            )
            return asignacion.grupo_id
        else:
            logger.debug(
                f"No se encontró grupo para NIT",
                extra={"nit": nit, "responsable_id": responsable_id}
            )
            return None

    except Exception as e:
        logger.error(
            f"Error obteniendo grupo_id para NIT",
            extra={
                "nit": nit,
                "responsable_id": responsable_id,
                "error": str(e)
            },
            exc_info=True
        )
        return None


def get_grupos_por_nit(db: Session, nit: str) -> List[int]:
    """
    Obtiene TODOS los grupos a los que está asignado un NIT.

    Útil para NITs compartidos entre múltiples subsedes.

    Args:
        db: Sesión de base de datos
        nit: NIT del proveedor

    Returns:
        Lista de grupo_ids (puede estar vacía)

    Example:
        >>> get_grupos_por_nit(db, "900123456")
        [5, 6, 7]  # NIT compartido entre CAM, CAI, CASM
    """
    try:
        asignaciones = db.query(AsignacionNitResponsable.grupo_id).filter(
            AsignacionNitResponsable.nit == nit,
            AsignacionNitResponsable.activo == True,
            AsignacionNitResponsable.grupo_id.isnot(None)
        ).distinct().all()

        grupos = [a[0] for a in asignaciones]

        logger.debug(
            f"Grupos encontrados para NIT",
            extra={"nit": nit, "grupos": grupos, "count": len(grupos)}
        )

        return grupos

    except Exception as e:
        logger.error(
            f"Error obteniendo grupos para NIT",
            extra={"nit": nit, "error": str(e)},
            exc_info=True
        )
        return []


def get_responsables_por_nit_y_grupo(
    db: Session,
    nit: str,
    grupo_id: int
) -> List[int]:
    """
    Obtiene los responsables asignados a un NIT en un grupo específico.

    Útil para workflows automáticos donde múltiples responsables
    pueden aprobar facturas del mismo proveedor.

    Args:
        db: Sesión de base de datos
        nit: NIT del proveedor
        grupo_id: ID del grupo

    Returns:
        Lista de responsable_ids

    Example:
        >>> get_responsables_por_nit_y_grupo(db, "900123456", 5)
        [158, 200]  # Luis y María pueden aprobar en CAM
    """
    try:
        asignaciones = db.query(AsignacionNitResponsable.responsable_id).filter(
            AsignacionNitResponsable.nit == nit,
            AsignacionNitResponsable.grupo_id == grupo_id,
            AsignacionNitResponsable.activo == True
        ).all()

        responsables = [a[0] for a in asignaciones]

        logger.debug(
            f"Responsables encontrados para NIT y grupo",
            extra={
                "nit": nit,
                "grupo_id": grupo_id,
                "responsables": responsables,
                "count": len(responsables)
            }
        )

        return responsables

    except Exception as e:
        logger.error(
            f"Error obteniendo responsables",
            extra={"nit": nit, "grupo_id": grupo_id, "error": str(e)},
            exc_info=True
        )
        return []


def es_nit_compartido(db: Session, nit: str) -> Tuple[bool, List[int]]:
    """
    Verifica si un NIT está compartido entre múltiples grupos.

    Args:
        db: Sesión de base de datos
        nit: NIT del proveedor

    Returns:
        Tuple(es_compartido: bool, grupos: List[int])

    Example:
        >>> es_nit_compartido(db, "900123456")
        (True, [5, 6, 7])  # Compartido entre CAM, CAI, CASM
    """
    grupos = get_grupos_por_nit(db, nit)
    es_compartido = len(grupos) > 1

    if es_compartido:
        logger.info(
            f"NIT compartido detectado",
            extra={"nit": nit, "grupos": grupos, "count": len(grupos)}
        )

    return es_compartido, grupos


def get_nombre_grupo(db: Session, grupo_id: int) -> Optional[str]:
    """
    Obtiene el nombre de un grupo por su ID.

    Helper function para logging y debugging.

    Args:
        db: Sesión de base de datos
        grupo_id: ID del grupo

    Returns:
        Nombre del grupo o None
    """
    try:
        grupo = db.query(Grupo).filter(Grupo.id == grupo_id).first()
        return grupo.nombre if grupo else None
    except Exception as e:
        logger.error(f"Error obteniendo nombre de grupo {grupo_id}: {str(e)}")
        return None
