"""
Servicio de Workflow Automático de Aprobación de Facturas.

Gestiona la aprobación automática de facturas mediante análisis de patrones
y comparación con histórico. Soporta arquitectura multi-tenant con workflows
por grupo y múltiples responsables.
"""

import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

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

    Gestiona aprobación automática de facturas con análisis de patrones
    y sincronización de estados.
    """

    def __init__(self, db: Session):
        self.db = db
        try:
            self.comparador = ComparadorItemsService(db)
        except Exception as e:
            logger.error(
                f" Error inicializando ComparadorItemsService: {str(e)}",
                exc_info=True
            )
            self.comparador = None

        try:
            self.clasificador = ClasificacionProveedoresService(db)
        except Exception as e:
            logger.error(
                f" Error inicializando ClasificacionProveedoresService: {str(e)}",
                exc_info=True
            )
            self.clasificador = None

        try:
            from app.services.automation.notification_service import NotificationService
            self.notification_service = NotificationService()
        except Exception as e:
            logger.error(
                f" Error inicializando NotificationService: {str(e)}",
                exc_info=True
            )
            self.notification_service = None

    def _sincronizar_estado_factura(self, workflow: WorkflowAprobacionFactura) -> None:
        """
        Sincroniza estado de factura basado en workflows.

        Lógica: Primera decisión gana (rechazo o aprobación).
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
        Procesa una factura recién llegada.

        Crea workflows para todos los responsables del grupo asignado.
        Requiere que la factura tenga grupo_id y que el grupo tenga responsables.

        Args:
            factura_id: ID de la factura a procesar

        Returns:
            Dict con el resultado del procesamiento
        """
        factura = self.db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            return {"error": "Factura no encontrada", "factura_id": factura_id}

        workflow_existente = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.factura_id == factura_id
        ).first()

        if workflow_existente:
            return {
                "mensaje": "La factura ya tiene un workflow asignado",
                "workflow_id": workflow_existente.id,
                "estado": workflow_existente.estado.value
            }

        nit = self._extraer_nit(factura)

        if not factura.grupo_id:
            return self._crear_workflow_sin_grupo(factura, nit)

        responsables_grupo = self._buscar_responsables_por_grupo(factura.grupo_id)

        if not responsables_grupo:
            return self._crear_workflow_grupo_sin_responsables(factura, nit)
        workflows_creados = []
        workflows_info = []
        responsable_ids = []

        asignacion_nit = self._buscar_asignacion_responsable(nit) if nit else None

        for responsable in responsables_grupo:
            if asignacion_nit and len(workflows_creados) == 0:
                self._asegurar_clasificacion_proveedor(asignacion_nit)

            workflow = WorkflowAprobacionFactura(
                factura_id=factura.id,
                estado=EstadoFacturaWorkflow.RECIBIDA,
                nit_proveedor=nit,
                responsable_id=responsable.responsable_id,
                area_responsable=responsable.responsable.area if hasattr(responsable.responsable, 'area') else None,
                fecha_asignacion=datetime.now(),
                creado_en=datetime.now(),
                creado_por="SISTEMA_AUTO"
            )

            self.db.add(workflow)
            workflows_creados.append(workflow)
            workflows_info.append({
                "workflow_id": workflow.id,
                "responsable_id": responsable.responsable_id,
                "grupo_id": factura.grupo_id
            })
            responsable_ids.append(responsable.responsable_id)

        factura.responsable_id = responsables_grupo[0].responsable_id

        self.db.flush()
        self.db.commit()
        self.db.refresh(factura)
        if asignacion_nit:
            resultado_analisis = self._analizar_similitud_mes_anterior(
                factura,
                workflows_creados[0] if workflows_creados else None,
                asignacion_nit
            )
        else:
            resultado_analisis = {
                "requiere_revision": True,
                "motivo": "Sin asignación NIT específica para análisis automático"
            }

        from app.services.notificaciones_programadas import NotificacionesProgramadasService

        notif_service = NotificacionesProgramadasService(self.db)

        for responsable in responsables_grupo:
            factura.responsable_id = responsable.responsable_id
            self.db.flush()

            resultado = notif_service.notificar_nueva_factura(factura.id)

            if resultado.get('success'):
                logger.info(
                    f"Notificación enviada a {responsable.responsable.usuario} "
                    f"(grupo_id={factura.grupo_id}) para factura {factura.numero_factura}"
                )
            else:
                logger.warning(
                    f"No se pudo notificar a responsable ID {responsable.responsable_id}: "
                    f"{resultado.get('error')}"
                )

        factura.responsable_id = responsables_grupo[0].responsable_id
        self.db.flush()

        return {
            "exito": True,
            "workflow_ids": [w.id for w in workflows_creados],
            "factura_id": factura.id,
            "nit": nit,
            "grupo_id": factura.grupo_id,
            "responsables_asignados": responsable_ids,
            "total_responsables": len(responsables_grupo),
            **resultado_analisis
        }

    def _extraer_nit(self, factura: Factura) -> Optional[str]:
        """Extrae el NIT del proveedor de la factura."""
        if factura.proveedor and hasattr(factura.proveedor, 'nit'):
            return factura.proveedor.nit

        if factura.proveedor_id:
            from app.models.proveedor import Proveedor
            proveedor = self.db.query(Proveedor).filter(
                Proveedor.id == factura.proveedor_id
            ).first()
            if proveedor and proveedor.nit:
                return proveedor.nit

        return None

    def _buscar_responsables_por_grupo(self, grupo_id: int) -> list:
        """
        Busca todos los responsables activos de un grupo.

        Args:
            grupo_id: ID del grupo

        Returns:
            Lista de objetos ResponsableGrupo
        """
        from app.models.grupo import ResponsableGrupo

        try:
            responsables = self.db.query(ResponsableGrupo).filter(
                and_(
                    ResponsableGrupo.grupo_id == grupo_id,
                    ResponsableGrupo.activo == True
                )
            ).all()

            logger.debug(
                f"Responsables encontrados para grupo",
                extra={
                    "grupo_id": grupo_id,
                    "count": len(responsables),
                    "responsables": [r.responsable_id for r in responsables]
                }
            )

            return responsables

        except Exception as e:
            logger.error(
                f"Error buscando responsables del grupo",
                extra={"grupo_id": grupo_id, "error": str(e)},
                exc_info=True
            )
            return []

    def _buscar_asignacion_responsable(
        self, nit: Optional[str]
    ) -> Optional[AsignacionNitResponsable]:
        """
        Busca la asignación de responsable para un NIT.

        Se usa para clasificación de proveedores.
        """
        if not nit:
            return None

        es_valido, nit_normalizado = NitValidator.validar_nit(nit)

        if not es_valido:
            return None

        asignacion = self.db.query(AsignacionNitResponsable).filter(
            and_(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.activo == True
            )
        ).order_by(AsignacionNitResponsable.creado_en.asc()).first()

        return asignacion

    def _crear_workflow_sin_grupo(self, factura: Factura, nit: Optional[str]) -> Dict[str, Any]:
        """Crea workflow para factura sin grupo_id asignado."""
        logger.error(
            f"ERROR CRÍTICO: Factura sin grupo_id asignado",
            extra={
                "factura_id": factura.id,
                "numero_factura": factura.numero_factura,
                "nit": nit,
                "proveedor_id": factura.proveedor_id,
                "mensaje": "invoice_service.py debe asignar grupo_id automáticamente"
            }
        )

        workflow = WorkflowAprobacionFactura(
            factura_id=factura.id,
            estado=EstadoFacturaWorkflow.PENDIENTE_REVISION,
            nit_proveedor=nit,
            responsable_id=None,
            creado_en=datetime.now(),
            creado_por="SISTEMA_AUTO",
            metadata_workflow={
                "error_critico": "Factura sin grupo_id asignado",
                "requiere_configuracion": True,
                "accion_requerida": "Verificar configuración de grupos en invoice_service.py"
            }
        )

        self.db.add(workflow)
        self.db.commit()

        return {
            "exito": False,
            "workflow_id": workflow.id,
            "error": "Factura sin grupo_id - Configuración de grupos requerida",
            "nit": nit,
            "requiere_configuracion": True,
            "accion_requerida": "Asignar grupo_id a la factura"
        }

    def _crear_workflow_grupo_sin_responsables(self, factura: Factura, nit: Optional[str]) -> Dict[str, Any]:
        """Factura en cuarentena por grupo sin responsables."""
        from app.models.grupo import Grupo

        grupo = self.db.query(Grupo).filter(Grupo.id == factura.grupo_id).first()
        nombre_grupo = grupo.nombre if grupo else f"Grupo ID {factura.grupo_id}"
        codigo_grupo = grupo.codigo if grupo else "N/A"

        logger.error(
            f"CUARENTENA: Grupo sin responsables",
            extra={
                "factura_id": factura.id,
                "numero_factura": factura.numero_factura,
                "grupo_id": factura.grupo_id,
                "nombre_grupo": nombre_grupo,
                "codigo_grupo": codigo_grupo,
                "nit": nit,
                "tipo_error": "GRUPO_SIN_RESPONSABLES",
                "clasificacion": "CONFIGURACION_GRUPOS"
            }
        )

        factura.estado = EstadoFactura.en_cuarentena

        workflow = WorkflowAprobacionFactura(
            factura_id=factura.id,
            estado=EstadoFacturaWorkflow.PENDIENTE_REVISION,
            nit_proveedor=nit,
            responsable_id=None,
            creado_en=datetime.now(),
            creado_por="SISTEMA_AUTO",
            metadata_workflow={
                "tipo_error": "GRUPO_SIN_RESPONSABLES",
                "categoria": "CONFIGURACION_GRUPOS",
                "severidad": "CRITICA",
                "grupo_id": factura.grupo_id,
                "nombre_grupo": nombre_grupo,
                "codigo_grupo": codigo_grupo,
                "accion_dirigida": {
                    "tipo": "ASIGNAR_RESPONSABLES_GRUPO",
                    "url": f"/admin/grupos/{factura.grupo_id}/responsables",
                    "descripcion": f"Asignar responsables al grupo {nombre_grupo}",
                    "parametros": {
                        "grupo_id": factura.grupo_id,
                        "nombre_grupo": nombre_grupo,
                        "codigo_grupo": codigo_grupo
                    }
                },
                "agrupable_por": f"grupo_{factura.grupo_id}",
                "mensaje_usuario": f"El grupo '{nombre_grupo}' no tiene responsables asignados. "
                                   f"Asigne al menos un responsable para procesar las facturas de este grupo.",
                "requiere_configuracion": True,
                "en_cuarentena": True,
                "bloqueada_hasta_configuracion": True
            }
        )

        self.db.add(workflow)
        self.db.commit()

        return {
            "exito": False,
            "workflow_id": workflow.id,
            "tipo_error": "GRUPO_SIN_RESPONSABLES",
            "categoria": "CONFIGURACION_GRUPOS",
            "error": f"Grupo '{nombre_grupo}' sin responsables - Factura en cuarentena",
            "grupo_id": factura.grupo_id,
            "nombre_grupo": nombre_grupo,
            "codigo_grupo": codigo_grupo,
            "nit": nit,
            "estado_factura": "en_cuarentena",
            "requiere_configuracion": True,
            "accion_dirigida": f"/admin/grupos/{factura.grupo_id}/responsables",
            "mensaje_usuario": f"Asigne responsables al grupo '{nombre_grupo}' para procesar esta factura"
        }

    def _analizar_similitud_mes_anterior(
        self,
        factura: Factura,
        workflow: WorkflowAprobacionFactura,
        asignacion: AsignacionNitResponsable
    ) -> Dict[str, Any]:
        """Compara la factura item por item con facturas del mes anterior."""
        workflow.estado = EstadoFacturaWorkflow.EN_ANALISIS
        workflow.fecha_cambio_estado = datetime.now()
        self._sincronizar_estado_factura(workflow)
        tiempo_inicio = datetime.now()

        try:
            resultado_comparacion = self.comparador.comparar_factura_vs_historial(
                factura_id=factura.id,
                meses_historico=12
            )

            workflow.tiempo_en_analisis = int((datetime.now() - tiempo_inicio).total_seconds())
            workflow.criterios_comparacion = {
                "items_analizados": resultado_comparacion['items_analizados'],
                "items_ok": resultado_comparacion['items_ok'],
                "items_con_alertas": resultado_comparacion['items_con_alertas'],
                "nuevos_items_count": resultado_comparacion['nuevos_items_count'],
                "metodo": "ComparadorItemsService_v1.0"
            }

            if resultado_comparacion['items_analizados'] > 0:
                porcentaje_similitud = (
                    resultado_comparacion['items_ok'] /
                    resultado_comparacion['items_analizados'] * 100
                )
            else:
                porcentaje_similitud = 0

            workflow.porcentaje_similitud = Decimal(str(round(porcentaje_similitud, 2)))
            workflow.es_identica_mes_anterior = (resultado_comparacion['confianza'] >= 95)

            if resultado_comparacion['alertas']:
                workflow.diferencias_detectadas = resultado_comparacion['alertas']

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
            workflow.estado = EstadoFacturaWorkflow.PENDIENTE_REVISION
            workflow.fecha_cambio_estado = datetime.now()
            workflow.tiempo_en_analisis = int((datetime.now() - tiempo_inicio).total_seconds())
            workflow.criterios_comparacion = {
                "error_comparacion": str(e),
                "requiere_revision_manual": True
            }
            self._sincronizar_estado_factura(workflow)
            self.db.commit()

            return {
                "requiere_revision": True,
                "motivo": f"Error en análisis automático: {str(e)}",
                "estado": workflow.estado.value
            }

    def _puede_aprobar_automaticamente_v2(
        self,
        workflow: WorkflowAprobacionFactura,
        asignacion: AsignacionNitResponsable,
        factura: Factura,
        resultado_comparacion: Dict[str, Any]
    ) -> bool:
        """
        Determina si la factura puede aprobarse automáticamente.

        Args:
            workflow: Workflow actual
            asignacion: Configuración del usuario
            factura: Factura a evaluar
            resultado_comparacion: Resultado del ComparadorItemsService

        Returns:
            True si cumple todas las reglas de aprobación automática
        """
        if not asignacion.permitir_aprobacion_automatica:
            return False

        if asignacion.requiere_revision_siempre:
            return False

        umbral_requerido = self.clasificador.obtener_umbral_aprobacion(
            tipo_servicio=asignacion.tipo_servicio_proveedor,
            nivel_confianza=asignacion.nivel_confianza_proveedor
        )

        umbral_porcentaje = umbral_requerido * 100

        workflow.umbral_confianza_utilizado = Decimal(str(round(umbral_porcentaje, 2)))
        workflow.tipo_validacion_aplicada = f"{asignacion.tipo_servicio_proveedor}_{asignacion.nivel_confianza_proveedor}"

        if resultado_comparacion['confianza'] < umbral_porcentaje:
            return False

        alertas_criticas = [
            alerta for alerta in resultado_comparacion.get('alertas', [])
            if alerta.get('severidad') == 'alta'
        ]
        if alertas_criticas:
            return False

        if resultado_comparacion.get('nuevos_items_count', 0) > 0:
            return False

        if asignacion.monto_maximo_auto_aprobacion:
            if factura.total_a_pagar and factura.total_a_pagar > asignacion.monto_maximo_auto_aprobacion:
                return False

        if asignacion.requiere_orden_compra_obligatoria:
            if not hasattr(factura, 'orden_compra') and not hasattr(factura, 'numero_orden_compra'):
                pass
            elif not factura.orden_compra and not factura.numero_orden_compra:
                return False

        return True

    def _aprobar_automaticamente(
        self,
        workflow: WorkflowAprobacionFactura,
        factura: Factura
    ) -> Dict[str, Any]:
        """Aprueba automáticamente una factura."""
        workflow.estado = EstadoFacturaWorkflow.APROBADA_AUTO
        workflow.fecha_cambio_estado = datetime.now()
        workflow.tipo_aprobacion = TipoAprobacion.AUTOMATICA
        workflow.aprobada = True
        workflow.aprobada_por = "SISTEMA_AUTO"
        workflow.fecha_aprobacion = datetime.now()
        workflow.observaciones_aprobacion = (
            f"Aprobación automática - Confianza: {workflow.porcentaje_similitud}%\n"
            f"Análisis de items: {workflow.criterios_comparacion.get('items_ok', 0)}/{workflow.criterios_comparacion.get('items_analizados', 0)} items verificados\n"
            f"Método: ComparadorItemsService v1.0"
        )

        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        emails_enviados = 0
        if self.notification_service:
            try:
                criterios_cumplidos = [
                    f"Similitud con mes anterior: {workflow.porcentaje_similitud}%",
                    f"Items verificados: {workflow.criterios_comparacion.get('items_ok', 0)}/{workflow.criterios_comparacion.get('items_analizados', 0)}",
                    "Sin alertas críticas detectadas",
                    "Proveedor con historial confiable"
                ]

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
                        f"No se pudo enviar notificación de aprobación: {resultado_envio.get('error')}"
                    )

            except Exception as e:
                logger.error(
                    f" Error enviando notificación de aprobación para factura {factura.id}: {str(e)}",
                    exc_info=True
                )

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
                    f"Notificación a contabilidad enviada: {resultado_contador.get('emails_enviados')} contadores",
                    extra={
                        "factura_id": factura.id,
                        "contadores_notificados": resultado_contador.get('contadores_notificados')
                    }
                )
            else:
                logger.warning(
                    f"No se pudo notificar a contabilidad: {resultado_contador.get('error', 'Sin contadores activos')}"
                )

        except Exception as e:
            logger.error(
                f" Error notificando a contabilidad: {str(e)}",
                exc_info=True,
                extra={"factura_id": factura.id}
            )

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
        """Envía la factura a revisión manual."""
        workflow.estado = EstadoFacturaWorkflow.PENDIENTE_REVISION
        workflow.fecha_cambio_estado = datetime.now()

        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        emails_enviados = 0
        if self.notification_service:
            try:
                alertas_texto = []
                for alerta in resultado_comparacion.get('alertas', [])[:10]:
                    alertas_texto.append(
                        f"• {alerta.get('tipo', 'Alerta')}: {alerta.get('mensaje', 'Sin detalle')}"
                    )

                motivo = f"""Confianza de automatización: {resultado_comparacion.get('confianza', 0)}%

Análisis de Items:
- Total items: {resultado_comparacion.get('items_analizados', 0)}
- Items sin cambios: {resultado_comparacion.get('items_ok', 0)}
- Items con alertas: {resultado_comparacion.get('items_con_alertas', 0)}
- Items nuevos: {resultado_comparacion.get('nuevos_items_count', 0)}

Razón: La factura no alcanzó el umbral de confianza requerido para aprobación automática."""

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
                        f"No se pudo enviar notificación de revisión: {resultado_envio.get('error')}"
                    )

            except Exception as e:
                logger.error(
                    f" Error enviando notificación de revisión para factura {workflow.factura.id}: {str(e)}",
                    exc_info=True
                )

        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.PENDIENTE_REVISION,
            destinatarios=[],  # Los destinatarios ya se manejaron en NotificationService
            asunto=f"Factura Pendiente de Revisión - {workflow.factura.numero_factura}",
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
                asunto = f"Factura Aprobada - {factura.numero_factura}"
                cuerpo = f"La factura ha sido APROBADA por {quien_actuo}."
                if factura.observaciones_aprobacion:
                    cuerpo += f"\nObservaciones: {factura.observaciones_aprobacion}"

            elif evento == "RECHAZADA":
                asunto = f" Factura Rechazada - {factura.numero_factura}"
                cuerpo = f"La factura ha sido RECHAZADA por {quien_actuo}."
                if motivo:
                    cuerpo += f"\nMotivo: {motivo}"

            elif evento == "CONFLICTO":
                asunto = f"CONFLICTO EN FACTURA - {factura.numero_factura}"
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
                    f"Notificación de aprobación manual a contabilidad enviada: {resultado_contador.get('emails_enviados')} contadores",
                    extra={
                        "factura_id": workflow.factura_id,
                        "workflow_id": workflow.id,
                        "contadores_notificados": resultado_contador.get('contadores_notificados')
                    }
                )
        except Exception as e:
            logger.error(
                f" Error notificando aprobación manual a contabilidad: {str(e)}",
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
                    f"Notificación de rechazo a contabilidad enviada: {resultado_contador.get('emails_enviados')} contadores",
                    extra={
                        "factura_id": workflow.factura_id,
                        "workflow_id": workflow.id,
                        "contadores_notificados": resultado_contador.get('contadores_notificados')
                    }
                )
        except Exception as e:
            logger.error(
                f" Error notificando rechazo a contabilidad: {str(e)}",
                exc_info=True,
                extra={"workflow_id": workflow.id}
            )

        return {
            "exito": True,
            "workflow_id": workflow.id,
            "estado": workflow.estado.value,
            "rechazada_por": rechazado_por
        }

    def _asegurar_clasificacion_proveedor(self, asignacion: AsignacionNitResponsable) -> None:
        """Asegura que el proveedor esté clasificado antes de procesar la factura."""
        if asignacion.tipo_servicio_proveedor:
            if asignacion.metadata_riesgos:
                fecha_clasificacion = asignacion.metadata_riesgos.get('fecha_clasificacion')
                if fecha_clasificacion:
                    from dateutil.parser import parse
                    fecha_class = parse(fecha_clasificacion)
                    dias_desde_clasificacion = (datetime.now() - fecha_class).days

                    if dias_desde_clasificacion < 90:
                        return

        try:
            resultado = self.clasificador.clasificar_proveedor_automatico(
                nit=asignacion.nit,
                forzar_reclasificacion=False
            )

            if resultado['clasificado'] and not resultado.get('ya_clasificado'):
                print(f"Proveedor {asignacion.nit} clasificado automáticamente: "
                      f"{resultado['tipo_servicio'].value} - {resultado['nivel_confianza'].value}")

        except Exception as e:
            print(f"Error clasificando proveedor: {str(e)[:100]}")
            print(f"El proveedor continuará sin clasificación automática")
