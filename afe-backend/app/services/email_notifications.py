# app/services/email_notifications.py
"""Servicio de notificaciones por email para el sistema AFE."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.unified_email_service import get_unified_email_service

logger = logging.getLogger(__name__)

# Directorio de plantillas (app/templates/emails/)
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"

# Configurar Jinja2 Environment
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)


def _load_template(template_name: str):
    """Carga una plantilla Jinja2 desde el sistema de archivos."""
    try:
        return _jinja_env.get_template(template_name)
    except Exception as e:
        logger.error(f"Error cargando plantilla {template_name}: {str(e)}")
        raise


def _render_template(template, **kwargs) -> str:
    """Renderiza una plantilla Jinja2 con las variables proporcionadas."""
    try:
        return template.render(**kwargs)
    except Exception as e:
        logger.error(f"Error renderizando plantilla: {str(e)}")
        raise


def enviar_notificacion_factura_aprobada(
    email_responsable: str,
    nombre_responsable: str,
    numero_factura: str,
    nombre_proveedor: str,
    nit_proveedor: str,
    monto_factura: str,
    aprobado_por: str,
    fecha_aprobacion: Optional[str] = None,
    url_factura: Optional[str] = None,
    observaciones: Optional[str] = None
) -> Dict[str, Any]:
    """Envía notificación de factura aprobada."""
    if not fecha_aprobacion:
        fecha_aprobacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Cargar y renderizar plantilla
    template = _load_template("factura_aprobada.html")
    html_body = _render_template(
        template,
        nombre_responsable=nombre_responsable,
        numero_factura=numero_factura,
        nombre_proveedor=nombre_proveedor,
        nit_proveedor=nit_proveedor,
        monto_factura=monto_factura,
        fecha_aprobacion=fecha_aprobacion,
        aprobado_por=aprobado_por,
        url_factura=url_factura,
        observaciones=observaciones
    )

    # Enviar email
    email_service = get_unified_email_service()
    return email_service.send_email(
        to_email=email_responsable,
        subject=f"  Factura {numero_factura} - APROBADA",
        body_html=html_body,
        importance="high"
    )


def enviar_notificacion_factura_rechazada(
    email_responsable: str,
    nombre_responsable: str,
    numero_factura: str,
    nombre_proveedor: str,
    nit_proveedor: str,
    monto_factura: str,
    rechazado_por: str,
    motivo_rechazo: str,
    fecha_rechazo: Optional[str] = None,
    url_factura: Optional[str] = None,
    observaciones: Optional[str] = None
) -> Dict[str, Any]:
    """Envía notificación de factura rechazada."""
    if not fecha_rechazo:
        fecha_rechazo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    template = _load_template("factura_rechazada.html")
    html_body = _render_template(
        template,
        nombre_responsable=nombre_responsable,
        numero_factura=numero_factura,
        nombre_proveedor=nombre_proveedor,
        nit_proveedor=nit_proveedor,
        monto_factura=monto_factura,
        fecha_rechazo=fecha_rechazo,
        rechazado_por=rechazado_por,
        motivo_rechazo=motivo_rechazo,
        url_factura=url_factura,
        observaciones=observaciones
    )

    email_service = get_unified_email_service()
    return email_service.send_email(
        to_email=email_responsable,
        subject=f" Factura {numero_factura} - RECHAZADA",
        body_html=html_body,
        importance="high"
    )


def enviar_notificacion_factura_pendiente(
    email_responsable: str,
    nombre_responsable: str,
    numero_factura: str,
    nombre_proveedor: str,
    nit_proveedor: str,
    monto_factura: str,
    fecha_recepcion: str,
    centro_costos: str,
    dias_pendiente: int,
    link_sistema: str
) -> Dict[str, Any]:
    """Envía notificación de factura pendiente de aprobación."""
    template = _load_template("factura_pendiente.html")
    html_body = _render_template(
        template,
        nombre_responsable=nombre_responsable,
        numero_factura=numero_factura,
        nombre_proveedor=nombre_proveedor,
        nit_proveedor=nit_proveedor,
        monto_factura=monto_factura,
        fecha_recepcion=fecha_recepcion,
        centro_costos=centro_costos,
        dias_pendiente=dias_pendiente,
        link_sistema=link_sistema
    )

    email_service = get_unified_email_service()
    return email_service.send_email(
        to_email=email_responsable,
        subject=f"⏳ Factura {numero_factura} pendiente de aprobación - {dias_pendiente} días",
        body_html=html_body,
        importance="normal" if dias_pendiente < 5 else "high"
    )


def enviar_codigo_2fa(
    email_usuario: str,
    nombre_usuario: str,
    codigo_2fa: str,
    minutos_validez: int = 10
) -> Dict[str, Any]:
    """Envía código de verificación 2FA."""
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    template = _load_template("codigo_2fa.html")
    html_body = _render_template(
        template,
        nombre_usuario=nombre_usuario,
        codigo_2fa=codigo_2fa,
        minutos_validez=minutos_validez,
        fecha_hora=fecha_hora
    )

    email_service = get_unified_email_service()
    return email_service.send_email(
        to_email=email_usuario,
        subject=f" Tu código de verificación: {codigo_2fa}",
        body_html=html_body,
        importance="high"
    )


def enviar_recuperacion_password(
    email_usuario: str,
    nombre_usuario: str,
    link_recuperacion: str,
    minutos_validez: int = 30,
    ip_address: str = "No disponible"
) -> Dict[str, Any]:
    """Envía enlace de recuperación de contraseña."""
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    template = _load_template("recuperacion_password.html")
    html_body = _render_template(
        template,
        nombre_usuario=nombre_usuario,
        link_recuperacion=link_recuperacion,
        minutos_validez=minutos_validez,
        fecha_hora=fecha_hora,
        ip_address=ip_address
    )

    email_service = get_unified_email_service()
    return email_service.send_email(
        to_email=email_usuario,
        subject="🔑 Recuperación de contraseña - Sistema AFE",
        body_html=html_body,
        importance="high"
    )
