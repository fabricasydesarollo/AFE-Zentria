from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.orm import Session
import asyncio
from threading import Thread

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.init_db import create_default_roles_and_admin
from app.utils.logger import logger
from app.core.config import settings


# Background scheduler para tareas automáticas
_scheduler_thread = None
_scheduler_running = False


def run_automation_task():
    """
    Ejecuta la automatización de facturas en background.
    Se ejecuta periódicamente según configuración.

    Flujo:
    1. Procesa facturas SIN workflows (crea workflows automáticamente)
    2. Luego procesa facturas con workflows (toma decisiones de aprobación)
    """
    try:
        from app.services.automation.automation_service import AutomationService
        from app.services.workflow_automatico import WorkflowAutomaticoService
        from sqlalchemy import and_
        from app.models.factura import Factura
        from app.models.workflow_aprobacion import WorkflowAprobacionFactura

        db = SessionLocal()
        try:
            logger.info(" Iniciando automatización programada de facturas...")

            # PASO 1: Crear workflows para facturas que no los tienen
            logger.info(" [PASO 1] Creando workflows para facturas nuevas sin procesar...")
            workflow_service = WorkflowAutomaticoService(db)

            # Obtener facturas SIN workflows
            facturas_sin_workflow = db.query(Factura).filter(
                ~Factura.id.in_(
                    db.query(WorkflowAprobacionFactura.factura_id)
                )
            ).limit(100).all()

            workflows_creados = 0
            for factura in facturas_sin_workflow:
                try:
                    resultado = workflow_service.procesar_factura_nueva(factura.id)
                    if resultado.get('exito'):
                        workflows_creados += 1
                        logger.info(f"   Workflow creado para factura {factura.id}")
                    else:
                        logger.warning(f"   Workflow no se creó para factura {factura.id}: {resultado.get('error')}")
                except Exception as e:
                    logger.error(f"   Error creando workflow para factura {factura.id}: {str(e)}")

            if workflows_creados > 0:
                logger.info(f" [PASO 1]  {workflows_creados} workflows creados")
                db.commit()

            # PASO 2: Procesar facturas pendientes con automatización
            logger.info(" [PASO 2] Procesando automatización de facturas pendientes...")
            automation = AutomationService()
            resultado = automation.procesar_facturas_pendientes(
                db=db,
                limite_facturas=100,  # Procesar hasta 100 facturas por ciclo
                modo_debug=False
            )

            logger.info(
                f" Automatización completada: "
                f"{resultado['aprobadas_automaticamente']} aprobadas, "
                f"{resultado['enviadas_revision']} a revisión, "
                f"{resultado['errores']} errores"
            )

        except Exception as e:
            logger.error(f" Error en automatización programada: {str(e)}", exc_info=True)
        finally:
            db.close()

    except Exception as e:
        logger.error(f" Error crítico en task de automatización: {str(e)}", exc_info=True)


def schedule_automation_tasks():
    """
    Programa tareas de automatización periódicas.
    """
    import schedule
    import time

    global _scheduler_running

    # Configurar horarios de ejecución automática
    # Ejecutar cada hora durante horario laboral
    schedule.every().hour.at(":00").do(run_automation_task)

    # Ejecución especial: Lunes a las 8:00 AM (inicio de semana)
    schedule.every().monday.at("08:00").do(run_automation_task)

    logger.info(" Scheduler de automatización configurado")
    logger.info("   - Cada hora en punto durante el día")
    logger.info("   - Lunes a las 8:00 AM")

    _scheduler_running = True

    while _scheduler_running:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja startup/shutdown de la app.
    Ideal para inicializar y cerrar recursos empresariales.
    """
    global _scheduler_thread, _scheduler_running

    try:
        # --- Startup ---
        logger.info(" Iniciando aplicación AFE Backend...")

        if settings.environment == "development":
             Base.metadata.create_all(bind=engine)

        session = Session(bind=engine)
        try:
            create_default_roles_and_admin(session)
        finally:
            session.close()

        # --- Automatización Inicial ---
        # Ejecutar automatización al iniciar (modo asíncrono para no bloquear startup)
        logger.info(" Ejecutando automatización inicial de facturas...")

        def run_initial_automation():
            db = SessionLocal()
            try:
                from app.services.automation.automation_service import AutomationService
                automation = AutomationService()
                resultado = automation.procesar_facturas_pendientes(
                    db=db,
                    limite_facturas=50,
                    modo_debug=False
                )
                logger.info(
                    f" Automatización inicial: {resultado['aprobadas_automaticamente']} aprobadas, "
                    f"{resultado['enviadas_revision']} a revisión"
                )
            except Exception as e:
                logger.error(f" Error en automatización inicial: {str(e)}")
            finally:
                db.close()

        # Ejecutar en background thread para no bloquear
        initial_thread = Thread(target=run_initial_automation, daemon=True)
        initial_thread.start()

        # --- Scheduler de Tareas Periódicas ---
        # Iniciar scheduler en thread separado
        try:
            import schedule
            _scheduler_thread = Thread(target=schedule_automation_tasks, daemon=True)
            _scheduler_thread.start()
            logger.info(" Scheduler de automatización iniciado")
        except ImportError:
            logger.warning("  Módulo 'schedule' no disponible. Instalar con: pip install schedule")
            logger.info("   Automatización programada deshabilitada (solo manual)")

        # --- Scheduler de Notificaciones ---
        # Iniciar scheduler de notificaciones (resumen semanal, alertas urgentes)
        try:
            from app.services.scheduler_notificaciones import iniciar_scheduler_notificaciones
            iniciar_scheduler_notificaciones()
            logger.info(" Scheduler de notificaciones iniciado")
        except Exception as e:
            logger.warning(f"  Error iniciando scheduler de notificaciones: {str(e)}")

        logger.info(" Startup completado correctamente")

    except Exception as e:
        logger.exception(" Error en startup: %s", e)

    # La app se levanta aquí
    yield

    # --- Shutdown ---
    logger.info(" Aplicación apagándose...")

    # Detener scheduler de automatización
    _scheduler_running = False
    if _scheduler_thread:
        logger.info("   Deteniendo scheduler de automatización...")
        # El thread es daemon, se cerrará automáticamente

    # Detener scheduler de notificaciones
    try:
        from app.services.scheduler_notificaciones import detener_scheduler_notificaciones
        detener_scheduler_notificaciones()
    except Exception as e:
        logger.warning(f"  Error deteniendo scheduler de notificaciones: {str(e)}")

    logger.info(" Aplicación cerrada correctamente")
