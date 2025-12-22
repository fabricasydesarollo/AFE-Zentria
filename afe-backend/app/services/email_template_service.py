# app/services/email_template_service.py
"""
Servicio de renderizado de templates de email con Jinja2.

Templates profesionales para:
- Aprobación automática
- Revisión requerida
- Error crítico
- Resumen diario
"""

import logging
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailTemplateService:
    """
    Servicio de renderizado de templates de email.

    Usa Jinja2 para renderizar templates HTML profesionales.
    """

    def __init__(self):
        # Directorio de templates (app/templates/emails/)
        self.template_dir = Path(__file__).parent.parent / 'templates' / 'emails'

        # Crear directorio si no existe
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Configurar Jinja2
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Registrar filtros personalizados
        self.env.filters['currency'] = self._format_currency
        self.env.filters['percentage'] = self._format_percentage
        self.env.filters['date_es'] = self._format_date_es

    def _format_currency(self, value: float) -> str:
        """Formatea un número como moneda colombiana."""
        return f"${value:,.2f}".replace(',', '.')

    def _format_percentage(self, value: float) -> str:
        """Formatea un número como porcentaje."""
        return f"{value:.1f}%"

    def _format_date_es(self, value: datetime | str) -> str:
        """Formatea una fecha en español."""
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))

        meses = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]

        return f"{value.day} de {meses[value.month - 1]} de {value.year}"

    def render_aprobacion_automatica(self, data: Dict[str, Any]) -> tuple[str, str]:
        """
        Renderiza email de aprobación automática.

        Args:
            data: Diccionario con datos de la factura
                - numero_factura
                - proveedor_nombre
                - monto
                - fecha_emision
                - concepto
                - confianza
                - patron_detectado
                - factura_referencia
                - variacion_monto
                - criterios_cumplidos (list)
                - responsable_nombre

        Returns:
            (html_body, text_body)
        """
        try:
            template = self.env.get_template('aprobacion_automatica.html')
            html = template.render(**data)

            # Generar versión texto
            text = self._html_to_text_aprobacion(data)

            return html, text

        except Exception as e:
            logger.error(f"Error renderizando template aprobacion_automatica: {str(e)}")
            return self._fallback_aprobacion_html(data), self._fallback_aprobacion_text(data)

    def render_revision_requerida(self, data: Dict[str, Any]) -> tuple[str, str]:
        """
        Renderiza email de revisión requerida.

        Args:
            data: Diccionario con datos de la factura
                - numero_factura
                - proveedor_nombre
                - monto
                - fecha_emision
                - concepto
                - motivo_revision (str o list)
                - alertas (list)
                - contexto_historico (dict)
                - confianza
                - responsable_nombre
                - url_aprobar
                - url_rechazar

        Returns:
            (html_body, text_body)
        """
        try:
            template = self.env.get_template('revision_requerida.html')
            html = template.render(**data)

            # Generar versión texto
            text = self._html_to_text_revision(data)

            return html, text

        except Exception as e:
            logger.error(f"Error renderizando template revision_requerida: {str(e)}")
            return self._fallback_revision_html(data), self._fallback_revision_text(data)

    def render_error_critico(self, data: Dict[str, Any]) -> tuple[str, str]:
        """
        Renderiza email de error crítico.

        Args:
            data: Diccionario con datos del error
                - numero_factura
                - proveedor_nombre
                - error_descripcion
                - fecha_error
                - stack_trace (opcional)
                - responsable_nombre

        Returns:
            (html_body, text_body)
        """
        try:
            template = self.env.get_template('error_critico.html')
            html = template.render(**data)

            # Generar versión texto
            text = self._html_to_text_error(data)

            return html, text

        except Exception as e:
            logger.error(f"Error renderizando template error_critico: {str(e)}")
            return self._fallback_error_html(data), self._fallback_error_text(data)

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Renderiza un template genérico de email.

        Método genérico que funciona con cualquier template HTML existente.
        Se usa principalmente para notificaciones a contabilidad.

        Args:
            template_name: Nombre del template (ej: 'factura_aprobada.html')
            context: Diccionario con variables para el template

        Returns:
            HTML renderizado
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error renderizando template {template_name}: {str(e)}")
            # Fallback: devolver HTML simple con la información
            return f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Notificación</h2>
                <p>Factura: {context.get('numero_factura', 'N/A')}</p>
                <p>Proveedor: {context.get('nombre_proveedor', 'N/A')}</p>
                <p>Monto: {context.get('monto_factura', 'N/A')}</p>
                <p>Estado: {context.get('estado', 'N/A')}</p>
            </body>
            </html>
            """

    def render_resumen_diario(self, data: Dict[str, Any]) -> tuple[str, str]:
        """
        Renderiza email de resumen diario.

        Args:
            data: Diccionario con estadísticas
                - fecha
                - responsable_nombre
                - stats (dict con aprobadas_auto, revision, pendientes, rechazadas, tasa, monto_total)
                - facturas_atencion (list)
                - facturas_aprobadas (list de últimas 5)
                - tendencias (dict)

        Returns:
            (html_body, text_body)
        """
        try:
            template = self.env.get_template('resumen_diario.html')
            html = template.render(**data)

            # Generar versión texto
            text = self._html_to_text_resumen(data)

            return html, text

        except Exception as e:
            logger.error(f"Error renderizando template resumen_diario: {str(e)}")
            return self._fallback_resumen_html(data), self._fallback_resumen_text(data)

    # Métodos de fallback en caso de error en templates

    def _fallback_aprobacion_html(self, data: Dict[str, Any]) -> str:
        """Template HTML mínimo de aprobación."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Factura Aprobada Automáticamente</h2>
            <p>Hola {data.get('responsable_nombre', 'Usuario')},</p>
            <p>La factura <strong>{data.get('numero_factura')}</strong> ha sido aprobada automáticamente.</p>
            <ul>
                <li>Proveedor: {data.get('proveedor_nombre')}</li>
                <li>Monto: ${data.get('monto', 0):,.2f}</li>
                <li>Confianza: {data.get('confianza', 0)*100:.0f}%</li>
            </ul>
            <p>Saludos,<br>Sistema de Automatización AFE</p>
        </body>
        </html>
        """

    def _fallback_aprobacion_text(self, data: Dict[str, Any]) -> str:
        """Template texto mínimo de aprobación."""
        return f"""
Factura Aprobada Automáticamente

Hola {data.get('responsable_nombre', 'Usuario')},

La factura {data.get('numero_factura')} ha sido aprobada automáticamente.

- Proveedor: {data.get('proveedor_nombre')}
- Monto: ${data.get('monto', 0):,.2f}
- Confianza: {data.get('confianza', 0)*100:.0f}%

Saludos,
Sistema de Automatización AFE
        """

    def _fallback_revision_html(self, data: Dict[str, Any]) -> str:
        """Template HTML mínimo de revisión."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2> Factura Requiere Revisión</h2>
            <p>Hola {data.get('responsable_nombre', 'Usuario')},</p>
            <p>La factura <strong>{data.get('numero_factura')}</strong> requiere tu revisión.</p>
            <ul>
                <li>Proveedor: {data.get('proveedor_nombre')}</li>
                <li>Monto: ${data.get('monto', 0):,.2f}</li>
                <li>Motivo: {data.get('motivo_revision', 'No especificado')}</li>
            </ul>
            <p>Saludos,<br>Sistema de Automatización AFE</p>
        </body>
        </html>
        """

    def _fallback_revision_text(self, data: Dict[str, Any]) -> str:
        """Template texto mínimo de revisión."""
        return f"""
Factura Requiere Revisión

Hola {data.get('responsable_nombre', 'Usuario')},

La factura {data.get('numero_factura')} requiere tu revisión.

- Proveedor: {data.get('proveedor_nombre')}
- Monto: ${data.get('monto', 0):,.2f}
- Motivo: {data.get('motivo_revision', 'No especificado')}

Saludos,
Sistema de Automatización AFE
        """

    def _fallback_error_html(self, data: Dict[str, Any]) -> str:
        """Template HTML mínimo de error."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2> Error en Procesamiento</h2>
            <p>Hola Administrador,</p>
            <p>Error procesando factura <strong>{data.get('numero_factura')}</strong>.</p>
            <p>Error: {data.get('error_descripcion')}</p>
            <p>Fecha: {data.get('fecha_error')}</p>
            <p>Saludos,<br>Sistema de Automatización AFE</p>
        </body>
        </html>
        """

    def _fallback_error_text(self, data: Dict[str, Any]) -> str:
        """Template texto mínimo de error."""
        return f"""
Error en Procesamiento

Error procesando factura {data.get('numero_factura')}.

Error: {data.get('error_descripcion')}
Fecha: {data.get('fecha_error')}

Saludos,
Sistema de Automatización AFE
        """

    def _fallback_resumen_html(self, data: Dict[str, Any]) -> str:
        """Template HTML mínimo de resumen."""
        stats = data.get('stats', {})
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Resumen Diario</h2>
            <p>Hola {data.get('responsable_nombre', 'Usuario')},</p>
            <p>Estadísticas del día:</p>
            <ul>
                <li>Aprobadas automáticamente: {stats.get('aprobadas_auto', 0)}</li>
                <li>Requieren revisión: {stats.get('revision', 0)}</li>
                <li>Tasa de automatización: {stats.get('tasa', 0):.1f}%</li>
            </ul>
            <p>Saludos,<br>Sistema de Automatización AFE</p>
        </body>
        </html>
        """

    def _fallback_resumen_text(self, data: Dict[str, Any]) -> str:
        """Template texto mínimo de resumen."""
        stats = data.get('stats', {})
        return f"""
Resumen Diario

Hola {data.get('responsable_nombre', 'Usuario')},

Estadísticas del día:
- Aprobadas automáticamente: {stats.get('aprobadas_auto', 0)}
- Requieren revisión: {stats.get('revision', 0)}
- Tasa de automatización: {stats.get('tasa', 0):.1f}%

Saludos,
Sistema de Automatización AFE
        """

    def _html_to_text_aprobacion(self, data: Dict[str, Any]) -> str:
        """Convierte datos a versión texto de aprobación."""
        return self._fallback_aprobacion_text(data)

    def _html_to_text_revision(self, data: Dict[str, Any]) -> str:
        """Convierte datos a versión texto de revisión."""
        return self._fallback_revision_text(data)

    def _html_to_text_error(self, data: Dict[str, Any]) -> str:
        """Convierte datos a versión texto de error."""
        return self._fallback_error_text(data)

    def _html_to_text_resumen(self, data: Dict[str, Any]) -> str:
        """Convierte datos a versión texto de resumen."""
        return self._fallback_resumen_text(data)


# Singleton
_template_service_instance = None


def get_template_service() -> EmailTemplateService:
    """Obtiene instancia singleton del servicio de templates."""
    global _template_service_instance
    if _template_service_instance is None:
        _template_service_instance = EmailTemplateService()
    return _template_service_instance
