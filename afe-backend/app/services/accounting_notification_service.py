# app/services/accounting_notification_service.py
"""
Servicio profesional para notificaciones al equipo de contabilidad.

Este servicio gestiona las notificaciones que se envían a los contadores en:
1. Aprobación automática (sistema aprueba por similitud)
2. Aprobación manual (responsable aprueba)
3. Rechazo manual (responsable rechaza)

Arquitectura:
- Reutiliza templates existentes de aprobación/rechazo
- Agrega variable 'destinatario_rol' para personalizar mensaje
- Obtiene contadores activos del sistema
- Integra con UnifiedEmailService para envío
- Usa URLBuilderService centralizado para construcción de URLs

ACTUALIZACIÓN 2025-11-19:
- Ahora usa URLBuilderService en lugar de settings directos
- Garantiza consistencia de URLs entre desarrollo y producción
- Mantiene patrón enterprise-grade


Fecha: 2025-11-18
Nivel: Enterprise-Grade
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.factura import Factura
from app.models.usuario import Usuario
from app.models.role import Role
from app.services.unified_email_service import UnifiedEmailService
from app.services.email_template_service import EmailTemplateService
from app.services.url_builder_service import URLBuilderService
from app.core.config import settings, Roles
from app.utils.logger import logger
from datetime import datetime


class AccountingNotificationService:
    """
    Servicio para enviar notificaciones al equipo de contabilidad.

    Casos de uso:
    - Factura aprobada automáticamente → notificar contador
    - Factura aprobada manualmente → notificar contador
    - Factura rechazada manualmente → notificar contador (para que no la esperen)
    """

    def __init__(self, db: Session):
        """
        Inicializa el servicio.

        Args:
            db: Sesión de base de datos SQLAlchemy
        """
        self.db = db
        self.email_service = UnifiedEmailService()
        self.template_service = EmailTemplateService()

    def _get_contadores_activos(self) -> List[Usuario]:
        """
        Obtiene todos los usuarios con rol 'contador' que están activos.

        Returns:
            Lista de Responsables con rol contador
        """
        try:
            # Obtener contadores usando join con tabla roles
            contadores = (
                self.db.query(Usuario)
                .join(Role, Usuario.role_id == Role.id)
                .filter(
                    Role.nombre == Roles.CONTADOR,
                    Usuario.activo == True
                )
                .all()
            )

            logger.info(
                f"Contadores activos encontrados: {len(contadores)}",
                extra={"total_contadores": len(contadores)}
            )

            return contadores

        except Exception as e:
            logger.error(
                f"Error obteniendo contadores activos: {str(e)}",
                exc_info=True
            )
            return []

    def notificar_aprobacion_automatica_a_contabilidad(
        self,
        factura: Factura,
        confianza: float,
        factura_referencia_id: Optional[int] = None
    ) -> dict:
        """
        Notifica a contadores cuando el SISTEMA aprueba automáticamente una factura.

        Este método se llama desde WorkflowAutomaticoService cuando una factura
        es aprobada automáticamente por similitud con mes anterior.

        Args:
            factura: Factura aprobada automáticamente
            confianza: Nivel de confianza de la aprobación (0.0 - 1.0)
            factura_referencia_id: ID de factura del mes anterior usada como referencia

        Returns:
            Dict con resultado
        """
        try:
            contadores = self._get_contadores_activos()

            if not contadores:
                logger.warning("No hay contadores activos para notificar (aprobación automática)")
                return {
                    "success": False,
                    "emails_enviados": 0,
                    "contadores_notificados": []
                }

            # Preparar información
            numero_factura = factura.numero_factura or "Sin número"
            nombre_proveedor = factura.proveedor.razon_social if factura.proveedor else "Proveedor desconocido"
            nit_proveedor = factura.proveedor.nit if factura.proveedor else "N/A"

            # Formatear monto
            if factura.total_a_pagar:
                monto_factura = f"${factura.total_a_pagar:,.2f} COP"
            elif factura.total_calculado:
                monto_factura = f"${factura.total_calculado:,.2f} COP"
            else:
                monto_factura = "N/A"

            fecha_aprobacion = datetime.now().strftime("%d/%m/%Y %H:%M")
            confianza_porcentaje = f"{confianza * 100:.1f}%"

            emails_enviados = 0
            contadores_notificados = []

            # Enviar a cada contador
            for contador in contadores:
                try:
                    # Construir URL de factura usando URLBuilderService (centralizado)
                    url_factura = URLBuilderService.get_factura_detail_url(factura.id)

                    context = {
                        "destinatario_rol": "contador",
                        "nombre_destinatario": contador.nombre or contador.usuario,
                        "numero_factura": numero_factura,
                        "nombre_proveedor": nombre_proveedor,
                        "nit_proveedor": nit_proveedor,
                        "cufe": factura.cufe or "No disponible",
                        "monto_factura": monto_factura,
                        "fecha_aprobacion": fecha_aprobacion,
                        "aprobado_por": f"Sistema Automático (Confianza: {confianza_porcentaje})",
                        "observaciones": f"Factura aprobada automáticamente por similitud con factura anterior. Nivel de confianza: {confianza_porcentaje}",
                        "url_factura": url_factura,
                    }

                    # Usar template especial para contador (aprobación automática)
                    html_content = self.template_service.render_template(
                        "aprobacion_automatica_contabilidad.html",
                        context
                    )

                    self.email_service.send_email(
                        to_email=contador.email,
                        subject=f"✅ Factura {numero_factura} aprobada automáticamente - Lista para procesar",
                        body_html=html_content
                    )

                    emails_enviados += 1
                    contadores_notificados.append(contador.email)

                    logger.info(
                        f"Email de aprobación automática enviado a contador: {contador.email}",
                        extra={
                            "contador_email": contador.email,
                            "factura_id": factura.id,
                            "confianza": confianza
                        }
                    )

                except Exception as e:
                    logger.error(f"Error enviando email a contador {contador.email}: {str(e)}")

            return {
                "success": emails_enviados > 0,
                "emails_enviados": emails_enviados,
                "contadores_notificados": contadores_notificados
            }

        except Exception as e:
            logger.error(f"Error en notificar_aprobacion_automatica_a_contabilidad: {str(e)}", exc_info=True)
            return {"success": False, "emails_enviados": 0, "contadores_notificados": [], "error": str(e)}

    def notificar_aprobacion_manual_a_contabilidad(
        self,
        factura: Factura,
        aprobada_por: str,
        observaciones: Optional[str] = None
    ) -> dict:
        """
        Notifica a contadores cuando un RESPONSABLE aprueba manualmente una factura.

        Este método se llama desde WorkflowAutomaticoService.aprobar_manual()

        Args:
            factura: Factura aprobada manualmente
            aprobada_por: Nombre del usuario que aprobó
            observaciones: Observaciones de la aprobación

        Returns:
            Dict con resultado
        """
        try:
            contadores = self._get_contadores_activos()

            if not contadores:
                logger.warning("No hay contadores activos para notificar (aprobación manual)")
                return {"success": False, "emails_enviados": 0, "contadores_notificados": []}

            # Preparar información
            numero_factura = factura.numero_factura or "Sin número"
            nombre_proveedor = factura.proveedor.razon_social if factura.proveedor else "Proveedor desconocido"
            nit_proveedor = factura.proveedor.nit if factura.proveedor else "N/A"

            if factura.total_a_pagar:
                monto_factura = f"${factura.total_a_pagar:,.2f} COP"
            elif factura.total_calculado:
                monto_factura = f"${factura.total_calculado:,.2f} COP"
            else:
                monto_factura = "N/A"

            fecha_aprobacion = datetime.now().strftime("%d/%m/%Y %H:%M")

            emails_enviados = 0
            contadores_notificados = []

            for contador in contadores:
                try:
                    # Construir URL de factura usando URLBuilderService (centralizado)
                    url_factura = URLBuilderService.get_factura_detail_url(factura.id)

                    context = {
                        "destinatario_rol": "contador",
                        "nombre_destinatario": contador.nombre or contador.usuario,
                        "numero_factura": numero_factura,
                        "nombre_proveedor": nombre_proveedor,
                        "nit_proveedor": nit_proveedor,
                        "cufe": factura.cufe or "No disponible",
                        "monto_factura": monto_factura,
                        "fecha_aprobacion": fecha_aprobacion,
                        "aprobado_por": aprobada_por,
                        "observaciones": observaciones,
                        "url_factura": url_factura,
                    }

                    # Usar template especial para contador (aprobación manual)
                    html_content = self.template_service.render_template(
                        "aprobacion_contabilidad.html",
                        context
                    )

                    self.email_service.send_email(
                        to_email=contador.email,
                        subject=f"✅ Factura {numero_factura} aprobada - Lista para procesar",
                        body_html=html_content
                    )

                    emails_enviados += 1
                    contadores_notificados.append(contador.email)

                    logger.info(
                        f"Email de aprobación manual enviado a contador: {contador.email}",
                        extra={"contador_email": contador.email, "factura_id": factura.id}
                    )

                except Exception as e:
                    logger.error(f"Error enviando email a contador {contador.email}: {str(e)}")

            logger.info(
                f"Notificación de aprobación manual a contabilidad completada",
                extra={"factura_id": factura.id, "emails_enviados": emails_enviados}
            )

            return {
                "success": emails_enviados > 0,
                "emails_enviados": emails_enviados,
                "contadores_notificados": contadores_notificados
            }

        except Exception as e:
            logger.error(f"Error en notificar_aprobacion_manual_a_contabilidad: {str(e)}", exc_info=True)
            return {"success": False, "emails_enviados": 0, "contadores_notificados": [], "error": str(e)}

    def notificar_rechazo_a_contabilidad(
        self,
        factura: Factura,
        rechazada_por: str,
        motivo: str,
        detalle: Optional[str] = None
    ) -> dict:
        """
        Notifica a contadores cuando un RESPONSABLE rechaza una factura.

        Importante: El contador necesita saber que una factura fue rechazada
        para que NO la espere en el flujo de pago.

        Este método se llama desde WorkflowAutomaticoService.rechazar()

        Args:
            factura: Factura rechazada
            rechazada_por: Nombre del usuario que rechazó
            motivo: Motivo del rechazo
            detalle: Detalles adicionales

        Returns:
            Dict con resultado
        """
        try:
            contadores = self._get_contadores_activos()

            if not contadores:
                logger.warning("No hay contadores activos para notificar (rechazo)")
                return {"success": False, "emails_enviados": 0, "contadores_notificados": []}

            # Preparar información
            numero_factura = factura.numero_factura or "Sin número"
            nombre_proveedor = factura.proveedor.razon_social if factura.proveedor else "Proveedor desconocido"
            nit_proveedor = factura.proveedor.nit if factura.proveedor else "N/A"

            if factura.total_a_pagar:
                monto_factura = f"${factura.total_a_pagar:,.2f} COP"
            elif factura.total_calculado:
                monto_factura = f"${factura.total_calculado:,.2f} COP"
            else:
                monto_factura = "N/A"

            fecha_rechazo = datetime.now().strftime("%d/%m/%Y %H:%M")

            emails_enviados = 0
            contadores_notificados = []

            for contador in contadores:
                try:
                    # Construir URL de factura usando URLBuilderService (centralizado)
                    url_factura = URLBuilderService.get_factura_detail_url(factura.id)

                    context = {
                        "destinatario_rol": "contador",
                        "nombre_destinatario": contador.nombre or contador.usuario,
                        "numero_factura": numero_factura,
                        "nombre_proveedor": nombre_proveedor,
                        "nit_proveedor": nit_proveedor,
                        "cufe": factura.cufe or "No disponible",
                        "monto_factura": monto_factura,
                        "fecha_rechazo": fecha_rechazo,
                        "rechazado_por": rechazada_por,
                        "motivo_rechazo": motivo,
                        "detalle": detalle,
                        "url_factura": url_factura,
                    }

                    # Usar template especial para contador (rechazo)
                    html_content = self.template_service.render_template(
                        "rechazo_contabilidad.html",
                        context
                    )

                    self.email_service.send_email(
                        to_email=contador.email,
                        subject=f"❌ Factura {numero_factura} rechazada - No procesar pago",
                        body_html=html_content
                    )

                    emails_enviados += 1
                    contadores_notificados.append(contador.email)

                    logger.info(
                        f"Email de rechazo enviado a contador: {contador.email}",
                        extra={"contador_email": contador.email, "factura_id": factura.id}
                    )

                except Exception as e:
                    logger.error(f"Error enviando email de rechazo a contador {contador.email}: {str(e)}")

            logger.info(
                f"Notificación de rechazo a contabilidad completada",
                extra={"factura_id": factura.id, "emails_enviados": emails_enviados}
            )

            return {
                "success": emails_enviados > 0,
                "emails_enviados": emails_enviados,
                "contadores_notificados": contadores_notificados
            }

        except Exception as e:
            logger.error(f"Error en notificar_rechazo_a_contabilidad: {str(e)}", exc_info=True)
            return {"success": False, "emails_enviados": 0, "contadores_notificados": [], "error": str(e)}
