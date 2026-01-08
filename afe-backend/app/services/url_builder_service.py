"""Servicio centralizado de construcción de URLs del sistema."""

from typing import Optional
from urllib.parse import urljoin
from app.core.config import settings
from app.utils.logger import logger


class URLBuilderException(Exception):
    """Excepción para errores en construcción de URLs."""
    pass


class URLBuilderService:
    """Servicio centralizado para construir URLs del sistema."""

    @staticmethod
    def get_factura_detail_url(factura_id: int) -> str:
        """Obtiene la URL completa a los detalles de una factura."""
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
            base_url = settings.frontend_url.rstrip('/')
            url = f"{base_url}/facturas?id={factura_id}"

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

    @staticmethod
    def get_frontend_url() -> str:
        """Obtiene la URL base del frontend."""
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
        """Obtiene la URL base de la API."""
        try:
            url = settings.api_base_url.rstrip('/')

            if not url.startswith(('http://', 'https://')):
                raise URLBuilderException(f"API base URL inválida: {url}")

            return url

        except Exception as e:
            logger.error(f"Error obteniendo API base URL: {str(e)}")
            raise URLBuilderException(f"Error obteniendo API base URL: {str(e)}")

    @staticmethod
    def get_oauth_microsoft_redirect_uri() -> str:
        """Obtiene la URL de redirección OAuth de Microsoft."""
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
        """Construye la URL para logout de Microsoft."""
        try:
            if not settings.oauth_microsoft_tenant_id:
                raise URLBuilderException("OAUTH_MICROSOFT_TENANT_ID no está configurada")

            tenant_id = settings.oauth_microsoft_tenant_id.strip()
            url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"

            return url

        except Exception as e:
            logger.error(f"Error construyendo Microsoft logout URL: {str(e)}")
            raise URLBuilderException(f"Error construyendo Microsoft logout URL: {str(e)}")

    @staticmethod
    def get_api_endpoint(endpoint: str) -> str:
        """Construye URL completa para un endpoint de API."""
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

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Valida que una URL sea válida."""
        if not url or not isinstance(url, str):
            return False

        if not url.startswith(('http://', 'https://')):
            return False

        parts = url.split('://', 1)
        if len(parts) != 2 or not parts[1]:
            return False

        return True

    @staticmethod
    def get_config_summary() -> dict:
        """Retorna un resumen de la configuración de URLs actual."""
        return {
            "environment": settings.environment,
            "frontend_url": settings.frontend_url,
            "api_base_url": settings.api_base_url,
            "oauth_redirect_uri": settings.oauth_microsoft_redirect_uri,
            "is_production": settings.environment.lower() == "production",
            "is_development": settings.environment.lower() == "development",
        }


def register_url_builder_globals(jinja_env):
    """Registra URLBuilderService como global en entorno Jinja2."""
    jinja_env.globals['url_builder'] = URLBuilderService
