# -*- coding: utf-8 -*-
"""
Servicio de Notificaciones Programadas - Enterprise Grade

Sistema profesional de notificaciones que sigue mejores prácticas:
- Notificación inmediata de nuevas facturas
- Resumen semanal consolidado (Lunes 8 AM)
- Alertas críticas para facturas urgentes (> 10 días)
- No spam, balanceado y efectivo

Arquitectura: Similar a SAP Concur, Oracle Financials, Workday
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.core.config import settings
from app.models.factura import Factura, EstadoFactura
from app.models.usuario import Usuario
from app.services.email_notifications import (
    enviar_notificacion_factura_pendiente
)
from app.services.url_builder_service import URLBuilderService

logger = logging.getLogger(__name__)


class NotificacionesProgramadasService:
    """
    Servicio enterprise para gestión de notificaciones programadas.

    Estrategia:
    1. Inmediata → Nuevas facturas asignadas
    2. Semanal → Resumen de pendientes (Lunes 8 AM)
    3. Urgente → Facturas críticas (> 10 días)
    """

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # 1. NOTIFICACIÓN INMEDIATA - Nueva Factura Asignada
    # ========================================================================

    def notificar_nueva_factura(self, factura_id: int) -> Dict[str, Any]:
        """
        Envía notificación inmediata cuando se asigna una nueva factura.

        Se llama desde:
        - Workflow automático cuando asigna responsable
        - Endpoint manual de asignación

        Args:
            factura_id: ID de la factura recién asignada

        Returns:
            Resultado del envío
        """
        factura = self.db.query(Factura).filter(Factura.id == factura_id).first()

        if not factura:
            return {'success': False, 'error': 'Factura no encontrada'}

        # Buscar email del usuario
        email_responsable = None
        nombre_responsable = None

        if factura.usuario and factura.usuario.email:
            email_responsable = factura.usuario.email
            nombre_responsable = factura.usuario.nombre or factura.usuario.usuario

        if not email_responsable:
            logger.warning(f"No se puede notificar nueva factura {factura.numero_factura} - sin email")
            return {'success': False, 'error': 'Usuario sin email'}

        # Calcular días desde recepción
        dias_desde_recepcion = 0
        if factura.fecha_emision:
            dias_desde_recepcion = (datetime.now().date() - factura.fecha_emision).days

        # Enviar notificación
        from app.services.email_notifications import enviar_notificacion_factura_pendiente

        # Construir URL usando URLBuilderService (centralizado)
        url_factura = URLBuilderService.get_factura_detail_url(factura.id)

        resultado = enviar_notificacion_factura_pendiente(
            email_responsable=email_responsable,
            nombre_responsable=nombre_responsable,
            numero_factura=factura.numero_factura or f"ID-{factura.id}",
            nombre_proveedor=factura.proveedor.razon_social if factura.proveedor else "N/A",
            nit_proveedor=factura.proveedor.nit if factura.proveedor else "N/A",
            monto_factura=f"${factura.total_calculado:,.2f} COP" if factura.total_calculado else "N/A",
            fecha_recepcion=factura.fecha_emision.strftime("%Y-%m-%d") if factura.fecha_emision else "N/A",
            centro_costos="N/A",  # TODO: Agregar centro de costos si existe
            dias_pendiente=dias_desde_recepcion,
            link_sistema=url_factura
        )

        if resultado.get('success'):
            logger.info(f"Notificacion de nueva factura enviada: {factura.numero_factura} -> {email_responsable}")

        return resultado

    # ========================================================================
    # 2. RESUMEN SEMANAL - Facturas Pendientes (Lunes 8 AM)
    # ========================================================================

    def enviar_resumen_semanal(self) -> Dict[str, Any]:
        """
        Envía resumen semanal de facturas pendientes a cada responsable.

        Se ejecuta automáticamente:
        - Día: Lunes
        - Hora: 8:00 AM

        Returns:
            Estadísticas de envío
        """
        logger.info("Iniciando envio de resumen semanal de facturas pendientes...")

        # Obtener todos los usuarios con email
        usuarios = self.db.query(Usuario).filter(
            Usuario.email.isnot(None),
            Usuario.email != '',
            Usuario.activo == True
        ).all()

        resultados = {
            'total_responsables': len(usuarios),
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'responsables_sin_facturas': 0,
            'errores': []
        }

        for responsable in usuarios:
            try:
                # Obtener facturas pendientes del usuario
                facturas_pendientes = self.db.query(Factura).filter(
                    and_(
                        Factura.responsable_id == responsable.id,
                        Factura.estado == EstadoFactura.en_revision
                    )
                ).all()

                if not facturas_pendientes:
                    resultados['responsables_sin_facturas'] += 1
                    continue

                # Clasificar facturas por urgencia
                urgentes = []  # > 10 días
                pendientes = []  # 3-10 días
                recientes = []  # < 3 días

                for factura in facturas_pendientes:
                    dias = self._calcular_dias_pendiente(factura)

                    if dias > 10:
                        urgentes.append((factura, dias))
                    elif dias >= 3:
                        pendientes.append((factura, dias))
                    else:
                        recientes.append((factura, dias))

                # Enviar email con resumen
                resultado = self._enviar_email_resumen_semanal(
                    responsable=responsable,
                    urgentes=urgentes,
                    pendientes=pendientes,
                    recientes=recientes
                )

                if resultado.get('success'):
                    resultados['emails_enviados'] += 1
                else:
                    resultados['emails_fallidos'] += 1
                    resultados['errores'].append({
                        'responsable': responsable.usuario,
                        'error': resultado.get('error')
                    })

            except Exception as e:
                logger.error(f"Error enviando resumen a {responsable.usuario}: {str(e)}")
                resultados['emails_fallidos'] += 1
                resultados['errores'].append({
                    'responsable': responsable.usuario,
                    'error': str(e)
                })

        logger.info(
            f"Resumen semanal completado: {resultados['emails_enviados']} enviados, "
            f"{resultados['emails_fallidos']} fallidos, "
            f"{resultados['responsables_sin_facturas']} sin facturas"
        )

        return resultados

    # ========================================================================
    # 3. ALERTAS URGENTES - Facturas Críticas (> 10 días)
    # ========================================================================

    def enviar_alertas_urgentes(self) -> Dict[str, Any]:
        """
        Envía alertas urgentes para facturas con más de 10 días sin revisar.

        Se ejecuta automáticamente:
        - Frecuencia: Cada 3 días
        - Hora: 8:00 AM

        Returns:
            Estadísticas de envío
        """
        logger.info("Iniciando envio de alertas urgentes...")

        # Obtener facturas urgentes (> 10 días pendientes)
        facturas_urgentes = self.db.query(Factura).filter(
            and_(
                Factura.estado == EstadoFactura.en_revision,
                Factura.responsable_id.isnot(None)
            )
        ).all()

        # Filtrar por días
        facturas_criticas = []
        for factura in facturas_urgentes:
            dias = self._calcular_dias_pendiente(factura)
            if dias > 10:
                facturas_criticas.append((factura, dias))

        if not facturas_criticas:
            logger.info("No hay facturas urgentes (> 10 dias)")
            return {'total': 0, 'enviados': 0}

        # Agrupar por responsable
        por_responsable = {}
        for factura, dias in facturas_criticas:
            resp_id = factura.responsable_id
            if resp_id not in por_responsable:
                por_responsable[resp_id] = []
            por_responsable[resp_id].append((factura, dias))

        # Enviar alertas
        resultados = {'total': len(facturas_criticas), 'enviados': 0, 'fallidos': 0}

        for resp_id, facturas in por_responsable.items():
            responsable = self.db.query(Usuario).filter(Usuario.id == resp_id).first()

            if not responsable or not responsable.email:
                continue

            try:
                resultado = self._enviar_email_alerta_urgente(responsable, facturas)

                if resultado.get('success'):
                    resultados['enviados'] += len(facturas)
                else:
                    resultados['fallidos'] += len(facturas)

            except Exception as e:
                logger.error(f"Error enviando alerta urgente a {responsable.usuario}: {str(e)}")
                resultados['fallidos'] += len(facturas)

        logger.info(f"Alertas urgentes: {resultados['enviados']} facturas notificadas")
        return resultados

    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================

    def _calcular_dias_pendiente(self, factura: Factura) -> int:
        """Calcula días que lleva una factura pendiente."""
        if not factura.fecha_emision:
            return 0
        return (datetime.now().date() - factura.fecha_emision).days

    def _enviar_email_resumen_semanal(
        self,
        responsable: Usuario,
        urgentes: List,
        pendientes: List,
        recientes: List
    ) -> Dict[str, Any]:
        """Envía email de resumen semanal."""
        from app.services.unified_email_service import get_unified_email_service

        # Construir HTML del resumen
        total_facturas = len(urgentes) + len(pendientes) + len(recientes)
        total_monto = sum(
            f.total_calculado or 0
            for f, _ in (urgentes + pendientes + recientes)
        )

        html_urgentes = self._generar_lista_facturas(urgentes, "URGENTES (> 10 dias)", "red")
        html_pendientes = self._generar_lista_facturas(pendientes, "PENDIENTES (3-10 dias)", "orange")
        html_recientes = self._generar_lista_facturas(recientes, "RECIENTES (< 3 dias)", "green")

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px;">
                <h1 style="color: #333; border-bottom: 3px solid #007bff; padding-bottom: 15px;">
                    Resumen Semanal - Facturas Pendientes
                </h1>

                <p>Hola <strong>{responsable.nombre or responsable.usuario}</strong>,</p>

                <p>Tienes <strong>{total_facturas} facturas</strong> pendientes de revision por un total de <strong>${total_monto:,.2f} COP</strong>.</p>

                {html_urgentes}
                {html_pendientes}
                {html_recientes}

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{settings.frontend_url}/facturas"
                       style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">
                        Ver todas en el sistema
                    </a>
                </div>

                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #777; font-size: 12px;">
                    <p>Este es un resumen semanal automatico del Sistema AFE</p>
                    <p>Zentria - Gestion de Facturas Electronicas</p>
                </div>
            </div>
        </body>
        </html>
        """

        service = get_unified_email_service()
        return service.send_email(
            to_email=responsable.email,
            subject=f"Resumen Semanal: {total_facturas} facturas pendientes",
            body_html=body_html,
            importance="normal"
        )

    def _enviar_email_alerta_urgente(
        self,
        responsable: Usuario,
        facturas: List
    ) -> Dict[str, Any]:
        """Envía email de alerta urgente."""
        from app.services.unified_email_service import get_unified_email_service

        html_facturas = self._generar_lista_facturas(facturas, "FACTURAS URGENTES", "red")

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px;">
                <h1 style="color: #dc3545; border-bottom: 3px solid #dc3545; padding-bottom: 15px;">
                    ALERTA: Facturas Urgentes
                </h1>

                <p>Hola <strong>{responsable.nombre or responsable.usuario}</strong>,</p>

                <p style="color: #dc3545; font-weight: bold;">
                    Tienes {len(facturas)} facturas con mas de 10 dias sin revisar.
                </p>

                {html_facturas}

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{settings.frontend_url}/facturas"
                       style="display: inline-block; padding: 12px 24px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 5px;">
                        Revisar urgentemente
                    </a>
                </div>

                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #777; font-size: 12px;">
                    <p>Alerta automatica del Sistema AFE</p>
                </div>
            </div>
        </body>
        </html>
        """

        service = get_unified_email_service()
        return service.send_email(
            to_email=responsable.email,
            subject=f"URGENTE: {len(facturas)} facturas pendientes > 10 dias",
            body_html=body_html,
            importance="high"
        )

    def _generar_lista_facturas(self, facturas: List, titulo: str, color: str) -> str:
        """Genera HTML para lista de facturas."""
        if not facturas:
            return ""

        color_map = {
            "red": "#dc3545",
            "orange": "#ff9800",
            "green": "#28a745"
        }

        html = f"""
        <div style="margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-left: 4px solid {color_map.get(color, '#007bff')}; border-radius: 4px;">
            <h3 style="color: {color_map.get(color, '#007bff')}; margin-top: 0;">{titulo}: {len(facturas)}</h3>
            <ul style="list-style: none; padding: 0;">
        """

        for factura, dias in facturas:
            monto = f"${factura.total_calculado:,.2f}" if factura.total_calculado else "N/A"
            proveedor = factura.proveedor.razon_social[:30] if factura.proveedor else "N/A"

            html += f"""
                <li style="padding: 8px 0; border-bottom: 1px solid #dee2e6;">
                    <strong>{factura.numero_factura}</strong> - {proveedor} - {monto} COP - <span style="color: {color_map.get(color)};">{dias} dias</span>
                </li>
            """

        html += """
            </ul>
        </div>
        """

        return html


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

def notificar_nueva_factura_asignada(db: Session, factura_id: int) -> Dict[str, Any]:
    """
    Función de conveniencia para notificar nueva factura.

    Usar desde:
    - Workflow automático
    - Endpoint de asignación manual
    """
    service = NotificacionesProgramadasService(db)
    return service.notificar_nueva_factura(factura_id)
