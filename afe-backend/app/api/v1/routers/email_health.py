# app/api/v1/routers/email_health.py
"""
Endpoint de health check para servicios de email.

Permite monitorear el estado de Microsoft Graph y SMTP en tiempo real.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_role
from app.services.unified_email_service import get_unified_email_service
from app.utils.logger import logger


class SendTestEmailRequest(BaseModel):
    """Solicitud para enviar email de prueba."""
    to_email: str
    subject: str = "Email de Prueba - Sistema AFE"
    body: str = "Este es un email de prueba del sistema AFE."

router = APIRouter()


@router.get("/email/health")
async def email_health_status(
    current_user = Depends(require_role("admin"))
):
    """
    Verifica el estado de los servicios de email.

    Solo accesible para administradores.

    Returns:
        Estadísticas de los servicios de email disponibles.
    """
    # El decorador require_role ya valida que sea admin

    service = get_unified_email_service()

    return {
        "status": "ok",
        "graph_service": {
            "configured": bool(service.graph_service),
            "available": service.graph_service is not None
        },
        "smtp_service": {
            "configured": bool(service.smtp_service),
            "available": service.smtp_service is not None
        },
        "active_provider": service.get_active_provider(),
        "message": (
            "Email services operational"
            if service.get_active_provider() != "none"
            else "WARNING: No email services available"
        )
    }


@router.post("/email/send-test")
async def send_test_email(
    request: SendTestEmailRequest,
    current_user = Depends(require_role("admin"))
):
    """
    Envía un email de prueba para diagnosticar problemas de entrega.

    Útil para verificar que Microsoft Graph o SMTP estén funcionando.

    Solo accesible para administradores.
    """
    try:
        service = get_unified_email_service()

        # Crear HTML básico
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Email de Prueba - Sistema AFE</h2>
            <p>{request.body}</p>
            <p><small>Enviado desde: {service.get_active_provider()}</small></p>
        </body>
        </html>
        """

        logger.info(f"Enviando email de prueba a {request.to_email}")

        result = service.send_email(
            to_email=request.to_email,
            subject=request.subject,
            body_html=html_body
        )

        logger.info(f"Resultado de envío: {result}")

        return {
            "status": "success" if result.get('success') else "failed",
            "message": result,
            "provider": result.get('provider', 'unknown'),
            "recipient": request.to_email
        }
    except Exception as e:
        logger.error("Error enviando email de prueba: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        ) from e


@router.post("/email/reinitialize")
async def reinitialize_email_services(
    current_user = Depends(require_role("admin"))
):
    """
    Reinicializa los servicios de email.

    Útil si hay cambios en las variables de entorno o para
    recuperarse de fallos anteriores.

    Solo accesible para administradores.
    """
    # El decorador require_role ya valida que sea admin

    try:
        service = get_unified_email_service()
        service.reinitialize()

        logger.info("Email services reinicializados por admin")

        return {
            "status": "success",
            "message": "Email services reinicializados",
            "active_provider": service.get_active_provider()
        }
    except Exception as e:
        logger.error("Error reinicializando servicios: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        ) from e
