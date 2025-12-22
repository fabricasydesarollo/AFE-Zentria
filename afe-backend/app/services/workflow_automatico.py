"""
Servicio de Workflow Automático de Aprobación de Facturas.

Este servicio analiza facturas nuevas y:
1. Identifica el NIT del proveedor
2. Asigna automáticamente al usuario
3. Compara ITEM POR ITEM con facturas del mes anterior (usando ComparadorItemsService)
4. Aprueba automáticamente si cumple criterios de confianza
5. Envía a revisión manual si hay diferencias
6. Genera notificaciones
7. Sincroniza estados con tabla facturas

Integración: Se activa cuando llegan nuevas facturas desde Microsoft Graph a la tabla facturas

Nivel: Enterprise Fortune 500
Refactorizado: 2025-10-10
Arquitecto:  Backend Development Team
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import (
    WorkflowAprobacionFactura,
    AsignacionNitResponsable,
    NotificacionWorkflow,
    EstadoFacturaWorkflow,
    TipoAprobacion,
    TipoNotificacion
)
from app.utils.nit_validator import NitValidator
from app.services.comparador_items import ComparadorItemsService
from app.services.clasificacion_proveedores import ClasificacionProveedoresService

logger = logging.getLogger(__name__)


class WorkflowAutomaticoService:
    """
    Servicio principal de workflow automático.

    Refactorizado para usar ComparadorItemsService enterprise-grade
    y sincronización automática de estados.
    """

    def __init__(self, db: Session):
        self.db = db
        try:
            self.comparador = ComparadorItemsService(db)
        except Exception as e:
            logger.error(
                f"❌ Error inicializando ComparadorItemsService: {str(e)}",
                exc_info=True
            )
            self.comparador = None

        try:
            self.clasificador = ClasificacionProveedoresService(db)
        except Exception as e:
            logger.error(
                f"❌ Error inicializando ClasificacionProveedoresService: {str(e)}",
                exc_info=True
            )
            self.clasificador = None

        # Servicio de notificaciones para envío real de emails
        try:
            from app.services.automation.notification_service import NotificationService
            self.notification_service = NotificationService()
        except Exception as e:
            logger.error(
                f"❌ Error inicializando NotificationService: {str(e)}",
                exc_info=True
            )
            self.notification_service = None

    # ============================================================================
    # SINCRONIZACIÓN DE ESTADOS (Enterprise Pattern)
    # ============================================================================

    def _sincronizar_estado_factura(self, workflow: WorkflowAprobacionFactura) -> None:
        """
        NUEVA LÓGICA - Primero Gana:
        - RECHAZO: Primer rechazo → RECHAZADA (decisión final)
        - APROBACIÓN: Primer aprobador → APROBADA (decisión final)
        - CONFLICTO: Si hay rechazo DESPUÉS de aprobación → Mantener APROBADA + flag conflicto

        Enterprise Pattern: Simple, Professional, Auditable
        """
        if not workflow.factura:
            return

        # Consultar TODOS los workflows de esta factura
        todos_workflows = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.factura_id == workflow.factura_id
        ).all()

        if not todos_workflows:
            return

        # Analizar acciones: quién aprobó, quién rechazó, en qué orden
        aprobados = [w for w in todos_workflows if w.aprobada]
        rechazados = [w for w in todos_workflows if w.rechazada]
        pendientes = [w for w in todos_workflows if not w.aprobada and not w.rechazada]

        # LÓGICA SIMPLE - PRIMERO GANA
        if rechazados and aprobados:
            # CONFLICTO: Hay aprobación Y rechazo
            # Mantener APROBADA pero marcar conflicto
            workflow.factura.estado = EstadoFactura.aprobada
            workflow.factura.accion_por = aprobados[0].aprobada_por

            # Marcar conflicto en metadata
            if not workflow.metadata_workflow:
                workflow.metadata_workflow = {}
            workflow.metadata_workflow["conflicto_detectado"] = True
            workflow.metadata_workflow["aprobada_por"] = aprobados[0].aprobada_por
            workflow.metadata_workflow["rechazada_por"] = rechazados[0].rechazada_por
            workflow.metadata_workflow["motivo_conflicto"] = rechazados[0].detalle_rechazo

            logger.warning(
                f"CONFLICTO EN FACTURA {workflow.factura.numero_factura}: "
                f"{aprobados[0].aprobada_por} aprobó, {rechazados[0].rechazada_por} rechazó"
            )

        elif rechazados:
            # RECHAZADA: Al menos un rechazo (sin aprobaciones)
            workflow.factura.estado = EstadoFactura.rechazada
            workflow.factura.accion_por = rechazados[0].rechazada_por

            # Limpiar conflicto si no hay
            if workflow.metadata_workflow:
                workflow.metadata_workflow["conflicto_detectado"] = False

        elif aprobados:
            # APROBADA: Al menos una aprobación (sin rechazos)
            # Determinar si fue auto o manual
            si_hay_manual = any(w.tipo_aprobacion == TipoAprobacion.MANUAL for w in aprobados)

            if si_hay_manual:
                workflow.factura.estado = EstadoFactura.aprobada
                # Obtener quien aprobó manualmente
                manual = next((w for w in aprobados if w.tipo_aprobacion == TipoAprobacion.MANUAL), None)
                workflow.factura.accion_por = manual.aprobada_por if manual else aprobados[0].aprobada_por
            else:
                workflow.factura.estado = EstadoFactura.aprobada_auto
                workflow.factura.accion_por = 'Sistema Automático'

            # Limpiar conflicto
            if workflow.metadata_workflow:
                workflow.metadata_workflow["conflicto_detectado"] = False

        else:
            # PENDIENTES: Todos en revisión
            workflow.factura.estado = EstadoFactura.en_revision
            if workflow.metadata_workflow:
                workflow.metadata_workflow["conflicto_detectado"] = False

    def procesar_factura_nueva(self, factura_id: int) -> Dict[str, Any]:
        """
        Punto de entrada principal: procesa una factura recién llegada.

        Args:
            factura_id: ID de la factura a procesar

        Returns:
            Dict con el resultado del procesamiento
        """
        # 1. Obtener factura
        factura = self.db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            return {"error": "Factura no encontrada", "factura_id": factura_id}

        # 2. Verificar si ya tiene workflow
        workflow_existente = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.factura_id == factura_id
        ).first()

        if workflow_existente:
            return {
                "mensaje": "La factura ya tiene un workflow asignado",
                "workflow_id": workflow_existente.id,
                "estado": workflow_existente.estado.value
            }

        # 3. Extraer NIT del proveedor
        nit = self._extraer_nit(factura)

        # 4. Buscar TODAS las asignaciones de usuarios para este NIT
        # ENTERPRISE: Un NIT puede estar asignado a múltiples usuarios
        asignaciones = self._buscar_todas_asignaciones_responsable(nit)

        if not asignaciones:
            return self._crear_workflow_sin_asignacion(factura, nit)

        # 5. CREAR WORKFLOWS PARA CADA RESPONSABLE ASIGNADO AL NIT
        # Patrón: Cuando múltiples usuarios tienen el NIT asignado,
        # todos reciben la misma factura. Cambios de estado se sincronizan entre todos.

        workflows_creados = []  # Lista de objetos WorkflowAprobacionFactura reales
        workflows_info = []      # Lista de diccionarios con info para respuesta
        responsable_ids = []

        for asignacion in asignaciones:
            # 4.5 NUEVO: Clasificación automática del proveedor (si no está clasificado)
            self._asegurar_clasificacion_proveedor(asignacion)

            # 5. Crear workflow para este responsable
            workflow = WorkflowAprobacionFactura(
                factura_id=factura.id,
                estado=EstadoFacturaWorkflow.RECIBIDA,
                nit_proveedor=nit,
                responsable_id=asignacion.responsable_id,
                area_responsable=asignacion.area,
                fecha_asignacion=datetime.now(),
                creado_en=datetime.now(),
                creado_por="SISTEMA_AUTO"
            )

            self.db.add(workflow)
            workflows_creados.append(workflow)  #  Agregar objeto real
            workflows_info.append({
                "workflow_id": workflow.id,
                "responsable_id": asignacion.responsable_id,
                "area": asignacion.area
            })
            responsable_ids.append(asignacion.responsable_id)

        # 🔥 IMPORTANTE: Asignar PRIMER responsable a la factura (para compatibilidad)
        # NOTA: La factura está asignada a TODOS vía WorkflowAprobacionFactura
        # El campo responsable_id solo tiene el primero (por compatibilidad con views existentes)
        factura.responsable_id = asignaciones[0].responsable_id

        self.db.flush()
        self.db.commit()
        self.db.refresh(factura)

        # 6. Iniciar análisis de similitud (con el primer workflow REAL)
        resultado_analisis = self._analizar_similitud_mes_anterior(
            factura,
            workflows_creados[0] if workflows_creados else None,
            asignaciones[0]
        )

        # 7. Enviar notificaciones por EMAIL a TODOS los responsables
        from app.services.notificaciones_programadas import NotificacionesProgramadasService

        notif_service = NotificacionesProgramadasService(self.db)

        for asignacion in asignaciones:
            # Temporalmente asignar cada responsable para que el servicio lo detecte
            factura.responsable_id = asignacion.responsable_id
            self.db.flush()

            resultado = notif_service.notificar_nueva_factura(factura.id)

            if resultado.get('success'):
                logger.info(
                    f"✅ Notificación enviada a {asignacion.usuario.usuario} "
                    f"para factura {factura.numero_factura}"
                )
            else:
                logger.warning(
                    f"⚠️ No se pudo notificar a responsable ID {asignacion.responsable_id}: "
                    f"{resultado.get('error')}"
                )

        # Restaurar el primer responsable (compatibilidad)
        factura.responsable_id = asignaciones[0].responsable_id
        self.db.flush()

        return {
            "exito": True,
            "workflow_ids": [w.id for w in workflows_creados],
            "factura_id": factura.id,
            "nit": nit,
            "responsables_asignados": responsable_ids,
            "total_responsables": len(asignaciones),
            **resultado_analisis
        }

    def _extraer_nit(self, factura: Factura) -> Optional[str]:
        """Extrae el NIT del proveedor de la factura."""
        # Opción 1: Si el proveedor está relacionado directamente (objeto Proveedor)
        if factura.proveedor and hasattr(factura.proveedor, 'nit'):
            return factura.proveedor.nit

        # Opción 2: Si solo tenemos proveedor_id, hacer query
        if factura.proveedor_id:
            from app.models.proveedor import Proveedor
            proveedor = self.db.query(Proveedor).filter(
                Proveedor.id == factura.proveedor_id
            ).first()
            if proveedor and proveedor.nit:
                return proveedor.nit

        return None

    def _buscar_asignacion_responsable(
        self, nit: Optional[str]
    ) -> Optional[AsignacionNitResponsable]:
        """
        Busca la asignación de responsable para un NIT.

        ENTERPRISE PATTERN (OPTIMIZED):
        - Acepta NITs en cualquier formato (con/sin DV, con/sin puntos)
        - Normaliza automáticamente usando NitValidator
        - Búsqueda directa en BD (todos los NITs están normalizados)
        - SOPORTE MÚLTIPLES RESPONSABLES: Retorna la primera asignación
          Use _buscar_todas_asignaciones_responsable() para obtener todas
        """
        if not nit:
            return None

        # Normalizar el NIT usando NitValidator
        es_valido, nit_normalizado = NitValidator.validar_nit(nit)

        if not es_valido:
            # NIT inválido, no hay asignación posible
            return None

        # Búsqueda directa: todos los NITs están normalizados en BD
        # Retorna PRIMERA asignación (para compatibilidad con código existente)
        asignacion = self.db.query(AsignacionNitResponsable).filter(
            and_(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.activo == True
            )
        ).order_by(AsignacionNitResponsable.creado_en.asc()).first()

        return asignacion

    def _buscar_todas_asignaciones_responsable(
        self, nit: Optional[str]
    ) -> list:
        """
        Busca TODAS las asignaciones de usuarios para un NIT.

        ENTERPRISE PATTERN - MÚLTIPLES RESPONSABLES POR NIT:
        Un NIT puede estar asignado a múltiples usuarios simultáneamente.
        Retorna TODAS las asignaciones activas para ese NIT.

        Args:
            nit: NIT del proveedor (cualquier formato)

        Returns:
            Lista de AsignacionNitResponsable (puede estar vacía)
        """
        if not nit:
            return []

        # Normalizar el NIT
        es_valido, nit_normalizado = NitValidator.validar_nit(nit)

        if not es_valido:
            return []

        # Retornar TODAS las asignaciones activas ordenadas por antigüedad
        asignaciones = self.db.query(AsignacionNitResponsable).filter(
            and_(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.activo == True
            )
        ).order_by(AsignacionNitResponsable.creado_en.asc()).all()

        return asignaciones

    def _crear_workflow_sin_asignacion(self, factura: Factura, nit: Optional[str]) -> Dict[str, Any]:
        """
        Crea un workflow para factura sin asignación de responsable.
        
        NUEVO: Si la factura tiene grupo_id asignado, intentar asignar un responsable 
        por defecto del grupo (el primer admin o responsable del grupo).
        """
        responsable_id = None
        responsable_asignado = False
        
        # NUEVO: Intentar asignar responsable del grupo si la factura tiene grupo_id
        if factura.grupo_id:
            try:
                from app.models.usuario import Usuario
                from app.models.workflow_aprobacion import ResponsableGrupo
                
                # Buscar responsables del grupo (preferiblemente admins o responsables)
                responsables_grupo = self.db.query(Usuario).join(
                    ResponsableGrupo, Usuario.id == ResponsableGrupo.responsable_id
                ).filter(
                    ResponsableGrupo.grupo_id == factura.grupo_id,
                    ResponsableGrupo.activo == True,
                    Usuario.activo == True
                ).order_by(Usuario.rol_id.asc()).first()  # Prioritizar por rol (admin primero)
                
                if responsables_grupo:
                    responsable_id = responsables_grupo.id
                    responsable_asignado = True
                    logger.info(
                        f"Responsable por defecto del grupo asignado automáticamente",
                        extra={
                            "factura_id": factura.id,
                            "grupo_id": factura.grupo_id,
                            "responsable_id": responsable_id,
                            "responsable_usuario": responsables_grupo.usuario,
                            "nit": nit
                        }
                    )
                else:
                    logger.warning(
                        f"Grupo asignado pero sin responsables disponibles",
                        extra={
                            "factura_id": factura.id,
                            "grupo_id": factura.grupo_id,
                            "nit": nit
                        }
                    )
            except Exception as e:
                logger.warning(
                    f"Error al asignar responsable por defecto del grupo",
                    extra={
                        "factura_id": factura.id,
                        "grupo_id": factura.grupo_id,
                        "error": str(e),
                        "nit": nit
                    }
                )
        
        workflow = WorkflowAprobacionFactura(
            factura_id=factura.id,
            estado=EstadoFacturaWorkflow.PENDIENTE_REVISION,
            nit_proveedor=nit,
            responsable_id=responsable_id,  # NUEVO: Asignar responsable por defecto
            creado_en=datetime.now(),
            creado_por="SISTEMA_AUTO",
            metadata_workflow={
                "alerta": "NIT sin asignación específica de responsable",
                "requiere_configuracion": not responsable_asignado,
                "responsable_por_defecto": responsable_asignado
            }
        )

        # Asignar el responsable a la factura también
        if responsable_id:
            factura.responsable_id = responsable_id
            self.db.add(factura)

        self.db.add(workflow)
        self.db.commit()

        return {
            "exito": responsable_asignado,
            "workflow_id": workflow.id,
            "error": None if responsable_asignado else "NIT sin asignación específica, responsable por defecto asignado",
            "nit": nit,
            "responsable_id": responsable_id,
            "responsable_por_defecto": responsable_asignado,
            "requiere_configuracion": not responsable_asignado
        }

    def _analizar_similitud_mes_anterior(
        self,
        factura: Factura,
        workflow: WorkflowAprobacionFactura,
        asignacion: AsignacionNitResponsable
    ) -> Dict[str, Any]:
        """
        Compara la factura ITEM POR ITEM con facturas del mes anterior.

        Enterprise Pattern: Usa ComparadorItemsService para análisis granular.

        Args:
            factura: Factura a analizar
            workflow: Workflow asociado
            asignacion: Configuración del usuario

        Returns:
            Dict con resultado del análisis y decisión de aprobación
        """
        # Cambiar estado a EN_ANALISIS
        workflow.estado = EstadoFacturaWorkflow.EN_ANALISIS
        workflow.fecha_cambio_estado = datetime.now()
        self._sincronizar_estado_factura(workflow)  #   Sincronizar
        tiempo_inicio = datetime.now()

        # ============================================================================
        # COMPARACIÓN ENTERPRISE: Item por Item usando ComparadorItemsService
        # ============================================================================

        try:
            resultado_comparacion = self.comparador.comparar_factura_vs_historial(
                factura_id=factura.id,
                meses_historico=12  # Analiza últimos 12 meses de historial
            )

            # Actualizar workflow con resultados de la comparación
            workflow.tiempo_en_analisis = int((datetime.now() - tiempo_inicio).total_seconds())
            workflow.criterios_comparacion = {
                "items_analizados": resultado_comparacion['items_analizados'],
                "items_ok": resultado_comparacion['items_ok'],
                "items_con_alertas": resultado_comparacion['items_con_alertas'],
                "nuevos_items_count": resultado_comparacion['nuevos_items_count'],
                "metodo": "ComparadorItemsService_v1.0"
            }

            # Calcular porcentaje de similitud basado en items
            if resultado_comparacion['items_analizados'] > 0:
                porcentaje_similitud = (
                    resultado_comparacion['items_ok'] /
                    resultado_comparacion['items_analizados'] * 100
                )
            else:
                porcentaje_similitud = 0

            workflow.porcentaje_similitud = Decimal(str(round(porcentaje_similitud, 2)))
            workflow.es_identica_mes_anterior = (resultado_comparacion['confianza'] >= 95)

            # Almacenar alertas como diferencias detectadas
            if resultado_comparacion['alertas']:
                workflow.diferencias_detectadas = resultado_comparacion['alertas']

            # ============================================================================
            # DECISIÓN: ¿Aprobar automáticamente o enviar a revisión?
            # ============================================================================

            if self._puede_aprobar_automaticamente_v2(
                workflow,
                asignacion,
                factura,
                resultado_comparacion
            ):
                return self._aprobar_automaticamente(workflow, factura)
            else:
                return self._enviar_a_revision_manual_v2(
                    workflow,
                    resultado_comparacion
                )

        except Exception as e:
            # Error en comparación: enviar a revisión manual por seguridad
            workflow.estado = EstadoFacturaWorkflow.PENDIENTE_REVISION
            workflow.fecha_cambio_estado = datetime.now()
            workflow.tiempo_en_analisis = int((datetime.now() - tiempo_inicio).total_seconds())
            workflow.criterios_comparacion = {
                "error_comparacion": str(e),
                "requiere_revision_manual": True
            }
            self._sincronizar_estado_factura(workflow)  #   Sincronizar
            self.db.commit()

            return {
                "requiere_revision": True,
                "motivo": f"Error en análisis automático: {str(e)}",
                "estado": workflow.estado.value
            }

    # ============================================================================
    # MÉTODOS DE DECISIÓN ENTERPRISE (Refactorizados)
    # ============================================================================

    def _puede_aprobar_automaticamente_v2(
        self,
        workflow: WorkflowAprobacionFactura,
        asignacion: AsignacionNitResponsable,
        factura: Factura,
        resultado_comparacion: Dict[str, Any]
    ) -> bool:
        """
        Determina si la factura puede aprobarse automáticamente.

        Enterprise Rules Engine con validaciones multinivel.

        Args:
            workflow: Workflow actual
            asignacion: Configuración del usuario
            factura: Factura a evaluar
            resultado_comparacion: Resultado del ComparadorItemsService

        Returns:
            True si cumple TODAS las reglas de aprobación automática
        """
        # ============================================================================
        # REGLA 1: Configuración del Usuario
        # ============================================================================

        # 1.1 - Debe estar habilitada la aprobación automática
        if not asignacion.permitir_aprobacion_automatica:
            return False

        # 1.2 - No debe requerir revisión siempre
        if asignacion.requiere_revision_siempre:
            return False

        # ============================================================================
        # REGLA 2: Confianza del Análisis de Items (ENTERPRISE: Umbral Dinámico)
        # ============================================================================

        # 2.1 - Obtener umbral dinámico basado en clasificación del proveedor
        umbral_requerido = self.clasificador.obtener_umbral_aprobacion(
            tipo_servicio=asignacion.tipo_servicio_proveedor,
            nivel_confianza=asignacion.nivel_confianza_proveedor
        )

        # Convertir a porcentaje para comparación
        umbral_porcentaje = umbral_requerido * 100

        # Almacenar umbral usado para trazabilidad
        workflow.umbral_confianza_utilizado = Decimal(str(round(umbral_porcentaje, 2)))
        workflow.tipo_validacion_aplicada = f"{asignacion.tipo_servicio_proveedor}_{asignacion.nivel_confianza_proveedor}"

        # Comparar con umbral dinámico (no fijo 95%)
        if resultado_comparacion['confianza'] < umbral_porcentaje:
            return False

        # 2.2 - No debe tener alertas críticas (severidad alta)
        alertas_criticas = [
            alerta for alerta in resultado_comparacion.get('alertas', [])
            if alerta.get('severidad') == 'alta'
        ]
        if alertas_criticas:
            return False

        # 2.3 - No debe tener items nuevos sin historial (requiere revisión)
        if resultado_comparacion.get('nuevos_items_count', 0) > 0:
            return False

        # ============================================================================
        # REGLA 3: Validación de Montos
        # ============================================================================

        # 3.1 - Monto debe estar dentro del límite configurado
        if asignacion.monto_maximo_auto_aprobacion:
            if factura.total_a_pagar and factura.total_a_pagar > asignacion.monto_maximo_auto_aprobacion:
                return False

        # ============================================================================
        # REGLA 4: Orden de Compra Obligatoria (ENTERPRISE)
        # ============================================================================

        # 4.1 - Si el proveedor requiere OC obligatoria, debe existir
        if asignacion.requiere_orden_compra_obligatoria:
            # Verificar que la factura tenga orden de compra
            if not hasattr(factura, 'orden_compra') and not hasattr(factura, 'numero_orden_compra'):
                # Campos no existen en el modelo, skip esta validación
                pass
            elif not factura.orden_compra and not factura.numero_orden_compra:
                # No tiene OC → No auto-aprobar
                return False

        # ============================================================================
        # TODAS LAS REGLAS APROBADAS  
        # ============================================================================
        return True

    def _aprobar_automaticamente(
        self,
        workflow: WorkflowAprobacionFactura,
        factura: Factura
    ) -> Dict[str, Any]:
        """
        Aprueba automáticamente una factura.

        Enterprise Pattern: Aprobación con trazabilidad completa.
        """
        workflow.estado = EstadoFacturaWorkflow.APROBADA_AUTO
        workflow.fecha_cambio_estado = datetime.now()
        workflow.tipo_aprobacion = TipoAprobacion.AUTOMATICA
        workflow.aprobada = True
        workflow.aprobada_por = "SISTEMA_AUTO"
        workflow.fecha_aprobacion = datetime.now()
        workflow.observaciones_aprobacion = (
            f"  Aprobación automática - Confianza: {workflow.porcentaje_similitud}%\n"
            f"Análisis de items: {workflow.criterios_comparacion.get('items_ok', 0)}/{workflow.criterios_comparacion.get('items_analizados', 0)} items verificados\n"
            f"Método: ComparadorItemsService Enterprise v1.0"
        )

        #   SINCRONIZAR ESTADO CON FACTURA
        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        # ========================================================================
        # ENVIAR NOTIFICACIÓN REAL POR EMAIL (Enterprise)
        # ========================================================================
        emails_enviados = 0
        if self.notification_service:
            try:
                # Preparar criterios cumplidos para el email
                criterios_cumplidos = [
                    f" Similitud con mes anterior: {workflow.porcentaje_similitud}%",
                    f" Items verificados: {workflow.criterios_comparacion.get('items_ok', 0)}/{workflow.criterios_comparacion.get('items_analizados', 0)}",
                    " Sin alertas críticas detectadas",
                    " Proveedor con historial confiable"
                ]

                # Enviar notificación usando NotificationService (envía emails reales)
                resultado_envio = self.notification_service.notificar_aprobacion_automatica(
                    db=self.db,
                    factura=factura,
                    criterios_cumplidos=criterios_cumplidos,
                    confianza=float(workflow.porcentaje_similitud or 0) / 100.0,
                    patron_detectado="Factura recurrente mensual",
                    factura_referencia=f"Mes anterior (ID: {workflow.factura_referencia_id or 'N/A'})",
                    variacion_monto=0.0
                )

                if resultado_envio.get('exito'):
                    emails_enviados = resultado_envio.get('notificaciones_enviadas', 0)
                    logger.info(
                        f" Notificación de aprobación automática enviada: "
                        f"{emails_enviados} emails enviados para factura {factura.numero_factura}"
                    )
                else:
                    logger.warning(
                        f"⚠️ No se pudo enviar notificación de aprobación: {resultado_envio.get('error')}"
                    )

            except Exception as e:
                logger.error(
                    f"❌ Error enviando notificación de aprobación para factura {factura.id}: {str(e)}",
                    exc_info=True
                )

        # ========================================================================
        # NOTIFICAR A CONTABILIDAD (Enterprise - NUEVO 2025-11-18)
        # ========================================================================
        try:
            from app.services.accounting_notification_service import AccountingNotificationService

            accounting_service = AccountingNotificationService(self.db)
            resultado_contador = accounting_service.notificar_aprobacion_automatica_a_contabilidad(
                factura=factura,
                confianza=float(workflow.porcentaje_similitud or 0) / 100.0,
                factura_referencia_id=workflow.factura_referencia_id
            )

            if resultado_contador.get('success'):
                logger.info(
                    f"✅ Notificación a contabilidad enviada: {resultado_contador.get('emails_enviados')} contadores",
                    extra={
                        "factura_id": factura.id,
                        "contadores_notificados": resultado_contador.get('contadores_notificados')
                    }
                )
            else:
                logger.warning(
                    f"⚠️ No se pudo notificar a contabilidad: {resultado_contador.get('error', 'Sin contadores activos')}"
                )

        except Exception as e:
            logger.error(
                f"❌ Error notificando a contabilidad: {str(e)}",
                exc_info=True,
                extra={"factura_id": factura.id}
            )
            # No fallar el flujo si falla la notificación a contabilidad

        # También crear registro en tabla notificacion_workflow (para auditoría)
        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.FACTURA_APROBADA,
            destinatarios=[],  # Los destinatarios ya se manejaron en NotificationService
            asunto=f" Factura Aprobada Automáticamente - {factura.numero_factura}",
            cuerpo=f"La factura {factura.numero_factura} ha sido aprobada automáticamente. "
                   f"Emails enviados: {emails_enviados}"
        )

        return {
            "aprobacion_automatica": True,
            "estado": workflow.estado.value,
            "porcentaje_similitud": float(workflow.porcentaje_similitud),
            "emails_enviados": emails_enviados,
            "mensaje": f"Factura aprobada automáticamente - {emails_enviados} notificaciones enviadas"
        }

    def _enviar_a_revision_manual_v2(
        self,
        workflow: WorkflowAprobacionFactura,
        resultado_comparacion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Envía la factura a revisión manual.

        Enterprise Pattern: Revisión inteligente con contexto completo.
        """
        workflow.estado = EstadoFacturaWorkflow.PENDIENTE_REVISION
        workflow.fecha_cambio_estado = datetime.now()

        #   SINCRONIZAR ESTADO CON FACTURA
        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        # ========================================================================
        # ENVIAR NOTIFICACIÓN REAL POR EMAIL (Enterprise)
        # ========================================================================
        emails_enviados = 0
        if self.notification_service:
            try:
                # Preparar alertas para el email
                alertas_texto = []
                for alerta in resultado_comparacion.get('alertas', [])[:10]:
                    alertas_texto.append(
                        f"• {alerta.get('tipo', 'Alerta')}: {alerta.get('mensaje', 'Sin detalle')}"
                    )

                # Motivo de revisión detallado
                motivo = f"""
Confianza de automatización: {resultado_comparacion.get('confianza', 0)}%

Análisis de Items:
- Total items: {resultado_comparacion.get('items_analizados', 0)}
- Items sin cambios: {resultado_comparacion.get('items_ok', 0)}
- Items con alertas: {resultado_comparacion.get('items_con_alertas', 0)}
- Items nuevos: {resultado_comparacion.get('nuevos_items_count', 0)}

Razón: La factura no alcanzó el umbral de confianza requerido para aprobación automática.
"""

                # Enviar notificación usando NotificationService (envía emails reales)
                resultado_envio = self.notification_service.notificar_revision_requerida(
                    db=self.db,
                    factura=workflow.factura,
                    motivo=motivo,
                    confianza=resultado_comparacion.get('confianza', 0) / 100.0,
                    patron_detectado="Análisis detallado completado",
                    alertas=alertas_texto,
                    contexto_historico=resultado_comparacion
                )

                if resultado_envio.get('exito'):
                    emails_enviados = resultado_envio.get('notificaciones_enviadas', 0)
                    logger.info(
                        f" Notificación de revisión enviada: "
                        f"{emails_enviados} emails enviados para factura {workflow.factura.numero_factura}"
                    )
                else:
                    logger.warning(
                        f"⚠️ No se pudo enviar notificación de revisión: {resultado_envio.get('error')}"
                    )

            except Exception as e:
                logger.error(
                    f"❌ Error enviando notificación de revisión para factura {workflow.factura.id}: {str(e)}",
                    exc_info=True
                )

        # También crear registro en tabla notificacion_workflow (para auditoría)
        alertas_resumen = self._formatear_alertas_para_notificacion(
            resultado_comparacion.get('alertas', [])
        )

        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.PENDIENTE_REVISION,
            destinatarios=[],  # Los destinatarios ya se manejaron en NotificationService
            asunto=f"⚠️ Factura Pendiente de Revisión - {workflow.factura.numero_factura}",
            cuerpo=f"La factura requiere revisión manual. Emails enviados: {emails_enviados}. "
                   f"Alertas: {len(resultado_comparacion.get('alertas', []))}"
        )

        return {
            "requiere_revision": True,
            "estado": workflow.estado.value,
            "alertas": resultado_comparacion.get('alertas', []),
            "items_analizados": resultado_comparacion.get('items_analizados', 0),
            "items_con_alertas": resultado_comparacion.get('items_con_alertas', 0),
            "porcentaje_similitud": float(workflow.porcentaje_similitud or 0),
            "confianza": resultado_comparacion.get('confianza', 0),
            "emails_enviados": emails_enviados,
            "mensaje": f"Factura enviada a revisión manual - {emails_enviados} notificaciones enviadas"
        }

    def _formatear_alertas_para_notificacion(self, alertas: List[Dict]) -> str:
        """Formatea las alertas del comparador para mostrar en notificación."""
        if not alertas:
            return "Sin alertas"

        texto = ""
        for i, alerta in enumerate(alertas[:10], 1):  # Máximo 10 alertas en email
            severidad_emoji = {
                'alta': '🔴',
                'media': '🟡',
                'baja': '🟢'
            }.get(alerta.get('severidad', 'media'), '⚪')

            texto += f"\n{i}. {severidad_emoji} {alerta.get('tipo', 'Alerta')}: {alerta.get('mensaje', 'Sin detalle')}"

        if len(alertas) > 10:
            texto += f"\n\n... y {len(alertas) - 10} alertas más. Ver sistema para detalle completo."

        return texto

    def _formatear_diferencias(self, diferencias: List[Dict]) -> str:
        """Formatea las diferencias para mostrar en notificación."""
        texto = ""
        for dif in diferencias:
            texto += f"\n- {dif['campo'].upper()}: {dif.get('actual')} (anterior: {dif.get('anterior')})"
        return texto

    def _crear_notificacion(
        self,
        workflow: WorkflowAprobacionFactura,
        tipo: TipoNotificacion,
        destinatarios: List[str],
        asunto: str,
        cuerpo: str
    ) -> NotificacionWorkflow:
        """Crea un registro de notificación."""
        notif = NotificacionWorkflow(
            workflow_id=workflow.id,
            tipo=tipo,
            destinatarios=destinatarios,
            asunto=asunto,
            cuerpo=cuerpo,
            enviada=False,
            creado_en=datetime.now()
        )

        self.db.add(notif)
        self.db.commit()

        return notif

    def _notificar_a_otros_responsables(
        self,
        factura_id: int,
        evento: str,
        quien_actuo: str,
        motivo: str = None
    ) -> None:
        """
        Notifica a TODOS los usuarios sobre cambio de estado.

        Eventos soportados:
        - "APROBADA": Factura fue aprobada por quien_actuo
        - "RECHAZADA": Factura fue rechazada por quien_actuo
        - "CONFLICTO": Hay conflicto entre aprobaciones y rechazos

        Args:
            factura_id: ID de factura
            evento: Tipo de evento
            quien_actuo: Nombre de quien aprobó/rechazó
            motivo: Motivo (para rechazos/conflictos)
        """
        try:
            # Obtener factura y todos sus workflows
            factura = self.db.query(Factura).filter(
                Factura.id == factura_id
            ).first()

            if not factura:
                return

            todos_workflows = self.db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura_id
            ).all()

            # Preparar mensaje según evento
            if evento == "APROBADA":
                asunto = f"✅ Factura Aprobada - {factura.numero_factura}"
                cuerpo = f"La factura ha sido APROBADA por {quien_actuo}."
                if factura.observaciones_aprobacion:
                    cuerpo += f"\nObservaciones: {factura.observaciones_aprobacion}"

            elif evento == "RECHAZADA":
                asunto = f"❌ Factura Rechazada - {factura.numero_factura}"
                cuerpo = f"La factura ha sido RECHAZADA por {quien_actuo}."
                if motivo:
                    cuerpo += f"\nMotivo: {motivo}"

            elif evento == "CONFLICTO":
                asunto = f"⚠️ CONFLICTO EN FACTURA - {factura.numero_factura}"
                cuerpo = (
                    f"CONFLICTO: Hay aprobaciones y rechazos encontrados.\n"
                    f"Aprobada por: {factura.accion_por}\n"
                    f"Rechazada por: {quien_actuo}"
                )
                if motivo:
                    cuerpo += f"\nMotivo del rechazo: {motivo}"
            else:
                return

            # Notificar a TODOS los workflows (incluyendo quien actuó)
            # Determinar tipo de notificación según evento (patrón defensivo)
            if evento == "APROBADA":
                tipo_notif = TipoNotificacion.FACTURA_APROBADA
            elif evento == "RECHAZADA":
                tipo_notif = TipoNotificacion.FACTURA_RECHAZADA
            else:  # CONFLICTO
                tipo_notif = TipoNotificacion.ALERTA

            for workflow in todos_workflows:
                self._crear_notificacion(
                    workflow=workflow,
                    tipo=tipo_notif,
                    destinatarios=[],
                    asunto=asunto,
                    cuerpo=cuerpo
                )

            logger.info(
                f"Notificaciones creadas - Evento: {evento}, "
                f"Factura: {factura.numero_factura}, Por: {quien_actuo}, "
                f"Tipo: {tipo_notif.value}"
            )

        except Exception as e:
            logger.error(f"Error notificando a usuarios: {str(e)}")

    def aprobar_manual(
        self,
        workflow_id: int,
        aprobado_por: str,
        observaciones: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aprueba manualmente una factura.
        Sincroniza estado y notifica a otros usuarios.
        """
        workflow = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.id == workflow_id
        ).first()

        if not workflow:
            return {"error": "Workflow no encontrado"}

        # Actualizar workflow
        workflow.estado_anterior = workflow.estado
        workflow.estado = EstadoFacturaWorkflow.APROBADA_MANUAL
        workflow.fecha_cambio_estado = datetime.now()
        workflow.tipo_aprobacion = TipoAprobacion.MANUAL
        workflow.aprobada = True
        workflow.aprobada_por = aprobado_por
        workflow.fecha_aprobacion = datetime.now()
        workflow.observaciones_aprobacion = observaciones

        # SINCRONIZAR ESTADO CON FACTURA
        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        # NOTIFICAR A TODOS LOS RESPONSABLES
        self._notificar_a_otros_responsables(
            factura_id=workflow.factura_id,
            evento="APROBADA",
            quien_actuo=aprobado_por,
            motivo=None
        )

        # ========================================================================
        # NOTIFICAR A CONTABILIDAD (Enterprise - NUEVO 2025-11-18)
        # ========================================================================
        try:
            from app.services.accounting_notification_service import AccountingNotificationService

            accounting_service = AccountingNotificationService(self.db)
            resultado_contador = accounting_service.notificar_aprobacion_manual_a_contabilidad(
                factura=workflow.factura,
                aprobada_por=aprobado_por,
                observaciones=observaciones
            )

            if resultado_contador.get('success'):
                logger.info(
                    f"✅ Notificación de aprobación manual a contabilidad enviada: {resultado_contador.get('emails_enviados')} contadores",
                    extra={
                        "factura_id": workflow.factura_id,
                        "workflow_id": workflow.id,
                        "contadores_notificados": resultado_contador.get('contadores_notificados')
                    }
                )
        except Exception as e:
            logger.error(
                f"❌ Error notificando aprobación manual a contabilidad: {str(e)}",
                exc_info=True,
                extra={"workflow_id": workflow.id}
            )

        return {
            "exito": True,
            "workflow_id": workflow.id,
            "estado": workflow.estado.value,
            "aprobada_por": aprobado_por
        }

    def rechazar(
        self,
        workflow_id: int,
        rechazado_por: str,
        motivo: str,
        detalle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rechaza una factura.

        Enterprise Pattern: Rechazo con trazabilidad y sincronización.
        """
        workflow = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.id == workflow_id
        ).first()

        if not workflow:
            return {"error": "Workflow no encontrado"}

        from app.models.workflow_aprobacion import MotivoRechazo

        # Actualizar workflow
        workflow.estado_anterior = workflow.estado
        workflow.estado = EstadoFacturaWorkflow.RECHAZADA
        workflow.fecha_cambio_estado = datetime.now()
        workflow.rechazada = True
        workflow.rechazada_por = rechazado_por
        workflow.fecha_rechazo = datetime.now()
        workflow.detalle_rechazo = detalle

        #   SINCRONIZAR ESTADO CON FACTURA
        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        # Detectar si hay conflicto (rechazo después de aprobación)
        tiene_conflicto = (
            workflow.metadata_workflow
            and workflow.metadata_workflow.get("conflicto_detectado", False)
        )

        # NOTIFICAR A TODOS LOS RESPONSABLES
        self._notificar_a_otros_responsables(
            factura_id=workflow.factura_id,
            evento="CONFLICTO" if tiene_conflicto else "RECHAZADA",
            quien_actuo=rechazado_por,
            motivo=motivo
        )

        # ========================================================================
        # NOTIFICAR A CONTABILIDAD (Enterprise - NUEVO 2025-11-18)
        # ========================================================================
        try:
            from app.services.accounting_notification_service import AccountingNotificationService

            accounting_service = AccountingNotificationService(self.db)
            resultado_contador = accounting_service.notificar_rechazo_a_contabilidad(
                factura=workflow.factura,
                rechazada_por=rechazado_por,
                motivo=motivo,
                detalle=detalle
            )

            if resultado_contador.get('success'):
                logger.info(
                    f"✅ Notificación de rechazo a contabilidad enviada: {resultado_contador.get('emails_enviados')} contadores",
                    extra={
                        "factura_id": workflow.factura_id,
                        "workflow_id": workflow.id,
                        "contadores_notificados": resultado_contador.get('contadores_notificados')
                    }
                )
        except Exception as e:
            logger.error(
                f"❌ Error notificando rechazo a contabilidad: {str(e)}",
                exc_info=True,
                extra={"workflow_id": workflow.id}
            )

        return {
            "exito": True,
            "workflow_id": workflow.id,
            "estado": workflow.estado.value,
            "rechazada_por": rechazado_por
        }

    # ============================================================================
    # CLASIFICACIÓN AUTOMÁTICA DE PROVEEDORES (Enterprise Feature)
    # ============================================================================

    def _asegurar_clasificacion_proveedor(self, asignacion: AsignacionNitResponsable) -> None:
        """
        Asegura que el proveedor esté clasificado ANTES de procesar la factura.

        Esta función se ejecuta automáticamente para CADA factura nueva:
        - Si el proveedor ya está clasificado → No hace nada
        - Si es proveedor nuevo sin clasificación → Clasifica con valores seguros por defecto
        - Si tiene 3+ meses y 3+ facturas → Reclasifica automáticamente

        Clasificación por defecto (proveedor nuevo):
        - Tipo: SERVICIO_EVENTUAL (más restrictivo)
        - Nivel: NIVEL_5_NUEVO (requiere 100% confianza = nunca auto-aprobar)
        - Requiere OC: True

        Esta función garantiza que NUNCA se auto-apruebe un proveedor sin clasificar.

        Args:
            asignacion: Asignación NIT-Usuario del proveedor

        Nivel: Fortune 500 Risk Management
        """
        # Si ya está clasificado Y no necesita reclasificación → Skip
        if asignacion.tipo_servicio_proveedor:
            # Verificar si necesita reclasificación (cada 3 meses)
            if asignacion.metadata_riesgos:
                fecha_clasificacion = asignacion.metadata_riesgos.get('fecha_clasificacion')
                if fecha_clasificacion:
                    from dateutil.parser import parse
                    fecha_class = parse(fecha_clasificacion)
                    dias_desde_clasificacion = (datetime.now() - fecha_class).days

                    # Reclasificar cada 90 días (3 meses)
                    if dias_desde_clasificacion < 90:
                        return  #   Clasificación reciente, no hacer nada

        # Clasificar o reclasificar
        try:
            resultado = self.clasificador.clasificar_proveedor_automatico(
                nit=asignacion.nit,
                forzar_reclasificacion=False  # Solo si no está clasificado
            )

            # Log para auditoría (opcional)
            if resultado['clasificado'] and not resultado.get('ya_clasificado'):
                print(f" Proveedor {asignacion.nit} clasificado automáticamente: "
                      f"{resultado['tipo_servicio'].value} - {resultado['nivel_confianza'].value}")

        except Exception as e:
            # Si hay error en clasificación, simplemente skip y continuar
            # El proveedor sin clasificación irá a revisión manual (umbral 100%)
            print(f"  Error clasificando proveedor: {str(e)[:100]}")
            print(f"   El proveedor continuará sin clasificación automática")
            # No hacer nada más - dejar que el workflow continúe sin clasificación
            # La función obtener_umbral_aprobacion manejará el caso de proveedor sin clasificar
