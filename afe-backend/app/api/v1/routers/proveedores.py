from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.proveedor import ProveedorBase, ProveedorRead
from app.schemas.common import ErrorResponse
from app.crud.proveedor import create_proveedor, list_proveedores, get_proveedor, update_proveedor, delete_proveedor
from app.core.security import get_current_usuario, require_role
from app.utils.logger import logger
from app.models.grupo import ResponsableGrupo
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.proveedor import Proveedor
from sqlalchemy import distinct

router = APIRouter(tags=["Proveedores"])


# ==================== HELPER FUNCTIONS - MULTI-TENANT ====================

def get_grupos_usuario(usuario_id: int, db: Session) -> List[int]:
    """
    Obtiene los IDs de grupos a los que el usuario tiene acceso.

    Args:
        usuario_id: ID del usuario
        db: Sesión de base de datos

    Returns:
        Lista de IDs de grupos del usuario
    """
    grupos = db.query(ResponsableGrupo.grupo_id).filter(
        ResponsableGrupo.responsable_id == usuario_id,
        ResponsableGrupo.activo == True
    ).all()

    return [g[0] for g in grupos]


@router.get(
    "/",
    response_model=List[ProveedorRead],
    summary="Listar proveedores (multi-tenant)",
    description="""
    Obtiene una lista de proveedores filtrada por grupo empresarial.

    **Filtrado por rol:**
    - SuperAdmin: Ve todos los proveedores
    - Admin/Usuario: Solo ve proveedores cuyos NITs están asignados a responsables de su grupo

    **Implementación:** Filtra por asignacion_nit_responsable.grupo_id
    """
)
def list_all(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """
    Lista proveedores con filtrado multi-tenant.

    ARQUITECTURA: Proveedores Globales (sin restricción de asignaciones)
    - SuperAdmin: Ve todos los proveedores del sistema
    - Admin/Usuario: Ve todos los proveedores (no hay restricción por grupo)
    
    NOTA: Los proveedores se muestran siempre, aunque no tengan asignaciones.
    Las asignaciones se gestiona en el endpoint de asignaciones NIT.
    """

    # SuperAdmin ve todos los proveedores
    if current_user.role.nombre.lower() == "superadmin":
        proveedores = list_proveedores(db, skip=skip, limit=limit)
        logger.info(f"[MULTI-TENANT] SuperAdmin consultó {len(proveedores)} proveedores (sin filtro)")
        return proveedores

    # Admin/Usuario también ven TODOS los proveedores (para poder asignarlos)
    # No hay restricción por grupo en la lista de proveedores
    # Las restricciones de grupo se aplican en asignaciones
    proveedores = list_proveedores(db, skip=skip, limit=limit)
    
    logger.info(
        f"[MULTI-TENANT] Usuario {current_user.id} "
        f"consultó {len(proveedores)} proveedores"
    )

    return proveedores


@router.post(
    "/",
    response_model=ProveedorRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Crear proveedor",
    description="Registra un nuevo proveedor en el sistema."
)
def create(
    payload: ProveedorBase,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "responsable"])),
):
    p = create_proveedor(db, payload)
    logger.info("Proveedor creado", extra={"id": p.id, "usuario": current_user.usuario})
    return p


@router.get(
    "/{proveedor_id}",
    response_model=ProveedorRead,
    responses={
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse}
    },
    summary="Obtener proveedor (multi-tenant)",
    description="""
    Devuelve los datos de un proveedor específico.

    **Validación de permisos:**
    - SuperAdmin: Acceso a cualquier proveedor
    - Admin/Usuario: Solo proveedores con NITs asignados a su grupo
    """
)
def get_one(
    proveedor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """
    Obtiene un proveedor con validación multi-tenant.
    """
    p = get_proveedor(db, proveedor_id)
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proveedor no encontrado"
        )

    # SuperAdmin tiene acceso a todos los proveedores
    if current_user.role.nombre.lower() == "superadmin":
        return p

    # Validar que el NIT del proveedor esté asignado a un responsable del grupo del usuario
    grupos_ids = get_grupos_usuario(current_user.id, db)

    if not grupos_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sin grupos asignados"
        )

    # Verificar si existe asignación del NIT en alguno de los grupos del usuario
    tiene_acceso = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == p.nit,
        AsignacionNitResponsable.grupo_id.in_(grupos_ids)
    ).first() is not None

    if not tiene_acceso:
        logger.warning(
            f"[MULTI-TENANT] Usuario {current_user.id} intentó acceder a proveedor {proveedor_id} "
            f"(NIT: {p.nit}) sin permisos"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este proveedor"
        )

    return p


@router.put(
    "/{proveedor_id}",
    response_model=ProveedorRead,
    responses={404: {"model": ErrorResponse}},
    summary="Actualizar proveedor",
    description="Actualiza los datos de un proveedor por su ID."
)
def update(
    proveedor_id: int,
    payload: ProveedorBase,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    p = update_proveedor(db, proveedor_id, payload)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    logger.info("Proveedor actualizado", extra={"id": p.id, "usuario": current_user.usuario})
    return p


@router.delete(
    "/{proveedor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
    summary="Eliminar proveedor",
    description="Elimina un proveedor por su ID."
)
def delete(
    proveedor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    ok = delete_proveedor(db, proveedor_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    logger.info("Proveedor eliminado", extra={"id": proveedor_id, "usuario": current_user.usuario})
    return None
