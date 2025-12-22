# src/main.py
from __future__ import annotations
import sys
from typing import Optional
from datetime import datetime, timezone
import requests
from src.core.config import load_config
from src.utils.logger import get_logger
from src.core.app import App
from src.services.ingest_service import IngestService


# Códigos de salida
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_APP_ERROR = 2
EXIT_INGEST_ERROR = 3
EXIT_UNKNOWN_ERROR = 99


def main() -> int:

    logger = None
    
    try:
        # PASO 1: Cargar configuración
        try:
            cfg = load_config()
            logger = get_logger("Main", cfg.LOG_LEVEL)
            logger.info("=" * 70)
            logger.info("INICIANDO APLICACIÓN DE PROCESAMIENTO DE FACTURAS ELECTRÓNICAS")
            logger.info("=" * 70)
            logger.info("Configuración cargada exitosamente")
        except Exception as exc:
            # Si falla la configuración, loggear a stderr
            print(f"ERROR CRÍTICO: No se pudo cargar la configuración: {exc}", file=sys.stderr)
            return EXIT_CONFIG_ERROR
        
        # PASO 2: Ejecutar App (descarga de correos y parsing)
        logger.info("\n[FASE 1/2] Descarga de correos y extracción de facturas")
        logger.info("-" * 70)
        
        try:
            app = App(cfg)
            app_result = app.run()
            
            if app_result != EXIT_SUCCESS:
                logger.error(
                    "App finalizó con código de error: %d. No se procederá con la ingesta.",
                    app_result
                )
                return app_result
            
            logger.info("App ejecutado exitosamente")
            
        except Exception as exc:
            logger.error("Error ejecutando App: %s", exc, exc_info=True)
            return EXIT_APP_ERROR
        
        # PASO 3: Ejecutar ingesta a base de datos (solo si App fue exitoso)
        logger.info("\n[FASE 2/2] Ingesta de facturas a base de datos")
        logger.info("-" * 70)
        
        ingest_result = execute_ingest(cfg, logger)

        if ingest_result != EXIT_SUCCESS:
            logger.error("Ingesta finalizó con código de error: %d", ingest_result)
            return ingest_result

        # PASO 4: Actualizar timestamps de última ejecución
        logger.info("\n[FASE 3/3] Actualización de timestamps de ejecución")
        logger.info("-" * 70)

        try:
            actualizar_timestamps_ejecucion(cfg, logger)
            logger.info("Timestamps actualizados correctamente")
        except Exception as exc:
            logger.warning("Error actualizando timestamps: %s (continuando...)", exc)
            # No es crítico fallar aquí, solo registramos el error

        # PASO 5: Finalización exitosa
        logger.info("\n" + "=" * 70)
        logger.info("APLICACIÓN FINALIZADA EXITOSAMENTE")
        logger.info("=" * 70)

        return EXIT_SUCCESS
        
    except KeyboardInterrupt:
        if logger:
            logger.warning("\nAplicación interrumpida por el usuario (Ctrl+C)")
        else:
            print("\nAplicación interrumpida por el usuario", file=sys.stderr)
        return EXIT_UNKNOWN_ERROR
        
    except Exception as exc:
        if logger:
            logger.critical("Error inesperado en main(): %s", exc, exc_info=True)
        else:
            print(f"ERROR CRÍTICO inesperado: {exc}", file=sys.stderr)
        return EXIT_UNKNOWN_ERROR


def execute_ingest(cfg, logger) -> int:

    try:
        # Verificar si la ingesta está habilitada en la configuración
        ingest_enabled = getattr(cfg, 'INGEST_ENABLED', True)
        
        if not ingest_enabled:
            logger.info("Ingesta deshabilitada en configuración. Saltando fase de ingesta.")
            return EXIT_SUCCESS
        
        # Inicializar servicio de ingesta
        try:
            ingest_service = IngestService(cfg)
        except Exception as exc:
            logger.error("Error inicializando IngestService: %s", exc, exc_info=True)
            return EXIT_INGEST_ERROR
        
        # Verificar conexión a base de datos
        logger.info("Verificando conexión a base de datos...")
        if not ingest_service.verify_database_connection():
            logger.error("No se pudo conectar a la base de datos. Abortando ingesta.")
            return EXIT_INGEST_ERROR
        
        logger.info("Conexión a base de datos verificada correctamente")
        
        # Ejecutar ingesta
        logger.info("Iniciando proceso de ingesta...")
        try:
            stats = ingest_service.ingest_to_db()
            
            # Verificar si hubo errores críticos
            if stats['total_exitosas'] == 0 and stats['total_procesadas'] > 0:
                logger.error(
                    "ADVERTENCIA: Ninguna factura fue ingestada exitosamente de %d procesadas",
                    stats['total_procesadas']
                )
                return EXIT_INGEST_ERROR
            
            # Log de resumen
            logger.info("\nRESUMEN DE INGESTA:")
            logger.info("  NITs procesados: %d", len(stats['nits_procesados']))
            logger.info("  Facturas procesadas: %d", stats['total_procesadas'])
            logger.info("  Facturas exitosas: %d", stats['total_exitosas'])
            logger.info("  Facturas fallidas: %d", stats['total_fallidas'])
            
            if stats['total_fallidas'] > 0:
                success_rate = (stats['total_exitosas'] / stats['total_procesadas']) * 100
                logger.warning("  Tasa de éxito: %.2f%%", success_rate)
            
            # Mostrar progreso actual en DB
            try:
                progress = ingest_service.get_ingest_progress()
                logger.info("\nESTADO ACTUAL DE BASE DE DATOS:")
                logger.info("  Total facturas en DB: %d", progress['total_facturas_db'])
                
                if progress['facturas_por_nit']:
                    logger.info("  Top proveedores:")
                    for nit, info in list(progress['facturas_por_nit'].items())[:5]:
                        logger.info("    - %s: %d facturas", info['razon_social'][:40], info['total'])
                
                if progress['ultima_fecha_procesamiento']:
                    logger.info("  Última fecha de procesamiento: %s", progress['ultima_fecha_procesamiento'])
                    
            except Exception as exc:
                logger.warning("No se pudo obtener progreso de DB: %s", exc)
            
            logger.info("\nIngesta completada exitosamente")

            # SOLUCIÓN DE RAÍZ: Notificar backend para crear workflows y asignar responsables
            # Esto resuelve el problema de facturas insertadas después de las 8:00 AM
            if stats['total_exitosas'] > 0:
                notificar_backend_facturas_nuevas(cfg, logger)

            return EXIT_SUCCESS

        except Exception as exc:
            logger.error("Error durante el proceso de ingesta: %s", exc, exc_info=True)
            return EXIT_INGEST_ERROR

    except Exception as exc:
        logger.error("Error inesperado en execute_ingest(): %s", exc, exc_info=True)
        return EXIT_INGEST_ERROR


def notificar_backend_facturas_nuevas(cfg, logger) -> bool:
    """
    Notifica al backend que hay facturas nuevas para procesar workflows.

    SOLUCIÓN DE RAÍZ: Después de insertar facturas, el backend debe:
    1. Crear workflows para facturas sin procesar (responsable_id NULL)
    2. Asignar responsables según mapeo NIT
    3. Ejecutar automatización (aprobación automática si aplica)
    4. Enviar notificaciones a responsables

    Esto resuelve el problema de facturas insertadas después de las 8:00 AM
    que no recibían asignación de responsable automática.

    Returns:
        True si se notificó exitosamente, False si hubo errores
    """
    api_base_url = getattr(cfg, 'API_BASE_URL', 'http://localhost:8000')
    endpoint = f"{api_base_url}/api/v1/automation/procesar-facturas-nuevas"

    try:
        logger.info("\n🚀 Notificando al backend para procesar facturas nuevas...")
        logger.info("   Endpoint: %s", endpoint)

        response = requests.post(endpoint, timeout=30)

        if response.status_code == 200:
            data = response.json()
            result_data = data.get('data', {})

            logger.info("✅ Backend procesó facturas nuevas exitosamente:")
            logger.info("   - Workflows creados: %d", result_data.get('workflows_creados', 0))
            logger.info("   - Facturas procesadas: %d", result_data.get('facturas_procesadas', 0))
            logger.info("   - Aprobadas automáticamente: %d", result_data.get('aprobadas_automaticamente', 0))
            logger.info("   - Enviadas a revisión: %d", result_data.get('enviadas_revision', 0))

            if result_data.get('errores', 0) > 0:
                logger.warning("   - Errores: %d", result_data['errores'])

            return True
        else:
            logger.warning(
                "⚠️ Backend respondió con código HTTP %d: %s",
                response.status_code,
                response.text[:200]
            )
            return False

    except requests.Timeout:
        logger.error("❌ Timeout al notificar backend (>30s). Las facturas están guardadas, pero no se procesaron workflows.")
        return False
    except requests.RequestException as e:
        logger.error("❌ Error notificando backend: %s", e)
        logger.warning("   Las facturas están guardadas en DB, pero NO se crearon workflows.")
        logger.warning("   Se recomienda ejecutar manualmente: POST %s", endpoint)
        return False
    except Exception as e:
        logger.error("❌ Error inesperado notificando backend: %s", e, exc_info=True)
        return False


def actualizar_timestamps_ejecucion(cfg, logger) -> bool:
    """
    Actualiza los timestamps de última ejecución en el backend.

    Llamado después de una ejecución exitosa para registrar cuándo fue.
    Esto permite que la próxima ejecución sea incremental.

    Returns:
        True si se actualizó al menos una cuenta, False si hubo errores
    """
    api_base_url = getattr(cfg, 'API_BASE_URL', 'http://localhost:8000')
    endpoint = f"{api_base_url}/api/v1/email-config/actualizar-ultimo-procesamiento"
    fecha_ejecucion = datetime.now(timezone.utc)

    exito = True

    for user in cfg.users:
        if not user.cuenta_id:
            logger.warning(
                "Usuario %s no tiene cuenta_id. Saltando actualización de timestamps.",
                user.email
            )
            continue

        try:
            payload = {
                "cuenta_id": user.cuenta_id,
                "fecha_ejecucion": fecha_ejecucion.isoformat(),
            }

            response = requests.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(
                "Timestamps actualizados para cuenta %s (ID=%d)",
                user.email,
                user.cuenta_id
            )

        except requests.RequestException as e:
            logger.error(
                "Error actualizando timestamps para cuenta %s (ID=%d): %s",
                user.email,
                user.cuenta_id,
                e
            )
            exito = False

    return exito


def print_usage():
    usage = "Uso: python -m src.main [-h|--help]"
    print(usage)


if __name__ == "__main__":
    # Verificar argumentos de ayuda
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
        print_usage()
        sys.exit(EXIT_SUCCESS)
    
    # Ejecutar aplicación
    exit_code = main()
    sys.exit(exit_code)