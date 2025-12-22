"""
Tarea programada para análisis automático de patrones de facturas.

Esta tarea se ejecuta periódicamente (diariamente o semanalmente) para:
1. Analizar facturas recientes de la BD
2. Actualizar patrones en historial_pagos
3. Mantener el sistema de automatización actualizado

Configuración recomendada:
- Frecuencia: Diaria a las 2:00 AM
- Ventana de análisis: 12 meses
- Timeout: 30 minutos


Fecha: 2025-10-08
"""

import logging
from datetime import datetime
from typing import Dict, Any

from app.db.session import SessionLocal
from app.services.analisis_patrones_service import AnalizadorPatronesService


logger = logging.getLogger(__name__)


def analizar_patrones_periodico(
    ventana_meses: int = 12,
    forzar_recalculo: bool = False
) -> Dict[str, Any]:
    """
    Tarea programada de análisis de patrones.

    Esta función debe ser llamada por un scheduler (Celery, APScheduler, cron, etc.)

    Args:
        ventana_meses: Cantidad de meses hacia atrás a analizar
        forzar_recalculo: Si True, recalcula todos los patrones

    Returns:
        Resultado del análisis con estadísticas
    """
    logger.info("="*80)
    logger.info("INICIANDO ANÁLISIS PROGRAMADO DE PATRONES")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Ventana: {ventana_meses} meses")
    logger.info(f"Forzar recálculo: {forzar_recalculo}")
    logger.info("="*80)

    db = SessionLocal()

    try:
        # Ejecutar análisis
        analizador = AnalizadorPatronesService(db)

        resultado = analizador.analizar_patrones_desde_bd(
            ventana_meses=ventana_meses,
            forzar_recalculo=forzar_recalculo
        )

        # Log de resultados
        if resultado['exito']:
            stats = resultado['estadisticas']
            logger.info("  ANÁLISIS COMPLETADO EXITOSAMENTE")
            logger.info(f"   Facturas analizadas: {stats['facturas_analizadas']}")
            logger.info(f"   Patrones detectados: {stats['patrones_detectados']}")
            logger.info(f"   Patrones nuevos: {stats['patrones_nuevos']}")
            logger.info(f"   Patrones actualizados: {stats['patrones_actualizados']}")
            logger.info(f"   Patrones mejorados: {stats['patrones_mejorados']}")
            logger.info(f"   Patrones degradados: {stats['patrones_degradados']}")
            logger.info(f"   Errores: {stats['errores']}")
        else:
            logger.error(f" ERROR EN ANÁLISIS: {resultado.get('mensaje')}")

        return resultado

    except Exception as e:
        logger.error(f" ERROR CRÍTICO EN TAREA PROGRAMADA: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'exito': False,
            'mensaje': f'Error crítico: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }

    finally:
        db.close()
        logger.info("="*80)
        logger.info("FIN DE ANÁLISIS PROGRAMADO")
        logger.info("="*80)


# ============================================================================
# CONFIGURACIÓN PARA CELERY (si se usa)
# ============================================================================

try:
    from celery import shared_task

    @shared_task(name="analizar_patrones_periodico")
    def analizar_patrones_celery_task(ventana_meses: int = 12):
        """
        Wrapper de Celery para la tarea de análisis.

        Configuración en celeryconfig.py:
        ```python
        beat_schedule = {
            'analizar-patrones-diario': {
                'task': 'analizar_patrones_periodico',
                'schedule': crontab(hour=2, minute=0),  # 2:00 AM diario
                'args': (12,)  # 12 meses
            }
        }
        ```
        """
        return analizar_patrones_periodico(ventana_meses=ventana_meses)

except ImportError:
    logger.warning("Celery no disponible. Tarea programada solo manual.")


# ============================================================================
# CONFIGURACIÓN PARA APSCHEDULER (alternativa a Celery)
# ============================================================================

def configurar_apscheduler():
    """
    Configura APScheduler para ejecutar análisis periódico.

    Ejemplo de uso en main.py:
    ```python
    from app.tasks.analisis_patrones_task import configurar_apscheduler

    scheduler = configurar_apscheduler()
    scheduler.start()
    ```
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler()

        # Ejecutar diariamente a las 2:00 AM
        scheduler.add_job(
            func=analizar_patrones_periodico,
            trigger=CronTrigger(hour=2, minute=0),
            id='analizar_patrones_diario',
            name='Análisis de patrones diario',
            replace_existing=True,
            kwargs={'ventana_meses': 12, 'forzar_recalculo': False}
        )

        logger.info("  APScheduler configurado para análisis de patrones")
        return scheduler

    except ImportError:
        logger.error(" APScheduler no disponible. Instalar: pip install apscheduler")
        return None


# ============================================================================
# EJECUCIÓN MANUAL (para testing)
# ============================================================================

if __name__ == "__main__":
    """
    Ejecución manual para testing:

    python -m app.tasks.analisis_patrones_task
    """
    print(" Ejecutando análisis de patrones manualmente...")
    print()

    resultado = analizar_patrones_periodico(
        ventana_meses=12,
        forzar_recalculo=False
    )

    print()
    print("RESULTADO:")
    print(f"   Éxito: {resultado['exito']}")
    print(f"   Mensaje: {resultado.get('mensaje', 'N/A')}")

    if resultado['exito']:
        stats = resultado['estadisticas']
        print()
        print("📈 ESTADÍSTICAS:")
        print(f"   Facturas analizadas: {stats['facturas_analizadas']}")
        print(f"   Patrones nuevos: {stats['patrones_nuevos']}")
        print(f"   Patrones actualizados: {stats['patrones_actualizados']}")
        print(f"   Errores: {stats['errores']}")
