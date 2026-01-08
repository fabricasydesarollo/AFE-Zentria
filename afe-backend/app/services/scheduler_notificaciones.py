# -*- coding: utf-8 -*-
"""
Scheduler de Notificaciones Programadas - Enterprise Grade

Configura y ejecuta notificaciones automáticas:
- Resumen semanal: Lunes 8:00 AM
- Alertas urgentes: Cada 3 días 8:00 AM

Usa APScheduler para ejecución confiable y profesional.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import SessionLocal
from app.services.notificaciones_programadas import NotificacionesProgramadasService

logger = logging.getLogger(__name__)

# Scheduler global
_scheduler = None


def iniciar_scheduler_notificaciones():
    """
    Inicia el scheduler de notificaciones programadas.

    Se ejecuta al iniciar la aplicación (en lifespan).
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler de notificaciones ya esta iniciado")
        return

    _scheduler = BackgroundScheduler()

    # ========================================================================
    # JOB 1: Resumen Semanal - Lunes 8:00 AM
    # ========================================================================
    _scheduler.add_job(
        func=_ejecutar_resumen_semanal,
        trigger=CronTrigger(
            day_of_week='mon',  # Lunes
            hour=8,
            minute=0
        ),
        id='resumen_semanal_facturas',
        name='Resumen Semanal de Facturas Pendientes',
        replace_existing=True
    )

    # ========================================================================
    # JOB 2: Alertas Urgentes - Cada 3 días a las 8:00 AM
    # ========================================================================
    _scheduler.add_job(
        func=_ejecutar_alertas_urgentes,
        trigger=IntervalTrigger(days=3, start_date=datetime.now().replace(hour=8, minute=0, second=0)),
        id='alertas_urgentes_facturas',
        name='Alertas Urgentes Facturas > 10 dias',
        replace_existing=True
    )

    _scheduler.start()

    logger.info("Scheduler de notificaciones iniciado")
    logger.info("  - Resumen semanal: Lunes 8:00 AM")
    logger.info("  - Alertas urgentes: Cada 3 dias 8:00 AM")


def detener_scheduler_notificaciones():
    """
    Detiene el scheduler de notificaciones.

    Se ejecuta al cerrar la aplicación (en lifespan).
    """
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("Scheduler de notificaciones detenido")


# FUNCIONES DE EJECUCIÓN DE JOBS

def _ejecutar_resumen_semanal():
    """Ejecuta el envío del resumen semanal."""
    logger.info("=== INICIANDO RESUMEN SEMANAL ===")

    db = SessionLocal()
    try:
        service = NotificacionesProgramadasService(db)
        resultado = service.enviar_resumen_semanal()

        logger.info(
            f"Resumen semanal completado: "
            f"{resultado['emails_enviados']} enviados, "
            f"{resultado['emails_fallidos']} fallidos"
        )

    except Exception as e:
        logger.error(f"Error ejecutando resumen semanal: {str(e)}", exc_info=True)
    finally:
        db.close()


def _ejecutar_alertas_urgentes():
    """Ejecuta el envío de alertas urgentes."""
    logger.info("=== INICIANDO ALERTAS URGENTES ===")

    db = SessionLocal()
    try:
        service = NotificacionesProgramadasService(db)
        resultado = service.enviar_alertas_urgentes()

        logger.info(
            f"Alertas urgentes completadas: "
            f"{resultado['enviados']} facturas notificadas"
        )

    except Exception as e:
        logger.error(f"Error ejecutando alertas urgentes: {str(e)}", exc_info=True)
    finally:
        db.close()


# FUNCIONES PARA TESTING MANUAL

def ejecutar_resumen_semanal_manual():
    """Ejecuta resumen semanal manualmente (para testing)."""
    _ejecutar_resumen_semanal()


def ejecutar_alertas_urgentes_manual():
    """Ejecuta alertas urgentes manualmente (para testing)."""
    _ejecutar_alertas_urgentes()
