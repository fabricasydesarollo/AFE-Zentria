"""
URL Builder Service - Sistema Centralizado de Construcción de URLs

Este servicio es la ÚNICA fuente de verdad para construir URLs en todo el sistema.
Garantiza consistencia entre desarrollo y producción, y facilita cambios globales.

ARQUITECTURA:
============
- Centralización: Todas las URLs se construyen aquí (no en servicios/templates)
- Validación: URLs se validan antes de retornar
- Entornos: Soporta automáticamente desarrollo y producción
- Extensible: Fácil agregar nuevas URLs sin modificar templates

BENEFICIOS:
===========
1. Cambios globales en un solo archivo (ej: de query param a path param)
2. Testing centralizado
3. Validación de URLs
4. Documentación clara de patrones
5. Facilita onboarding de nuevos desarrolladores

PATRONES SOPORTADOS:
====================
- Facturas:           /facturas?id={id}       (ESTÁNDAR)
- API Endpoints:      /api/v1/{resource}
- Microsoft OAuth:    https://login.microsoftonline.com/...
- Microsoft Graph:    https://graph.microsoft.com/...

VALIDACIÓN:
===========
- URLs deben ser válidas (contener protocolo, dominio, etc)
- Query params se validan como enteros positivos
- Se lanzan excepciones para URLs inválidas (fail-fast)

ENTORNOS:
=========
- development: http://localhost:5173
- production: https://afe.zentria.com.co (configurable)

USO:
====
    from app.services.url_builder_service import URLBuilderService

    # Obtener URL a detalles de factura
    url = URLBuilderService.get_factura_detail_url(factura_id=123)
    # Resultado: "https://afe.zentria.com.co/facturas?id=123" (o localhost en dev)

    # Obtener URL base de API
    api_url = URLBuilderService.get_api_base_url()

HISTORIAL:
==========
- 2025-11-19: Creación inicial (versión 1.0)
  * Servicio centralizado de URLs
  * Soporte para múltiples entornos
  * Validación básica de URLs


Nivel: Enterprise-Grade
"""

from typing import Optional
from urllib.parse import urljoin
from app.core.config import settings
from app.utils.logger import logger


class URLBuilderException(Exception):
    """Excepción para errores en construcción de URLs."""
    pass


class URLBuilderService:
    """
    Servicio centralizado para construir URLs del sistema.

    Garantiza consistencia entre desarrollo y producción.
    Interfaz única para todas las URLs del sistema.
    """

    # =========================================================================
    # FACTURAS
    # =========================================================================

    @staticmethod
    def get_factura_detail_url(factura_id: int) -> str:
        """
        Obtiene la URL completa a los detalles de una factura.

        PATRÓN: /facturas?id={factura_id}

        Esta es la URL que se incluye en:
        - Emails de notificación (botón "Ver Detalles")
        - Links de redirección en el sistema
        - Reportes y auditoría

        Args:
            factura_id: ID de la factura (entero positivo)

        Returns:
            str: URL completa (ej: https://afe.zentria.com.co/facturas?id=123)

        Raises:
            URLBuilderException: Si factura_id no es válido

        Examples:
            >>> URLBuilderService.get_factura_detail_url(123)
            'https://afe.zentria.com.co/facturas?id=123'

            >>> URLBuilderService.get_factura_detail_url(0)
            URLBuilderException: factura_id debe ser un entero positivo
        """
        # Validación
        if not isinstance(factura_id, int) or factura_id <= 0:
            logger.error(
                f"factura_id inválido en URLBuilderService.get_factura_detail_url",
                extra={"factura_id": factura_id, "type": type(factura_id).__name__}
            )
            raise URLBuilderException(
                f"factura_id debe ser un entero positivo, recibido: {factura_id}"
            )

        try:
            # Construcción segura de URL
            base_url = settings.frontend_url.rstrip('/')
            url = f"{base_url}/facturas?id={factura_id}"

            # Validación básica
            if not url.startswith(('http://', 'https://')):
                raise URLBuilderException(f"URL inválida: {url}")

            logger.debug(
                f"URL de factura construida",
                extra={"factura_id": factura_id, "url": url}
            )

            return url

        except Exception as e:
            logger.error(
                f"Error en get_factura_detail_url: {str(e)}",
                exc_info=True,
                extra={"factura_id": factura_id}
            )
            raise URLBuilderException(f"Error construyendo URL de factura: {str(e)}")

    # =========================================================================
    # URLS BASE
    # =========================================================================

    @staticmethod
    def get_frontend_url() -> str:
        """
        Obtiene la URL base del frontend.

        IMPORTANTE: Esta es la URL base sin trailing slash para evitar
        duplicados cuando se concatena con paths.

        Returns:
            str: URL base del frontend (ej: https://afe.zentria.com.co)

        Examples:
            >>> URLBuilderService.get_frontend_url()
            'https://afe.zentria.com.co'
        """
        try:
            url = settings.frontend_url.rstrip('/')

            if not url.startswith(('http://', 'https://')):
                raise URLBuilderException(f"Frontend URL inválida: {url}")

            return url

        except Exception as e:
            logger.error(f"Error obteniendo frontend URL: {str(e)}")
            raise URLBuilderException(f"Error obteniendo frontend URL: {str(e)}")

    @staticmethod
    def get_api_base_url() -> str:
        """
        Obtiene la URL base de la API.

        Usada para:
        - Links directos a endpoints de API
        - Headers de redirección
        - Referencias en documentación

        IMPORTANTE: Sin trailing slash

        Returns:
            str: URL base de API (ej: https://api.afe.zentria.com.co)

        Examples:
            >>> URLBuilderService.get_api_base_url()
            'https://api.afe.zentria.com.co'
        """
        try:
            url = settings.api_base_url.rstrip('/')

            if not url.startswith(('http://', 'https://')):
                raise URLBuilderException(f"API base URL inválida: {url}")

            return url

        except Exception as e:
            logger.error(f"Error obteniendo API base URL: {str(e)}")
            raise URLBuilderException(f"Error obteniendo API base URL: {str(e)}")

    # =========================================================================
    # AUTHENTICATION & OAUTH
    # =========================================================================

    @staticmethod
    def get_oauth_microsoft_redirect_uri() -> str:
        """
        Obtiene la URL de redirección OAuth de Microsoft.

        CRÍTICA: Debe coincidir exactamente con lo registrado en Azure AD

        Returns:
            str: URI de redirección OAuth

        Examples:
            >>> URLBuilderService.get_oauth_microsoft_redirect_uri()
            'https://afe.zentria.com.co/auth/microsoft/callback'
        """
        try:
            uri = settings.oauth_microsoft_redirect_uri.rstrip('/')

            if not uri.startswith(('http://', 'https://')):
                raise URLBuilderException(f"OAuth redirect URI inválida: {uri}")

            if '/auth/microsoft/callback' not in uri:
                logger.warning(
                    f"OAuth redirect URI no contiene patrón esperado",
                    extra={"uri": uri}
                )

            return uri

        except Exception as e:
            logger.error(f"Error obteniendo OAuth redirect URI: {str(e)}")
            raise URLBuilderException(f"Error obteniendo OAuth redirect URI: {str(e)}")

    @staticmethod
    def get_microsoft_logout_url() -> str:
        """
        Construye la URL para logout de Microsoft.

        Patrón: https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout

        Returns:
            str: URL de logout de Microsoft

        Examples:
            >>> URLBuilderService.get_microsoft_logout_url()
            'https://login.microsoftonline.com/c9ef7bf6-bbe0-4c50-b2e9-ea58d635ca46/oauth2/v2.0/logout'
        """
        try:
            if not settings.oauth_microsoft_tenant_id:
                raise URLBuilderException("OAUTH_MICROSOFT_TENANT_ID no está configurada")

            tenant_id = settings.oauth_microsoft_tenant_id.strip()
            url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"

            return url

        except Exception as e:
            logger.error(f"Error construyendo Microsoft logout URL: {str(e)}")
            raise URLBuilderException(f"Error construyendo Microsoft logout URL: {str(e)}")

    # =========================================================================
    # API ENDPOINTS
    # =========================================================================

    @staticmethod
    def get_api_endpoint(endpoint: str) -> str:
        """
        Construye URL completa para un endpoint de API.

        Args:
            endpoint: Endpoint relativo (ej: /api/v1/facturas)

        Returns:
            str: URL completa del endpoint

        Examples:
            >>> URLBuilderService.get_api_endpoint('/api/v1/facturas')
            'https://api.afe.zentria.com.co/api/v1/facturas'
        """
        try:
            if not endpoint:
                raise URLBuilderException("endpoint no puede estar vacío")

            base = URLBuilderService.get_api_base_url()
            endpoint = endpoint.lstrip('/')

            url = f"{base}/{endpoint}"

            if not url.startswith(('http://', 'https://')):
                raise URLBuilderException(f"Endpoint URL inválida: {url}")

            return url

        except URLBuilderException:
            raise
        except Exception as e:
            logger.error(f"Error construyendo endpoint URL: {str(e)}")
            raise URLBuilderException(f"Error construyendo endpoint URL: {str(e)}")

    # =========================================================================
    # VALIDACIÓN
    # =========================================================================

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Valida que una URL sea válida.

        Chequeos básicos:
        - No está vacía
        - Contiene protocolo (http:// o https://)
        - Contiene un dominio

        Args:
            url: URL a validar

        Returns:
            bool: True si es válida, False si no

        Examples:
            >>> URLBuilderService.is_valid_url('https://example.com')
            True

            >>> URLBuilderService.is_valid_url('not-a-url')
            False
        """
        if not url or not isinstance(url, str):
            return False

        if not url.startswith(('http://', 'https://')):
            return False

        # Chequeo básico: tiene algo después del protocolo
        parts = url.split('://', 1)
        if len(parts) != 2 or not parts[1]:
            return False

        return True

    # =========================================================================
    # INFORMACIÓN DE CONFIGURACIÓN (DEBUG/LOGGING)
    # =========================================================================

    @staticmethod
    def get_config_summary() -> dict:
        """
        Retorna un resumen de la configuración de URLs actual.

        SEGURIDAD: No incluye secretos o datos sensibles

        Returns:
            dict: Resumen de configuración

        Examples:
            >>> URLBuilderService.get_config_summary()
            {
                'environment': 'production',
                'frontend_url': 'https://afe.zentria.com.co',
                'api_base_url': 'https://api.afe.zentria.com.co',
                'oauth_redirect_uri': 'https://afe.zentria.com.co/auth/microsoft/callback'
            }
        """
        return {
            "environment": settings.environment,
            "frontend_url": settings.frontend_url,
            "api_base_url": settings.api_base_url,
            "oauth_redirect_uri": settings.oauth_microsoft_redirect_uri,
            "is_production": settings.environment.lower() == "production",
            "is_development": settings.environment.lower() == "development",
        }


# ============================================================================
# SINGLETON PARA USO EN TEMPLATES JINJA2
# ============================================================================
# Esto permite usar URLBuilderService desde los templates HTML como un helper

def register_url_builder_globals(jinja_env):
    """
    Registra URLBuilderService como global en entorno Jinja2.

    Permite usar en templates:
        {{ url_builder.get_factura_detail_url(factura_id) }}

    Args:
        jinja_env: Ambiente Jinja2 a registrar

    Usage en app/services/email_template_service.py:
        from app.services.url_builder_service import register_url_builder_globals

        jinja_env = Environment(loader=FileSystemLoader(...))
        register_url_builder_globals(jinja_env)
    """
    jinja_env.globals['url_builder'] = URLBuilderService
