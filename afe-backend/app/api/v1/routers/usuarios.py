#app/api/v1/routers/usuarios.py
"""
Router para gestión de Usuarios.

 IMPORTANTE: Algunos endpoints relacionados con usuario-proveedor
fueron movidos a /api/v1/asignacion-nit/*

  NUEVOS ENDPOINTS: Ver /api/v1/asignacion-nit/
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.schemas.common import ErrorResponse
from app.crud.usuario import (
    get_usuario_by_usuario,
    create_usuario,
    update_usuario
)
from app.core.security import get_current_usuario, require_role
from app.utils.logger import logger

router = APIRouter(tags=["Usuarios"])


# ==================== ENDPOINTS DE USUARIOS ====================

@router.post(
    "/",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Crear usuario",
    description="Crea un nuevo usuario en el sistema."
)
def create_usuario_endpoint(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin"])),
):
    """Crea un nuevo usuario"""
    if get_usuario_by_usuario(db, payload.usuario):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario ya existe"
        )

    u = create_usuario(db, payload)
    logger.info("Usuario creado", extra={"id": u.id, "usuario": u.usuario})
    return u


@router.get(
    "/",
    response_model=List[UsuarioRead],
    summary="Listar usuarios",
    description="Obtiene usuarios con sus grupos asignados. SuperAdmin ve todos, Admin solo ve usuarios de su grupo y subgrupos."
)
def list_usuarios(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin", "responsable", "viewer"])),
):
    """
    Lista todos los usuarios con sus grupos asignados (multi-tenant).
    
    Para Admins:
    - Ve usuarios de sus grupos DIRECTOS y todos sus SUBGRUPOS jerárquicos
    - Ejemplo: admin de AVIDANTI ve usuarios de AVIDANTI + CAM + CAI + CASM
    """
    from app.models.usuario import Usuario
    from app.models.grupo import ResponsableGrupo, Grupo
    from sqlalchemy.orm import joinedload

    # SuperAdmin ve todos los usuarios
    if current_user.role.nombre.lower() == "superadmin":
        usuarios = db.query(Usuario).options(
            joinedload(Usuario.grupos).joinedload(ResponsableGrupo.grupo)
        ).all()
        grupo_ids_visibles = None  # SuperAdmin ve todos los grupos
    else:
        # Admin/Responsable/Viewer solo ven usuarios de sus grupos y SUBGRUPOS
        # 1. Obtener los grupos del usuario actual (directos)
        grupos_usuario_actual = db.query(ResponsableGrupo.grupo_id).filter(
            ResponsableGrupo.responsable_id == current_user.id,
            ResponsableGrupo.activo == True
        ).all()
        grupo_ids_directos = [g[0] for g in grupos_usuario_actual]

        if not grupo_ids_directos:
            # Si el usuario no tiene grupos asignados, no ve ningún usuario
            return []

        # 2. Obtener TODOS los subgrupos (descendientes) de los grupos del admin
        grupo_ids_con_subgrupos = set(grupo_ids_directos)  # Empezar con los directos
        
        def agregar_descendientes_recursivos(grupo_padre_id):
            """Obtiene recursivamente todos los descendientes de un grupo"""
            hijos = db.query(Grupo).filter(
                Grupo.grupo_padre_id == grupo_padre_id
            ).all()
            for hijo in hijos:
                grupo_ids_con_subgrupos.add(hijo.id)
                agregar_descendientes_recursivos(hijo.id)
        
        # Aplicar recursión a todos los grupos directos del admin
        for grupo_id in grupo_ids_directos:
            agregar_descendientes_recursivos(grupo_id)
        
        grupo_ids_visibles = list(grupo_ids_con_subgrupos)

        # 3. Obtener todos los usuarios que pertenecen a esos grupos (directos + subgrupos)
        usuarios_ids = db.query(ResponsableGrupo.responsable_id).filter(
            ResponsableGrupo.grupo_id.in_(grupo_ids_visibles),
            ResponsableGrupo.activo == True
        ).distinct().all()
        usuario_ids = [u[0] for u in usuarios_ids]

        # 4. Cargar usuarios filtrados CON TODOS sus grupos (no filtrados aún)
        usuarios = db.query(Usuario).options(
            joinedload(Usuario.grupos).joinedload(ResponsableGrupo.grupo)
        ).filter(Usuario.id.in_(usuario_ids)).all()

    # Transformar para incluir solo grupos activos y visibles
    result = []
    for usuario in usuarios:
        # Filtrar grupos según lo que el usuario puede ver
        grupos_filtrados = []
        for rg in usuario.grupos:
            # Condiciones de visibilidad
            if not (rg.activo and rg.grupo and not rg.grupo.eliminado):
                continue  # Saltar si no está activo o grupo está eliminado
            
            # Si es Admin/Responsable, solo mostrar grupos que puede ver
            if grupo_ids_visibles is not None and rg.grupo_id not in grupo_ids_visibles:
                continue  # Saltar si el grupo no está en su lista visible
            
            grupos_filtrados.append({
                "id": rg.grupo.id,
                "codigo": rg.grupo.codigo_corto,
                "nombre": rg.grupo.nombre
            })
        
        # Solo incluir usuario si tiene al menos un grupo visible
        if not grupos_filtrados and grupo_ids_visibles is not None:
            continue  # No incluir si es Admin y no tiene grupos visibles
        
        usuario_dict = {
            "id": usuario.id,
            "usuario": usuario.usuario,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "area": usuario.area,
            "telefono": usuario.telefono,
            "activo": usuario.activo,
            "must_change_password": usuario.must_change_password,
            "last_login": usuario.last_login,
            "creado_en": usuario.creado_en,
            "role_id": usuario.role_id,
            "role": usuario.role,
            "grupos": grupos_filtrados
        }
        result.append(usuario_dict)

    return result


# ==================== ENDPOINT DE USUARIO ACTUAL ====================
# IMPORTANTE: Este endpoint debe ir ANTES de /{usuario_id} para que FastAPI
# no confunda "/me" con un ID de usuario

@router.get(
    "/me",
    response_model=UsuarioRead,
    summary="Obtener datos del usuario actual",
    description="Retorna los datos actualizados del usuario autenticado desde la base de datos"
)
def get_me(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """
    Obtiene los datos actualizados del usuario actual desde la base de datos.
    Útil para refrescar el perfil sin necesidad de cerrar sesión.
    """
    from app.models.usuario import Usuario
    from app.models.grupo import ResponsableGrupo
    from sqlalchemy.orm import joinedload

    # Consultar usuario actualizado desde la BD con grupos
    usuario_actualizado = db.query(Usuario).options(
        joinedload(Usuario.grupos).joinedload(ResponsableGrupo.grupo)
    ).filter(Usuario.id == current_user.id).first()

    if not usuario_actualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Transformar respuesta para incluir grupos con formato correcto
    usuario_dict = {
        "id": usuario_actualizado.id,
        "usuario": usuario_actualizado.usuario,
        "nombre": usuario_actualizado.nombre,
        "email": usuario_actualizado.email,
        "area": usuario_actualizado.area,
        "telefono": usuario_actualizado.telefono,
        "activo": usuario_actualizado.activo,
        "must_change_password": usuario_actualizado.must_change_password,
        "last_login": usuario_actualizado.last_login,
        "creado_en": usuario_actualizado.creado_en,
        "role_id": usuario_actualizado.role_id,
        "role": usuario_actualizado.role,
        "grupos": [
            {
                "id": rg.grupo.id,
                "codigo": rg.grupo.codigo_corto or rg.grupo.codigo,
                "nombre": rg.grupo.nombre
            }
            for rg in usuario_actualizado.grupos
            if rg.activo and rg.grupo and not rg.grupo.eliminado
        ]
    }

    return usuario_dict


@router.get(
    "/{usuario_id}",
    response_model=UsuarioRead,
    summary="Obtener usuario por ID",
    description="Obtiene un usuario específico por su ID."
)
def get_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "responsable", "viewer"])),
):
    """Obtiene un usuario por ID"""
    from app.models.usuario import Usuario

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {usuario_id} no encontrado"
        )

    return usuario


@router.put(
    "/{usuario_id}",
    response_model=UsuarioRead,
    summary="Actualizar usuario",
    description="Actualiza la información de un usuario."
)
def update_usuario_endpoint(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin"])),
):
    """Actualiza un usuario"""
    try:
        usuario = update_usuario(db, usuario_id, payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {usuario_id} no encontrado"
        )

    logger.info(f"Usuario actualizado: {usuario_id}")

    # Transformar respuesta para incluir grupos con formato correcto
    usuario_dict = {
        "id": usuario.id,
        "usuario": usuario.usuario,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "area": usuario.area,
        "telefono": usuario.telefono,
        "activo": usuario.activo,
        "must_change_password": usuario.must_change_password,
        "last_login": usuario.last_login,
        "creado_en": usuario.creado_en,
        "role_id": usuario.role_id,
        "role": usuario.role,
        "grupos": [
            {
                "id": rg.grupo.id,
                "codigo": rg.grupo.codigo_corto,
                "nombre": rg.grupo.nombre
            }
            for rg in usuario.grupos
            if rg.activo and rg.grupo and not rg.grupo.eliminado
        ]
    }

    return usuario_dict


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario",
    description="Elimina permanentemente un usuario si no tiene datos asociados. Solo SuperAdmin y Admin."
)
def delete_usuario_endpoint(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin"])),  # SuperAdmin y Admin
):
    """Elimina permanentemente un usuario con validaciones de seguridad"""
    from app.models.usuario import Usuario
    from app.models.factura import Factura
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura

    # 1. Verificar que el usuario existe
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {usuario_id} no encontrado"
        )

    # 2. No puede eliminarse a sí mismo
    if usuario_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario"
        )

    # 3. Verificar que no tenga facturas asignadas
    facturas_count = db.query(Factura).filter(Factura.responsable_id == usuario_id).count()
    if facturas_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar: el usuario tiene {facturas_count} factura(s) asignada(s)"
        )

    # 4. Verificar que no tenga workflows de aprobación
    workflows_count = db.query(WorkflowAprobacionFactura).filter(
        (WorkflowAprobacionFactura.responsable_id == usuario_id) |
        (WorkflowAprobacionFactura.aprobada_por == usuario_id) |
        (WorkflowAprobacionFactura.rechazada_por == usuario_id)
    ).count()
    if workflows_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar: el usuario tiene {workflows_count} registro(s) en workflows de aprobación"
        )

    # 5. Eliminar las asignaciones de grupos (tabla ResponsableGrupo)
    from app.models.grupo import ResponsableGrupo
    db.query(ResponsableGrupo).filter(ResponsableGrupo.responsable_id == usuario_id).delete()

    # 6. Eliminar las asignaciones de NIT (tabla AsignacionNitResponsable)
    from app.models.workflow_aprobacion import AsignacionNitResponsable
    db.query(AsignacionNitResponsable).filter(AsignacionNitResponsable.responsable_id == usuario_id).delete()

    # 7. Si pasa todas las validaciones, eliminar permanentemente el usuario
    db.delete(usuario)
    db.commit()

    logger.info(f"Usuario eliminado permanentemente: {usuario_id} ({usuario.usuario})")
    return None


# ==================== ENDPOINT DE DIAGNÓSTICO ====================

@router.get(
    "/me/diagnostico",
    summary="Diagnóstico del usuario actual",
    description="Retorna información de diagnóstico sobre el usuario autenticado y sus asignaciones"
)
def diagnostico_usuario(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """
    Retorna:
    - ID y nombre del usuario actual
    - Total de asignaciones en AsignacionNitResponsable
    - Total de facturas donde responsable_id = current_user.id
    - IDs de proveedores según _obtener_proveedor_ids_de_responsable()
    """
    from app.models.workflow_aprobacion import AsignacionNitResponsable
    from app.models.factura import Factura
    from app.crud.factura import _obtener_proveedor_ids_de_responsable
    from sqlalchemy import func

    # Info del usuario
    usuario_info = {
        "id": current_user.id,
        "usuario": current_user.usuario,
        "nombre": current_user.nombre,
        "rol": current_user.role.nombre if hasattr(current_user, 'role') and current_user.role else None,
    }

    # Asignaciones explícitas en AsignacionNitResponsable
    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.responsable_id == current_user.id,
        AsignacionNitResponsable.activo == True
    ).all()

    asignaciones_info = {
        "total": len(asignaciones),
        "nits": [a.nit for a in asignaciones],
        "proveedores": [a.proveedor.razon_social if a.proveedor else f"NIT {a.nit}" for a in asignaciones]
    }

    # Facturas donde responsable_id = current_user.id
    total_facturas_directas = db.query(func.count(Factura.id)).filter(
        Factura.responsable_id == current_user.id
    ).scalar()

    # Usar la función _obtener_proveedor_ids_de_responsable
    proveedor_ids = _obtener_proveedor_ids_de_responsable(db, current_user.id)

    # Contar facturas de esos proveedores
    facturas_filtradas = db.query(func.count(Factura.id)).filter(
        Factura.proveedor_id.in_(proveedor_ids) if proveedor_ids else None
    ).scalar() if proveedor_ids else 0

    return {
        "usuario": usuario_info,
        "asignaciones_explicitas": asignaciones_info,
        "facturas_donde_responsable_id_es_actual": total_facturas_directas,
        "proveedor_ids_obtenidos": proveedor_ids,
        "facturas_de_esos_proveedores": facturas_filtradas,
        "nota": "Si 'asignaciones_explicitas.total' > 0, se usan esos NITs. Si = 0, se usan facturas_donde_responsable_id_es_actual"
    }


# ==================== ENDPOINTS DE ASIGNACIONES ====================
#  NOTA: Los endpoints de asignación usuario-proveedor fueron
# movidos a /api/v1/asignacion-nit/*
#
# - GET /asignacion-nit/ - Listar asignaciones
# - POST /asignacion-nit/ - Crear asignación
# - PUT /asignacion-nit/{id} - Actualizar asignación
# - DELETE /asignacion-nit/{id} - Eliminar asignación
# - POST /asignacion-nit/bulk - Asignación masiva
# - GET /asignacion-nit/por-responsable/{responsable_id} - Asignaciones por usuario
#
# ==================== FIN DEL ARCHIVO ====================
