# app/api/v1/routers/automation.py
"""
Router para las APIs del sistema de automatización de facturas.

Proporciona endpoints para:
- Ejecutar procesamiento manual de automatización
- Consultar estado de facturas procesadas automáticamente  
- Configurar parámetros de automatización
- Obtener estadísticas del sistema
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.services.automation.automation_service import AutomationService
from app.services.automation.notification_service import NotificationService, ConfiguracionNotificacion
from app.services.audit_service import AuditService
from app.crud import factura as crud_factura
from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import TipoAprobacion, WorkflowAprobacionFactura
from app.schemas.common import ResponseBase
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


router = APIRouter(tags=["Automatización"])


# ==================== ENDPOINT DE INICIALIZACIÓN ENTERPRISE ====================

@router.post("/inicializar-sistema", summary=" Inicialización Enterprise del Sistema Completo")
def inicializar_sistema_completo(
    archivo_presupuesto: Optional[str] = None,
    año_fiscal: int = 2025,
    responsable_default_id: int = 1,
    ejecutar_vinculacion: bool = True,
    ejecutar_workflow: bool = True,
    dry_run: bool = False,
    db: Session = Depends(get_db)
):
    """
    **INICIALIZACIÓN COMPLETA DEL SISTEMA ENTERPRISE**

    Ejecuta la inicialización orquestada de todo el sistema:

    1.   **Verificación de Estado**: Analiza el estado actual
    2.   **Validación de Pre-requisitos**: Valida datos y configuraciones
    3.   **Importación de Presupuesto**: Importa desde Excel (si se proporciona)
    4.   **Auto-configuración NIT-Usuario**: Crea asignaciones automáticamente
    5.   **Vinculación de Facturas**: Vincula facturas existentes con presupuesto
    6.   **Activación de Workflow**: Activa workflow de aprobación
    7.   **Reporte Ejecutivo**: Genera reporte completo

    **Características Enterprise:**
    - Transacciones atómicas (todo o nada)
    - Rollback automático en errores
    - Idempotente (se puede ejecutar múltiples veces)
    - Logging detallado
    - Dry-run para simulación

    **Parámetros:**
    - `archivo_presupuesto`: Ruta al Excel de presupuesto (opcional)
    - `año_fiscal`: Año a procesar (default: 2025)
    - `responsable_default_id`: ID del usuario por defecto
    - `ejecutar_vinculacion`: Si debe vincular facturas (default: true)
    - `ejecutar_workflow`: Si debe activar workflow (default: true)
    - `dry_run`: Si true, solo simula sin hacer cambios (default: false)

    **Ejemplo de uso:**
    ```bash
    # Simular (dry-run)
    POST /api/v1/automation/inicializar-sistema?dry_run=true

    # Ejecutar completo
    POST /api/v1/automation/inicializar-sistema?archivo_presupuesto=presupuesto.xlsx
    ```
    """
    from app.services.inicializacion_sistema import InicializacionSistemaService

    servicio = InicializacionSistemaService(db)

    resultado = servicio.inicializar_sistema_completo(
        archivo_presupuesto=archivo_presupuesto,
        año_fiscal=año_fiscal,
        responsable_default_id=responsable_default_id,
        ejecutar_vinculacion=ejecutar_vinculacion,
        ejecutar_workflow=ejecutar_workflow,
        dry_run=dry_run
    )

    if not resultado.get("exito"):
        raise HTTPException(
            status_code=500,
            detail={
                "mensaje": "Error en la inicialización del sistema",
                "errores": resultado.get("errores", [])
            }
        )

    return resultado


# Esquemas de respuesta
class EstadisticasAutomatizacion(BaseModel):
    """Esquema para estadísticas de automatización."""
    facturas_procesadas_hoy: int
    facturas_aprobadas_automaticamente: int
    facturas_en_revision: int
    tasa_automatizacion: float
    tiempo_promedio_procesamiento: Optional[float]
    ultimo_procesamiento: Optional[datetime]


class ConfiguracionAutomatizacion(BaseModel):
    """Esquema para configuración de automatización."""
    confianza_minima_aprobacion: float = Field(ge=0.0, le=1.0, default=0.85)
    dias_historico_patron: int = Field(ge=7, le=365, default=90)
    variacion_monto_permitida: float = Field(ge=0.0, le=1.0, default=0.10)
    requiere_orden_compra: bool = False
    notificaciones_activas: bool = True
    procesamiento_automatico_activo: bool = True


class SolicitudProcesamiento(BaseModel):
    """Esquema para solicitud de procesamiento manual."""
    limite_facturas: int = Field(ge=1, le=100, default=20)
    modo_debug: bool = False
    solo_proveedor_id: Optional[int] = None
    forzar_reprocesamiento: bool = False


class ResultadoFacturaAutomatizada(BaseModel):
    """Esquema para resultado de factura procesada."""
    factura_id: int
    numero_factura: str
    decision: str
    confianza: float
    motivo: str
    fecha_procesamiento: datetime
    requiere_accion_manual: bool


# Instancias de servicios (se crean al cargar el módulo)
automation_service = AutomationService()
notification_service = NotificationService()


@router.post("/regenerar-hashes-facturas", summary="🔧 Regenerar Hashes de Facturas")
async def regenerar_hashes_facturas(
    limite: int = Query(default=1000, ge=1, le=5000, description="Límite de facturas a procesar"),
    db: Session = Depends(get_db)
):
    """
    **ENDPOINT DE MANTENIMIENTO: Regenerar Hashes de Facturas**

    Regenera los campos concepto_hash y concepto_normalizado para facturas
    que no los tienen. Estos campos son CRÍTICOS para la comparación automática.

    **¿Por qué es necesario?**
    - El concepto_hash es usado para encontrar facturas del mes anterior
    - Sin él, TODAS las facturas van a revisión manual
    - Las facturas antiguas no tienen estos campos

    **Proceso:**
    1. Busca facturas con concepto_hash NULL
    2. Normaliza el concepto (lowercase, sin espacios extras)
    3. Genera MD5 hash del concepto normalizado
    4. Actualiza en BD

    **Parámetros:**
    - limite: Máximo de facturas a procesar (1-5000)

    **Retorna:**
    - total_procesadas
    - actualizadas
    - errores
    """
    try:
        import hashlib
        import re

        logger.info(f"🔧 Iniciando regeneración de hashes de facturas (límite: {limite})")

        # Obtener facturas sin concepto_hash
        facturas_sin_hash = db.query(Factura).filter(
            Factura.concepto_hash.is_(None)
        ).limit(limite).all()

        if not facturas_sin_hash:
            return {
                "success": True,
                "message": "No hay facturas sin concepto_hash",
                "data": {
                    "total_procesadas": 0,
                    "actualizadas": 0,
                    "errores": 0
                }
            }

        logger.info(f" Encontradas {len(facturas_sin_hash)} facturas sin concepto_hash")

        actualizadas = 0
        errores = 0

        for factura in facturas_sin_hash:
            try:
                # Usar concepto_principal (campo correcto en la tabla)
                concepto = factura.concepto_principal or ""

                # Si no hay concepto_principal, usar descripción de items
                if not concepto and factura.items:
                    # Concatenar descripciones de items
                    concepto = " | ".join([item.descripcion for item in factura.items if item.descripcion])

                # Si aún no hay concepto, usar número de factura como fallback
                if not concepto:
                    concepto = factura.numero_factura or "sin_concepto"

                # Normalizar concepto
                concepto_normalizado = concepto.lower().strip()
                concepto_normalizado = re.sub(r'\s+', ' ', concepto_normalizado)  # Espacios múltiples

                # Generar hash MD5
                concepto_hash = hashlib.md5(concepto_normalizado.encode('utf-8')).hexdigest()

                # Actualizar factura
                factura.concepto_normalizado = concepto_normalizado
                factura.concepto_hash = concepto_hash

                actualizadas += 1

                # Commit cada 100 facturas
                if actualizadas % 100 == 0:
                    db.commit()
                    logger.info(f"💾 Actualizadas {actualizadas} facturas")

            except Exception as e:
                logger.error(f"❌ Error procesando factura {factura.id}: {str(e)}", exc_info=True)
                errores += 1

        # Commit final
        db.commit()

        logger.info(f" Regeneración completada: {actualizadas} facturas actualizadas, {errores} errores")

        return {
            "success": True,
            "message": f"Regenerados hashes para {actualizadas} facturas",
            "data": {
                "total_procesadas": len(facturas_sin_hash),
                "actualizadas": actualizadas,
                "errores": errores
            }
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error crítico regenerando hashes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerando hashes: {str(e)}"
        )


@router.post("/procesar-workflows-pendientes", summary="🚀 Procesar Workflows Pendientes (Enterprise)")
async def procesar_workflows_pendientes(
    limite: int = Query(default=100, ge=1, le=500, description="Límite de workflows a procesar"),
    solo_estado_recibida: bool = Query(default=True, description="Solo procesar workflows en estado 'recibida'"),
    ejecutar_analisis: bool = Query(default=True, description="Ejecutar análisis de comparación automática"),
    incluir_no_aprobadas: bool = Query(default=True, description="Incluir facturas no aprobadas en búsqueda (para primera ejecución)"),
    db: Session = Depends(get_db)
):
    """
    **ENDPOINT ENTERPRISE: Procesar Workflows Pendientes**

    Procesa workflows que están en estado "recibida" y ejecuta el análisis
    de aprobación automática para cada uno.

    **Flujo:**
    1. Obtiene workflows en estado "recibida"
    2. Para cada workflow, ejecuta comparación con mes anterior
    3. Evalúa criterios de aprobación automática
    4. Sincroniza estados con tabla facturas
    5. Genera notificaciones

    **Parámetros:**
    - `limite`: Máximo de workflows a procesar (1-500)
    - `solo_estado_recibida`: Si true, solo procesa workflows en estado "recibida"
    - `ejecutar_analisis`: Si true, ejecuta análisis de comparación automática

    **Retorna:**
    - Total workflows procesados
    - Aprobados automáticamente
    - Enviados a revisión
    - Errores encontrados
    """
    try:
        from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow
        from app.services.workflow_automatico import WorkflowAutomaticoService
        from app.services.comparador_items import ComparadorItemsService
        from app.crud.factura import find_factura_mes_anterior
        from sqlalchemy import and_

        logger.info(f"🚀 Iniciando procesamiento de workflows pendientes (límite: {limite})")

        # Obtener workflows pendientes
        query = db.query(WorkflowAprobacionFactura)

        if solo_estado_recibida:
            query = query.filter(WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.RECIBIDA)

        workflows_pendientes = query.limit(limite).all()

        if not workflows_pendientes:
            return {
                "success": True,
                "message": "No hay workflows pendientes de procesamiento",
                "data": {
                    "total_workflows": 0,
                    "procesados": 0,
                    "aprobados_auto": 0,
                    "en_revision": 0,
                    "errores": 0
                }
            }

        logger.info(f" Encontrados {len(workflows_pendientes)} workflows pendientes")

        # Inicializar servicios
        workflow_service = WorkflowAutomaticoService(db)
        comparador_service = ComparadorItemsService(db) if ejecutar_analisis else None

        # Contadores
        procesados = 0
        aprobados_auto = 0
        en_revision = 0
        errores = 0
        detalles = []

        for workflow in workflows_pendientes:
            try:
                factura = workflow.factura
                if not factura:
                    logger.warning(f"⚠️  Workflow {workflow.id} sin factura asociada")
                    errores += 1
                    continue

                logger.info(f" Procesando workflow {workflow.id} - Factura {factura.numero_factura}")

                # PASO 1: Buscar factura del mes anterior
                # Si incluir_no_aprobadas=True, buscar manualmente sin filtro de estado
                factura_anterior = None

                if incluir_no_aprobadas:
                    # Búsqueda manual sin filtro de estado (para primera ejecución)
                    from dateutil.relativedelta import relativedelta
                    from sqlalchemy import extract, and_

                    fecha_mes_anterior = factura.fecha_emision - relativedelta(months=1)

                    factura_anterior = db.query(Factura).filter(
                        and_(
                            Factura.proveedor_id == factura.proveedor_id,
                            Factura.concepto_hash == factura.concepto_hash,
                            extract('year', Factura.fecha_emision) == fecha_mes_anterior.year,
                            extract('month', Factura.fecha_emision) == fecha_mes_anterior.month,
                            Factura.id != factura.id
                        )
                    ).order_by(Factura.fecha_emision.desc()).first()
                else:
                    # Búsqueda normal (solo facturas aprobadas)
                    factura_anterior = find_factura_mes_anterior(
                        db=db,
                        proveedor_id=factura.proveedor_id,
                        fecha_actual=factura.fecha_emision,
                        concepto_hash=factura.concepto_hash,
                        numero_factura=factura.numero_factura
                    )

                # PASO 2: Comparar con mes anterior (si existe)
                comparacion_mes_anterior = None
                if factura_anterior:
                    diferencia_monto = abs(float(factura.total_a_pagar or 0) - float(factura_anterior.total_a_pagar or 0))
                    diferencia_porcentaje = (diferencia_monto / float(factura_anterior.total_a_pagar)) * 100 if factura_anterior.total_a_pagar else 0

                    comparacion_mes_anterior = {
                        'tiene_mes_anterior': True,
                        'factura_anterior_id': factura_anterior.id,
                        'diferencia_porcentaje': diferencia_porcentaje,
                        'decision_sugerida': 'aprobar_auto' if diferencia_porcentaje <= 5.0 else 'en_revision',
                        'razon': f'Monto varía {diferencia_porcentaje:.2f}% respecto al mes anterior',
                        'confianza': 0.95 if diferencia_porcentaje <= 5.0 else 0.60
                    }

                    # Actualizar workflow con información de comparación
                    workflow.factura_mes_anterior_id = factura_anterior.id

                    # Calcular porcentaje de similitud (0-100, nunca negativo)
                    # Si diferencia > 100%, similitud = 0%
                    porcentaje_similitud = max(0, min(100, 100 - diferencia_porcentaje))
                    workflow.porcentaje_similitud = round(porcentaje_similitud, 2)

                    workflow.es_identica_mes_anterior = (diferencia_porcentaje <= 5.0)
                    workflow.diferencias_detectadas = {
                        'monto_actual': float(factura.total_a_pagar or 0),
                        'monto_anterior': float(factura_anterior.total_a_pagar or 0),
                        'diferencia_absoluta': diferencia_monto,
                        'diferencia_porcentual': round(diferencia_porcentaje, 2)
                    }
                else:
                    comparacion_mes_anterior = {
                        'tiene_mes_anterior': False,
                        'razon': 'Sin factura del mes anterior para comparar',
                        'decision_sugerida': 'en_revision',
                        'confianza': 0.50
                    }

                # PASO 3: Decidir aprobación
                if comparacion_mes_anterior['decision_sugerida'] == 'aprobar_auto':
                    # APROBAR AUTOMÁTICAMENTE
                    workflow.estado = EstadoFacturaWorkflow.APROBADA_AUTO
                    workflow.tipo_aprobacion = TipoAprobacion.AUTOMATICA
                    workflow.aprobada = True
                    workflow.aprobada_por = 'Sistema Automático'
                    workflow.fecha_aprobacion = datetime.utcnow()
                    workflow.observaciones_aprobacion = f'Aprobada automáticamente: {comparacion_mes_anterior["razon"]}'

                    # Sincronizar con factura
                    workflow_service._sincronizar_estado_factura(workflow)

                    # ENVIAR NOTIFICACIÓN DE APROBACIÓN AUTOMÁTICA ✨
                    try:
                        from app.services.automation.notification_service import NotificationService

                        notification_service = NotificationService()

                        # Extraer información del patrón detectado
                        patron_detectado = "Mes sobre mes"
                        factura_referencia = None
                        variacion_monto = 0.0

                        if workflow.diferencias_detectadas:
                            variacion_monto = workflow.diferencias_detectadas.get('diferencia_porcentual', 0.0)
                            monto_anterior = workflow.diferencias_detectadas.get('monto_anterior', 0)
                            if monto_anterior:
                                factura_referencia = f"Factura mes anterior: ${monto_anterior:,.2f}"

                        # Obtener criterios cumplidos para la notificación
                        criterios_cumplidos = [
                            f"Variación de monto: {variacion_monto:.2f}%",
                            "Factura idéntica al mes anterior",
                            f"Similitud: {workflow.porcentaje_similitud}%"
                        ]

                        notification_service.notificar_aprobacion_automatica(
                            db=db,
                            factura=factura,
                            criterios_cumplidos=criterios_cumplidos,
                            confianza=comparacion_mes_anterior['confianza'],
                            patron_detectado=patron_detectado,
                            factura_referencia=factura_referencia,
                            variacion_monto=variacion_monto
                        )
                        logger.info(f"  📧 Notificación de aprobación automática enviada para factura {factura.numero_factura}")
                    except Exception as e:
                        logger.error(f"  ❌ Error enviando notificación de aprobación automática: {str(e)}")

                    aprobados_auto += 1
                    logger.info(f"   Workflow {workflow.id} APROBADO AUTOMÁTICAMENTE")

                    detalles.append({
                        'workflow_id': workflow.id,
                        'factura_id': factura.id,
                        'numero_factura': factura.numero_factura,
                        'decision': 'aprobada_auto',
                        'confianza': comparacion_mes_anterior['confianza'],
                        'motivo': comparacion_mes_anterior['razon']
                    })

                else:
                    # ENVIAR A REVISIÓN
                    workflow.estado = EstadoFacturaWorkflow.PENDIENTE_REVISION

                    # Sincronizar con factura
                    workflow_service._sincronizar_estado_factura(workflow)

                    en_revision += 1
                    logger.info(f"  ⚠️  Workflow {workflow.id} enviado a REVISIÓN")

                    detalles.append({
                        'workflow_id': workflow.id,
                        'factura_id': factura.id,
                        'numero_factura': factura.numero_factura,
                        'decision': 'en_revision',
                        'confianza': comparacion_mes_anterior['confianza'],
                        'motivo': comparacion_mes_anterior['razon']
                    })

                procesados += 1

                # Commit cada 50 workflows
                if procesados % 50 == 0:
                    db.commit()
                    logger.info(f"💾 Guardados {procesados} workflows procesados")

            except Exception as e:
                logger.error(f"❌ Error procesando workflow {workflow.id}: {str(e)}", exc_info=True)
                errores += 1

        # Commit final
        db.commit()

        logger.info(f" Procesamiento completado: {procesados} workflows procesados, {aprobados_auto} aprobados automáticamente, {en_revision} en revisión")

        return {
            "success": True,
            "message": f"Procesados {procesados} workflows exitosamente",
            "data": {
                "total_workflows": len(workflows_pendientes),
                "procesados": procesados,
                "aprobados_automaticamente": aprobados_auto,
                "enviados_revision": en_revision,
                "errores": errores,
                "tasa_automatizacion_pct": round((aprobados_auto / procesados * 100) if procesados > 0 else 0, 2),
                "detalles": detalles[:20]  # Primeros 20 para no saturar respuesta
            }
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error crítico en procesamiento de workflows: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error en el procesamiento de workflows: {str(e)}"
        )


@router.post("/procesar", response_model=Dict[str, Any])
async def procesar_facturas_pendientes(
    solicitud: SolicitudProcesamiento,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ejecuta el procesamiento automático de facturas pendientes.

    Esta operación puede tomar varios minutos dependiendo de la cantidad
    de facturas pendientes.
    """
    try:
        # Validar que hay facturas pendientes
        facturas_pendientes = crud_factura.get_facturas_pendientes_procesamiento(
            db, limit=solicitud.limite_facturas
        )

        if not facturas_pendientes:
            return ResponseBase(
                success=True,
                message="No hay facturas pendientes de procesamiento automático",
                data={"facturas_procesadas": 0}
            )

        # Filtrar por proveedor si se especifica
        if solicitud.solo_proveedor_id:
            facturas_pendientes = [
                f for f in facturas_pendientes
                if f.proveedor_id == solicitud.solo_proveedor_id
            ]

        # Ejecutar procesamiento
        resultado = automation_service.procesar_facturas_pendientes(
            db=db,
            limite_facturas=len(facturas_pendientes),
            modo_debug=solicitud.modo_debug
        )

        # Programar envío de notificaciones en segundo plano
        if resultado['resumen_general']['facturas_procesadas'] > 0:
            background_tasks.add_task(
                enviar_notificaciones_procesamiento,
                db,
                resultado
            )

        return ResponseBase(
            success=True,
            message=f"Procesadas {resultado['resumen_general']['facturas_procesadas']} facturas",
            data=resultado
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el procesamiento automático: {str(e)}"
        )


@router.get("/estadisticas", response_model=EstadisticasAutomatizacion)
async def obtener_estadisticas_automatizacion(
    dias_atras: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas del sistema de automatización.
    """
    try:
        fecha_inicio = datetime.utcnow() - timedelta(days=dias_atras)
        
        # Consultar facturas procesadas automáticamente
        facturas_automatizadas = crud_factura.get_facturas_procesadas_automaticamente(
            db, fecha_desde=fecha_inicio
        )
        
        # Calcular estadísticas
        total_procesadas = len(facturas_automatizadas)
        aprobadas_auto = len([
            f for f in facturas_automatizadas 
            if f.estado == EstadoFactura.aprobada_auto
        ])
        en_revision = len([
            f for f in facturas_automatizadas 
            if f.estado == EstadoFactura.en_revision
        ])
        
        tasa_automatizacion = (aprobadas_auto / max(total_procesadas, 1)) * 100
        
        # Obtener último procesamiento
        ultimo_procesamiento = None
        if facturas_automatizadas:
            ultima_factura = max(
                facturas_automatizadas, 
                key=lambda x: x.fecha_procesamiento_auto or datetime.min
            )
            ultimo_procesamiento = ultima_factura.fecha_procesamiento_auto
        
        return EstadisticasAutomatizacion(
            facturas_procesadas_hoy=total_procesadas,
            facturas_aprobadas_automaticamente=aprobadas_auto,
            facturas_en_revision=en_revision,
            tasa_automatizacion=tasa_automatizacion,
            tiempo_promedio_procesamiento=None,  # Por implementar
            ultimo_procesamiento=ultimo_procesamiento
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get("/facturas-procesadas", response_model=List[ResultadoFacturaAutomatizada])
async def obtener_facturas_procesadas(
    dias_atras: int = Query(default=7, ge=1, le=90),
    estado: Optional[str] = Query(default=None),
    proveedor_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de facturas procesadas automáticamente.
    """
    try:
        fecha_inicio = datetime.utcnow() - timedelta(days=dias_atras)
        
        # Obtener facturas procesadas
        facturas = crud_factura.get_facturas_procesadas_automaticamente(
            db, 
            fecha_desde=fecha_inicio,
            estado=estado,
            proveedor_id=proveedor_id,
            limit=limit
        )
        
        # Convertir a esquema de respuesta
        resultados = []
        for factura in facturas:
            resultado = ResultadoFacturaAutomatizada(
                factura_id=factura.id,
                numero_factura=factura.numero_factura,
                decision=factura.estado.value if factura.estado else "desconocido",
                confianza=float(factura.confianza_automatica or 0),
                motivo=factura.motivo_decision or "",
                fecha_procesamiento=factura.fecha_procesamiento_auto or datetime.utcnow(),
                requiere_accion_manual=(factura.estado != EstadoFactura.aprobada_auto)
            )
            resultados.append(resultado)
        
        return resultados
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo facturas procesadas: {str(e)}"
        )


@router.get("/configuracion", response_model=Dict[str, Any])
async def obtener_configuracion():
    """
    Obtiene la configuración actual del sistema de automatización.
    """
    try:
        config = automation_service.obtener_configuracion_actual()
        return ResponseBase(
            success=True,
            message="Configuración obtenida exitosamente",
            data=config
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo configuración: {str(e)}"
        )


@router.put("/configuracion")
async def actualizar_configuracion(
    nueva_config: ConfiguracionAutomatizacion,
    db: Session = Depends(get_db)
):
    """
    Actualiza la configuración del sistema de automatización.
    """
    try:
        # Convertir a formato interno
        config_interna = {
            'decision_engine': {
                'confianza_minima_aprobacion': nueva_config.confianza_minima_aprobacion,
                'requiere_orden_compra': nueva_config.requiere_orden_compra
            },
            'pattern_detector': {
                'dias_historico': nueva_config.dias_historico_patron,
                'tolerancia_variacion_monto': nueva_config.variacion_monto_permitida
            }
        }
        
        # Aplicar configuración
        automation_service.actualizar_configuracion(config_interna)
        
        # Registrar cambio en auditoría
        from app.crud import audit as crud_audit
        crud_audit.create_audit(
            db=db,
            entidad="configuracion_automatizacion",
            entidad_id=0,
            accion="actualizacion",
            usuario="sistema",
            detalle=nueva_config.dict()
        )
        
        return ResponseBase(
            success=True,
            message="Configuración actualizada exitosamente",
            data=nueva_config.dict()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando configuración: {str(e)}"
        )


@router.post("/reprocesar/{factura_id}")
async def reprocesar_factura(
    factura_id: int,
    modo_debug: bool = Query(default=False),
    db: Session = Depends(get_db)
):
    """
    Reprocesa una factura específica con el sistema de automatización.
    """
    try:
        # Obtener la factura
        factura = crud_factura.get_factura(db, factura_id)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        # Resetear campos de procesamiento automático
        campos_reset = {
            'patron_recurrencia': None,
            'confianza_automatica': None,
            'factura_referencia_id': None,
            'motivo_decision': None,
            'procesamiento_info': None,
            'fecha_procesamiento_auto': None,
            'aprobada_automaticamente': False
        }
        crud_factura.update_factura(db, factura, campos_reset)
        
        # Reprocesar
        resultado = automation_service.procesar_factura_individual(
            db, factura, modo_debug
        )
        
        return ResponseBase(
            success=True,
            message=f"Factura {factura.numero_factura} reprocesada exitosamente",
            data=resultado
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reprocesando factura: {str(e)}"
        )


@router.get("/patrones/{proveedor_id}")
async def analizar_patrones_proveedor(
    proveedor_id: int,
    dias_atras: int = Query(default=90, ge=30, le=365),
    db: Session = Depends(get_db)
):
    """
    Analiza los patrones de facturación de un proveedor específico.
    """
    try:
        # Obtener facturas del proveedor
        fecha_inicio = datetime.utcnow() - timedelta(days=dias_atras)
        facturas = crud_factura.get_facturas_by_proveedor_fecha(
            db, proveedor_id, fecha_inicio
        )
        
        if not facturas:
            return ResponseBase(
                success=True,
                message="No se encontraron facturas para análisis",
                data={"patrones": [], "total_facturas": 0}
            )
        
        # Agrupar por concepto normalizado y analizar patrones
        patrones_detectados = {}
        
        for factura in facturas:
            concepto = factura.concepto_normalizado or "sin_concepto"
            if concepto not in patrones_detectados:
                patrones_detectados[concepto] = []
            patrones_detectados[concepto].append(factura)
        
        # Analizar cada grupo de facturas
        analisis_patrones = []
        pattern_detector = automation_service.pattern_detector
        
        for concepto, grupo_facturas in patrones_detectados.items():
            if len(grupo_facturas) >= 2:  # Mínimo 2 facturas para detectar patrón
                # Tomar la última factura como referencia
                factura_referencia = max(grupo_facturas, key=lambda x: x.fecha_emision)
                facturas_historicas = [f for f in grupo_facturas if f.id != factura_referencia.id]
                
                resultado_patron = pattern_detector.analizar_patron_recurrencia(
                    factura_referencia, facturas_historicas
                )
                
                analisis_patrones.append({
                    'concepto': concepto,
                    'total_facturas': len(grupo_facturas),
                    'es_recurrente': resultado_patron.es_recurrente,
                    'patron_temporal': resultado_patron.patron_temporal.tipo,
                    'confianza_patron': float(resultado_patron.confianza_global),
                    'promedio_dias': resultado_patron.patron_temporal.promedio_dias,
                    'monto_estable': resultado_patron.patron_monto.estable,
                    'variacion_monto_pct': float(resultado_patron.patron_monto.variacion_porcentaje)
                })
        
        return ResponseBase(
            success=True,
            message=f"Análisis completado para {len(facturas)} facturas",
            data={
                "patrones": analisis_patrones,
                "total_facturas": len(facturas),
                "conceptos_analizados": len(patrones_detectados)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analizando patrones del proveedor: {str(e)}"
        )


@router.post("/notificar-resumen")
async def enviar_notificacion_resumen_manual(
    dias_atras: int = Query(default=1, ge=1, le=7),
    usuarios_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """
    Envía manualmente un resumen de procesamiento a los usuarios.
    """
    try:
        # Obtener estadísticas del período
        fecha_inicio = datetime.utcnow() - timedelta(days=dias_atras)
        facturas_procesadas = crud_factura.get_facturas_procesadas_automaticamente(
            db, fecha_desde=fecha_inicio
        )
        
        # Simular estadísticas de procesamiento
        estadisticas = {
            'resumen_general': {
                'facturas_procesadas': len(facturas_procesadas),
                'aprobadas_automaticamente': len([f for f in facturas_procesadas if f.estado == EstadoFactura.aprobada_auto]),
                'enviadas_revision': len([f for f in facturas_procesadas if f.estado == EstadoFactura.en_revision]),
                'tasa_automatizacion': 0
            }
        }
        
        # Calcular tasa
        if estadisticas['resumen_general']['facturas_procesadas'] > 0:
            estadisticas['resumen_general']['tasa_automatizacion'] = (
                estadisticas['resumen_general']['aprobadas_automaticamente'] / 
                estadisticas['resumen_general']['facturas_procesadas'] * 100
            )
        
        # Obtener facturas pendientes
        facturas_pendientes = crud_factura.get_facturas_pendientes_procesamiento(db)
        
        # Enviar notificación
        resultado = notification_service.enviar_resumen_procesamiento(
            db=db,
            estadisticas_procesamiento=estadisticas,
            facturas_pendientes=facturas_pendientes,
            usuarios_notificar=usuarios_ids
        )
        
        return ResponseBase(
            success=resultado['exito'],
            message="Notificación de resumen enviada" if resultado['exito'] else "Error enviando notificación",
            data=resultado
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error enviando notificación de resumen: {str(e)}"
        )


@router.get("/dashboard/metricas", summary="Métricas del Dashboard en Tiempo Real")
async def obtener_metricas_dashboard(
    db: Session = Depends(get_db)
):
    """
    **ENDPOINT OPTIMIZADO PARA DASHBOARD**

    Retorna métricas en tiempo real para el dashboard principal:
    - Facturas aprobadas automáticamente hoy
    - Facturas en revisión manual
    - Facturas pendientes de procesamiento
    - Tasa de automatización del día
    - Últimas facturas procesadas
    - Estadísticas de la última ejecución

    **Optimizado para:**
    - Respuesta rápida (< 500ms)
    - Datos agregados y cacheables
    - Formato listo para visualización
    """
    try:
        from sqlalchemy import and_, func
        from datetime import date

        hoy = datetime.utcnow().date()

        # Métricas del día actual
        facturas_aprobadas_hoy = db.query(func.count(Factura.id)).filter(
            and_(
                Factura.estado == EstadoFactura.aprobada_auto,
                func.date(Factura.fecha_procesamiento_auto) == hoy
            )
        ).scalar() or 0

        facturas_revision_hoy = db.query(func.count(Factura.id)).filter(
            and_(
                Factura.estado == EstadoFactura.en_revision,
                func.date(Factura.fecha_procesamiento_auto) == hoy
            )
        ).scalar() or 0

        facturas_pendientes_total = db.query(func.count(Factura.id)).filter(
            Factura.estado == EstadoFactura.en_revision
        ).scalar() or 0

        # Tasa de automatización del día
        total_procesadas_hoy = facturas_aprobadas_hoy + facturas_revision_hoy
        tasa_automatizacion = (
            (facturas_aprobadas_hoy / total_procesadas_hoy * 100)
            if total_procesadas_hoy > 0 else 0
        )

        # Últimas 10 facturas procesadas automáticamente
        ultimas_facturas = db.query(Factura).filter(
            Factura.fecha_procesamiento_auto.isnot(None)
        ).order_by(
            Factura.fecha_procesamiento_auto.desc()
        ).limit(10).all()

        ultimas_facturas_data = [
            {
                'id': f.id,
                'numero_factura': f.numero_factura,
                'proveedor': f.proveedor.razon_social if f.proveedor else 'N/A',
                'total': float(f.total_a_pagar) if f.total_a_pagar else 0,
                'estado': f.estado.value if f.estado else 'pendiente',
                'confianza': float(f.confianza_automatica) if f.confianza_automatica else 0,
                'fecha_procesamiento': f.fecha_procesamiento_auto.isoformat() if f.fecha_procesamiento_auto else None,
                'motivo': f.motivo_decision or 'Sin motivo'
            }
            for f in ultimas_facturas
        ]

        # Estadísticas de la última semana
        fecha_semana = datetime.utcnow() - timedelta(days=7)
        facturas_semana = db.query(func.count(Factura.id)).filter(
            and_(
                Factura.fecha_procesamiento_auto >= fecha_semana,
                Factura.estado.in_([EstadoFactura.aprobada_auto, EstadoFactura.en_revision])
            )
        ).scalar() or 0

        facturas_aprobadas_semana = db.query(func.count(Factura.id)).filter(
            and_(
                Factura.fecha_procesamiento_auto >= fecha_semana,
                Factura.estado == EstadoFactura.aprobada_auto
            )
        ).scalar() or 0

        return {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'metricas_hoy': {
                'facturas_aprobadas_automaticamente': facturas_aprobadas_hoy,
                'facturas_en_revision_manual': facturas_revision_hoy,
                'facturas_pendientes_procesamiento': facturas_pendientes_total,
                'total_procesadas': total_procesadas_hoy,
                'tasa_automatizacion_pct': round(tasa_automatizacion, 1)
            },
            'metricas_semana': {
                'total_procesadas': facturas_semana,
                'aprobadas_automaticamente': facturas_aprobadas_semana,
                'tasa_automatizacion_pct': round(
                    (facturas_aprobadas_semana / facturas_semana * 100) if facturas_semana > 0 else 0,
                    1
                )
            },
            'ultimas_facturas': ultimas_facturas_data,
            'estado_sistema': {
                'automatizacion_activa': True,
                'ultima_ejecucion': ultimas_facturas[0].fecha_procesamiento_auto.isoformat() if ultimas_facturas else None,
                'proxima_ejecucion_programada': 'Cada hora en punto'
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo métricas del dashboard: {str(e)}"
        )


# Función auxiliar para notificaciones en segundo plano
async def enviar_notificaciones_procesamiento(db: Session, resultado_procesamiento: Dict[str, Any]):
    """Envía notificaciones de procesamiento en segundo plano."""
    try:
        # Identificar facturas que requieren notificación
        facturas_revision = []
        facturas_aprobadas = []

        for factura_info in resultado_procesamiento.get('facturas_procesadas', []):
            if factura_info.get('requiere_accion_manual', False):
                facturas_revision.append(factura_info['factura_id'])
            elif factura_info.get('decision') == 'aprobacion_automatica':
                facturas_aprobadas.append(factura_info['factura_id'])

        # Enviar notificaciones para facturas que requieren revisión
        for factura_id in facturas_revision:
            factura = crud_factura.get_factura(db, factura_id)
            if factura:
                notification_service.notificar_revision_requerida(
                    db=db,
                    factura=factura,
                    motivo=factura.motivo_decision or "Requiere revisión manual",
                    confianza=float(factura.confianza_automatica or 0),
                    patron_detectado=factura.patron_recurrencia or "no_detectado"
                )

        # Enviar resumen general si se procesaron facturas
        if resultado_procesamiento['resumen_general']['facturas_procesadas'] > 0:
            facturas_pendientes = crud_factura.get_facturas_pendientes_procesamiento(db)
            notification_service.enviar_resumen_procesamiento(
                db=db,
                estadisticas_procesamiento=resultado_procesamiento,
                facturas_pendientes=facturas_pendientes
            )

    except Exception as e:
        # Registrar error pero no fallar el procesamiento principal
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error enviando notificaciones en segundo plano: {str(e)}")


# ==================== DEBUG ENDPOINT ====================

@router.get("/debug/conteos-workflows", summary="🔧 Debug: Conteos de Workflows y Facturas")
def debug_conteos_workflows(db: Session = Depends(get_db)):
    """
    Endpoint de debug para verificar inconsistencias entre workflows y facturas.
    """
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow, TipoAprobacion
    from sqlalchemy import func

    # Contar workflows por estado
    workflows_por_estado = db.query(
        WorkflowAprobacionFactura.estado,
        func.count(WorkflowAprobacionFactura.id)
    ).group_by(WorkflowAprobacionFactura.estado).all()

    # Contar workflows aprobados automáticamente
    workflows_aprobados_auto = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_AUTO
    ).count()

    # Contar por tipo de aprobación
    workflows_por_tipo = db.query(
        WorkflowAprobacionFactura.tipo_aprobacion,
        func.count(WorkflowAprobacionFactura.id)
    ).group_by(WorkflowAprobacionFactura.tipo_aprobacion).all()

    # Contar facturas por estado
    facturas_por_estado = db.query(
        Factura.estado,
        func.count(Factura.id)
    ).group_by(Factura.estado).all()

    # Facturas únicas con workflow aprobado auto
    facturas_unicas_aprobadas_auto = db.query(
        func.count(func.distinct(WorkflowAprobacionFactura.factura_id))
    ).filter(
        WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_AUTO
    ).scalar()

    # Facturas en BD con estado aprobada_auto
    facturas_bd_aprobadas_auto = db.query(Factura).filter(
        Factura.estado == EstadoFactura.aprobada_auto
    ).count()

    return {
        "workflows_por_estado": {estado.value: count for estado, count in workflows_por_estado},
        "workflows_aprobados_auto_total": workflows_aprobados_auto,
        "workflows_por_tipo_aprobacion": {
            (tipo.value if tipo else "NULL"): count
            for tipo, count in workflows_por_tipo
        },
        "facturas_por_estado": {estado.value: count for estado, count in facturas_por_estado},
        "facturas_unicas_con_workflow_aprobado_auto": facturas_unicas_aprobadas_auto,
        "facturas_bd_con_estado_aprobada_auto": facturas_bd_aprobadas_auto,
        "inconsistencia_detectada": facturas_unicas_aprobadas_auto != facturas_bd_aprobadas_auto
    }


@router.post("/resincronizar-estados-facturas", summary=" Re-sincronizar Estados de Facturas")
def resincronizar_estados_facturas(db: Session = Depends(get_db)):
    """
    Re-sincroniza el estado de TODAS las facturas basándose en TODOS sus workflows.

    Aplica la nueva lógica multi-responsable donde:
    - Si TODOS los workflows están aprobados → factura aprobada_auto
    - Si ALGUNO está pendiente → factura en_revision
    - Si ALGUNO está rechazado → factura rechazada

    Ejecutar después de corregir la lógica de sincronización.
    """
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow
    from app.services.workflow_automatico import WorkflowAutomaticoService
    from sqlalchemy import func

    # Obtener todas las facturas que tienen workflows
    facturas_con_workflows = db.query(Factura.id).filter(
        Factura.id.in_(
            db.query(WorkflowAprobacionFactura.factura_id).distinct()
        )
    ).all()

    workflow_service = WorkflowAutomaticoService(db)

    facturas_actualizadas = 0
    cambios_por_estado = {
        "aprobada_auto": 0,
        "en_revision": 0,
        "rechazada": 0,
        "aprobada": 0
    }

    for (factura_id,) in facturas_con_workflows:
        # Obtener la factura y uno de sus workflows
        factura = db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            continue

        estado_anterior = factura.estado.value

        # Obtener cualquier workflow de esta factura para llamar a sincronizar
        workflow = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.factura_id == factura_id
        ).first()

        if workflow:
            # Aplicar la nueva lógica de sincronización
            workflow_service._sincronizar_estado_factura(workflow)

            estado_nuevo = factura.estado.value

            if estado_anterior != estado_nuevo:
                facturas_actualizadas += 1
                cambios_por_estado[estado_nuevo] = cambios_por_estado.get(estado_nuevo, 0) + 1

    db.commit()

    # Obtener estadísticas finales
    facturas_finales = db.query(
        Factura.estado,
        func.count(Factura.id)
    ).group_by(Factura.estado).all()

    return {
        "success": True,
        "message": f"Re-sincronizadas {facturas_actualizadas} facturas",
        "estadisticas": {
            "total_facturas_con_workflows": len(facturas_con_workflows),
            "facturas_actualizadas": facturas_actualizadas,
            "cambios_por_estado": cambios_por_estado,
            "estados_finales": {estado.value: count for estado, count in facturas_finales}
        }
    }


@router.get("/debug/analizar-workflows-por-factura", summary="🔍 Analizar Distribución de Workflows por Factura")
def analizar_workflows_por_factura(db: Session = Depends(get_db)):
    """
    Analiza por qué 87 workflows aprobados resultan en solo 44 facturas aprobadas.

    Respuesta: Sistema multi-responsable
    - Una factura puede tener múltiples workflows (uno por responsable)
    - La factura solo se marca aprobada_auto si TODOS sus workflows están aprobados
    - Si tiene workflows mixtos (algunos aprobados, otros pendientes) → en_revision
    """
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow
    from sqlalchemy import func

    # Obtener facturas con workflows agrupados
    facturas_con_workflows = db.query(
        WorkflowAprobacionFactura.factura_id,
        func.count(WorkflowAprobacionFactura.id).label('total_workflows'),
        func.sum(
            func.case((WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_AUTO, 1), else_=0)
        ).label('workflows_aprobados_auto'),
        func.sum(
            func.case((WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.PENDIENTE_REVISION, 1), else_=0)
        ).label('workflows_pendientes')
    ).group_by(WorkflowAprobacionFactura.factura_id).all()

    # Analizar distribuciones
    facturas_todos_aprobados = 0
    facturas_mixtas = 0
    facturas_todas_pendientes = 0

    ejemplos_mixtas = []

    for factura_id, total, aprobados, pendientes in facturas_con_workflows:
        if aprobados == total and aprobados > 0:
            # TODOS los workflows aprobados
            facturas_todos_aprobados += 1
        elif aprobados > 0 and pendientes > 0:
            # Workflows MIXTOS (algunos aprobados, otros pendientes)
            facturas_mixtas += 1
            if len(ejemplos_mixtas) < 5:
                ejemplos_mixtas.append({
                    "factura_id": factura_id,
                    "total_workflows": total,
                    "aprobados_auto": aprobados,
                    "pendientes": pendientes
                })
        elif pendientes == total:
            # TODOS pendientes
            facturas_todas_pendientes += 1

    # Calcular promedio de workflows por factura
    total_facturas = len(facturas_con_workflows)
    total_workflows = sum(row[1] for row in facturas_con_workflows)
    promedio_workflows_por_factura = total_workflows / total_facturas if total_facturas > 0 else 0

    return {
        "resumen": {
            "total_facturas": total_facturas,
            "total_workflows": total_workflows,
            "promedio_workflows_por_factura": round(promedio_workflows_por_factura, 2)
        },
        "distribucion": {
            "facturas_todos_workflows_aprobados": facturas_todos_aprobados,
            "facturas_workflows_mixtos": facturas_mixtas,
            "facturas_todos_workflows_pendientes": facturas_todas_pendientes
        },
        "explicacion": {
            "porque_solo_44_aprobadas": f"De {total_facturas} facturas con workflows, solo {facturas_todos_aprobados} tienen TODOS sus workflows aprobados. Las {facturas_mixtas} facturas con workflows mixtos permanecen en 'en_revision' hasta que TODOS los usuarios aprueben.",
            "ejemplo_factura_mixta": ejemplos_mixtas[0] if ejemplos_mixtas else None
        },
        "ejemplos_facturas_mixtas": ejemplos_mixtas
    }


@router.post("/procesar-facturas-nuevas", summary="🚀 Procesar Facturas Nuevas (Llamado desde invoice_extractor)")
async def procesar_facturas_nuevas(
    db: Session = Depends(get_db)
):
    """
    **ENDPOINT PARA INVOICE_EXTRACTOR**

    Este endpoint es llamado automáticamente por invoice_extractor después
    de insertar facturas nuevas en la base de datos.

    **Flujo:**
    1. Crea workflows para facturas sin procesar (responsable_id NULL)
    2. Asigna responsables según mapeo NIT
    3. Ejecuta automatización (aprobación automática si aplica)
    4. Envía notificaciones a responsables

    **Sin autenticación requerida** - Solo llamado desde red interna

    **Retorna:**
    - Total facturas procesadas
    - Workflows creados
    - Responsables asignados
    - Notificaciones enviadas
    """
    try:
        from app.services.workflow_automatico import WorkflowAutomaticoService

        logger.info("[invoice_extractor] Procesando facturas nuevas...")

        service = WorkflowAutomaticoService(db)

        # PASO 1: Buscar facturas sin responsable (sin workflows)
        logger.info("  [PASO 1] Buscando facturas sin workflow...")
        facturas_sin_workflow = db.query(Factura).outerjoin(
            WorkflowAprobacionFactura,
            Factura.id == WorkflowAprobacionFactura.factura_id
        ).filter(
            WorkflowAprobacionFactura.id.is_(None)
        ).all()

        if not facturas_sin_workflow:
            logger.info("  No hay facturas sin workflow para procesar")
            return {
                "success": True,
                "message": "No hay facturas nuevas para procesar",
                "data": {
                    "workflows_creados": 0,
                    "facturas_procesadas": 0,
                    "aprobadas_automaticamente": 0,
                    "enviadas_revision": 0,
                    "errores": 0
                }
            }

        logger.info(f"  Encontradas {len(facturas_sin_workflow)} facturas sin workflow")

        # PASO 2: Procesar cada factura
        logger.info("  [PASO 2] Procesando facturas...")
        workflows_creados = 0
        aprobadas_auto = 0
        en_revision = 0
        errores = 0

        for factura in facturas_sin_workflow:
            try:
                resultado = service.procesar_factura_nueva(factura.id)

                if "error" in resultado:
                    errores += 1
                    logger.error(f"  Error en factura {factura.id}: {resultado['error']}")
                    continue

                workflows_creados += resultado.get('workflows_creados', 0)

                # Verificar estado final
                workflow = db.query(WorkflowAprobacionFactura).filter(
                    WorkflowAprobacionFactura.factura_id == factura.id
                ).first()

                if workflow:
                    from app.models.workflow_aprobacion import EstadoFacturaWorkflow
                    if workflow.estado == EstadoFacturaWorkflow.APROBADA_AUTO:
                        aprobadas_auto += 1
                    elif workflow.estado == EstadoFacturaWorkflow.PENDIENTE_REVISION:
                        en_revision += 1

                logger.info(f"  Procesada factura {factura.numero_factura} (ID: {factura.id})")

            except Exception as e:
                errores += 1
                logger.error(f"  Error procesando factura {factura.id}: {str(e)}")

        db.commit()

        logger.info(f"  Completado: {len(facturas_sin_workflow)} facturas procesadas")

        return {
            "success": True,
            "message": f"Procesadas {len(facturas_sin_workflow)} facturas nuevas",
            "data": {
                "workflows_creados": workflows_creados,
                "facturas_procesadas": len(facturas_sin_workflow),
                "aprobadas_automaticamente": aprobadas_auto,
                "enviadas_revision": en_revision,
                "errores": errores
            }
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error procesando facturas nuevas: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando facturas nuevas: {str(e)}"
        )


@router.post("/notificar-aprobaciones-retroactivas", summary="📧 Notificar Aprobaciones Automáticas Retroactivas")
def notificar_aprobaciones_retroactivas(
    limite: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Envía notificaciones retroactivas para facturas que fueron aprobadas automáticamente
    pero nunca se notificó al usuario (antes de implementar las notificaciones).

    Busca workflows en estado APROBADA_AUTO que no tengan notificación de tipo
    APROBACION_AUTOMATICA y les envía la notificación correspondiente.
    """
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow, TipoNotificacion, NotificacionWorkflow
    from app.services.automation.notification_service import NotificationService

    # Buscar workflows aprobados automáticamente
    workflows_aprobados_auto = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_AUTO,
        WorkflowAprobacionFactura.tipo_aprobacion == TipoAprobacion.AUTOMATICA
    ).limit(limite).all()

    if not workflows_aprobados_auto:
        return {
            "success": True,
            "message": "No hay workflows aprobados automáticamente sin notificar",
            "data": {
                "total_workflows": 0,
                "notificaciones_enviadas": 0,
                "errores": 0
            }
        }

    notification_service = NotificationService()
    notificaciones_enviadas = 0
    errores = 0
    detalles = []

    for workflow in workflows_aprobados_auto:
        try:
            # Verificar si ya tiene notificación de aprobación automática
            notificacion_existente = db.query(NotificacionWorkflow).filter(
                NotificacionWorkflow.workflow_id == workflow.id,
                NotificacionWorkflow.tipo == TipoNotificacion.APROBACION_AUTOMATICA
            ).first()

            if notificacion_existente:
                logger.info(f"  ⏭️  Workflow {workflow.id} ya tiene notificación, saltando...")
                continue

            factura = workflow.factura
            if not factura:
                logger.warning(f"  ⚠️  Workflow {workflow.id} sin factura asociada")
                errores += 1
                continue

            # Construir criterios cumplidos desde los datos guardados
            criterios_cumplidos = []
            if workflow.diferencias_detectadas:
                diferencia_pct = workflow.diferencias_detectadas.get('diferencia_porcentual', 0)
                criterios_cumplidos.append(f"Variación de monto: {diferencia_pct:.2f}%")

            if workflow.porcentaje_similitud:
                criterios_cumplidos.append(f"Similitud: {workflow.porcentaje_similitud}%")

            if workflow.es_identica_mes_anterior:
                criterios_cumplidos.append("Factura idéntica al mes anterior")

            if not criterios_cumplidos:
                criterios_cumplidos = ["Aprobada automáticamente por el sistema"]

            # Construir información del patrón detectado
            patron_detectado = "Mes sobre mes"
            factura_referencia = None
            variacion_monto = 0.0

            if workflow.diferencias_detectadas:
                variacion_monto = workflow.diferencias_detectadas.get('diferencia_porcentual', 0.0)
                monto_anterior = workflow.diferencias_detectadas.get('monto_anterior', 0)
                if monto_anterior:
                    factura_referencia = f"Factura mes anterior: ${monto_anterior:,.2f}"

            # Enviar notificación retroactiva
            resultado = notification_service.notificar_aprobacion_automatica(
                db=db,
                factura=factura,
                criterios_cumplidos=criterios_cumplidos,
                confianza=0.95,  # Default para aprobaciones retroactivas
                patron_detectado=patron_detectado,
                factura_referencia=factura_referencia,
                variacion_monto=variacion_monto
            )

            if resultado.get('exito'):
                notificaciones_enviadas += resultado.get('notificaciones_enviadas', 0)
                logger.info(f"   Notificación retroactiva enviada para workflow {workflow.id} - factura {factura.numero_factura}")

                detalles.append({
                    'workflow_id': workflow.id,
                    'factura_id': factura.id,
                    'numero_factura': factura.numero_factura,
                    'responsable': workflow.responsable.nombre if workflow.responsable else 'N/A',
                    'notificaciones_enviadas': resultado.get('notificaciones_enviadas', 0)
                })
            else:
                errores += 1
                logger.error(f"  ❌ Error enviando notificación para workflow {workflow.id}")

        except Exception as e:
            errores += 1
            logger.error(f"  ❌ Error procesando workflow {workflow.id}: {str(e)}")

    db.commit()

    return {
        "success": True,
        "message": f"Procesadas {len(workflows_aprobados_auto)} facturas aprobadas automáticamente",
        "data": {
            "total_workflows_revisados": len(workflows_aprobados_auto),
            "notificaciones_enviadas": notificaciones_enviadas,
            "errores": errores,
            "detalles": detalles[:20]  # Primeros 20 para no sobrecargar
        }
    }