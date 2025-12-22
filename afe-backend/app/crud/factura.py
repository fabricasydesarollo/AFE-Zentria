#app/crud/factura.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import and_, func, desc, or_, distinct
from datetime import datetime, date

from app.models.factura import Factura, EstadoFactura
from app.models.proveedor import Proveedor
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.utils.nit_validator import NitValidator


# ==================== ENTERPRISE HELPERS ====================


def _obtener_factura_ids_de_responsable(
    db: Session, responsable_id: int, usar_workflow: bool = True
) -> List[int]:
    """
    Obtiene los IDs de facturas que están asignadas al usuario.

    ENTERPRISE PATTERN (MULTI-RESPONSABLE SUPPORT):
    - Con usar_workflow=True (default): Usa WorkflowAprobacionFactura (recomendado)
      * Refleja la nueva arquitectura multi-responsable
      * Un responsable ve una factura si tiene un workflow para ella
      * Soporta múltiples usuarios por NIT correctamente

    - Con usar_workflow=False: Fallback a búsqueda por NITs asignados (legacy)
      * Mantiene compatibilidad con sistema anterior
      * Busca por AsignacionNitResponsable

    Args:
        db: Sesión de base de datos
        responsable_id: ID del usuario
        usar_workflow: Si True, usa WorkflowAprobacionFactura (default). Si False, usa NITs.

    Returns:
        Lista de factura_ids asignadas al usuario
    """
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura

    if usar_workflow:
        # NUEVO (Arquitectura multi-responsable): Filtrar por WorkflowAprobacionFactura
        # Una factura es "visible" para un usuario si tiene un workflow para ella
        workflow_factura_ids = db.query(
            distinct(WorkflowAprobacionFactura.factura_id)
        ).filter(
            WorkflowAprobacionFactura.responsable_id == responsable_id
        ).all()

        factura_ids = [fid for (fid,) in workflow_factura_ids]

        if factura_ids:
            return factura_ids

        # Fallback a búsqueda por NITs si no hay workflows (migración gradual)
        return _obtener_factura_ids_por_nits(db, responsable_id)
    else:
        # FALLBACK (Legacy): Filtrar por NITs asignados
        return _obtener_factura_ids_por_nits(db, responsable_id)


def _obtener_factura_ids_por_nits(db: Session, responsable_id: int) -> List[int]:
    """
    Obtiene factura IDs basadas en los NITs asignados al usuario.

    Versión legacy para compatibilidad durante migración.

    Returns:
        Lista de factura_ids cuyos proveedores tienen NITs asignados al usuario
    """
    # Obtener NITs asignados al usuario (YA están normalizados en BD)
    asignaciones = db.query(AsignacionNitResponsable.nit).filter(
        AsignacionNitResponsable.responsable_id == responsable_id,
        AsignacionNitResponsable.activo == True
    ).all()

    nits_asignados = [nit for (nit,) in asignaciones if nit]

    if not nits_asignados:
        return []

    # Obtener IDs de proveedores con esos NITs
    proveedor_ids = db.query(Proveedor.id).filter(
        Proveedor.nit.in_(nits_asignados)
    ).all()
    proveedor_ids_list = [prov_id for (prov_id,) in proveedor_ids]

    if not proveedor_ids_list:
        return []

    # Obtener facturas de esos proveedores
    factura_ids = db.query(distinct(Factura.id)).filter(
        Factura.proveedor_id.in_(proveedor_ids_list)
    ).all()

    return [fid for (fid,) in factura_ids]


def _obtener_proveedor_ids_de_responsable(db: Session, responsable_id: int) -> List[int]:
    """
    Obtiene los IDs de proveedores cuyos NITs están asignados al usuario.

    ENTERPRISE PATTERN (OPTIMIZED):
    - Busca NITs asignados explícitamente en AsignacionNitResponsable
    - Si no hay asignaciones, retorna todos los proveedores (fallback para compatibilidad)
    - Compatible con MySQL/PostgreSQL

    Returns:
        Lista de proveedor_ids que coinciden con los NITs asignados
    """
    # Obtener NITs asignados al usuario (YA están normalizados en BD)
    asignaciones = db.query(AsignacionNitResponsable.nit).filter(
        AsignacionNitResponsable.responsable_id == responsable_id,
        AsignacionNitResponsable.activo == True
    ).all()

    nits_asignados = [nit for (nit,) in asignaciones if nit]

    # Si hay asignaciones explícitas, filtrar por ellas
    if nits_asignados:
        # Búsqueda directa: todos los NITs están normalizados en BD
        proveedor_ids = db.query(Proveedor.id).filter(
            Proveedor.nit.in_(nits_asignados)
        ).all()
        return [prov_id for (prov_id,) in proveedor_ids]

    # Si NO hay asignaciones explícitas, usar las facturas asignadas al usuario
    # Esta es una fallback para soportar ambos modelos:
    # - Modelo 1: NITs asignados explícitamente en AsignacionNitResponsable
    # - Modelo 2: Facturas asignadas directamente al usuario en Factura.responsable_id
    facturas_del_responsable = db.query(distinct(Factura.proveedor_id)).filter(
        Factura.responsable_id == responsable_id,
        Factura.proveedor_id.isnot(None)
    ).all()

    return [prov_id for (prov_id,) in facturas_del_responsable]


def obtener_usuarios_de_nit(db: Session, nit: str) -> List:
    """
    Obtiene TODOS los usuarios asignados a un NIT (con normalización automática).

    ENTERPRISE PATTERN:
    - Acepta NITs en cualquier formato (con/sin DV, con/sin puntos)
    - Normaliza automáticamente usando NitValidator
    - Búsqueda directa en BD (todos los NITs están normalizados)

    Args:
        db: Sesión de base de datos
        nit: NIT del proveedor (cualquier formato, se normaliza automáticamente)

    Returns:
        Lista de objetos Usuario asignados a ese NIT
    """
    from app.models.usuario import Usuario

    if not nit:
        return []

    # Normalizar el NIT buscado usando NitValidator
    es_valido, nit_normalizado = NitValidator.validar_nit(nit)

    if not es_valido:
        # NIT inválido, retornar lista vacía
        return []

    # Obtener todas las asignaciones activas con ese NIT normalizado
    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == nit_normalizado,
        AsignacionNitResponsable.activo == True
    ).all()

    if not asignaciones:
        return []

    # Obtener los IDs únicos de usuarios
    responsable_ids = [asig.responsable_id for asig in asignaciones]

    # Obtener los objetos Usuario completos
    usuarios = db.query(Usuario).filter(
        Usuario.id.in_(responsable_ids)
    ).all()

    return usuarios


# -----------------------------------------------------
# Obtener factura por ID
# -----------------------------------------------------
def get_factura(db: Session, factura_id: int) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.id == factura_id).first()


# -----------------------------------------------------
# Contar facturas totales (para paginación)
# -----------------------------------------------------
def count_facturas(
    db: Session,
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
    responsable_id: Optional[int] = None,
    mes: Optional[int] = None,
    año: Optional[int] = None,
) -> int:
    """
    Cuenta el total de facturas que coinciden con los filtros.

    ENTERPRISE: Si se filtra por responsable_id:
    - Filtra directamente por responsable_id en la factura (responsable asignado)
    - Una factura es "asignada" si tiene responsable_id = current_user.id
    """
    from sqlalchemy import extract

    # Filtrar por facturas asignadas al usuario
    # Filtrar directamente por responsable_id en la factura
    query = db.query(func.count(Factura.id))

    if responsable_id:
        query = query.filter(Factura.responsable_id == responsable_id)

    if nit:
        query = query.join(Proveedor).filter(Proveedor.nit == nit)

    if numero_factura:
        query = query.filter(Factura.numero_factura == numero_factura)

    # Filtrar por mes y año actual si se especifica
    if mes is not None and año is not None:
        query = query.filter(
            extract('month', Factura.creado_en) == mes,
            extract('year', Factura.creado_en) == año
        )

    return query.scalar()


# -----------------------------------------------------
# Listar facturas (con filtros opcionales)
# -----------------------------------------------------
def list_facturas(
    db: Session,
    skip: int = 0,
    limit: int = 500,
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
    responsable_id: Optional[int] = None,
    mes: Optional[int] = None,
    año: Optional[int] = None,
) -> List[Factura]:
    """
    Lista facturas con orden cronológico empresarial.

    ENTERPRISE (MULTI-RESPONSABLE): Si se filtra por responsable_id:
    - NUEVO: Filtra por WorkflowAprobacionFactura (arquitectura multi-responsable)
      * Un responsable ve una factura si tiene un workflow para ella
      * Soporta correctamente múltiples usuarios por NIT
    - FALLBACK: Si no hay workflows, usa búsqueda por NITs (migración gradual)

    Esto garantiza que "Facturas Asignadas" muestra solo las facturas del usuario,
    incluso cuando un NIT está compartido entre múltiples usuarios.
    """
    from sqlalchemy.orm import joinedload, selectinload
    from sqlalchemy import extract

    query = db.query(Factura).options(
        joinedload(Factura.proveedor),
        joinedload(Factura.usuario),
        selectinload(Factura.workflow_history)
    )

    # ENTERPRISE: Filtrar por facturas asignadas al usuario
    # Filtrar directamente por responsable_id en la factura
    if responsable_id:
        query = query.filter(Factura.responsable_id == responsable_id)

    if nit:
        query = query.join(Proveedor).filter(Proveedor.nit == nit)

    if numero_factura:
        query = query.filter(Factura.numero_factura == numero_factura)

    # Filtrar por mes y año actual si se especifica
    if mes is not None and año is not None:
        query = query.filter(
            extract('month', Factura.creado_en) == mes,
            extract('year', Factura.creado_en) == año
        )

    # Orden cronológico empresarial: más recientes primero
    return query.order_by(
        desc(Factura.fecha_emision),
        desc(Factura.id)
    ).offset(skip).limit(limit).all()


# CURSOR-BASED PAGINATION (Para grandes volúmenes) ✨

def list_facturas_cursor(
    db: Session,
    limit: int = 500,
    cursor_timestamp: Optional[datetime] = None,
    cursor_id: Optional[int] = None,
    direction: str = "next",  # "next" o "prev"
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
    responsable_id: Optional[int] = None,
    grupo_id: Optional[int] = None,
    grupos_ids: Optional[List[int]] = None,
) -> Tuple[List[Factura], bool]:
    """
    Lista facturas usando cursor-based pagination para escalabilidad empresarial.

    Este método es O(1) constante independiente del tamaño del dataset.
    Perfecto para scroll infinito y datasets de 10k+ registros.

    ENTERPRISE (MULTI-RESPONSABLE): Si se filtra por responsable_id:
    - NUEVO: Filtra por WorkflowAprobacionFactura (arquitectura multi-responsable)
      * Un responsable ve una factura si tiene un workflow para ella
      * Soporta correctamente múltiples usuarios por NIT

    MULTI-TENANT: Soporta filtrado por grupo
    - grupo_id: Filtra por un grupo específico
    - grupos_ids: Filtra por lista de grupos (para usuarios con múltiples grupos)

    Args:
        db: Sesión de base de datos
        limit: Máximo de registros a retornar (default: 500)
        cursor_timestamp: Fecha del último registro visto
        cursor_id: ID del último registro visto
        direction: "next" para adelante, "prev" para atrás
        nit: Filtro opcional por NIT
        numero_factura: Filtro opcional por número
        responsable_id: Filtro por responsable (permisos)
        grupo_id: Filtro por grupo específico (multi-tenant)
        grupos_ids: Filtro por lista de grupos (multi-tenant)

    Returns:
        Tupla (facturas, has_more)
    """
    from sqlalchemy.orm import joinedload, selectinload

    # Cargar relaciones con joinedload/selectinload para poblar campos calculados en el schema
    query = db.query(Factura).options(
        joinedload(Factura.proveedor),
        joinedload(Factura.usuario),
        selectinload(Factura.workflow_history)  # Compatible con viewonly=True
    )

    # ENTERPRISE: Filtrar por facturas asignadas al usuario (via workflows)
    if responsable_id:
        factura_ids = _obtener_factura_ids_de_responsable(db, responsable_id, usar_workflow=True)

        if not factura_ids:
            return [], False  # Sin facturas asignadas

        # Filtrar por IDs de facturas
        query = query.filter(Factura.id.in_(factura_ids))

    if nit:
        query = query.join(Proveedor).filter(Proveedor.nit == nit)

    if numero_factura:
        query = query.filter(Factura.numero_factura == numero_factura)

    # MULTI-TENANT: Filtrar por grupo
    if grupo_id:
        query = query.filter(Factura.grupo_id == grupo_id)
    elif grupos_ids:
        query = query.filter(Factura.grupo_id.in_(grupos_ids))

    # Aplicar cursor para navegación
    if cursor_timestamp and cursor_id:
        if direction == "next":
            # Obtener registros DESPUÉS del cursor
            query = query.filter(
                or_(
                    Factura.fecha_emision < cursor_timestamp,
                    and_(
                        Factura.fecha_emision == cursor_timestamp,
                        Factura.id < cursor_id
                    )
                )
            )
        else:  # prev
            # Obtener registros ANTES del cursor
            query = query.filter(
                or_(
                    Factura.fecha_emision > cursor_timestamp,
                    and_(
                        Factura.fecha_emision == cursor_timestamp,
                        Factura.id > cursor_id
                    )
                )
            )

    # Ordenar (siempre más recientes primero)
    if direction == "prev":
        # Para navegación hacia atrás, invertir orden temporalmente
        query = query.order_by(
            Factura.fecha_emision.asc(),
            Factura.id.asc()
        )
    else:
        query = query.order_by(
            desc(Factura.fecha_emision),
            desc(Factura.id)
        )

    # Traer limit + 1 para saber si hay más
    facturas = query.limit(limit + 1).all()

    # Detectar si hay más registros
    has_more = len(facturas) > limit

    # Retornar solo los primeros 'limit' registros
    result_facturas = facturas[:limit]

    # Si es navegación hacia atrás, revertir el orden al original
    if direction == "prev":
        result_facturas = list(reversed(result_facturas))

    return result_facturas, has_more


# ENDPOINT PARA DASHBOARD EMPRESARIAL - SIN LÍMITES ✨
# -----------------------------------------------------
# Obtener TODAS las facturas (Solo para admins con dashboard completo)
# -----------------------------------------------------
def list_all_facturas_for_dashboard(
    db: Session,
    responsable_id: Optional[int] = None,
) -> List[Factura]:
    """
    **ENDPOINT EMPRESARIAL PARA DASHBOARDS**

    Retorna TODAS las facturas sin límites de paginación.

    ENTERPRISE (MULTI-RESPONSABLE): Si se filtra por responsable_id:
    - NUEVO: Filtra por WorkflowAprobacionFactura (arquitectura multi-responsable)
      * Un responsable ve una factura si tiene un workflow para ella
      * Soporta correctamente múltiples usuarios por NIT
    - FALLBACK: Si no hay workflows, usa búsqueda por NITs (migración gradual)
    """
    from sqlalchemy.orm import joinedload, selectinload

    query = db.query(Factura).options(
        joinedload(Factura.proveedor),
        joinedload(Factura.usuario),
        selectinload(Factura.workflow_history)
    )

    # ENTERPRISE: Filtrar por facturas asignadas al usuario (via workflows)
    if responsable_id:
        factura_ids = _obtener_factura_ids_de_responsable(db, responsable_id, usar_workflow=True)

        if not factura_ids:
            return []  # Sin facturas asignadas

        # Filtrar por IDs de facturas
        query = query.filter(Factura.id.in_(factura_ids))

    # Orden cronológico empresarial: más recientes primero
    return query.order_by(
        desc(Factura.fecha_emision),
        desc(Factura.id)
    ).all()


# -----------------------------------------------------
# Buscar por CUFE
# -----------------------------------------------------
def find_by_cufe(db: Session, cufe: str) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.cufe == cufe).first()


# -----------------------------------------------------
# Buscar por número de factura
# -----------------------------------------------------
def get_factura_by_numero(db: Session, numero_factura: str) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.numero_factura == numero_factura).first()


# -----------------------------------------------------
# Buscar por número de factura y proveedor
# -----------------------------------------------------
def find_by_numero_proveedor(db: Session, numero: str, proveedor_id: int) -> Optional[Factura]:
    return (
        db.query(Factura)
        .filter(
            and_(
                Factura.numero_factura == numero,
                Factura.proveedor_id == proveedor_id
            )
        )
        .first()
    )


# -----------------------------------------------------
# Crear factura
# -----------------------------------------------------
def create_factura(db: Session, data: dict) -> Factura:
    obj = Factura(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# -----------------------------------------------------
# Actualizar factura
# -----------------------------------------------------
def update_factura(db: Session, factura: Factura, fields: dict) -> Factura:
    for k, v in fields.items():
        setattr(factura, k, v)
    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura


# ============================================================================
# FUNCIONES PARA AUTOMATIZACIÓN DE FACTURAS RECURRENTES (Refactorizadas)
# ============================================================================
# NOTA: Las funciones basadas en conceptos se eliminaron porque esos campos
# ya no existen en la tabla facturas. Usar factura_items en su lugar.
# ============================================================================


# -----------------------------------------------------
# Obtener facturas pendientes para procesamiento automático
# -----------------------------------------------------
def get_facturas_pendientes_procesamiento(db: Session, limit: int = 50) -> List[Factura]:
    """
    Obtiene facturas en estado 'pendiente' que aún no han sido procesadas
    por el sistema de automatización
    """
    return (
        db.query(Factura)
        .filter(
            and_(
                Factura.estado == EstadoFactura.en_revision,
                Factura.fecha_procesamiento_auto.is_(None)
            )
        )
        .order_by(Factura.creado_en.asc())  # Procesar las más antiguas primero
        .limit(limit)
        .all()
    )


# -----------------------------------------------------
# Marcar factura como procesada automáticamente
# -----------------------------------------------------
def marcar_como_procesada_automaticamente(
    db: Session,
    factura: Factura,
    decision_data: dict
) -> Factura:
    """
    Actualiza una factura con los resultados del procesamiento automático
    """
    from datetime import datetime
    
    campos_actualizacion = {
        "patron_recurrencia": decision_data.get("patron_recurrencia"),
        "confianza_automatica": decision_data.get("confianza"),
        "factura_referencia_id": decision_data.get("factura_referencia_id"),
        "motivo_decision": decision_data.get("motivo_decision"),
        "procesamiento_info": decision_data.get("procesamiento_info", {}),
        "fecha_procesamiento_auto": datetime.utcnow(),
        "version_algoritmo": decision_data.get("version_algoritmo", "1.0")
    }
    
    # Solo actualizar estado si se recomienda aprobación automática
    if decision_data.get("estado_sugerido") == "aprobada_auto":
        campos_actualizacion["estado"] = "aprobada_auto"
        campos_actualizacion["aprobada_automaticamente"] = True
    elif decision_data.get("estado_sugerido") == "en_revision":
        campos_actualizacion["estado"] = "en_revision"
    
    return update_factura(db, factura, campos_actualizacion)


# -----------------------------------------------------
# Obtener facturas procesadas automáticamente
# -----------------------------------------------------
def get_facturas_procesadas_automaticamente(
    db: Session,
    fecha_desde: Optional[object] = None,
    estado: Optional[str] = None,
    proveedor_id: Optional[int] = None,
    limit: int = 100
) -> List[Factura]:
    """
    Obtiene facturas que han sido procesadas por el sistema automático
    """
    from datetime import datetime
    
    query = db.query(Factura).filter(
        Factura.fecha_procesamiento_auto.isnot(None)
    )
    
    if fecha_desde:
        query = query.filter(Factura.fecha_procesamiento_auto >= fecha_desde)
    
    if estado:
        query = query.filter(Factura.estado == estado)
        
    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)
    
    return (
        query
        .order_by(Factura.fecha_procesamiento_auto.desc())
        .limit(limit)
        .all()
    )


# -----------------------------------------------------
# Obtener facturas por proveedor y rango de fechas
# -----------------------------------------------------
def get_facturas_by_proveedor_fecha(
    db: Session,
    proveedor_id: int,
    fecha_desde: object,
    fecha_hasta: Optional[object] = None,
    limit: int = 200
) -> List[Factura]:
    """
    Obtiene facturas de un proveedor específico en un rango de fechas
    """
    from datetime import datetime
    
    query = db.query(Factura).filter(
        and_(
            Factura.proveedor_id == proveedor_id,
            Factura.fecha_emision >= fecha_desde
        )
    )
    
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)
    
    return (
        query
        .order_by(Factura.fecha_emision.desc())
        .limit(limit)
        .all()
    )


# FUNCIONES PARA CLASIFICACIÓN POR PERÍODOS MENSUALES ✨

# -----------------------------------------------------
# Obtener resumen de facturas agrupadas por mes
# -----------------------------------------------------
def get_facturas_resumen_por_mes(
    db: Session,
    año: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene un resumen de facturas agrupadas por mes/año con totales.
    Ahora calcula año/mes desde fecha_emision (campos eliminados de BD).

    Returns:
        Lista de diccionarios con: periodo, año, mes, total_facturas, monto_total
    """
    from sqlalchemy import extract

    query = db.query(
        extract('year', Factura.fecha_emision).label('año'),
        extract('month', Factura.fecha_emision).label('mes'),
        func.count(Factura.id).label('total_facturas'),
        func.sum(Factura.total_a_pagar).label('monto_total'),
        func.sum(Factura.subtotal).label('subtotal_total'),
        func.sum(Factura.iva).label('iva_total')
    ).filter(Factura.fecha_emision.isnot(None))

    if año:
        query = query.filter(extract('year', Factura.fecha_emision) == año)

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    if estado:
        query = query.filter(Factura.estado == estado)

    result = query.group_by(
        extract('year', Factura.fecha_emision),
        extract('month', Factura.fecha_emision)
    ).order_by(
        desc('año'),
        desc('mes')
    ).all()

    return [
        {
            "periodo": f"{int(row.año)}-{int(row.mes):02d}",
            "año": int(row.año),
            "mes": int(row.mes),
            "total_facturas": row.total_facturas,
            "monto_total": float(row.monto_total) if row.monto_total else 0.0,
            "subtotal_total": float(row.subtotal_total) if row.subtotal_total else 0.0,
            "iva_total": float(row.iva_total) if row.iva_total else 0.0
        }
        for row in result
    ]


# =====================================================
# NUEVO: Obtener resumen DETALLADO con desglose por estado
# =====================================================
def get_facturas_resumen_por_mes_detallado(
    db: Session,
    año: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    grupo_id_filter: Optional[int | List[int]] = None,
    responsable_id_filter: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene un resumen DETALLADO de facturas agrupadas por mes/año CON DESGLOSE POR ESTADO.

    IMPORTANTE: Agrupa por creado_en (fecha de creación en sistema) para coincidir con
    el dashboard mes actual que también usa creado_en.

    **MULTI-TENANT:**
    - grupo_id_filter: Filtra por grupo (puede ser int único o lista de grupos)
    - responsable_id_filter: Filtra por responsable (accion_por)

    Retorna para cada mes:
    - Total facturas y montos globales
    - Desglose por estado: en_revision, aprobada, aprobada_auto, rechazada

    Ideal para dashboards que necesitan visualizar distribución de estados.

    Returns:
        Lista de diccionarios con: periodo, año, mes, total_facturas, monto_total, facturas_por_estado{}
    """
    from sqlalchemy import extract

    # Obtener todos los períodos (año/mes) - CORREGIDO: usar creado_en para coincidir con dashboard
    periodos_query = db.query(
        extract('year', Factura.creado_en).label('año'),
        extract('month', Factura.creado_en).label('mes'),
    ).filter(Factura.creado_en.isnot(None))

    # Aplicar filtro de grupo para períodos
    if grupo_id_filter is not None:
        if isinstance(grupo_id_filter, list):
            periodos_query = periodos_query.filter(Factura.grupo_id.in_(grupo_id_filter))
        else:
            periodos_query = periodos_query.filter(Factura.grupo_id == grupo_id_filter)

    # Aplicar filtro de responsable para períodos
    if responsable_id_filter is not None:
        periodos_query = periodos_query.filter(Factura.accion_por == str(responsable_id_filter))

    periodos_query = periodos_query.distinct()

    if año:
        periodos_query = periodos_query.filter(extract('year', Factura.creado_en) == año)

    periodos = periodos_query.order_by(desc('año'), desc('mes')).all()

    result_detallado = []

    for período_año, período_mes in periodos:
        # Query base para este período - CORREGIDO: usar creado_en para coincidir con dashboard
        base_query = db.query(Factura).filter(
            extract('year', Factura.creado_en) == período_año,
            extract('month', Factura.creado_en) == período_mes
        )

        # Aplicar filtro de grupo
        if grupo_id_filter is not None:
            if isinstance(grupo_id_filter, list):
                base_query = base_query.filter(Factura.grupo_id.in_(grupo_id_filter))
            else:
                base_query = base_query.filter(Factura.grupo_id == grupo_id_filter)

        # Aplicar filtro de responsable
        if responsable_id_filter is not None:
            base_query = base_query.filter(Factura.accion_por == str(responsable_id_filter))

        if proveedor_id:
            base_query = base_query.filter(Factura.proveedor_id == proveedor_id)

        # Contar por estado
        en_revision = base_query.filter(Factura.estado == EstadoFactura.en_revision).count()
        aprobada = base_query.filter(Factura.estado == EstadoFactura.aprobada).count()
        aprobada_auto = base_query.filter(Factura.estado == EstadoFactura.aprobada_auto).count()
        rechazada = base_query.filter(Factura.estado == EstadoFactura.rechazada).count()

        # Totales globales
        total_facturas = base_query.count()

        if total_facturas > 0:  # Solo incluir períodos con datos
            monto_total = base_query.with_entities(func.sum(Factura.total_a_pagar)).scalar() or 0.0
            subtotal_total = base_query.with_entities(func.sum(Factura.subtotal)).scalar() or 0.0
            iva_total = base_query.with_entities(func.sum(Factura.iva)).scalar() or 0.0

            result_detallado.append({
                "periodo": f"{int(período_año)}-{int(período_mes):02d}",
                "año": int(período_año),
                "mes": int(período_mes),
                "total_facturas": total_facturas,
                "monto_total": float(monto_total),
                "subtotal_total": float(subtotal_total),
                "iva_total": float(iva_total),
                "facturas_por_estado": {
                    "en_revision": en_revision,
                    "aprobada": aprobada,
                    "aprobada_auto": aprobada_auto,
                    "rechazada": rechazada
                }
            })

    return result_detallado


# -----------------------------------------------------
# Obtener facturas de un período específico
# -----------------------------------------------------
def get_facturas_por_periodo(
    db: Session,
    periodo: str,  # formato: "YYYY-MM"
    skip: int = 0,
    limit: int = 100,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None
) -> List[Factura]:
    """
    Obtiene facturas de un período específico (mes/año).
    Ahora filtra por fecha_emision (periodo_factura eliminado de BD).

    Args:
        periodo: Período en formato "YYYY-MM" (ej: "2025-07")
    """
    from sqlalchemy import extract

    # Parsear periodo "YYYY-MM"
    año, mes = map(int, periodo.split('-'))

    query = db.query(Factura).filter(
        extract('year', Factura.fecha_emision) == año,
        extract('month', Factura.fecha_emision) == mes
    )

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    if estado:
        query = query.filter(Factura.estado == estado)

    return query.order_by(Factura.fecha_emision.desc()).offset(skip).limit(limit).all()


# -----------------------------------------------------
# Contar facturas por período
# -----------------------------------------------------
def count_facturas_por_periodo(
    db: Session,
    periodo: str,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None
) -> int:
    """
    Cuenta facturas de un período específico.
    Ahora usa fecha_emision (periodo_factura eliminado de BD).
    """
    from sqlalchemy import extract

    # Parsear periodo "YYYY-MM"
    año, mes = map(int, periodo.split('-'))

    query = db.query(func.count(Factura.id)).filter(
        extract('year', Factura.fecha_emision) == año,
        extract('month', Factura.fecha_emision) == mes
    )

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    if estado:
        query = query.filter(Factura.estado == estado)

    return query.scalar()


# -----------------------------------------------------
# Obtener estadísticas por período
# -----------------------------------------------------
def get_estadisticas_periodo(
    db: Session,
    periodo: str,
    proveedor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Obtiene estadísticas detalladas de un período específico.
    Ahora usa fecha_emision (periodo_factura eliminado de BD).
    """
    from sqlalchemy import extract

    # Parsear periodo "YYYY-MM"
    año, mes = map(int, periodo.split('-'))

    # Filtros base
    periodo_filter = and_(
        extract('year', Factura.fecha_emision) == año,
        extract('month', Factura.fecha_emision) == mes
    )

    query = db.query(Factura).filter(periodo_filter)

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    # Estadísticas por estado
    stats_by_estado = db.query(
        Factura.estado,
        func.count(Factura.id).label('cantidad'),
        func.sum(Factura.total_a_pagar).label('monto')
    ).filter(periodo_filter)

    if proveedor_id:
        stats_by_estado = stats_by_estado.filter(Factura.proveedor_id == proveedor_id)

    stats_by_estado = stats_by_estado.group_by(Factura.estado).all()

    # Totales generales
    totales = db.query(
        func.count(Factura.id).label('total_facturas'),
        func.sum(Factura.total_a_pagar).label('monto_total'),
        func.sum(Factura.subtotal).label('subtotal'),
        func.sum(Factura.iva).label('iva'),
        func.avg(Factura.total_a_pagar).label('promedio')
    ).filter(periodo_filter)

    if proveedor_id:
        totales = totales.filter(Factura.proveedor_id == proveedor_id)

    totales = totales.first()

    return {
        "periodo": periodo,
        "total_facturas": totales.total_facturas or 0,
        "monto_total": float(totales.monto_total) if totales.monto_total else 0.0,
        "subtotal": float(totales.subtotal) if totales.subtotal else 0.0,
        "iva": float(totales.iva) if totales.iva else 0.0,
        "promedio": float(totales.promedio) if totales.promedio else 0.0,
        "por_estado": [
            {
                "estado": row.estado.value if hasattr(row.estado, 'value') else row.estado,
                "cantidad": row.cantidad,
                "monto": float(row.monto) if row.monto else 0.0
            }
            for row in stats_by_estado
        ]
    }


# -----------------------------------------------------
# Obtener años disponibles
# -----------------------------------------------------
def get_años_disponibles(db: Session) -> List[int]:
    """
    Obtiene lista de años que tienen facturas registradas.
    Ahora usa fecha_emision (año_factura eliminado de BD).
    """
    from sqlalchemy import extract

    result = db.query(
        extract('year', Factura.fecha_emision).label('año')
    ).filter(
        Factura.fecha_emision.isnot(None)
    ).distinct().order_by(desc('año')).all()

    return [int(row.año) for row in result]


# -----------------------------------------------------
# Obtener jerarquía año → mes → facturas
# -----------------------------------------------------
def get_jerarquia_facturas(
    db: Session,
    año: Optional[int] = None,
    mes: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit_por_mes: int = 100
) -> Dict[str, Any]:
    """
    Retorna facturas organizadas jerárquicamente: Año → Mes → Facturas

    Estructura de respuesta:
    {
        "2025": {
            "10": {
                "total_facturas": 4,
                "monto_total": 12500.00,
                "facturas": [...]
            },
            "09": {...}
        },
        "2024": {...}
    }

    Optimizado con índices: idx_facturas_orden_cronologico, idx_facturas_año_mes_estado
    """
    from collections import defaultdict
    from sqlalchemy import extract

    query = db.query(Factura).filter(Factura.fecha_emision.isnot(None))

    # Filtros opcionales
    if año:
        query = query.filter(extract('year', Factura.fecha_emision) == año)

    if mes:
        query = query.filter(extract('month', Factura.fecha_emision) == mes)

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    if estado:
        query = query.filter(Factura.estado == estado)

    # Ordenar cronológicamente: más recientes primero
    facturas = query.order_by(
        desc(Factura.fecha_emision),
        desc(Factura.id)
    ).all()

    # Construir jerarquía
    jerarquia = defaultdict(lambda: defaultdict(lambda: {
        "total_facturas": 0,
        "monto_total": 0.0,
        "subtotal": 0.0,
        "iva": 0.0,
        "facturas": []
    }))

    for factura in facturas:
        # Derivar año y mes desde fecha_emision
        año_key = str(factura.fecha_emision.year) if factura.fecha_emision else "0000"
        mes_key = str(factura.fecha_emision.month).zfill(2) if factura.fecha_emision else "00"  # "01", "02", etc.

        mes_data = jerarquia[año_key][mes_key]

        # Agregar a contadores
        mes_data["total_facturas"] += 1
        mes_data["monto_total"] += float(factura.total_a_pagar or 0)
        mes_data["subtotal"] += float(factura.subtotal or 0)
        mes_data["iva"] += float(factura.iva or 0)

        # Agregar factura (limitado por mes para performance)
        if len(mes_data["facturas"]) < limit_por_mes:
            mes_data["facturas"].append({
                "id": factura.id,
                "numero_factura": factura.numero_factura,
                "fecha_emision": factura.fecha_emision.isoformat() if factura.fecha_emision else None,
                "total": float(factura.total_a_pagar or 0),
                "estado": factura.estado.value if hasattr(factura.estado, 'value') else factura.estado,
                "proveedor_id": factura.proveedor_id,
                "cufe": factura.cufe
            })

    # Convertir defaultdict a dict normal para JSON
    return {año: dict(meses) for año, meses in jerarquia.items()}


# -----------------------------------------------------
# Buscar facturas del mes anterior (para automatización)
# -----------------------------------------------------
def find_facturas_mes_anterior(
    db: Session,
    proveedor_id: int,
    fecha_actual: date,
    concepto_hash: Optional[str] = None,
    concepto_normalizado: Optional[str] = None,
    numero_factura: Optional[str] = None,
    limit: int = 10
) -> List[Factura]:
    """
    Busca facturas del mes anterior del mismo proveedor.

    Ahora soporta filtrado adicional por concepto_hash para matching más preciso.

    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor
        fecha_actual: Fecha de la factura actual
        concepto_hash: Hash MD5 del concepto para matching rápido (opcional)
        concepto_normalizado: Concepto normalizado para comparación (opcional)
        numero_factura: Número de factura para excluir (opcional)
        limit: Límite de facturas a retornar

    Returns:
        Lista de facturas del mes anterior del mismo proveedor
    """
    from dateutil.relativedelta import relativedelta
    from sqlalchemy import extract

    # Calcular fecha del mes anterior
    fecha_mes_anterior = fecha_actual - relativedelta(months=1)

    # Buscar facturas del mismo proveedor en el mes anterior
    query = db.query(Factura).filter(
        and_(
            Factura.proveedor_id == proveedor_id,
            extract('year', Factura.fecha_emision) == fecha_mes_anterior.year,
            extract('month', Factura.fecha_emision) == fecha_mes_anterior.month,
            # Solo considerar facturas aprobadas
            or_(
                Factura.estado == EstadoFactura.aprobada,
                Factura.estado == EstadoFactura.aprobada_auto
            )
        )
    )

    # Filtrar por concepto_hash si se proporciona (matching rápido)
    if concepto_hash:
        query = query.filter(Factura.concepto_hash == concepto_hash)

    # Excluir la factura actual si se proporciona su número
    if numero_factura:
        query = query.filter(Factura.numero_factura != numero_factura)

    facturas = query.order_by(desc(Factura.fecha_emision)).limit(limit).all()

    return facturas


# Versión singular para AutomationService (retorna solo la más reciente)
def find_factura_mes_anterior(
    db: Session,
    proveedor_id: int,
    fecha_actual: date,
    concepto_hash: Optional[str] = None,
    concepto_normalizado: Optional[str] = None,
    numero_factura: Optional[str] = None
) -> Optional[Factura]:
    """
    Busca LA factura más reciente del mes anterior del mismo proveedor.

    Esta es la versión singular que retorna un solo resultado (o None).

    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor
        fecha_actual: Fecha de la factura actual
        concepto_hash: Hash MD5 del concepto para matching rápido (opcional)
        concepto_normalizado: Concepto normalizado para comparación (opcional)
        numero_factura: Número de factura para excluir (opcional)

    Returns:
        La factura más reciente del mes anterior, o None si no se encuentra
    """
    facturas = find_facturas_mes_anterior(
        db=db,
        proveedor_id=proveedor_id,
        fecha_actual=fecha_actual,
        concepto_hash=concepto_hash,
        concepto_normalizado=concepto_normalizado,
        numero_factura=numero_factura,
        limit=1
    )

    return facturas[0] if facturas else None




# -----------------------------------------------------
# Buscar facturas por número de orden de compra (para automatización)
# -----------------------------------------------------
def find_facturas_by_orden_compra(
    db: Session,
    orden_compra_numero: str,
    proveedor_id: Optional[int] = None
) -> List[Factura]:
    """
    Busca facturas asociadas a una orden de compra.

    Args:
        db: Sesión de base de datos
        orden_compra_numero: Número de orden de compra
        proveedor_id: ID del proveedor (opcional)

    Returns:
        Lista de facturas asociadas a la orden de compra
    """
    query = db.query(Factura).filter(
        Factura.orden_compra_numero == orden_compra_numero
    )

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    return query.order_by(desc(Factura.fecha_emision)).all()


# -----------------------------------------------------
# Buscar facturas por hash de concepto
# -----------------------------------------------------
def find_facturas_by_concepto_hash(
    db: Session,
    concepto_hash: str,
    proveedor_id: Optional[int] = None,
    limit: int = 10
) -> List[Factura]:
    """
    Busca facturas con el mismo hash de concepto.

    Útil para encontrar facturas recurrentes idénticas.

    Args:
        db: Sesión de base de datos
        concepto_hash: Hash MD5 del concepto normalizado
        proveedor_id: ID del proveedor (opcional, para filtrar por proveedor)
        limit: Límite de facturas a retornar

    Returns:
        Lista de facturas con el mismo hash de concepto
    """
    query = db.query(Factura).filter(
        Factura.concepto_hash == concepto_hash
    )

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    return query.order_by(desc(Factura.fecha_emision)).limit(limit).all()


# -----------------------------------------------------
# Buscar facturas por concepto normalizado de proveedor
# -----------------------------------------------------
def find_facturas_by_concepto_proveedor(
    db: Session,
    proveedor_id: int,
    concepto_normalizado: str,
    limit: int = 12
) -> List[Factura]:
    """
    Busca facturas con el mismo concepto normalizado del mismo proveedor.

    Útil para encontrar facturas recurrentes basadas en el concepto.

    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor
        concepto_normalizado: Concepto normalizado de la factura
        limit: Límite de facturas a retornar

    Returns:
        Lista de facturas con el mismo concepto normalizado
    """
    query = db.query(Factura).filter(
        and_(
            Factura.proveedor_id == proveedor_id,
            Factura.concepto_normalizado == concepto_normalizado
        )
    )

    return query.order_by(desc(Factura.fecha_emision)).limit(limit).all()
