"""Router API para gestión de asignaciones NIT-Usuario."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_usuario, require_role
from app.utils.logger import logger
from app.utils.nit_validator import NitValidator
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.usuario import Usuario
from app.models.proveedor import Proveedor
from app.models.factura import Factura
from app.models.email_config import NitConfiguracion
from app.models.grupo import ResponsableGrupo
from app.services.audit_service import AuditService
from pydantic import BaseModel


router = APIRouter(prefix="/asignacion-nit", tags=["Asignación NIT-Usuario"])


class AsignacionNitCreate(BaseModel):
    """Crear nueva asignación NIT -> Usuario."""
    nit: str
    responsable_id: int
    grupo_id: Optional[int] = None
    nombre_proveedor: Optional[str] = None
    area: Optional[str] = None
    permitir_aprobacion_automatica: bool = True
    requiere_revision_siempre: bool = False


class AsignacionNitUpdate(BaseModel):
    """Actualizar asignación existente."""
    responsable_id: Optional[int] = None
    nombre_proveedor: Optional[str] = None
    area: Optional[str] = None
    permitir_aprobacion_automatica: Optional[bool] = None
    requiere_revision_siempre: Optional[bool] = None
    activo: Optional[bool] = None


class ResponsableSimple(BaseModel):
    """Información básica del usuario."""
    id: int
    usuario: str
    nombre: str
    email: str
    area: Optional[str] = None

    class Config:
        from_attributes = True


class AsignacionNitResponse(BaseModel):
    """Respuesta de asignación con nombre_proveedor calculado desde relación."""
    id: int
    nit: str
    nombre_proveedor: Optional[str] = None
    responsable_id: int
    grupo_id: Optional[int] = None
    area: Optional[str]
    permitir_aprobacion_automatica: bool
    requiere_revision_siempre: bool
    activo: bool
    responsable: Optional[ResponsableSimple] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_asignacion(cls, asignacion: AsignacionNitResponsable, responsable: Optional[Usuario] = None):
        """Factory method que obtiene razon_social desde relación con Proveedor."""
        return cls(
            id=asignacion.id,
            nit=asignacion.nit,
            nombre_proveedor=asignacion.proveedor.razon_social if asignacion.proveedor else f"NIT {asignacion.nit}",
            responsable_id=asignacion.responsable_id,
            grupo_id=asignacion.grupo_id,
            area=asignacion.area,
            permitir_aprobacion_automatica=asignacion.permitir_aprobacion_automatica,
            requiere_revision_siempre=asignacion.requiere_revision_siempre,
            activo=asignacion.activo,
            responsable=ResponsableSimple.from_orm(responsable) if responsable else None
        )


class NitBulkItem(BaseModel):
    """Item individual para creación bulk."""
    nit: str
    nombre_proveedor: str
    area: Optional[str] = None


class AsignacionBulkCreate(BaseModel):
    """Asignar múltiples NITs a un usuario."""
    responsable_id: int
    nits: List[NitBulkItem]
    permitir_aprobacion_automatica: Optional[bool] = True
    activo: Optional[bool] = True


class AsignacionBulkSimple(BaseModel):
    """Asignación bulk simplificada con solo NITs."""
    responsable_id: int
    nits: str
    permitir_aprobacion_automatica: Optional[bool] = True
    activo: Optional[bool] = True


class AsignacionBulkDirect(BaseModel):
    """Asignación bulk directa sin restricciones de existencia previa."""
    responsable_id: int
    nits: str
    permitir_aprobacion_automatica: Optional[bool] = True
    activo: Optional[bool] = True


class AsignacionesPorResponsableResponse(BaseModel):
    """Respuesta agrupada de asignaciones por responsable."""
    responsable_id: int
    responsable: ResponsableSimple
    asignaciones: List[AsignacionNitResponse]
    total: int

    class Config:
        from_attributes = True


def get_grupos_usuario(usuario_id: int, db: Session) -> List[int]:
    """Obtiene los IDs de grupos a los que el usuario tiene acceso."""
    grupos = db.query(ResponsableGrupo.grupo_id).filter(
        ResponsableGrupo.responsable_id == usuario_id,
        ResponsableGrupo.activo == True
    ).all()

    return [g[0] for g in grupos]


def sincronizar_facturas_por_nit(db: Session, nit: str, responsable_id: int, responsable_anterior_id: Optional[int] = None, validar_existencia: bool = False):
    """Actualiza todas las facturas de un NIT para asignarles el usuario correcto."""
    if validar_existencia:
        proveedores_validacion = db.query(Proveedor).filter(
            Proveedor.nit == nit
        ).all()

        if not proveedores_validacion:
            return None

    proveedores = db.query(Proveedor).filter(
        Proveedor.nit == nit
    ).all()

    total_facturas = 0

    for proveedor in proveedores:
        if responsable_anterior_id is not None:
            facturas = db.query(Factura).filter(
                Factura.proveedor_id == proveedor.id,
                Factura.responsable_id == responsable_anterior_id
            ).all()
        else:
            facturas = db.query(Factura).filter(
                Factura.proveedor_id == proveedor.id,
                Factura.responsable_id.is_(None)
            ).all()

        for factura in facturas:
            factura.responsable_id = responsable_id
            total_facturas += 1

    if responsable_anterior_id is not None:
        logger.info(
            f"[PHASE 2] Sincronizadas {total_facturas} facturas para NIT {nit} "
            f"({len(proveedores)} proveedores) -> Reassignment completo: "
            f"Usuario {responsable_anterior_id} → {responsable_id}"
        )
    else:
        logger.info(
            f"Sincronizadas {total_facturas} facturas para NIT {nit} "
            f"({len(proveedores)} proveedores) -> Usuario {responsable_id} (sin asignar)"
        )

    return total_facturas


def desasignar_facturas_por_nit(db: Session, nit: str, responsable_id: int):
    """Desasigna SOLO las facturas del NIT específico para el usuario."""
    es_valido, nit_normalizado = NitValidator.validar_nit(nit)
    if not es_valido:
        logger.warning(f"NIT inválido en desasignación: {nit}")
        return 0

    proveedor = db.query(Proveedor).filter(
        Proveedor.nit == nit_normalizado
    ).first()

    if not proveedor:
        logger.info(f"No existe proveedor con NIT {nit_normalizado}")
        return 0

    otras_asignaciones = db.query(AsignacionNitResponsable).filter(
        and_(
            AsignacionNitResponsable.nit == nit_normalizado,
            AsignacionNitResponsable.activo == True,
            AsignacionNitResponsable.responsable_id != responsable_id
        )
    ).order_by(AsignacionNitResponsable.creado_en.asc()).all()

    if otras_asignaciones:
        nuevo_responsable_id = otras_asignaciones[0].responsable_id
        logger.info(
            f"Encontradas {len(otras_asignaciones)} asignaciones activas para NIT {nit_normalizado}. "
            f"Reasignando facturas a Usuario ID={nuevo_responsable_id}"
        )
    else:
        nuevo_responsable_id = None
        logger.info(f"No hay otras asignaciones activas para NIT {nit_normalizado}. Facturas quedarán sin asignar.")

    facturas = db.query(Factura).filter(
        and_(
            Factura.proveedor_id == proveedor.id,
            Factura.responsable_id == responsable_id
        )
    ).all()

    total_facturas = len(facturas)
    for factura in facturas:
        factura.responsable_id = nuevo_responsable_id

    if nuevo_responsable_id:
        logger.info(
            f"Reasignadas {total_facturas} facturas del NIT {nit_normalizado} "
            f"de Usuario ID={responsable_id} → Usuario ID={nuevo_responsable_id}"
        )
    else:
        logger.info(
            f"Desasignadas {total_facturas} facturas del NIT {nit_normalizado} "
            f"para Usuario ID={responsable_id} → responsable_id = NULL"
        )

    return total_facturas


@router.get("/", response_model=List[AsignacionNitResponse])
def listar_asignaciones_nit(
    skip: int = 0,
    limit: int = 100,
    responsable_id: Optional[int] = Query(None),
    nit: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))
):
    """Lista todas las asignaciones NIT -> Usuario ACTIVAS con filtrado multi-tenant."""
    if current_user.role.nombre.lower() == "superadmin":
        query = db.query(AsignacionNitResponsable).filter(AsignacionNitResponsable.activo == True)
        logger.info(f"[MULTI-TENANT] SuperAdmin {current_user.id} consultando asignaciones (sin filtro)")
    else:
        grupos_ids = get_grupos_usuario(current_user.id, db)

        if not grupos_ids:
            logger.warning(f"[MULTI-TENANT] Admin {current_user.id} sin grupos asignados - retornando lista vacía")
            return []

        responsables_ids = db.query(ResponsableGrupo.responsable_id).filter(
            ResponsableGrupo.grupo_id.in_(grupos_ids),
            ResponsableGrupo.activo == True
        ).distinct().all()
        responsables_ids = [r[0] for r in responsables_ids]

        query = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == True,
            or_(
                AsignacionNitResponsable.grupo_id.in_(grupos_ids),
                AsignacionNitResponsable.grupo_id.is_(None),
                AsignacionNitResponsable.responsable_id.in_(responsables_ids)
            )
        )
        logger.info(f"[MULTI-TENANT] Admin {current_user.id} (grupos: {grupos_ids}, {len(responsables_ids)} responsables) consultando asignaciones (incluye transitivas)")

    if responsable_id is not None:
        query = query.filter(AsignacionNitResponsable.responsable_id == responsable_id)

    # ENTERPRISE: Filtro por NIT con normalización automática usando NitValidator
    # Acepta NITs en cualquier formato y normaliza antes de buscar
    if nit is not None:
        # Normalizar el NIT de búsqueda usando NitValidator
        es_valido, nit_normalizado_busqueda = NitValidator.validar_nit(nit)

        if not es_valido:
            # NIT inválido, retornar lista vacía
            asignaciones = []
        else:
            # Búsqueda exacta con NIT normalizado (todos en BD están normalizados)
            asignaciones = query.filter(
                AsignacionNitResponsable.nit == nit_normalizado_busqueda
            ).offset(skip).limit(limit).all()
    else:
        # Sin filtro de NIT, usar query normal con paginación en DB
        asignaciones = query.offset(skip).limit(limit).all()

    resultado = []
    for asig in asignaciones:
        resultado.append(AsignacionNitResponse.from_asignacion(asig, asig.usuario))

    return resultado


@router.post("/", response_model=AsignacionNitResponse, status_code=status.HTTP_201_CREATED)
def crear_asignacion_nit(
    payload: AsignacionNitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))
):
    """Crea una nueva asignación NIT -> Usuario."""
    from app.utils.nit_validator import NitValidator
    es_valido, nit_normalizado = NitValidator.validar_nit(payload.nit)
    if not es_valido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"NIT inválido: {payload.nit}. {nit_normalizado}"
        )

    from app.models.proveedor import Proveedor
    from app.models.grupo import Grupo

    proveedor = db.query(Proveedor).filter(
        Proveedor.nit == nit_normalizado
    ).first()

    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"NIT {nit_normalizado} no está registrado como proveedor. "
                   f"Debe crear el proveedor primero en la sección 'Proveedores' antes de asignarlo."
        )

    grupo = None
    if payload.grupo_id:
        grupo = db.query(Grupo).filter(Grupo.id == payload.grupo_id).first()
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo/Sede {payload.grupo_id} no encontrado"
            )

    responsable = db.query(Usuario).filter(Usuario.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {payload.responsable_id} no encontrado"
        )

    if payload.grupo_id:
        es_miembro = db.query(ResponsableGrupo).filter(
            ResponsableGrupo.responsable_id == payload.responsable_id,
            ResponsableGrupo.grupo_id == payload.grupo_id,
            ResponsableGrupo.activo == True
        ).first()

        if not es_miembro:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El responsable '{responsable.nombre}' no pertenece al grupo '{grupo.nombre}'. "
                       f"Debe asignar primero el usuario al grupo en 'Grupos y Sedes'."
            )

    existente = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == nit_normalizado,
        AsignacionNitResponsable.responsable_id == payload.responsable_id
    ).first()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El responsable '{responsable.nombre}' ya tiene asignado el NIT {nit_normalizado}. "
                   f"Esta asignación ya existe en el sistema. "
                   f"Para cambiar el usuario, elimine esta asignación primero."
        )

    nueva_asignacion = AsignacionNitResponsable(
        nit=nit_normalizado,
        responsable_id=payload.responsable_id,
        grupo_id=payload.grupo_id,
        area=payload.area or responsable.area,
        permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
        requiere_revision_siempre=payload.requiere_revision_siempre,
        activo=True,
        creado_por=current_user.usuario
    )

    db.add(nueva_asignacion)
    db.flush()

    total_facturas = sincronizar_facturas_por_nit(db, nit_normalizado, payload.responsable_id)

    db.commit()
    db.refresh(nueva_asignacion)

    logger.info(
        f"Asignación NIT CREADA: {nit_normalizado} ({proveedor.razon_social}) -> Usuario {payload.responsable_id} "
        f"(ID={nueva_asignacion.id}, {total_facturas} facturas sincronizadas)"
    )

    return AsignacionNitResponse.from_asignacion(nueva_asignacion, responsable)


@router.put("/{asignacion_id}", response_model=AsignacionNitResponse)
def actualizar_asignacion_nit(
    asignacion_id: int,
    payload: AsignacionNitUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))
):
    """Actualiza una asignación NIT -> Usuario existente."""
    asignacion = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.id == asignacion_id
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación con ID {asignacion_id} no encontrada"
        )

    # Guardar responsable anterior para detectar cambio
    responsable_anterior = asignacion.responsable_id

    # Actualizar campos
    if payload.responsable_id is not None:
        asignacion.responsable_id = payload.responsable_id
    # nombre_proveedor eliminado

    if payload.area is not None:
        asignacion.area = payload.area
    if payload.permitir_aprobacion_automatica is not None:
        asignacion.permitir_aprobacion_automatica = payload.permitir_aprobacion_automatica
    if payload.requiere_revision_siempre is not None:
        asignacion.requiere_revision_siempre = payload.requiere_revision_siempre
    if payload.activo is not None:
        asignacion.activo = payload.activo

    # Si cambió el usuario, sincronizar facturas (PHASE 2: REASSIGNMENT COMPLETO)
    if payload.responsable_id and payload.responsable_id != responsable_anterior:
        total_facturas = sincronizar_facturas_por_nit(
            db,
            asignacion.nit,
            payload.responsable_id,
            responsable_anterior_id=responsable_anterior  # PHASE 2: Pasa responsable anterior para sync completo
        )
        logger.info(
            f"Usuario cambiado: {responsable_anterior} -> {payload.responsable_id}, "
            f"{total_facturas} facturas sincronizadas (PHASE 2: Reassignment completo)"
        )

    db.commit()
    db.refresh(asignacion)

    # Obtener datos completos del usuario
    responsable = db.query(Usuario).filter(Usuario.id == asignacion.responsable_id).first()

    return AsignacionNitResponse.from_asignacion(asignacion, responsable)


@router.delete("/{asignacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asignacion_nit(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))  # Admin y SuperAdmin
):
    """Elimina (marca como inactiva) una asignación NIT -> Usuario."""
    asignacion = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.id == asignacion_id
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación con ID {asignacion_id} no encontrada"
        )

    if not asignacion.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asignación con ID {asignacion_id} ya está inactiva"
        )

    nit = asignacion.nit
    responsable_id = asignacion.responsable_id

    asignacion.activo = False
    asignacion.actualizado_por = current_user.usuario
    asignacion.actualizado_en = datetime.utcnow()

    db.commit()

    logger.info(
        f"Asignación NIT marcada como inactiva (soft delete): "
        f"NIT={nit}, Usuario ID={responsable_id}, ID={asignacion_id}, "
        f"Marcado por={current_user.usuario}"
    )


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_bulk(
    payload: AsignacionBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))
):
    """Asigna múltiples NITs a un usuario de una sola vez."""
    responsable = db.query(Usuario).filter(Usuario.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {payload.responsable_id} no encontrado"
        )

    creadas = 0
    omitidas = 0
    errores = []

    for nit_item in payload.nits:
        try:
            es_valido, nit_normalizado_o_error = NitValidator.validar_nit(nit_item.nit)
            if not es_valido:
                errores.append(f"NIT {nit_item.nit}: {nit_normalizado_o_error}")
                logger.error(f"Error normalizando NIT {nit_item.nit}: {nit_normalizado_o_error}")
                continue

            nit_normalizado = nit_normalizado_o_error

            proveedor = db.query(Proveedor).filter(
                Proveedor.nit == nit_normalizado
            ).first()

            nombre_proveedor_final = proveedor.razon_social if proveedor else nit_item.nombre_proveedor

            existente = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.responsable_id == payload.responsable_id
            ).first()

            if existente:
                omitidas += 1
                logger.debug(f"Asignación ya existe, omitida: NIT {nit_normalizado} -> Usuario {payload.responsable_id}")
                continue

            nueva = AsignacionNitResponsable(
                nit=nit_normalizado,
                responsable_id=payload.responsable_id,
                area=nit_item.area or responsable.area,
                permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
                requiere_revision_siempre=False,
                creado_por=current_user.usuario
            )
            db.add(nueva)
            sincronizar_facturas_por_nit(db, nit_normalizado, payload.responsable_id)
            creadas += 1
            logger.debug(f"Nueva asignación creada: NIT {nit_normalizado} ({nombre_proveedor_final}) -> Usuario {payload.responsable_id}")

        except Exception as e:
            errores.append(f"NIT {nit_item.nit}: {str(e)}")
            logger.error(f"Error procesando NIT {nit_item.nit}: {str(e)}")

    db.commit()

    if creadas > 0 or omitidas > 0:
        logger.info(
            f"Asignación bulk completada: "
            f"{creadas} creadas, {omitidas} omitidas"
            + (f", {len(errores)} errores" if errores else "")
        )

    mensaje_partes = []
    if creadas > 0:
        mensaje_partes.append(f"{creadas} asignación(es) creada(s)")
    if omitidas > 0:
        mensaje_partes.append(f"{omitidas} ya existía(n)")
    if errores:
        mensaje_partes.append(f"{len(errores)} error(es)")

    mensaje = " | ".join(mensaje_partes) if mensaje_partes else "Sin cambios"

    operacion_exitosa = (creadas > 0) or (omitidas > 0 and len(errores) == 0)

    return {
        "success": operacion_exitosa,
        "total_procesados": len(payload.nits),
        "creadas": creadas,
        "omitidas": omitidas,
        "errores": errores,
        "mensaje": mensaje
    }


@router.post("/bulk-simple", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_bulk_simple(
    payload: AsignacionBulkSimple,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))
):
    """Asignación bulk simplificada con validación de proveedores."""
    responsable = db.query(Usuario).filter(
        Usuario.id == payload.responsable_id
    ).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {payload.responsable_id} no encontrado"
        )

    import re
    nits_raw = re.split(r'[,\n\t\r;]', payload.nits)
    nits_procesados_raw = [nit.strip() for nit in nits_raw if nit.strip()]

    if not nits_procesados_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontraron NITs válidos en el texto proporcionado"
        )

    nits_procesados = []
    nits_normalizacion_errores = []

    for nit_raw in nits_procesados_raw:
        es_valido, nit_normalizado_o_error = NitValidator.validar_nit(nit_raw)
        if es_valido:
            nits_procesados.append(nit_normalizado_o_error)
        else:
            nits_normalizacion_errores.append((nit_raw, nit_normalizado_o_error))

    if nits_normalizacion_errores:
        errores_str = "; ".join([f"{nit} ({err})" for nit, err in nits_normalizacion_errores])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Algunos NITs no pudieron ser normalizados: {errores_str}"
        )

    nits_invalidos = []
    for nit_normalizado in nits_procesados:
        proveedor = db.query(Proveedor).filter(
            Proveedor.nit == nit_normalizado
        ).first()

        if not proveedor:
            nits_invalidos.append(nit_normalizado)

    if nits_invalidos:
        nits_invalidos_str = ", ".join(nits_invalidos)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Ninguno de los NITs ingresados está registrado como "
                f"proveedor: {nits_invalidos_str}. "
                "Verifique que los NITs existan en la tabla de proveedores."
            )
        )

    creadas = 0
    omitidas = 0
    errores = []

    for nit_normalizado in nits_procesados:
        try:
            proveedor = db.query(Proveedor).filter(
                Proveedor.nit == nit_normalizado
            ).first()
            nombre_proveedor = (
                proveedor.razon_social if proveedor else f"Proveedor {nit_normalizado}"
            )

            existente = db.query(
                AsignacionNitResponsable
            ).filter(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.responsable_id == (
                    payload.responsable_id
                )
            ).first()

            if existente:
                omitidas += 1
                logger.debug(
                    f"Asignación ya existe: NIT {nit_normalizado}"
                )
                continue

            nueva = AsignacionNitResponsable(
                nit=nit_normalizado,
                responsable_id=payload.responsable_id,
                area=responsable.area,
                permitir_aprobacion_automatica=(
                    payload.permitir_aprobacion_automatica
                ),
                requiere_revision_siempre=False,
                creado_por=current_user.usuario
            )
            db.add(nueva)
            sincronizar_facturas_por_nit(
                db, nit_normalizado, payload.responsable_id
            )
            creadas += 1
            logger.debug(f"Nueva asignación creada: NIT {nit_normalizado}")

        except Exception as e:
            errores.append(f"NIT {nit_normalizado}: {str(e)}")
            logger.error(f"Error procesando NIT {nit_normalizado}: {str(e)}")

    db.commit()

    if creadas > 0 or omitidas > 0:
        logger.info(
            f"Asignación bulk simple completada: "
            f"{creadas} creadas, {omitidas} omitidas"
            + (f", {len(errores)} errores" if errores else "")
        )

    mensaje_partes = []
    if creadas > 0:
        mensaje_partes.append(f"{creadas} creada(s)")
    if omitidas > 0:
        mensaje_partes.append(f"{omitidas} ya existía(n)")
    if errores:
        mensaje_partes.append(f"{len(errores)} error(es)")

    mensaje = " | ".join(mensaje_partes) if mensaje_partes else (
        "Sin cambios"
    )

    operacion_exitosa = (
        (creadas > 0) or
        (omitidas > 0 and len(errores) == 0)
    )

    return {
        "success": operacion_exitosa,
        "total_procesados": len(nits_procesados),
        "creadas": creadas,
        "omitidas": omitidas,
        "errores": errores,
        "mensaje": mensaje
    }


@router.get("/por-responsable/{responsable_id}", response_model=AsignacionesPorResponsableResponse)
def obtener_asignaciones_por_responsable(
    responsable_id: int,
    activo: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))  # Admin y SuperAdmin
):
    """
    Obtiene todas las asignaciones de un usuario específico.
    Retorna estructura agrupada compatible con el frontend.
    """
    # Verificar que el usuario existe
    responsable = db.query(Usuario).filter(Usuario.id == responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {responsable_id} no encontrado"
        )

    # Obtener asignaciones
    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.responsable_id == responsable_id,
        AsignacionNitResponsable.activo == activo
    ).all()

    # Construir lista de asignaciones con responsable
    asignaciones_response = []
    for asig in asignaciones:
        asignaciones_response.append(AsignacionNitResponse.from_asignacion(asig, responsable))

    # Retornar estructura agrupada
    return AsignacionesPorResponsableResponse(
        responsable_id=responsable_id,
        responsable=ResponsableSimple.from_orm(responsable),
        asignaciones=asignaciones_response,
        total=len(asignaciones_response)
    )


# ==================== NUEVO ENDPOINT: Asignación desde nit_configuracion ====================

@router.post("/diagnostico-nits", status_code=status.HTTP_200_OK)
def diagnostico_nits(
    payload: AsignacionBulkSimple,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))
):
    """
    ENDPOINT DE DIAGNÓSTICO - Verifica qué está pasando con los NITs.
    Retorna información detallada sobre cada NIT enviado.
    """
    import re
    nits_raw = re.split(r'[,\n\t\r;]', payload.nits)
    nits_procesados_raw = [nit.strip() for nit in nits_raw if nit.strip()]

    resultado = []
    for nit_raw in nits_procesados_raw:
        es_valido, nit_normalizado_o_error = NitValidator.validar_nit(nit_raw)

        if es_valido:
            # Buscar en nit_configuracion
            nit_config = db.query(NitConfiguracion).filter(
                NitConfiguracion.nit == nit_normalizado_o_error
            ).all()

            resultado.append({
                "nit_original": nit_raw,
                "nit_normalizado": nit_normalizado_o_error,
                "valido": True,
                "en_nit_configuracion": len(nit_config) > 0,
                "registros_en_config": len(nit_config),
                "config_activos": len([x for x in nit_config if x.activo])
            })
        else:
            resultado.append({
                "nit_original": nit_raw,
                "valido": False,
                "error": nit_normalizado_o_error
            })

    return {"nits": resultado, "total": len(resultado)}


@router.post("/bulk-nit-config", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_desde_nit_config(
    payload: AsignacionBulkSimple,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))
):
    """Asigna NITs directamente desde la tabla nit_configuracion."""
    responsable = db.query(Usuario).filter(
        Usuario.id == payload.responsable_id
    ).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {payload.responsable_id} no encontrado"
        )

    import re
    nits_raw = re.split(r'[,\n\t\r;]', payload.nits)
    nits_procesados_raw = [nit.strip() for nit in nits_raw if nit.strip()]

    if not nits_procesados_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontraron NITs válidos en el texto proporcionado"
        )

    nits_procesados = []
    nits_normalizacion_errores = []

    for nit_raw in nits_procesados_raw:
        es_valido, nit_normalizado_o_error = NitValidator.validar_nit(nit_raw)
        if es_valido:
            nits_procesados.append(nit_normalizado_o_error)
        else:
            nits_normalizacion_errores.append((nit_raw, nit_normalizado_o_error))

    if nits_normalizacion_errores:
        errores_str = "; ".join([f"{nit} ({err})" for nit, err in nits_normalizacion_errores])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Algunos NITs no pudieron ser normalizados: {errores_str}"
        )

    nits_invalidos = []
    for nit_normalizado in nits_procesados:
        nit_config = db.query(NitConfiguracion).filter(
            NitConfiguracion.nit == nit_normalizado,
            NitConfiguracion.activo == True
        ).first()

        if not nit_config:
            nits_invalidos.append(nit_normalizado)

    if nits_invalidos:
        nits_invalidos_str = ", ".join(nits_invalidos)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Los siguientes NITs no están configurados en nit_configuracion: "
                f"{nits_invalidos_str}. "
                "Agregúelos a la configuración de extracción de emails primero."
            )
        )

    creadas = 0
    reactivadas = 0
    omitidas = 0
    nits_omitidos = []
    errores = []

    for nit_normalizado in nits_procesados:
        try:
            # Verificar si ya existe la asignación ACTIVA
            asignacion_activa = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.responsable_id == payload.responsable_id,
                AsignacionNitResponsable.activo == True
            ).first()

            if asignacion_activa:
                omitidas += 1
                nits_omitidos.append(nit_normalizado)  # Registrar cuál fue omitido
                continue

            # Verificar si existe una asignación INACTIVA (para reactivar)
            asignacion_inactiva = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.responsable_id == payload.responsable_id,
                AsignacionNitResponsable.activo == False
            ).first()

            if asignacion_inactiva:
                # REACTIVAR la asignación existente
                asignacion_inactiva.activo = True
                asignacion_inactiva.actualizado_por = "BULK_NIT_CONFIG"
                asignacion_inactiva.actualizado_en = datetime.utcnow()
                reactivadas += 1
                continue

            # Obtener nombre del NIT desde nit_configuracion si existe
            nit_config = db.query(NitConfiguracion).filter(
                NitConfiguracion.nit == nit_normalizado
            ).first()
            nombre_proveedor = nit_config.nombre_proveedor if nit_config else None

            # Crear nueva asignación
            nueva_asignacion = AsignacionNitResponsable(
                nit=nit_normalizado,
                responsable_id=payload.responsable_id,
                nombre_proveedor=nombre_proveedor,
                permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
                activo=True,
                creado_por="BULK_NIT_CONFIG",
                creado_en=datetime.utcnow()
            )
            db.add(nueva_asignacion)
            creadas += 1

        except Exception as e:
            logger.error(f"Error asignando NIT {nit_normalizado}: {str(e)}", exc_info=True)
            errores.append({
                "nit": nit_normalizado,
                "error": str(e)
            })

    # Commit con manejo de errores mejorado
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Error en COMMIT de asignaciones: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar asignaciones: {str(e)}"
        )

    # Log de auditoría
    logger.info(
        f"Asignaciones desde nit_configuracion: {creadas} creadas, {reactivadas} reactivadas, "
        f"{omitidas} omitidas, {len(errores)} errores",
        extra={
            "responsable_id": payload.responsable_id,
            "total_nits": len(nits_procesados),
            "creadas": creadas,
            "reactivadas": reactivadas,
            "omitidas": omitidas,
            "errores": len(errores)
        }
    )

    mensaje = (
        f"Se procesaron {len(nits_procesados)} NITs. "
        f"Creadas: {creadas}, Reactivadas: {reactivadas}, Omitidas: {omitidas}, "
        f"Errores: {len(errores)}"
    )

    return {
        "success": len(errores) == 0,
        "total_procesados": len(nits_procesados),
        "creadas": creadas,
        "reactivadas": reactivadas,
        "omitidas": omitidas,
        "nits_omitidos": nits_omitidos,  # Lista de NITs que ya estaban asignados
        "errores": errores,
        "responsable_id": payload.responsable_id,
        "mensaje": mensaje
    }


# ==================== DIAGNOSTIC ENDPOINTS ====================

@router.get("/diagnostico", response_model=dict)
def diagnostico_asignaciones(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))
):
    """
    Endpoint de diagnóstico para verificar la integridad de las asignaciones.
    
    **VERIFICA:**
    - asignaciones_nit_invalido: NITs que no existen en proveedores
    - asignaciones_nit_no_normalizado: NITs en formato incorrecto
    - estadisticas: Estadísticas generales
    - asignaciones_nit_invalido: NITs que no existen en proveedores
    - asignaciones_nit_no_normalizado: NITs en formato incorrecto
    - estadisticas: Estadísticas generales
    
    **Nivel:** Diagnostics
    """
    # PASO 1: Obtener todas las asignaciones activas
    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.activo == True
    ).all()
    
    
    # PASO 2: (Eliminado - nombre_proveedor ya no existe)

    
    # PASO 3: Verificar NITs que no existen en proveedores
    nits_invalidos = []
    for asig in asignaciones:
        proveedor = db.query(Proveedor).filter(
            Proveedor.nit == asig.nit
        ).first()
        
        if not proveedor:
            nits_invalidos.append({
                "id": asig.id,
                "nit": asig.nit,
                # nombre_proveedor eliminado
                "responsable_id": asig.responsable_id
            })
    
    # PASO 4: Verificar NITs no normalizados
    nits_no_normalizados = []
    for asig in asignaciones:
        es_valido, nit_normalizado = NitValidator.validar_nit(asig.nit)
        
        if es_valido and nit_normalizado != asig.nit:
            nits_no_normalizados.append({
                "id": asig.id,
                "nit_actual": asig.nit,
                "nit_normalizado": nit_normalizado,
                "responsable_id": asig.responsable_id
            })
    
    # PASO 5: Estadísticas generales
    total_asignaciones = len(asignaciones)
    total_responsables = len(set(asig.responsable_id for asig in asignaciones))
    total_nits_unicos = len(set(asig.nit for asig in asignaciones))
    
    # PASO 6: Verificar sincronización de facturas
    facturas_sin_asignar = db.query(Factura).filter(
        Factura.responsable_id.is_(None)
    ).count()
    
    return {
        "total_asignaciones": total_asignaciones,
        "total_responsables": total_responsables,
        "total_nits_unicos": total_nits_unicos,
        "asignaciones_sin_nombre": {
            "count": len(sin_nombre),
            "items": sin_nombre
        },
        "asignaciones_nit_invalido": {
            "count": len(nits_invalidos),
            "items": nits_invalidos
        },
        "asignaciones_nit_no_normalizado": {
            "count": len(nits_no_normalizados),
            "items": nits_no_normalizados
        },
        "facturas_sin_asignar": facturas_sin_asignar,
        "estado": "OK" if (len(nits_invalidos) == 0 and len(nits_no_normalizados) == 0) else "ADVERTENCIAS",
        "mensaje": (
            "Todas las asignaciones están correctamente configuradas" 
            if (len(nits_invalidos) == 0 and len(nits_no_normalizados) == 0)
            else f"Se encontraron {len(nits_invalidos)} NITs inválidos, {len(nits_no_normalizados)} NITs no normalizados"
        )
    }


@router.post("/diagnostico/reparar", response_model=dict)
def reparar_asignaciones(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "superadmin"]))
):
    """
    Repara automáticamente problemas comunes en asignaciones.
    
    **REPARACIONES:**
    1. Normaliza NITs al formato correcto
    
    **NO REPARA:**
    - NITs que no existen en proveedores (requiere acción manual)
    
    **Nivel:** Enterprise Production-Ready Auto-Repair
    """
    reparaciones = {
        # nombres_completados eliminado
        "nits_normalizados": 0,
        "errores": []
    }
    
    # PASO 1: Obtener todas las asignaciones activas
    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.activo == True
    ).all()
    
    for asig in asignaciones:
        try:
            # REPARACIÓN 1: (Eliminado - nombre_proveedor ya no existe)

            
            # REPARACIÓN 2: Normalizar NIT
            es_valido, nit_normalizado = NitValidator.validar_nit(asig.nit)
            
            if es_valido and nit_normalizado != asig.nit:
                asig.nit = nit_normalizado
                asig.actualizado_por = current_user.usuario
                asig.actualizado_en = datetime.utcnow()
                reparaciones["nits_normalizados"] += 1
                logger.info(f"NIT normalizado para asignación {asig.id}: {asig.nit} → {nit_normalizado}")
        
        except Exception as e:
            reparaciones["errores"].append({
                "asignacion_id": asig.id,
                "nit": asig.nit,
                "error": str(e)
            })
            logger.error(f" Error reparando asignación {asig.id}: {str(e)}")
    
    # Commit de cambios
    db.commit()
    
    return {
        "success": len(reparaciones["errores"]) == 0,
        "reparaciones": reparaciones,
        "mensaje": (
            f"Reparación completada: "
            f"{reparaciones['nits_normalizados']} NITs normalizados"
            if len(reparaciones["errores"]) == 0
            else f"Reparación con errores: {len(reparaciones['errores'])} errores encontrados"
        )
    }
