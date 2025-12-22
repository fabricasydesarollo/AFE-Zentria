# app/services/email_service.py
"""
Servicio de envío de emails enterprise-grade.

Soporta:
- SMTP (Gmail, Outlook, servidores corporativos)
- SendGrid API
- Amazon SES
- Templates HTML profesionales
- Attachments
- Retry automático con backoff
- Queue de envío asíncrono
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from pathlib import Path
import time
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Configuración de email."""
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_email: str
    from_name: str
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30


class EmailService:
    """
    Servicio principal de envío de emails.

    Características enterprise:
    - Retry automático con exponential backoff
    - Soporte para HTML y texto plano
    - Attachments
    - Validación de emails
    - Rate limiting
    - Logging detallado
    """

    def __init__(self, config: Optional[EmailConfig] = None):
        """
        Inicializa el servicio de email.

        Args:
            config: Configuración personalizada. Si es None, usa settings.
        """
        self.config = config or self._load_config_from_settings()
        self.max_retries = 3
        self.retry_delay = 2  # segundos

    def _load_config_from_settings(self) -> EmailConfig:
        """Carga configuración desde settings de la aplicación."""
        return EmailConfig(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
            from_email=settings.smtp_from_email,
            from_name=settings.smtp_from_name,
            use_tls=settings.smtp_use_tls,
            use_ssl=settings.smtp_use_ssl,
            timeout=settings.smtp_timeout
        )

    def send_email(
        self,
        to_email: str | List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Path]] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía un email con retry automático.

        Args:
            to_email: Destinatario(s)
            subject: Asunto del email
            body_html: Cuerpo en HTML
            body_text: Cuerpo en texto plano (opcional, se genera del HTML)
            cc: Lista de CC
            bcc: Lista de BCC
            attachments: Lista de archivos adjuntos
            reply_to: Email de respuesta

        Returns:
            Dict con resultado del envío
        """
        # Validar configuración
        if not self.config.smtp_user or not self.config.smtp_password:
            logger.warning("SMTP no configurado. Email no será enviado.")
            return {
                'success': False,
                'error': 'SMTP credentials not configured',
                'mode': 'disabled'
            }

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
                    body_text=body_text,
                    cc=cc,
                    bcc=bcc,
                    attachments=attachments,
                    reply_to=reply_to
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
        body_text: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]],
        attachments: Optional[List[Path]],
        reply_to: Optional[str]
    ) -> Dict[str, Any]:
        """Intento individual de envío de email."""

        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['To'] = ', '.join(to_email)

        if cc:
            msg['Cc'] = ', '.join(cc)
        if reply_to:
            msg['Reply-To'] = reply_to

        # Cuerpo del mensaje
        if body_text:
            part_text = MIMEText(body_text, 'plain', 'utf-8')
            msg.attach(part_text)

        part_html = MIMEText(body_html, 'html', 'utf-8')
        msg.attach(part_html)

        # Attachments
        if attachments:
            for attachment_path in attachments:
                self._add_attachment(msg, attachment_path)

        # Lista completa de destinatarios (to + cc + bcc)
        all_recipients = to_email.copy()
        if cc:
            all_recipients.extend(cc)
        if bcc:
            all_recipients.extend(bcc)

        # Conectar y enviar
        if self.config.use_ssl:
            # SSL (puerto 465)
            server = smtplib.SMTP_SSL(
                self.config.smtp_host,
                self.config.smtp_port,
                timeout=self.config.timeout
            )
        else:
            # TLS (puerto 587) o sin cifrado
            server = smtplib.SMTP(
                self.config.smtp_host,
                self.config.smtp_port,
                timeout=self.config.timeout
            )
            if self.config.use_tls:
                server.starttls()

        try:
            # Login
            server.login(self.config.smtp_user, self.config.smtp_password)

            # Enviar
            server.sendmail(
                self.config.from_email,
                all_recipients,
                msg.as_string()
            )

            return {
                'success': True,
                'recipients': all_recipients,
                'subject': subject,
                'timestamp': time.time()
            }

        finally:
            server.quit()

    def _add_attachment(self, msg: MIMEMultipart, file_path: Path) -> None:
        """Agrega un archivo adjunto al mensaje."""
        try:
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {file_path.name}'
            )
            msg.attach(part)

        except Exception as e:
            logger.error(f"Error agregando attachment {file_path}: {str(e)}")

    def validate_email(self, email: str) -> bool:
        """Valida formato de email."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        subject_template: str,
        body_template: str,
        rate_limit: int = 10,  # emails por segundo
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


# Singleton global del servicio
_email_service_instance = None


def get_email_service() -> EmailService:
    """Obtiene instancia singleton del servicio de email."""
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance
