# app/api/v1/routers/dashboard.py
"""
Dashboard optimizado con Progressive Disclosure (Option A)

Endpoints para vista principal del dashboard con filtrado dinámico:
- Mes actual + estados activos (dashboard principal)
- Alerta de fin de mes (contextual)
- Histórico completo (vista separada)
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status, Header
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, and_, or_
from typing import List, Optional
from datetime import datetime, date, timedelta
from calendar import monthrange

from app.db.session import get_db
from app.core.security import get_current_usuario, require_role
from app.models.factura import Factura, EstadoFactura
from app.models.proveedor import Proveedor
from app.models.workflow_aprobacion import WorkflowAprobacionFactura
from app.models.usuario import Usuario
from app.models.grupo import Grupo, ResponsableGrupo
from app.schemas.factura import FacturaRead
from pydantic import BaseModel, Field
from app.utils.logger import logger
from app.core.grupos_utils import (
    get_grupos_usuario,
    usuario_es_admin
)


router = APIRouter(tags=["Dashboard"])


# ============================================================================
# SCHEMAS - DASHBOARD OPERACIONAL
# ============================================================================

class EstadisticasMesActual(BaseModel):
    """Estadísticas del mes actual (solo estados activos)"""
    total: int = Field(description="Total de facturas del mes actual")
    en_revision: int = Field(description="Facturas en revisión (requieren acción responsable)")
    aprobadas: int = Field(description="Facturas aprobadas (requieren acción contador)")
    aprobadas_auto: int = Field(description="Facturas aprobadas automáticamente (requieren acción contador)")
    rechazadas: int = Field(description="Facturas rechazadas (inactivas)")
    en_cuarentena: int = Field(default=0, description="Facturas en cuarentena (grupo sin responsables)")


class CuarentenaGrupo(BaseModel):
    """Información de un grupo con facturas en cuarentena"""
    grupo_id: int
    nombre_grupo: str
    codigo_grupo: str
    total_facturas: int
    impacto_financiero: float
    url_asignar_responsables: str


class CuarentenaResumen(BaseModel):
    """Resumen de cuarentena para dashboard"""
    total_facturas: int = Field(description="Total de facturas en cuarentena")
    total_grupos_afectados: int = Field(description="Total de grupos con facturas en cuarentena")
    impacto_financiero_total: float = Field(description="Suma total de facturas en cuarentena")
    grupos: List[CuarentenaGrupo] = Field(default_factory=list, description="Detalle por grupo")


class DashboardMesActualResponse(BaseModel):
    """Respuesta completa del dashboard del mes actual"""
    mes: int = Field(description="Mes actual (1-12)")
    año: int = Field(description="Año actual")
    nombre_mes: str = Field(description="Nombre del mes en español")
    estadisticas: EstadisticasMesActual
    facturas: List[FacturaRead]
    total_facturas: int = Field(description="Total de facturas retornadas")
    cuarentena: Optional[CuarentenaResumen] = Field(None, description="Información de cuarentena (solo para admin/superadmin)")


class AlertaMesResponse(BaseModel):
    """Respuesta de alerta de fin de mes"""
    mostrar_alerta: bool = Field(description="Si se debe mostrar la alerta")
    dias_restantes: int = Field(description="Días restantes para fin de mes")
    facturas_pendientes: int = Field(description="Facturas pendientes (en_revision + aprobadas)")
    mensaje: Optional[str] = Field(None, description="Mensaje de alerta personalizado")
    nivel_urgencia: str = Field(description="Nivel de urgencia: info, warning, critical")


class EstadisticasHistorico(BaseModel):
    """Estadísticas del período histórico (todos los estados)"""
    total: int = Field(description="Total de facturas del período")
    validadas: int = Field(description="Facturas validadas por contador")
    devueltas: int = Field(description="Facturas devueltas por contador")
    rechazadas: int = Field(description="Facturas rechazadas por responsable")
    pendientes: int = Field(description="Facturas aún pendientes (en_revision + aprobadas)")


class HistoricoResponse(BaseModel):
    """Respuesta completa de vista histórica"""
    mes: int = Field(description="Mes consultado")
    año: int = Field(description="Año consultado")
    nombre_mes: str = Field(description="Nombre del mes en español")
    estadisticas: EstadisticasHistorico
    facturas: List[FacturaRead]
    total_facturas: int = Field(description="Total de facturas retornadas")


# ============================================================================
# SCHEMAS - DASHBOARD SUPERADMIN (ADMINISTRATIVO)
# ============================================================================

class GrupoStats(BaseModel):
    """Estadísticas de un grupo"""
    id: int
    codigo: str
    nombre: str
    nivel: int
    usuarios_asignados: int = Field(description="Usuarios con acceso a este grupo")
    facturas_mes_actual: int = Field(description="Facturas creadas en el mes actual")
    facturas_pendientes: int = Field(description="Facturas en estados pendientes")
    activo: bool


class ActividadReciente(BaseModel):
    """Actividad reciente del sistema"""
    fecha: datetime
    tipo: str = Field(description="Tipo: factura_creada, usuario_creado, grupo_creado, etc.")
    descripcion: str
    usuario: Optional[str] = None
    grupo: Optional[str] = None


class SuperAdminDashboardResponse(BaseModel):
    """Dashboard administrativo para SuperAdmin"""

    # Métricas globales
    total_usuarios: int = Field(description="Total de usuarios en el sistema")
    usuarios_activos: int = Field(description="Usuarios con activo=True")
    total_grupos: int = Field(description="Total de grupos")
    grupos_activos: int = Field(description="Grupos con activo=True")

    # Distribución por roles
    usuarios_por_rol: dict = Field(description="Cantidad de usuarios por rol")

    # Estadísticas de facturas globales (últimos 30 días)
    facturas_ultimos_30_dias: int
    facturas_mes_actual: int
    facturas_cuarentena: int = Field(default=0, description="Facturas sin grupo_id asignado (MULTI-TENANT 2025-12-14)")

    # Grupos con más actividad (top 5)
    grupos_mas_activos: List[GrupoStats]

    # Actividad reciente del sistema (últimas 10 acciones)
    actividad_reciente: List[ActividadReciente]


# ============================================================================
# UTILIDADES
# ============================================================================

MESES_ESPAÑOL = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def get_mes_actual():
    """Retorna mes y año actual"""
    hoy = date.today()
    return hoy.month, hoy.year


def get_dias_restantes_mes() -> int:
    """Calcula días restantes hasta fin de mes"""
    hoy = date.today()
    ultimo_dia = monthrange(hoy.year, hoy.month)[1]
    ultimo_dia_mes = date(hoy.year, hoy.month, ultimo_dia)
    return (ultimo_dia_mes - hoy).days


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/mes-actual",
    response_model=DashboardMesActualResponse,
    summary="Dashboard del mes actual (Progressive Disclosure + Multi-Tenant)",
    description="""
    Retorna facturas del mes actual en estados ACTIVOS únicamente.

    Estados activos:
    - en_revision (requiere acción responsable)
    - aprobada (requiere acción contador)
    - aprobada_auto (requiere acción contador)
    - rechazada (para referencia)

    NO incluye:
    - validada_contabilidad (ya procesada)
    - devuelta_contabilidad (ya procesada)

    Optimizado con índices en (año, mes, estado).

    MULTI-TENANT:
    - Usuarios no-admin solo ven facturas de sus grupos asignados
    - Admin puede filtrar por grupo específico con parámetro grupo_id
    """
)
def get_dashboard_mes_actual(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_usuario),
    x_grupo_id: Optional[int] = Header(None, alias="X-Grupo-Id", description="ID del grupo seleccionado (multi-tenant)")
):
    """
    Dashboard principal: solo mes actual + estados activos.

    Implementa Progressive Disclosure (Option A):
    - Focus en facturas que requieren ACCIÓN
    - Sin saturación de información
    - Performance optimizada
    """
    try:
        mes_actual, año_actual = get_mes_actual()

        logger.info(f"Dashboard mes actual solicitado: {MESES_ESPAÑOL[mes_actual]} {año_actual} por usuario {current_user.usuario}")

        # Estados activos (facturas que requieren atención o son del mes)
        estados_activos = [
            EstadoFactura.en_revision.value,
            EstadoFactura.aprobada.value,
            EstadoFactura.aprobada_auto.value,
            EstadoFactura.rechazada.value,
            EstadoFactura.validada_contabilidad.value,
            EstadoFactura.devuelta_contabilidad.value
        ]

        # Query principal: mes actual + estados activos
        query = db.query(Factura).options(
            joinedload(Factura.proveedor),
            joinedload(Factura.usuario)
        ).filter(
            extract('month', Factura.creado_en) == mes_actual,
            extract('year', Factura.creado_en) == año_actual,
            Factura.estado.in_(estados_activos)
        )

        # ========================================================================
        # SEGURIDAD: Filtrar por responsable según rol (CRÍTICO)
        # ========================================================================
        if hasattr(current_user, 'role') and current_user.role.nombre.lower() == 'responsable':
            # RESPONSABLES solo ven SUS facturas asignadas
            query = query.filter(Factura.responsable_id == current_user.id)
            logger.info(f"Filtro de seguridad aplicado: responsable {current_user.usuario} (ID {current_user.id})")
        # ADMIN, CONTADOR y VIEWER ven todas las facturas (sin filtro)
        # CONTADOR: solo lectura, no puede hacer acciones
        else:
            role_name = current_user.role.nombre if hasattr(current_user, 'role') else 'DESCONOCIDO'
            logger.info(f"Usuario {role_name} {current_user.usuario}: acceso completo (solo lectura para CONTADOR/VIEWER)")

        # ========================================================================
        # FASE 2: MULTI-TENANT - Filtrar por grupo (desde header X-Grupo-Id)
        # ========================================================================
        if x_grupo_id is not None:
            # Validar acceso al grupo solicitado
            if not usuario_es_admin(current_user):
                grupos_usuario = get_grupos_usuario(current_user.id, db)
                if x_grupo_id not in grupos_usuario:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Usuario no tiene acceso al grupo {x_grupo_id}"
                    )
            query = query.filter(Factura.grupo_id == x_grupo_id)
            logger.info(f"[MULTI-TENANT] Filtro por grupo {x_grupo_id} aplicado (header X-Grupo-Id)")
        elif not usuario_es_admin(current_user):
            # Usuario no-admin sin header: aplicar filtro automático por sus grupos
            grupos_usuario = get_grupos_usuario(current_user.id, db)
            if grupos_usuario:
                query = query.filter(Factura.grupo_id.in_(grupos_usuario))
                logger.info(f"[MULTI-TENANT] Filtro automático por grupos {grupos_usuario}")

        query = query.order_by(
            # Priorizar por estado (las que requieren acción primero)
            Factura.estado,
            Factura.creado_en.desc()
        )

        facturas = query.all()

        # Calcular estadísticas
        total = len(facturas)
        en_revision = sum(1 for f in facturas if f.estado == EstadoFactura.en_revision.value)
        aprobadas = sum(1 for f in facturas if f.estado == EstadoFactura.aprobada.value)
        aprobadas_auto = sum(1 for f in facturas if f.estado == EstadoFactura.aprobada_auto.value)
        rechazadas = sum(1 for f in facturas if f.estado == EstadoFactura.rechazada.value)

        # Contar facturas en cuarentena (del mes actual)
        en_cuarentena_count = db.query(func.count(Factura.id)).filter(
            extract('month', Factura.creado_en) == mes_actual,
            extract('year', Factura.creado_en) == año_actual,
            Factura.estado == EstadoFactura.en_cuarentena.value
        ).scalar() or 0

        logger.info(
            f"Dashboard mes actual: {total} facturas "
            f"(en_revision: {en_revision}, aprobadas: {aprobadas}, "
            f"aprobadas_auto: {aprobadas_auto}, rechazadas: {rechazadas}, "
            f"en_cuarentena: {en_cuarentena_count})"
        )

        # ========================================================================
        # CUARENTENA: Solo para Super Admin y Admin
        # ========================================================================
        cuarentena_info = None
        if hasattr(current_user, 'role') and current_user.role.nombre.lower() in ['superadmin', 'admin']:
            try:
                from app.services.cuarentena_service import CuarentenaService
                cuarentena_service = CuarentenaService(db)
                resumen_cuarentena = cuarentena_service.obtener_resumen_cuarentena()

                # Transformar formato del servicio a formato del dashboard
                grupos_cuarentena = []
                if resumen_cuarentena.get('problemas'):
                    for problema in resumen_cuarentena['problemas']:
                        for subproblema in problema.get('subproblemas', []):
                            grupos_cuarentena.append(CuarentenaGrupo(
                                grupo_id=subproblema['grupo_id'],
                                nombre_grupo=subproblema['nombre_grupo'],
                                codigo_grupo=subproblema['codigo_grupo'],
                                total_facturas=subproblema['total_facturas'],
                                impacto_financiero=float(subproblema['impacto_financiero']),
                                url_asignar_responsables=subproblema['accion_dirigida']['url']
                            ))

                cuarentena_info = CuarentenaResumen(
                    total_facturas=resumen_cuarentena.get('total', 0),
                    total_grupos_afectados=len(grupos_cuarentena),
                    impacto_financiero_total=float(resumen_cuarentena.get('impacto_financiero', 0)),
                    grupos=grupos_cuarentena
                )

                logger.info(f"Cuarentena incluida en dashboard: {cuarentena_info.total_facturas} facturas en cuarentena")
            except Exception as e:
                logger.warning(f"Error obteniendo información de cuarentena para dashboard: {str(e)}")
                # No fallar el dashboard si hay error en cuarentena

        return DashboardMesActualResponse(
            mes=mes_actual,
            año=año_actual,
            nombre_mes=MESES_ESPAÑOL[mes_actual],
            estadisticas=EstadisticasMesActual(
                total=total,
                en_revision=en_revision,
                aprobadas=aprobadas,
                aprobadas_auto=aprobadas_auto,
                rechazadas=rechazadas,
                en_cuarentena=en_cuarentena_count
            ),
            facturas=[FacturaRead.model_validate(f) for f in facturas],
            total_facturas=total,
            cuarentena=cuarentena_info
        )

    except Exception as e:
        logger.error(f"Error en dashboard mes actual: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener dashboard del mes actual: {str(e)}"
        )


@router.get(
    "/alerta-mes",
    response_model=AlertaMesResponse,
    summary="Alerta contextual de fin de mes (Multi-Tenant)",
    description="""
    Retorna si se debe mostrar alerta de fin de mes.

    Lógica de alerta:
    - Solo se muestra si días_restantes < 5 Y hay facturas pendientes
    - Facturas pendientes = en_revision + aprobada + aprobada_auto

    Niveles de urgencia:
    - info: 4-5 días restantes
    - warning: 2-3 días restantes
    - critical: 0-1 días restantes

    MULTI-TENANT:
    - Usuarios no-admin solo ven alertas de sus grupos asignados
    - Admin puede filtrar por grupo específico con parámetro grupo_id
    """
)
def get_alerta_mes(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_usuario),
    x_grupo_id: Optional[int] = Header(None, alias="X-Grupo-Id", description="ID del grupo seleccionado (multi-tenant)")
):
    """
    Alerta contextual: solo muestra si hay facturas pendientes cerca de fin de mes.

    UX :
    - No invasiva (banner superior)
    - Solo aparece cuando es relevante
    - Mensaje personalizado según urgencia
    """
    try:
        mes_actual, año_actual = get_mes_actual()
        dias_restantes = get_dias_restantes_mes()

        # Contar facturas pendientes del mes actual
        estados_pendientes = [
            EstadoFactura.en_revision.value,
            EstadoFactura.aprobada.value,
            EstadoFactura.aprobada_auto.value
        ]

        query_pendientes = db.query(func.count(Factura.id)).filter(
            extract('month', Factura.creado_en) == mes_actual,
            extract('year', Factura.creado_en) == año_actual,
            Factura.estado.in_(estados_pendientes)
        )

        # ========================================================================
        # SEGURIDAD: Filtrar por responsable según rol (CRÍTICO)
        # ========================================================================
        if hasattr(current_user, 'role') and current_user.role.nombre.lower() == 'responsable':
            query_pendientes = query_pendientes.filter(Factura.responsable_id == current_user.id)
        # ADMIN, CONTADOR y VIEWER ven todas (sin filtro)

        # ========================================================================
        # FASE 2: MULTI-TENANT - Filtrar por grupo (desde header X-Grupo-Id)
        # ========================================================================
        if x_grupo_id is not None:
            # Validar acceso al grupo solicitado
            if not usuario_es_admin(current_user):
                grupos_usuario = get_grupos_usuario(current_user.id, db)
                if x_grupo_id not in grupos_usuario:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Usuario no tiene acceso al grupo {x_grupo_id}"
                    )
            query_pendientes = query_pendientes.filter(Factura.grupo_id == x_grupo_id)
            logger.info(f"[MULTI-TENANT] Alerta filtrada por grupo {x_grupo_id} (header X-Grupo-Id)")
        elif not usuario_es_admin(current_user):
            # Usuario no-admin sin header: aplicar filtro automático por sus grupos
            grupos_usuario = get_grupos_usuario(current_user.id, db)
            if grupos_usuario:
                query_pendientes = query_pendientes.filter(Factura.grupo_id.in_(grupos_usuario))
                logger.info(f"[MULTI-TENANT] Alerta con filtro automático por grupos {grupos_usuario}")

        facturas_pendientes = query_pendientes.scalar()

        # Decidir si mostrar alerta
        mostrar_alerta = (dias_restantes < 5) and (facturas_pendientes > 0)

        # Determinar nivel de urgencia
        if dias_restantes <= 1:
            nivel_urgencia = "critical"
            if dias_restantes == 0:
                mensaje = f" Tienes {facturas_pendientes} factura(s) pendiente(s). El mes cierra HOY."
            else:
                mensaje = f" Tienes {facturas_pendientes} factura(s) pendiente(s). El mes cierra MAÑANA."
        elif dias_restantes <= 3:
            nivel_urgencia = "warning"
            mensaje = f"Tienes {facturas_pendientes} factura(s) pendiente(s). El mes cierra en {dias_restantes} días."
        else:
            nivel_urgencia = "info"
            mensaje = f"Tienes {facturas_pendientes} factura(s) pendiente(s). El mes cierra en {dias_restantes} días."

        logger.info(
            f"Alerta mes: mostrar={mostrar_alerta}, días={dias_restantes}, "
            f"pendientes={facturas_pendientes}, urgencia={nivel_urgencia}"
        )

        return AlertaMesResponse(
            mostrar_alerta=mostrar_alerta,
            dias_restantes=dias_restantes,
            facturas_pendientes=facturas_pendientes,
            mensaje=mensaje if mostrar_alerta else None,
            nivel_urgencia=nivel_urgencia
        )

    except Exception as e:
        logger.error(f"Error en alerta mes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular alerta de mes: {str(e)}"
        )


@router.get(
    "/historico",
    response_model=HistoricoResponse,
    summary="Vista histórica completa (análisis + Multi-Tenant)",
    description="""
    Retorna TODAS las facturas de un período específico (todos los estados).

    Incluye todos los estados:
    - en_revision, aprobada, aprobada_auto (aún pendientes)
    - validada_contabilidad (completadas exitosamente)
    - devuelta_contabilidad (devueltas por contador)
    - rechazada (rechazadas por responsable)

    Usar para:
    - Análisis histórico
    - Reportes mensuales
    - Auditoría
    - Exportaciones

    MULTI-TENANT:
    - Usuarios no-admin solo ven facturas de sus grupos asignados
    - Admin puede filtrar por grupo específico con parámetro grupo_id
    """
)
def get_historico(
    mes: int = Query(..., ge=1, le=12, description="Mes a consultar (1-12)"),
    anio: int = Query(..., ge=2020, le=2100, description="Año a consultar"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_usuario),
    x_grupo_id: Optional[int] = Header(None, alias="X-Grupo-Id", description="ID del grupo seleccionado (multi-tenant)")
):
    """
    Vista histórica: análisis completo de un período.

    Progressive Disclosure:
    - Dashboard principal = Acción (mes actual, estados activos)
    - Histórico = Análisis (cualquier mes, todos los estados)
    """
    try:
        logger.info(f"Histórico solicitado: {MESES_ESPAÑOL[mes]} {anio} por usuario {current_user.usuario}")

        # Query: mes específico + TODOS los estados
        query = db.query(Factura).options(
            joinedload(Factura.proveedor),
            joinedload(Factura.usuario)
        ).filter(
            extract('month', Factura.creado_en) == mes,
            extract('year', Factura.creado_en) == anio
        )

        # ========================================================================
        # SEGURIDAD: Filtrar por responsable según rol (CRÍTICO)
        # ========================================================================
        if hasattr(current_user, 'role') and current_user.role.nombre.lower() == 'responsable':
            # RESPONSABLES solo ven SUS facturas asignadas
            query = query.filter(Factura.responsable_id == current_user.id)
            logger.info(f"Histórico con filtro de seguridad: responsable {current_user.usuario}")
        # ADMIN, CONTADOR y VIEWER ven todas las facturas (sin filtro)
        else:
            role_name = current_user.role.nombre if hasattr(current_user, 'role') else 'DESCONOCIDO'
            logger.info(f"Histórico: {role_name} {current_user.usuario} - acceso completo")

        # ========================================================================
        # FASE 2: MULTI-TENANT - Filtrar por grupo (desde header X-Grupo-Id)
        # ========================================================================
        if x_grupo_id is not None:
            # Validar acceso al grupo solicitado
            if not usuario_es_admin(current_user):
                grupos_usuario = get_grupos_usuario(current_user.id, db)
                if x_grupo_id not in grupos_usuario:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Usuario no tiene acceso al grupo {x_grupo_id}"
                    )
            query = query.filter(Factura.grupo_id == x_grupo_id)
            logger.info(f"[MULTI-TENANT] Histórico filtrado por grupo {x_grupo_id} (header X-Grupo-Id)")
        elif not usuario_es_admin(current_user):
            # Usuario no-admin sin header: aplicar filtro automático por sus grupos
            grupos_usuario = get_grupos_usuario(current_user.id, db)
            if grupos_usuario:
                query = query.filter(Factura.grupo_id.in_(grupos_usuario))
                logger.info(f"[MULTI-TENANT] Histórico con filtro automático por grupos {grupos_usuario}")

        query = query.order_by(Factura.creado_en.desc())

        facturas = query.all()

        # Calcular estadísticas completas
        total = len(facturas)
        validadas = sum(1 for f in facturas if f.estado == EstadoFactura.validada_contabilidad.value)
        devueltas = sum(1 for f in facturas if f.estado == EstadoFactura.devuelta_contabilidad.value)
        rechazadas = sum(1 for f in facturas if f.estado == EstadoFactura.rechazada.value)

        # Pendientes = estados que aún requieren acción
        estados_pendientes = [
            EstadoFactura.en_revision.value,
            EstadoFactura.aprobada.value,
            EstadoFactura.aprobada_auto.value
        ]
        pendientes = sum(1 for f in facturas if f.estado in estados_pendientes)

        logger.info(
            f"Histórico {MESES_ESPAÑOL[mes]} {anio}: {total} facturas "
            f"(validadas: {validadas}, devueltas: {devueltas}, "
            f"rechazadas: {rechazadas}, pendientes: {pendientes})"
        )

        return HistoricoResponse(
            mes=mes,
            año=anio,
            nombre_mes=MESES_ESPAÑOL[mes],
            estadisticas=EstadisticasHistorico(
                total=total,
                validadas=validadas,
                devueltas=devueltas,
                rechazadas=rechazadas,
                pendientes=pendientes
            ),
            facturas=[FacturaRead.model_validate(f) for f in facturas],
            total_facturas=total
        )

    except Exception as e:
        logger.error(f"Error en histórico: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener histórico: {str(e)}"
        )


# ============================================================================
# SCHEMAS - ESTADÍSTICAS PARA GRÁFICAS
# ============================================================================

class EstadisticasGraficasResponse(BaseModel):
    """Estadísticas optimizadas para componentes de gráficas reutilizables"""

    # KPIs principales
    total_facturas: int = Field(description="Total de facturas en el período")
    pendientes_revision: int = Field(description="Facturas en revisión (acción responsable)")
    pendientes_validacion: int = Field(description="Facturas aprobadas (acción contador)")
    validadas: int = Field(description="Facturas validadas por contador")
    rechazadas: int = Field(description="Facturas rechazadas")
    devueltas: int = Field(description="Facturas devueltas por contador")

    # Distribución por estado (para gráfica de dona/torta)
    distribucion_estados: dict = Field(
        description="Distribución porcentual por estado: {estado: {count: int, porcentaje: float}}"
    )

    # Datos para gráfica de barras por mes (últimos 6 meses)
    facturas_por_mes: List[dict] = Field(
        description="Facturas de últimos 6 meses: [{mes: str, total: int, aprobadas: int, rechazadas: int}]"
    )

    # Datos para gráfica de línea (tendencia)
    tendencia_aprobacion: List[dict] = Field(
        description="Tasa de aprobación últimos 6 meses: [{mes: str, tasa_aprobacion: float}]"
    )

    # Metadata
    periodo: str = Field(description="Descripción del período consultado")
    grupo_id: Optional[int] = Field(None, description="ID del grupo filtrado (null si es global)")
    rol: str = Field(description="Rol del usuario que consulta")


# ============================================================================
# ENDPOINTS - ESTADÍSTICAS PARA GRÁFICAS
# ============================================================================

@router.get(
    "/stats",
    response_model=EstadisticasGraficasResponse,
    summary="Estadísticas para gráficas del dashboard (Multi-Tenant)",
    description="""
    Endpoint optimizado para componentes de gráficas reutilizables.

    Retorna datos estructurados para:
    - KPI Cards (contadores principales)
    - Gráfica de dona/torta (distribución de estados)
    - Gráfica de barras (facturas por mes)
    - Gráfica de línea (tendencia de aprobación)

    COMPORTAMIENTO POR ROL:
    - SuperAdmin: Estadísticas globales o de grupo específico (con X-Grupo-Id)
    - Admin: Estadísticas de sus grupos asignados o grupo específico
    - Responsable: Solo estadísticas de facturas asignadas a él
    - Contador: Estadísticas globales (lectura)
    - Viewer: Estadísticas de sus grupos (lectura)

    FILTROS MULTI-TENANT:
    - Automático por grupos del usuario (no-admin)
    - Por grupo específico con header X-Grupo-Id
    - SuperAdmin puede ver todo sin filtro

    PERÍODO: Últimos 6 meses por defecto
    """
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_usuario),
    x_grupo_id: Optional[int] = Header(None, alias="X-Grupo-Id", description="ID del grupo seleccionado (multi-tenant)")
):
    """
    Estadísticas optimizadas para componentes de gráficas reutilizables.

    Diseño Enterprise:
    - Sin duplicación de código
    - Consultas optimizadas con agregaciones SQL
    - Respuesta estructurada para componentes React
    """
    try:
        logger.info(f"[DASHBOARD-STATS] Usuario {current_user.usuario} (rol: {current_user.role.nombre}) solicitando estadísticas")

        # ========================================================================
        # PASO 1: Determinar período (últimos 6 meses)
        # ========================================================================
        hoy = date.today()
        hace_6_meses = hoy - timedelta(days=180)

        # ========================================================================
        # PASO 2: Construir query base con filtrado multi-tenant
        # ========================================================================
        query_base = db.query(Factura)
        rol_nombre = current_user.role.nombre.lower()

        # FILTRO POR ROL
        if rol_nombre == 'responsable':
            # Responsables solo ven SUS facturas asignadas (por responsable_id)
            query_base = query_base.filter(Factura.responsable_id == current_user.id)
            logger.info(f"[DASHBOARD-STATS] Filtro responsable: responsable_id={current_user.id}")

        # FILTRO POR GRUPO (Multi-Tenant)
        if x_grupo_id is not None:
            # Validar acceso al grupo solicitado
            if rol_nombre not in ['superadmin', 'admin', 'contador']:
                grupos_usuario = get_grupos_usuario(current_user.id, db)
                if x_grupo_id not in grupos_usuario:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Usuario no tiene acceso al grupo {x_grupo_id}"
                    )
            query_base = query_base.filter(Factura.grupo_id == x_grupo_id)
            logger.info(f"[DASHBOARD-STATS] Filtro por grupo: {x_grupo_id}")
        elif rol_nombre not in ['superadmin', 'admin', 'contador']:
            # Usuario no-admin sin header: aplicar filtro automático por sus grupos
            grupos_usuario = get_grupos_usuario(current_user.id, db)
            if grupos_usuario:
                query_base = query_base.filter(Factura.grupo_id.in_(grupos_usuario))
                logger.info(f"[DASHBOARD-STATS] Filtro automático por grupos: {grupos_usuario}")

        # ========================================================================
        # PASO 3: KPIs PRINCIPALES (últimos 6 meses)
        # ========================================================================
        query_periodo = query_base.filter(Factura.creado_en >= hace_6_meses)

        todas_facturas = query_periodo.all()
        total_facturas = len(todas_facturas)

        pendientes_revision = sum(1 for f in todas_facturas if f.estado == EstadoFactura.en_revision.value)
        pendientes_validacion = sum(
            1 for f in todas_facturas
            if f.estado in [EstadoFactura.aprobada.value, EstadoFactura.aprobada_auto.value]
        )
        validadas = sum(1 for f in todas_facturas if f.estado == EstadoFactura.validada_contabilidad.value)
        rechazadas = sum(1 for f in todas_facturas if f.estado == EstadoFactura.rechazada.value)
        devueltas = sum(1 for f in todas_facturas if f.estado == EstadoFactura.devuelta_contabilidad.value)

        # ========================================================================
        # PASO 4: DISTRIBUCIÓN POR ESTADO (para gráfica de dona/torta)
        # ========================================================================
        distribucion_estados = {}
        estados_map = {
            'en_revision': pendientes_revision,
            'aprobadas': pendientes_validacion,
            'validadas': validadas,
            'rechazadas': rechazadas,
            'devueltas': devueltas
        }

        for estado, count in estados_map.items():
            porcentaje = (count / total_facturas * 100) if total_facturas > 0 else 0
            distribucion_estados[estado] = {
                'count': count,
                'porcentaje': round(porcentaje, 2)
            }

        # ========================================================================
        # PASO 5: FACTURAS POR MES (últimos 6 meses) - Gráfica de barras
        # ========================================================================
        facturas_por_mes = []

        for i in range(6):
            mes_fecha = hoy - timedelta(days=30 * i)
            mes_num = mes_fecha.month
            año_num = mes_fecha.year

            facturas_mes = [
                f for f in todas_facturas
                if f.creado_en.month == mes_num and f.creado_en.year == año_num
            ]

            total_mes = len(facturas_mes)
            aprobadas_mes = sum(
                1 for f in facturas_mes
                if f.estado in [
                    EstadoFactura.aprobada.value,
                    EstadoFactura.aprobada_auto.value,
                    EstadoFactura.validada_contabilidad.value
                ]
            )
            rechazadas_mes = sum(
                1 for f in facturas_mes
                if f.estado == EstadoFactura.rechazada.value
            )

            facturas_por_mes.insert(0, {
                'mes': f"{MESES_ESPAÑOL[mes_num]} {año_num}",
                'total': total_mes,
                'aprobadas': aprobadas_mes,
                'rechazadas': rechazadas_mes
            })

        # ========================================================================
        # PASO 6: TENDENCIA DE APROBACIÓN (últimos 6 meses) - Gráfica de línea
        # ========================================================================
        tendencia_aprobacion = []

        for dato_mes in facturas_por_mes:
            total_mes = dato_mes['total']
            aprobadas_mes = dato_mes['aprobadas']

            tasa_aprobacion = (aprobadas_mes / total_mes * 100) if total_mes > 0 else 0

            tendencia_aprobacion.append({
                'mes': dato_mes['mes'],
                'tasa_aprobacion': round(tasa_aprobacion, 2)
            })

        # ========================================================================
        # PASO 7: CONSTRUIR RESPUESTA
        # ========================================================================
        periodo_descripcion = f"Últimos 6 meses ({hace_6_meses.strftime('%Y-%m-%d')} a {hoy.strftime('%Y-%m-%d')})"

        logger.info(
            f"[DASHBOARD-STATS] Estadísticas generadas: {total_facturas} facturas, "
            f"rol={rol_nombre}, grupo_id={x_grupo_id}"
        )

        return EstadisticasGraficasResponse(
            total_facturas=total_facturas,
            pendientes_revision=pendientes_revision,
            pendientes_validacion=pendientes_validacion,
            validadas=validadas,
            rechazadas=rechazadas,
            devueltas=devueltas,
            distribucion_estados=distribucion_estados,
            facturas_por_mes=facturas_por_mes,
            tendencia_aprobacion=tendencia_aprobacion,
            periodo=periodo_descripcion,
            grupo_id=x_grupo_id,
            rol=rol_nombre
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DASHBOARD-STATS] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas del dashboard: {str(e)}"
        )


# ============================================================================
# ENDPOINTS - SUPERADMIN
# ============================================================================

@router.get(
    "/superadmin",
    response_model=SuperAdminDashboardResponse,
    summary="Dashboard administrativo para SuperAdmin",
    description="""
    Dashboard con métricas administrativas e infraestructura del sistema.

    NO incluye operaciones de facturas (eso es para admin/responsable/contador).

    Métricas incluidas:
    - Total de usuarios y grupos
    - Distribución por roles
    - Grupos más activos
    - Actividad reciente del sistema

    **Requiere rol:** superadmin
    """
)
def get_superadmin_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_usuario)
):
    """
    Dashboard administrativo exclusivo para SuperAdmin.

    Focus en infraestructura y gestión, no en operaciones.
    """
    try:
        # Verificar que sea SuperAdmin
        if not hasattr(current_user, 'role') or current_user.role.nombre.lower() != 'superadmin':
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado. Solo SuperAdmin puede ver este dashboard."
            )

        logger.info(f"Dashboard SuperAdmin solicitado por: {current_user.usuario}")

        # ========================================================================
        # 1. MÉTRICAS DE USUARIOS
        # ========================================================================
        total_usuarios = db.query(func.count(Usuario.id)).scalar()
        usuarios_activos = db.query(func.count(Usuario.id)).filter(Usuario.activo == True).scalar()

        # Distribución por roles
        from app.models.role import Role
        usuarios_por_rol = {}
        roles = db.query(Role).all()
        for rol in roles:
            count = db.query(func.count(Usuario.id)).filter(Usuario.role_id == rol.id).scalar()
            usuarios_por_rol[rol.nombre] = count

        # ========================================================================
        # 2. MÉTRICAS DE GRUPOS
        # ========================================================================
        total_grupos = db.query(func.count(Grupo.id)).filter(Grupo.eliminado == False).scalar()
        grupos_activos = db.query(func.count(Grupo.id)).filter(
            Grupo.eliminado == False,
            Grupo.activo == True
        ).scalar()

        # ========================================================================
        # 3. MÉTRICAS DE FACTURAS GLOBALES
        # ========================================================================
        hoy = date.today()
        hace_30_dias = hoy - timedelta(days=30)
        mes_actual, año_actual = get_mes_actual()

        # Facturas últimos 30 días
        facturas_ultimos_30_dias = db.query(func.count(Factura.id)).filter(
            Factura.creado_en >= hace_30_dias
        ).scalar()

        # Facturas del mes actual
        facturas_mes_actual = db.query(func.count(Factura.id)).filter(
            extract('month', Factura.creado_en) == mes_actual,
            extract('year', Factura.creado_en) == año_actual
        ).scalar()

        # MULTI-TENANT 2025-12-14: Facturas en cuarentena
        facturas_cuarentena = db.query(func.count(Factura.id)).filter(
            Factura.estado == EstadoFactura.en_cuarentena
        ).scalar()

        # ========================================================================
        # 4. GRUPOS MÁS ACTIVOS (Top 5 por facturas del mes actual)
        # ========================================================================
        grupos_stats = db.query(
            Grupo.id,
            Grupo.codigo_corto,
            Grupo.nombre,
            Grupo.nivel,
            Grupo.activo,
            func.count(Factura.id).label('facturas_mes')
        ).outerjoin(
            Factura,
            and_(
                Factura.grupo_id == Grupo.id,
                extract('month', Factura.creado_en) == mes_actual,
                extract('year', Factura.creado_en) == año_actual
            )
        ).filter(
            Grupo.eliminado == False
        ).group_by(
            Grupo.id,
            Grupo.codigo_corto,
            Grupo.nombre,
            Grupo.nivel,
            Grupo.activo
        ).order_by(
            func.count(Factura.id).desc()
        ).limit(5).all()

        grupos_mas_activos = []
        for g in grupos_stats:
            # Contar usuarios asignados
            usuarios_asignados = db.query(func.count(ResponsableGrupo.responsable_id.distinct())).filter(
                ResponsableGrupo.grupo_id == g.id,
                ResponsableGrupo.activo == True
            ).scalar()

            # Contar facturas pendientes
            estados_pendientes = [
                EstadoFactura.en_revision.value,
                EstadoFactura.aprobada.value,
                EstadoFactura.aprobada_auto.value
            ]
            facturas_pendientes = db.query(func.count(Factura.id)).filter(
                Factura.grupo_id == g.id,
                Factura.estado.in_(estados_pendientes)
            ).scalar()

            grupos_mas_activos.append(GrupoStats(
                id=g.id,
                codigo=g.codigo_corto,
                nombre=g.nombre,
                nivel=g.nivel,
                usuarios_asignados=usuarios_asignados or 0,
                facturas_mes_actual=g.facturas_mes or 0,
                facturas_pendientes=facturas_pendientes or 0,
                activo=g.activo
            ))

        # ========================================================================
        # 5. ACTIVIDAD RECIENTE (últimas 10 acciones)
        # ========================================================================
        actividad_reciente = []

        # Últimas facturas creadas (5 más recientes)
        ultimas_facturas = db.query(Factura).options(
            joinedload(Factura.usuario),
            joinedload(Factura.grupo)
        ).order_by(Factura.creado_en.desc()).limit(5).all()

        for f in ultimas_facturas:
            actividad_reciente.append(ActividadReciente(
                fecha=f.creado_en,
                tipo="factura_creada",
                descripcion=f"Factura {f.numero_factura} creada",
                usuario=f.usuario.nombre if f.usuario else None,
                grupo=f.grupo.codigo_corto if f.grupo else None
            ))

        # Últimos usuarios creados (5 más recientes)
        ultimos_usuarios = db.query(Usuario).order_by(Usuario.creado_en.desc()).limit(5).all()

        for u in ultimos_usuarios:
            actividad_reciente.append(ActividadReciente(
                fecha=u.creado_en,
                tipo="usuario_creado",
                descripcion=f"Usuario {u.nombre} registrado",
                usuario="SYSTEM",
                grupo=None
            ))

        # Ordenar por fecha descendente y tomar últimas 10
        actividad_reciente.sort(key=lambda x: x.fecha, reverse=True)
        actividad_reciente = actividad_reciente[:10]

        logger.info(
            f"Dashboard SuperAdmin: {total_usuarios} usuarios, {total_grupos} grupos, "
            f"{facturas_mes_actual} facturas este mes"
        )

        return SuperAdminDashboardResponse(
            total_usuarios=total_usuarios or 0,
            usuarios_activos=usuarios_activos or 0,
            total_grupos=total_grupos or 0,
            grupos_activos=grupos_activos or 0,
            usuarios_por_rol=usuarios_por_rol,
            facturas_ultimos_30_dias=facturas_ultimos_30_dias or 0,
            facturas_mes_actual=facturas_mes_actual or 0,
            facturas_cuarentena=facturas_cuarentena or 0,  # MULTI-TENANT 2025-12-14
            grupos_mas_activos=grupos_mas_activos,
            actividad_reciente=actividad_reciente
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en dashboard SuperAdmin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener dashboard SuperAdmin: {str(e)}"
        )
