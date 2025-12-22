# app/services/microsoft_graph_email_service.py
"""
Servicio de envío de emails usando Microsoft Graph API.

Características:
- Envío desde buzón compartido (notificacionrpa.auto@zentria.com.co)
- Autenticación OAuth2 segura
- Soporte para HTML, CC, BCC, adjuntos
- Retry automático con backoff
- Logging detallado
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import time
import base64
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GraphEmailConfig:
    """Configuración para Microsoft Graph API."""
    tenant_id: str
    client_id: str
    client_secret: str
    from_email: str  # Email del buzón compartido
    from_name: str = "Sistema AFE - Notificaciones"


class MicrosoftGraphEmailService:
    """
    Servicio de envío de emails usando Microsoft Graph API.

    Más seguro y robusto que SMTP tradicional.
    """

    def __init__(self, config: GraphEmailConfig):
        """
        Inicializa el servicio de Microsoft Graph.

        Args:
            config: Configuración de Graph API
        """
        self.config = config
        self.token = None
        self.token_expires = None
        self.max_retries = 3
        self.retry_delay = 2  # segundos
        self.graph_base_url = "https://graph.microsoft.com/v1.0"

    def _get_token(self) -> str:
        """
        Obtiene token OAuth2 con cache automático.

        Returns:
            str: Bearer token válido
        """
        # Si tenemos token válido en cache, usarlo
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return self.token

        # Solicitar nuevo token
        url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }

        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            self.token = result["access_token"]
            # Guardar expiración con 1 minuto de margen
            self.token_expires = datetime.now() + timedelta(seconds=result["expires_in"] - 60)

            logger.info("  Token de Microsoft Graph obtenido exitosamente")
            return self.token

        except Exception as e:
            logger.error(f" Error obteniendo token de Graph: {str(e)}")
            raise

    def send_email(
        self,
        to_email: str | List[str],
        subject: str,
        body_html: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Path]] = None,
        importance: str = "normal"  # "low", "normal", "high"
    ) -> Dict[str, Any]:
        """
        Envía un email usando Microsoft Graph con retry automático.

        Args:
            to_email: Destinatario(s)
            subject: Asunto del email
            body_html: Cuerpo en HTML
            cc: Lista de CC
            bcc: Lista de BCC
            attachments: Lista de archivos adjuntos
            importance: Importancia del mensaje

        Returns:
            Dict con resultado del envío
        """
        # Normalizar destinatarios
        if isinstance(to_email, str):
            to_email = [to_email]

        # Intentar envío con retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = self._send_email_attempt(
                    to_email=to_email,
                    subject=subject,
                    body_html=body_html,
                    cc=cc,
                    bcc=bcc,
                    attachments=attachments,
                    importance=importance
                )

                logger.info(f"  Email enviado exitosamente a {', '.join(to_email)}")
                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"  Intento {attempt + 1}/{self.max_retries} falló al enviar email: {str(e)}"
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    sleep_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Esperando {sleep_time}s antes del siguiente intento...")
                    time.sleep(sleep_time)

        # Si llegamos aquí, todos los intentos fallaron
        logger.error(f" Error enviando email después de {self.max_retries} intentos: {last_error}")
        return {
            'success': False,
            'error': last_error,
            'attempts': self.max_retries
        }

    def _send_email_attempt(
        self,
        to_email: List[str],
        subject: str,
        body_html: str,
        cc: Optional[List[str]],
        bcc: Optional[List[str]],
        attachments: Optional[List[Path]],
        importance: str
    ) -> Dict[str, Any]:
        """Intento individual de envío de email usando Graph API."""

        token = self._get_token()

        # Construir mensaje según formato de Graph API
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body_html
                },
                "toRecipients": [
                    {"emailAddress": {"address": email}} for email in to_email
                ],
                "importance": importance
            },
            "saveToSentItems": "true"
        }

        # Agregar CC si existe
        if cc:
            message["message"]["ccRecipients"] = [
                {"emailAddress": {"address": email}} for email in cc
            ]

        # Agregar BCC si existe
        if bcc:
            message["message"]["bccRecipients"] = [
                {"emailAddress": {"address": email}} for email in bcc
            ]

        # Agregar attachments si existen
        if attachments:
            message["message"]["attachments"] = []
            for file_path in attachments:
                attachment_data = self._prepare_attachment(file_path)
                if attachment_data:
                    message["message"]["attachments"].append(attachment_data)

        # Enviar usando el buzón compartido
        url = f"{self.graph_base_url}/users/{self.config.from_email}/sendMail"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=message, headers=headers, timeout=30)

        # Graph API retorna 202 Accepted para envío exitoso
        if response.status_code == 202:
            return {
                'success': True,
                'recipients': to_email,
                'subject': subject,
                'timestamp': datetime.now().isoformat(),
                'provider': 'microsoft_graph'
            }
        else:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get('error', {}).get('message', response.text)
            except:
                pass

            raise Exception(f"Graph API error [{response.status_code}]: {error_detail}")

    def _prepare_attachment(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Prepara un adjunto para Graph API.

        Args:
            file_path: Ruta del archivo

        Returns:
            Dict con datos del adjunto en formato Graph API
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            # Codificar en base64
            content_base64 = base64.b64encode(content).decode('utf-8')

            # Determinar content type (simplificado)
            content_type = "application/octet-stream"
            if file_path.suffix.lower() == '.pdf':
                content_type = "application/pdf"
            elif file_path.suffix.lower() == '.xml':
                content_type = "application/xml"
            elif file_path.suffix.lower() in ['.jpg', '.jpeg']:
                content_type = "image/jpeg"
            elif file_path.suffix.lower() == '.png':
                content_type = "image/png"

            return {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": file_path.name,
                "contentType": content_type,
                "contentBytes": content_base64
            }

        except Exception as e:
            logger.error(f"Error preparando attachment {file_path}: {str(e)}")
            return None

    def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        subject_template: str,
        body_template: str,
        rate_limit: int = 10,
        delay_between_batches: float = 1.0
    ) -> Dict[str, Any]:
        """
        Envía emails en bulk con rate limiting.

        Args:
            recipients: Lista de dicts con 'email' y variables para template
            subject_template: Template del asunto con {variables}
            body_template: Template del cuerpo con {variables}
            rate_limit: Máximo emails por segundo
            delay_between_batches: Delay entre batches

        Returns:
            Estadísticas de envío
        """
        results = {
            'total': len(recipients),
            'sent': 0,
            'failed': 0,
            'errors': []
        }

        for i, recipient_data in enumerate(recipients):
            try:
                email = recipient_data.pop('email')

                # Formatear subject y body con variables del recipient
                subject = subject_template.format(**recipient_data)
                body = body_template.format(**recipient_data)

                result = self.send_email(
                    to_email=email,
                    subject=subject,
                    body_html=body
                )

                if result['success']:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'email': email,
                        'error': result.get('error')
                    })

                # Rate limiting
                if (i + 1) % rate_limit == 0:
                    time.sleep(delay_between_batches)

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'email': recipient_data.get('email', 'unknown'),
                    'error': str(e)
                })
                logger.error(f"Error en bulk email #{i}: {str(e)}")

        logger.info(
            f"Bulk email completado: {results['sent']}/{results['total']} enviados, "
            f"{results['failed']} fallidos"
        )

        return results


# Factory function para crear instancia del servicio
def get_graph_email_service(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    from_email: str,
    from_name: str
) -> MicrosoftGraphEmailService:
    """
    Crea instancia del servicio de email con Graph.

    IMPORTANTE: from_email y from_name DEBEN ser provistos explícitamente
    desde la configuración (app.core.config.settings). No hay valores por defecto
    para evitar hardcodeo de credenciales.

    Args:
        tenant_id: Tenant ID de Azure
        client_id: Client ID de la aplicación
        client_secret: Client Secret
        from_email: Email del buzón compartido (desde GRAPH_FROM_EMAIL en .env)
        from_name: Nombre para mostrar (desde GRAPH_FROM_NAME en .env)

    Returns:
        Instancia configurada del servicio

    Raises:
        TypeError: Si from_email o from_name no están provistos
    """
    config = GraphEmailConfig(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        from_email=from_email,
        from_name=from_name
    )

    return MicrosoftGraphEmailService(config)
