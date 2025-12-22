"""
Servicio de Notificaciones por Email.

Envía notificaciones relacionadas con el workflow de aprobación de facturas.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from app.models.workflow_aprobacion import NotificacionWorkflow, WorkflowAprobacionFactura
from app.core.config import settings


class NotificacionService:
    """
    Servicio para envío de notificaciones por email.
    """

    def __init__(self, db: Session):
        self.db = db
        # Configuración SMTP (ajustar según tu proveedor)
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', None)
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
        self.from_email = getattr(settings, 'FROM_EMAIL', 'noreply@afe.com')

    def enviar_notificacion(self, notificacion_id: int) -> Dict[str, Any]:
        """
        Envía una notificación por email.

        Args:
            notificacion_id: ID de la notificación a enviar

        Returns:
            Dict con resultado del envío
        """
        notif = self.db.query(NotificacionWorkflow).filter(
            NotificacionWorkflow.id == notificacion_id
        ).first()

        if not notif:
            return {"error": "Notificación no encontrada"}

        if notif.enviada:
            return {"mensaje": "Notificación ya fue enviada", "fecha_envio": notif.fecha_envio}

        try:
            # Obtener destinatarios reales
            destinatarios = self._obtener_destinatarios(notif)

            if not destinatarios:
                notif.error = "No se encontraron destinatarios"
                notif.intentos_envio += 1
                self.db.commit()
                return {"error": "No hay destinatarios para enviar"}

            # Crear mensaje
            mensaje = self._crear_mensaje_email(
                destinatarios=destinatarios,
                asunto=notif.asunto,
                cuerpo=notif.cuerpo
            )

            # Enviar
            self._enviar_email(mensaje, destinatarios)

            # Actualizar registro
            notif.enviada = True
            notif.fecha_envio = datetime.now()
            notif.intentos_envio += 1
            notif.error = None

            self.db.commit()

            return {
                "exito": True,
                "notificacion_id": notif.id,
                "destinatarios": destinatarios,
                "fecha_envio": notif.fecha_envio
            }

        except Exception as e:
            # Registrar error
            notif.error = str(e)
            notif.intentos_envio += 1
            self.db.commit()

            return {
                "error": str(e),
                "notificacion_id": notif.id,
                "intentos": notif.intentos_envio
            }

    def _obtener_destinatarios(self, notif: NotificacionWorkflow) -> List[str]:
        """
        Obtiene la lista de emails destinatarios según el tipo de notificación.

        Enterprise Pattern: Routing robusto con validaciones defensivas.
        - Los valores de tipo deben coincidir exactamente con TipoNotificacion enum
        - Se valida que workflow.responsable exista antes de acceder
        - Se elimina duplicados al final
        """
        import logging
        logger = logging.getLogger(__name__)

        destinatarios = []
        workflow = notif.workflow

        # Validación defensiva: Si workflow no existe, retornar vacío
        if not workflow:
            logger.warning(f"NotificacionWorkflow {notif.id}: workflow es None")
            return []

        # Si ya tiene destinatarios en JSON, usarlos (bypass automático)
        if notif.destinatarios and isinstance(notif.destinatarios, list) and len(notif.destinatarios) > 0:
            logger.debug(f"Usando destinatarios predefinidos para notificación {notif.id}")
            return notif.destinatarios

        # Log del tipo de notificación para debugging
        logger.debug(f"Procesando notificación {notif.id}: tipo={notif.tipo.value}")

        # Según el tipo de notificación, agregar destinatarios
        # ⚠️ CRÍTICO: Usar valores EXACTOS del enum (minúsculas)
        if notif.tipo.value in ['factura_recibida', 'pendiente_revision', 'recordatorio']:
            # Enviar al usuario asignado
            if workflow.responsable and hasattr(workflow.responsable, 'email') and workflow.responsable.email:
                destinatarios.append(workflow.responsable.email)
                logger.debug(f"Agregado responsable: {workflow.responsable.email}")

        # Notificaciones de aprobación/rechazo: ir a responsable + contabilidad
        if notif.tipo.value in ['factura_aprobada', 'factura_rechazada']:
            # 1. Enviar al usuario que actuó
            if workflow.responsable and hasattr(workflow.responsable, 'email') and workflow.responsable.email:
                destinatarios.append(workflow.responsable.email)
                logger.debug(f"Agregado responsable para {notif.tipo.value}: {workflow.responsable.email}")

            # 2. Agregar email de contabilidad (equipo que procesará el pago)
            email_contabilidad = getattr(settings, 'EMAIL_CONTABILIDAD', None)
            if email_contabilidad:
                destinatarios.append(email_contabilidad)
                logger.debug(f"Agregado email contabilidad: {email_contabilidad}")

        # Buscar emails adicionales de la asignación NIT
        from app.models.workflow_aprobacion import AsignacionNitResponsable

        if workflow.nit_proveedor:
            asignacion = self.db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == workflow.nit_proveedor
            ).first()

            if asignacion and asignacion.emails_notificacion:
                if isinstance(asignacion.emails_notificacion, list):
                    destinatarios.extend(asignacion.emails_notificacion)

        # Eliminar duplicados
        return list(set(destinatarios))

    def _crear_mensaje_email(
        self,
        destinatarios: List[str],
        asunto: str,
        cuerpo: str
    ) -> MIMEMultipart:
        """Crea el mensaje de email."""
        mensaje = MIMEMultipart('alternative')
        mensaje['Subject'] = asunto
        mensaje['From'] = self.from_email
        mensaje['To'] = ', '.join(destinatarios)

        # Crear versión HTML del cuerpo
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #333;">Sistema de Aprobación de Facturas AFE</h2>
              </div>
              <div style="padding: 20px; background-color: #fff;">
                {cuerpo.replace(chr(10), '<br>')}
              </div>
              <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; font-size: 12px; color: #666;">
                <p>Este es un mensaje automático. Por favor no responder.</p>
                <p>Sistema de Gestión de Facturas - AFE Backend</p>
              </div>
            </div>
          </body>
        </html>
        """

        # Adjuntar versión texto plano y HTML
        parte_texto = MIMEText(cuerpo, 'plain', 'utf-8')
        parte_html = MIMEText(html, 'html', 'utf-8')

        mensaje.attach(parte_texto)
        mensaje.attach(parte_html)

        return mensaje

    def _enviar_email(self, mensaje: MIMEMultipart, destinatarios: List[str]):
        """Envía el email via SMTP."""
        if not self.smtp_user or not self.smtp_password:
            # Modo de prueba: solo simular envío
            print(f"[MODO PRUEBA] Email a: {destinatarios}")
            print(f"[MODO PRUEBA] Asunto: {mensaje['Subject']}")
            return

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(mensaje)

    def enviar_notificaciones_pendientes(self, limite: int = 50) -> Dict[str, Any]:
        """
        Envía las notificaciones pendientes en lote.

        Args:
            limite: Máximo de notificaciones a procesar

        Returns:
            Dict con estadísticas de envío
        """
        notificaciones = self.db.query(NotificacionWorkflow).filter(
            NotificacionWorkflow.enviada == False
        ).limit(limite).all()

        resultados = {
            "total_procesadas": 0,
            "exitosas": 0,
            "fallidas": 0,
            "errores": []
        }

        for notif in notificaciones:
            resultado = self.enviar_notificacion(notif.id)

            resultados["total_procesadas"] += 1

            if resultado.get("exito"):
                resultados["exitosas"] += 1
            else:
                resultados["fallidas"] += 1
                resultados["errores"].append({
                    "notificacion_id": notif.id,
                    "error": resultado.get("error")
                })

        return resultados

    def enviar_recordatorios_facturas_pendientes(self, dias_pendiente: int = 3) -> Dict[str, Any]:
        """
        Envía recordatorios para facturas que llevan más de X días pendientes de revisión.

        Args:
            dias_pendiente: Días que debe estar pendiente para enviar recordatorio

        Returns:
            Dict con estadísticas
        """
        from datetime import timedelta
        from app.models.workflow_aprobacion import EstadoFacturaWorkflow, TipoNotificacion

        fecha_limite = datetime.now() - timedelta(days=dias_pendiente)

        workflows_pendientes = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.PENDIENTE_REVISION,
            WorkflowAprobacionFactura.fecha_cambio_estado <= fecha_limite
        ).all()

        recordatorios_enviados = 0

        for workflow in workflows_pendientes:
            # Verificar si ya se envió recordatorio recientemente (últimas 24h)
            ultimo_recordatorio = self.db.query(NotificacionWorkflow).filter(
                NotificacionWorkflow.workflow_id == workflow.id,
                NotificacionWorkflow.tipo == TipoNotificacion.RECORDATORIO,
                NotificacionWorkflow.creado_en >= datetime.now() - timedelta(hours=24)
            ).first()

            if ultimo_recordatorio:
                continue

            # Crear recordatorio
            from app.services.workflow_automatico import WorkflowAutomaticoService

            servicio = WorkflowAutomaticoService(self.db)
            servicio._crear_notificacion(
                workflow=workflow,
                tipo=TipoNotificacion.RECORDATORIO,
                destinatarios=[],
                asunto=f"🔔 Recordatorio: Factura Pendiente de Revisión - {workflow.factura.numero_factura}",
                cuerpo=f"""
                La factura {workflow.factura.numero_factura} lleva {dias_pendiente}+ días pendiente de revisión.

                Proveedor: {workflow.factura.proveedor}
                Monto: ${workflow.factura.total:,.2f}
                Fecha recepción: {workflow.email_fecha_recepcion or workflow.creado_en}

                Por favor, revise y apruebe o rechace la factura a la brevedad.
                """
            )

            workflow.recordatorios_enviados += 1
            recordatorios_enviados += 1

        self.db.commit()

        return {
            "facturas_pendientes": len(workflows_pendientes),
            "recordatorios_enviados": recordatorios_enviados
        }
