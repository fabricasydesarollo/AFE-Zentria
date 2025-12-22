# app/tasks/automation_tasks.py
"""
Tareas programadas para el sistema de automatización de facturas.

Este módulo define las tareas que se ejecutan de forma automática
para procesar facturas recurrentes sin intervención manual.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from app.db.session import get_db
from app.services.automation.automation_service import AutomationService
from app.services.automation.notification_service import NotificationService
from app.crud import audit as crud_audit


# Configurar logging
logger = logging.getLogger(__name__)


class AutomationScheduler:
    """
    Programador de tareas de automatización.
    """
    
    def __init__(self):
        self.automation_service = AutomationService()
        self.notification_service = NotificationService()

    def ejecutar_procesamiento_programado(
        self, 
        limite_facturas: int = 100,
        notificar_resultados: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta el procesamiento programado de facturas.
        
        Esta función está diseñada para ser llamada por un cron job
        o sistema de tareas programadas como Celery.
        """
        inicio = datetime.utcnow()
        logger.info(f"Iniciando procesamiento automático programado - {inicio}")
        
        try:
            # Obtener sesión de base de datos
            db = next(get_db())
            
            try:
                # Ejecutar procesamiento
                resultado = self.automation_service.procesar_facturas_pendientes(
                    db=db,
                    limite_facturas=limite_facturas,
                    modo_debug=False
                )
                
                # Enviar notificaciones si hay resultados
                if notificar_resultados and resultado['resumen_general']['facturas_procesadas'] > 0:
                    self._enviar_notificaciones_programadas(db, resultado)
                
                # Registrar éxito en auditoría
                self._registrar_ejecucion_auditoria(db, resultado, "exitoso")
                
                fin = datetime.utcnow()
                duracion = (fin - inicio).total_seconds()
                
                logger.info(f"Procesamiento programado completado en {duracion:.2f} segundos")
                
                return {
                    'exito': True,
                    'inicio': inicio,
                    'fin': fin,
                    'duracion_segundos': duracion,
                    'resultado': resultado
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error en procesamiento programado: {str(e)}")
            
            # Intentar registrar error en auditoría
            try:
                db = next(get_db())
                self._registrar_ejecucion_auditoria(db, None, "error", str(e))
                db.close()
            except:
                pass
            
            return {
                'exito': False,
                'error': str(e),
                'inicio': inicio,
                'fin': datetime.utcnow()
            }

    def _enviar_notificaciones_programadas(self, db, resultado: Dict[str, Any]) -> None:
        """Envía notificaciones de los resultados del procesamiento programado."""
        try:
            # Solo enviar resumen si se procesaron facturas
            if resultado['resumen_general']['facturas_procesadas'] > 0:
                from app.crud import factura as crud_factura
                
                facturas_pendientes = crud_factura.get_facturas_pendientes_procesamiento(db)
                
                self.notification_service.enviar_resumen_procesamiento(
                    db=db,
                    estadisticas_procesamiento=resultado,
                    facturas_pendientes=facturas_pendientes
                )
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones programadas: {str(e)}")

    def _registrar_ejecucion_auditoria(
        self, 
        db,
        resultado: Dict[str, Any] = None,
        estado: str = "exitoso",
        error: str = None
    ) -> None:
        """Registra la ejecución de la tarea programada en auditoría."""
        try:
            detalles = {
                'tipo_tarea': 'procesamiento_automatico_programado',
                'estado': estado,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if resultado:
                detalles.update({
                    'facturas_procesadas': resultado['resumen_general']['facturas_procesadas'],
                    'aprobadas_automaticamente': resultado['resumen_general']['aprobadas_automaticamente'],
                    'enviadas_revision': resultado['resumen_general']['enviadas_revision'],
                    'tasa_automatizacion': resultado['resumen_general']['tasa_automatizacion']
                })
            
            if error:
                detalles['error'] = error
            
            crud_audit.create_audit(
                db=db,
                entidad="sistema",
                entidad_id=0,  # ID del sistema
                accion="tarea_programada_automatizacion",
                usuario="sistema_scheduler",
                detalle=detalles
            )
            
        except Exception as e:
            logger.error(f"Error registrando auditoría de tarea programada: {str(e)}")


# Función principal para integración con sistemas de tareas
def ejecutar_automatizacion_programada() -> Dict[str, Any]:
    """
    Función principal para ejecutar desde sistemas de tareas como Celery o cron.
    
    Ejemplo de uso con cron:
    # Ejecutar cada hora en horario laboral
    0 9-17 * * 1-5 /path/to/python -c "from app.tasks.automation_tasks import ejecutar_automatizacion_programada; ejecutar_automatizacion_programada()"
    
    Ejemplo de uso con Celery:
    @celery_app.task
    def tarea_automatizacion():
        return ejecutar_automatizacion_programada()
    """
    scheduler = AutomationScheduler()
    return scheduler.ejecutar_procesamiento_programado()


# Función para ejecutar procesamiento durante horarios específicos
def ejecutar_si_horario_laboral() -> Dict[str, Any]:
    """
    Ejecuta el procesamiento solo durante horario laboral.
    
    Útil para evitar procesamientos fuera de horario.
    """
    ahora = datetime.now()
    
    # Verificar si es horario laboral (9 AM - 5 PM, Lunes a Viernes)
    if (ahora.weekday() < 5 and  # Lunes a Viernes
        9 <= ahora.hour < 17):    # 9 AM a 5 PM
        
        return ejecutar_automatizacion_programada()
    else:
        logger.info("Procesamiento omitido - fuera de horario laboral")
        return {
            'exito': True,
            'mensaje': 'Procesamiento omitido - fuera de horario laboral',
            'timestamp': ahora
        }


if __name__ == "__main__":
    # Permitir ejecución directa del script
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Modo de prueba
        resultado = ejecutar_automatizacion_programada()
        print("Resultado del procesamiento:")
        print(f"Éxito: {resultado['exito']}")
        if resultado['exito'] and 'resultado' in resultado:
            stats = resultado['resultado']['resumen_general']
            print(f"Facturas procesadas: {stats['facturas_procesadas']}")
            print(f"Aprobadas automáticamente: {stats['aprobadas_automaticamente']}")
            print(f"Enviadas a revisión: {stats['enviadas_revision']}")
            print(f"Tasa de automatización: {stats['tasa_automatizacion']:.1f}%")
    else:
        # Ejecución normal
        ejecutar_automatizacion_programada()