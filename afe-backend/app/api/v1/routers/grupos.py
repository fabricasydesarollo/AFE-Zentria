"""Router de Grupos - API Multi-Tenant con Jerarquía."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.schemas.grupo import (
    GrupoCreate,
    GrupoUpdate,
    GrupoResponse,
    GrupoListResponse,
    GrupoFilter,
    GrupoHierarchical,
    ResponsableGrupoCreate,
    ResponsableGrupoUpdate,
    ResponsableGrupoResponse,
    ResponsableGrupoDetalle
)
from app.schemas.common import ErrorResponse
from app.crud import grupo as crud_grupo
from app.core.security import get_current_usuario, require_role
from app.utils.logger import logger

router = APIRouter(tags=["Grupos"])


@router.get(
    "/",
    response_model=GrupoListResponse,
    summary="Listar grupos",
    description="Obtiene una lista paginada de grupos con filtros opcionales y filtrado multi-tenant."
)
def list_all(
    skip: int = Query(0, ge=0, description="Offset para paginación"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de resultados"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    eliminado: Optional[bool] = Query(False, description="Incluir grupos eliminados"),
    grupo_padre_id: Optional[int] = Query(None, description="Filtrar por grupo padre"),
    nivel: Optional[int] = Query(None, ge=1, description="Filtrar por nivel jerárquico"),
    codigo_corto: Optional[str] = Query(None, description="Filtrar por código"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """Lista grupos con filtrado multi-tenant por rol."""
    from app.models.grupo import Grupo, ResponsableGrupo
    from app.core.grupos_utils import get_grupos_usuario
    rol_nombre = current_user.role.nombre if current_user.role else "usuario"

    if rol_nombre.lower() == "superadmin":
        # SuperAdmin: sin filtros, ve todo
        filtros = GrupoFilter(
            activo=activo,
            eliminado=eliminado,
            grupo_padre_id=grupo_padre_id,
            nivel=nivel,
            codigo_corto=codigo_corto
        )
        grupos, total = crud_grupo.list_grupos(db, filtros=filtros, skip=skip, limit=limit)
    else:
        # Admin y otros roles: SOLO sus grupos asignados
        grupos_ids = get_grupos_usuario(current_user.id, db)

        if not grupos_ids:
            logger.warning(f"[MULTI-TENANT] Usuario {current_user.id} sin grupos asignados")
            return GrupoListResponse(total=0, grupos=[])

        # Filtrar grupos por IDs del usuario
        query = db.query(Grupo).filter(Grupo.id.in_(grupos_ids))

        if activo is not None:
            query = query.filter(Grupo.activo == activo)
        if not eliminado:
            query = query.filter(Grupo.eliminado == False)
        if grupo_padre_id is not None:
            query = query.filter(Grupo.grupo_padre_id == grupo_padre_id)
        if nivel is not None:
            query = query.filter(Grupo.nivel == nivel)
        if codigo_corto is not None:
            query = query.filter(Grupo.codigo_corto == codigo_corto)

        total = query.count()
        grupos = query.order_by(Grupo.nivel, Grupo.nombre).offset(skip).limit(limit).all()

        logger.info(f"[MULTI-TENANT] Usuario {current_user.id} ({rol_nombre}) ve {total} grupos de {len(grupos_ids)} asignados")

    return GrupoListResponse(total=total, grupos=grupos)


@router.get(
    "/raiz",
    response_model=List[GrupoResponse],
    summary="Listar grupos raíz",
    description="Obtiene todos los grupos sin padre (nivel 1)."
)
def list_raiz(
    activos_only: bool = Query(True, description="Solo grupos activos"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """Lista todos los grupos raíz (sin grupo padre)."""
    grupos = crud_grupo.get_grupos_raiz(db, activos_only=activos_only)
    return grupos


@router.get(
    "/mis-grupos",
    response_model=List[GrupoResponse],
    summary="Obtener mis grupos asignados",
    description="Obtiene los grupos a los que el usuario actual tiene acceso."
)
def get_mis_grupos(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """Obtiene los grupos asignados al usuario actual."""
    from app.models.grupo import ResponsableGrupo, Grupo

    # SuperAdmin ve todos los grupos
    if current_user.role.nombre.lower() == "superadmin":
        grupos = db.query(Grupo).filter(Grupo.activo == True).order_by(Grupo.ruta_jerarquica).all()
        return grupos

    # Usuario normal: solo sus grupos asignados
    grupos = (
        db.query(Grupo)
        .join(ResponsableGrupo, Grupo.id == ResponsableGrupo.grupo_id)
        .filter(
            ResponsableGrupo.responsable_id == current_user.id,
            ResponsableGrupo.activo == True,
            Grupo.activo == True
        )
        .order_by(Grupo.ruta_jerarquica)
        .all()
    )

    return grupos


@router.get(
    "/arbol",
    response_model=List[GrupoResponse],
    summary="Obtener árbol jerárquico",
    description="Obtiene el árbol jerárquico completo o desde un grupo específico."
)
def get_arbol(
    grupo_id: Optional[int] = Query(None, description="ID del grupo raíz (None = todo el árbol)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """Obtiene el árbol jerárquico de grupos."""
    grupos = crud_grupo.get_arbol_jerarquico(db, grupo_id=grupo_id)
    return grupos


@router.get(
    "/{grupo_id}",
    response_model=GrupoResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener grupo",
    description="Devuelve los datos completos de un grupo específico."
)
def get_one(
    grupo_id: int,
    include_deleted: bool = Query(False, description="Incluir si está eliminado"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """Obtiene un grupo por su ID."""
    grupo = crud_grupo.get_grupo(db, grupo_id, include_deleted=include_deleted)
    if not grupo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupo {grupo_id} no encontrado"
        )
    return grupo


@router.get(
    "/{grupo_id}/hijos",
    response_model=List[GrupoResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Listar hijos de un grupo",
    description="Obtiene todos los grupos hijos directos de un grupo padre."
)
def get_hijos(
    grupo_id: int,
    activos_only: bool = Query(True, description="Solo grupos activos"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """Lista todos los hijos directos de un grupo."""
    # Verificar que el grupo padre existe
    padre = crud_grupo.get_grupo(db, grupo_id)
    if not padre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupo padre {grupo_id} no encontrado"
        )

    hijos = crud_grupo.get_hijos(db, grupo_id, activos_only=activos_only)
    return hijos


@router.post(
    "/",
    response_model=GrupoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Crear grupo",
    description="Registra un nuevo grupo en el sistema."
)
def create(
    payload: GrupoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin"])),
):
    """Crea un nuevo grupo."""
    try:
        nuevo_grupo = crud_grupo.create_grupo(
            db,
            grupo_data=payload,
            creado_por=current_user.usuario
        )
        logger.info(
            f"Grupo creado: {nuevo_grupo.codigo_corto}",
            extra={"grupo_id": nuevo_grupo.id, "usuario": current_user.usuario}
        )
        return nuevo_grupo
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/{grupo_id}",
    response_model=GrupoResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Actualizar grupo",
    description="Actualiza los datos de un grupo existente."
)
def update(
    grupo_id: int,
    payload: GrupoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin"])),
):
    """Actualiza un grupo existente."""
    try:
        grupo = crud_grupo.update_grupo(
            db,
            grupo_id=grupo_id,
            grupo_data=payload,
            actualizado_por=current_user.usuario
        )
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo {grupo_id} no encontrado"
            )

        logger.info(
            f"Grupo actualizado: {grupo.codigo_corto}",
            extra={"grupo_id": grupo.id, "usuario": current_user.usuario}
        )
        return grupo
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{grupo_id}",
    response_model=GrupoResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Eliminar grupo (soft delete)",
    description="Marca un grupo como eliminado sin borrarlo físicamente."
)
def delete(
    grupo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin"])),
):
    """Realiza soft delete de un grupo."""
    try:
        grupo = crud_grupo.soft_delete_grupo(
            db,
            grupo_id=grupo_id,
            eliminado_por=current_user.usuario
        )
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo {grupo_id} no encontrado"
            )

        logger.warning(
            f"Grupo eliminado (soft delete): {grupo.codigo_corto}",
            extra={"grupo_id": grupo.id, "usuario": current_user.usuario}
        )
        return grupo
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{grupo_id}/restore",
    response_model=GrupoResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Restaurar grupo eliminado",
    description="Restaura un grupo previamente eliminado."
)
def restore(
    grupo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Restaura un grupo eliminado."""
    grupo = crud_grupo.restore_grupo(
        db,
        grupo_id=grupo_id,
        restaurado_por=current_user.usuario
    )
    if not grupo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupo {grupo_id} no encontrado o no está eliminado"
        )

    logger.info(
        f"Grupo restaurado: {grupo.codigo_corto}",
        extra={"grupo_id": grupo.id, "usuario": current_user.usuario}
    )
    return grupo


@router.post(
    "/{grupo_id}/responsables",
    response_model=ResponsableGrupoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Asignar responsable a grupo",
    description="Asigna un usuario responsable a un grupo específico."
)
def asignar_responsable(
    grupo_id: int,
    payload: ResponsableGrupoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin"])),
):
    """Asigna un usuario responsable a un grupo."""
    try:
        asignacion = crud_grupo.asignar_responsable_a_grupo(
            db=db,
            responsable_id=payload.responsable_id,
            grupo_id=grupo_id,
            asignado_por=current_user.usuario,
            activo=payload.activo
        )

        logger.info(
            f"Responsable asignado a grupo",
            extra={
                "responsable_id": payload.responsable_id,
                "grupo_id": grupo_id,
                "usuario": current_user.usuario
            }
        )

        return asignacion
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{grupo_id}/responsables",
    response_model=List[ResponsableGrupoDetalle],
    summary="Listar responsables de un grupo",
    description="Obtiene todos los responsables asignados a un grupo."
)
def listar_responsables(
    grupo_id: int,
    activos_only: bool = Query(True, description="Solo asignaciones activas"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """Lista todos los responsables asignados a un grupo."""
    from app.models.usuario import Usuario
    from app.models.grupo import Grupo

    asignaciones = crud_grupo.listar_responsables_de_grupo(
        db=db,
        grupo_id=grupo_id,
        activos_only=activos_only
    )

    # Enriquecer con datos de usuario y grupo
    resultado = []
    for asignacion in asignaciones:
        usuario = db.query(Usuario).filter(Usuario.id == asignacion.responsable_id).first()
        grupo = db.query(Grupo).filter(Grupo.id == asignacion.grupo_id).first()

        # Obtener rol del usuario
        rol_nombre = None
        if usuario and usuario.role:
            rol_nombre = usuario.role.nombre
        elif usuario and hasattr(usuario, 'rol'):
            rol_nombre = usuario.rol

        resultado.append(ResponsableGrupoDetalle(
            id=asignacion.id,
            responsable_id=asignacion.responsable_id,
            grupo_id=asignacion.grupo_id,
            activo=asignacion.activo,
            asignado_en=asignacion.asignado_en,
            asignado_por=asignacion.asignado_por,
            actualizado_en=asignacion.actualizado_en,
            actualizado_por=asignacion.actualizado_por,
            responsable_usuario=usuario.usuario if usuario else None,
            responsable_nombre=usuario.nombre if usuario else None,
            responsable_email=usuario.email if usuario else None,
            responsable_rol=rol_nombre,
            responsable_area=usuario.area if usuario else None,
            grupo_nombre=grupo.nombre if grupo else None,
            grupo_codigo=grupo.codigo_corto if grupo else None,
            grupo_nivel=grupo.nivel if grupo else None
        ))

    return resultado


@router.delete(
    "/{grupo_id}/responsables/{responsable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
    summary="Remover responsable de grupo",
    description="Desactiva la asignación de un responsable a un grupo."
)
def remover_responsable(
    grupo_id: int,
    responsable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin"])),
):
    """Desactiva la asignación de un responsable a un grupo."""
    success = crud_grupo.remover_responsable_de_grupo(
        db=db,
        responsable_id=responsable_id,
        grupo_id=grupo_id,
        actualizado_por=current_user.usuario
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación no encontrada para responsable {responsable_id} en grupo {grupo_id}"
        )

    logger.info(
        f"Responsable removido de grupo",
        extra={
            "responsable_id": responsable_id,
            "grupo_id": grupo_id,
            "usuario": current_user.usuario
        }
    )


@router.get(
    "/responsables/{responsable_id}/grupos",
    response_model=List[ResponsableGrupoDetalle],
    summary="Listar grupos de un responsable",
    description="Obtiene todos los grupos asignados a un responsable."
)
def listar_grupos_responsable(
    responsable_id: int,
    activos_only: bool = Query(True, description="Solo asignaciones activas"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """Lista todos los grupos asignados a un responsable."""
    from app.models.usuario import Usuario
    from app.models.grupo import Grupo

    asignaciones = crud_grupo.listar_grupos_de_responsable(
        db=db,
        responsable_id=responsable_id,
        activos_only=activos_only
    )

    # Enriquecer con datos de usuario y grupo
    resultado = []
    for asignacion in asignaciones:
        usuario = db.query(Usuario).filter(Usuario.id == asignacion.responsable_id).first()
        grupo = db.query(Grupo).filter(Grupo.id == asignacion.grupo_id).first()

        # Obtener rol del usuario
        rol_nombre = None
        if usuario and usuario.role:
            rol_nombre = usuario.role.nombre
        elif usuario and hasattr(usuario, 'rol'):
            rol_nombre = usuario.rol

        resultado.append(ResponsableGrupoDetalle(
            id=asignacion.id,
            responsable_id=asignacion.responsable_id,
            grupo_id=asignacion.grupo_id,
            activo=asignacion.activo,
            asignado_en=asignacion.asignado_en,
            asignado_por=asignacion.asignado_por,
            actualizado_en=asignacion.actualizado_en,
            actualizado_por=asignacion.actualizado_por,
            responsable_usuario=usuario.usuario if usuario else None,
            responsable_nombre=usuario.nombre if usuario else None,
            responsable_email=usuario.email if usuario else None,
            responsable_rol=rol_nombre,
            responsable_area=usuario.area if usuario else None,
            grupo_nombre=grupo.nombre if grupo else None,
            grupo_codigo=grupo.codigo_corto if grupo else None,
            grupo_nivel=grupo.nivel if grupo else None
        ))

    return resultado


@router.patch(
    "/asignaciones/{asignacion_id}",
    response_model=ResponsableGrupoResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Actualizar estado de asignación",
    description="Activa o desactiva una asignación responsable-grupo."
)
def actualizar_asignacion(
    asignacion_id: int,
    payload: ResponsableGrupoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Actualiza el estado de una asignación."""
    asignacion = crud_grupo.actualizar_estado_asignacion(
        db=db,
        asignacion_id=asignacion_id,
        activo=payload.activo,
        actualizado_por=current_user.usuario
    )

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación {asignacion_id} no encontrada"
        )

    logger.info(
        f"Asignación actualizada",
        extra={
            "asignacion_id": asignacion_id,
            "activo": payload.activo,
            "usuario": current_user.usuario
        }
    )

    return asignacion
