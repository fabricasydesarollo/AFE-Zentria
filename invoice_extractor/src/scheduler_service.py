# src/scheduler_service.py
"""
Servicio de automatización para extracción de facturas.
Ejecuta el proceso de extracción 3 veces al día usando APScheduler.
"""
from __future__ import annotations
import sys
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from src.core.config import load_config
from src.utils.logger import get_logger
from src.core.app import App
from src.services.ingest_service import IngestService


class InvoiceExtractorScheduler:
    """Scheduler para automatizar la extracción de facturas"""

    def __init__(self):
        """Inicializa el scheduler y carga la configuración"""
        try:
            self.config = load_config()
            self.logger = get_logger("Scheduler", self.config.LOG_LEVEL)
            self.scheduler = BlockingScheduler()
            self.execution_count = 0

            self.logger.info("=" * 80)
            self.logger.info("SERVICIO DE AUTOMATIZACIÓN DE EXTRACCIÓN DE FACTURAS INICIADO")
            self.logger.info("=" * 80)
            self.logger.info("Configuración: Ejecución programada 3 veces al día")
            self.logger.info("Horarios: 08:00, 13:00, 18:00")
            self.logger.info("=" * 80)

        except Exception as exc:
            print(f"ERROR CRÍTICO: No se pudo inicializar el scheduler: {exc}", file=sys.stderr)
            raise

    def extract_invoices_job(self):
        """
        Trabajo principal que ejecuta la extracción de facturas.
        Este método es llamado por el scheduler automáticamente.
        """
        self.execution_count += 1

        self.logger.info("\n" + "=" * 80)
        self.logger.info(f"INICIANDO EJECUCIÓN AUTOMÁTICA #{self.execution_count}")
        self.logger.info(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 80)

        try:
            # FASE 1: Ejecutar App (descarga de correos y parsing)
            self.logger.info("\n[FASE 1/2] Descarga de correos y extracción de facturas")
            self.logger.info("-" * 80)

            app = App(self.config)
            app_result = app.run()

            if app_result != 0:
                self.logger.error(
                    f"App finalizó con código de error: {app_result}. "
                    "No se procederá con la ingesta."
                )
                self._log_execution_summary(success=False, error="App falló")
                return

            self.logger.info("Descarga y extracción completada exitosamente")

            # FASE 2: Ejecutar ingesta a base de datos
            self.logger.info("\n[FASE 2/2] Ingesta de facturas a base de datos")
            self.logger.info("-" * 80)

            ingest_result = self._execute_ingest()

            if ingest_result != 0:
                self.logger.error(f"Ingesta finalizó con código de error: {ingest_result}")
                self._log_execution_summary(success=False, error="Ingesta falló")
                return

            # Ejecución exitosa
            self._log_execution_summary(success=True)

        except KeyboardInterrupt:
            self.logger.warning("\nEjecución interrumpida por el usuario (Ctrl+C)")
            raise

        except Exception as exc:
            self.logger.error(
                f"Error inesperado durante la ejecución: {exc}",
                exc_info=True
            )
            self._log_execution_summary(success=False, error=str(exc))

    def _execute_ingest(self) -> int:
        """
        Ejecuta el proceso de ingesta a la base de datos.

        Returns:
            int: Código de salida (0 = éxito, otro = error)
        """
        try:
            # Verificar si la ingesta está habilitada
            ingest_enabled = getattr(self.config, 'INGEST_ENABLED', True)

            if not ingest_enabled:
                self.logger.info("Ingesta deshabilitada en configuración. Saltando fase de ingesta.")
                return 0

            # Inicializar servicio de ingesta
            ingest_service = IngestService(self.config)

            # Verificar conexión a base de datos
            self.logger.info("Verificando conexión a base de datos...")
            if not ingest_service.verify_database_connection():
                self.logger.error("No se pudo conectar a la base de datos. Abortando ingesta.")
                return 3

            self.logger.info("Conexión a base de datos verificada correctamente")

            # Ejecutar ingesta
            self.logger.info("Iniciando proceso de ingesta...")
            stats = ingest_service.ingest_to_db()

            # Verificar resultados
            if stats['total_exitosas'] == 0 and stats['total_procesadas'] > 0:
                self.logger.error(
                    f"ADVERTENCIA: Ninguna factura fue ingestada exitosamente de "
                    f"{stats['total_procesadas']} procesadas"
                )
                return 3

            # Log de resumen
            self.logger.info("\nRESUMEN DE INGESTA:")
            self.logger.info(f"  NITs procesados: {len(stats['nits_procesados'])}")
            self.logger.info(f"  Facturas procesadas: {stats['total_procesadas']}")
            self.logger.info(f"  Facturas exitosas: {stats['total_exitosas']}")
            self.logger.info(f"  Facturas fallidas: {stats['total_fallidas']}")

            if stats['total_fallidas'] > 0:
                success_rate = (stats['total_exitosas'] / stats['total_procesadas']) * 100
                self.logger.warning(f"  Tasa de éxito: {success_rate:.2f}%")

            # Mostrar estado actual de la DB
            try:
                progress = ingest_service.get_ingest_progress()
                self.logger.info("\nESTADO ACTUAL DE BASE DE DATOS:")
                self.logger.info(f"  Total facturas en DB: {progress['total_facturas_db']}")

                if progress['facturas_por_nit']:
                    self.logger.info("  Top proveedores:")
                    for nit, info in list(progress['facturas_por_nit'].items())[:5]:
                        self.logger.info(f"    - {info['razon_social'][:40]}: {info['total']} facturas")

                if progress['ultima_fecha_procesamiento']:
                    self.logger.info(f"  Última fecha de procesamiento: {progress['ultima_fecha_procesamiento']}")

            except Exception as exc:
                self.logger.warning(f"No se pudo obtener progreso de DB: {exc}")

            self.logger.info("\nIngesta completada exitosamente")
            return 0

        except Exception as exc:
            self.logger.error(f"Error durante el proceso de ingesta: {exc}", exc_info=True)
            return 3

    def _log_execution_summary(self, success: bool, error: str = None):
        """
        Registra un resumen de la ejecución.

        Args:
            success: Si la ejecución fue exitosa
            error: Mensaje de error (si aplica)
        """
        self.logger.info("\n" + "=" * 80)
        if success:
            self.logger.info(f"EJECUCIÓN AUTOMÁTICA #{self.execution_count} COMPLETADA EXITOSAMENTE")
            self.logger.info(f"Finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.logger.error(f"EJECUCIÓN AUTOMÁTICA #{self.execution_count} FALLÓ")
            self.logger.error(f"Error: {error}")
            self.logger.info(f"Finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 80 + "\n")

    def setup_schedule(self):
        """
        Configura el calendario de ejecuciones.
        Programa 3 ejecuciones diarias: 08:00, 13:00, 18:00
        """
        # Ejecución a las 09:30 (9:30 AM)
        self.scheduler.add_job(
            self.extract_invoices_job,
            trigger=CronTrigger(hour=9, minute=30),
            id='morning_extraction',
            name='Extracción matutina (09:30)',
            replace_existing=True
        )

        # Ejecución a las 13:00 (1 PM)
        self.scheduler.add_job(
            self.extract_invoices_job,
            trigger=CronTrigger(hour=13, minute=0),
            id='midday_extraction',
            name='Extracción mediodía (13:00)',
            replace_existing=True
        )

        # Ejecución a las 18:00 (6 PM)
        self.scheduler.add_job(
            self.extract_invoices_job,
            trigger=CronTrigger(hour=18, minute=0),
            id='evening_extraction',
            name='Extracción vespertina (18:00)',
            replace_existing=True
        )

        self.logger.info("\n CALENDARIO DE EJECUCIONES CONFIGURADO:")
        self.logger.info("   09:30 - Extracción matutina")
        self.logger.info("   13:00 - Extracción mediodía")
        self.logger.info("   18:00 - Extracción vespertina")
        self.logger.info("")

    def start(self):
        """
        Inicia el scheduler y comienza a ejecutar los trabajos programados.
        Este método bloqueará el hilo hasta que se detenga el scheduler.
        """
        try:
            self.setup_schedule()

            self.logger.info(" Scheduler iniciado y en ejecución...")
            self.logger.info(" Esperando próxima ejecución programada...")
            self.logger.info(" Presiona Ctrl+C para detener el servicio")
            self.logger.info("")

            # Iniciar el scheduler primero para que calcule next_run_time
            self.scheduler.start()

        except KeyboardInterrupt:
            self.logger.info("\n" + "=" * 80)
            self.logger.info(" DETENIENDO SERVICIO DE AUTOMATIZACIÓN...")
            self.logger.info("=" * 80)
            self.stop()

        except Exception as exc:
            self.logger.error(f"Error al iniciar el scheduler: {exc}", exc_info=True)
            raise

    def stop(self):
        """Detiene el scheduler de manera ordenada"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.logger.info(" Scheduler detenido correctamente")
            self.logger.info(f" Total de ejecuciones realizadas: {self.execution_count}")
            self.logger.info("=" * 80)


def main():
    """Punto de entrada principal para el servicio de automatización"""
    try:
        scheduler_service = InvoiceExtractorScheduler()
        scheduler_service.start()

    except KeyboardInterrupt:
        print("\n Servicio detenido por el usuario")
        sys.exit(0)

    except Exception as exc:
        print(f" Error fatal: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
