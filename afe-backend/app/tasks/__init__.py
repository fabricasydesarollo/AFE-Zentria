# app/tasks/__init__.py
"""
Módulo de tareas programadas para el sistema AFE.

Este módulo contiene las definiciones de tareas que se ejecutan
de forma automatizada en segundo plano.
"""

from .automation_tasks import (
    ejecutar_automatizacion_programada,
    ejecutar_si_horario_laboral,
    AutomationScheduler
)

__all__ = [
    "ejecutar_automatizacion_programada",
    "ejecutar_si_horario_laboral", 
    "AutomationScheduler"
]