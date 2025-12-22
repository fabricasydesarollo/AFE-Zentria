# app/services/automation/__init__.py
"""
Módulo de automatización para facturas recurrentes.

Este módulo contiene toda la lógica para:
- Detectar patrones de recurrencia
- Generar fingerprints de facturas
- Tomar decisiones automáticas
- Procesar facturas pendientes
"""

from .automation_service import AutomationService
from .pattern_detector import PatternDetector
from .fingerprint_generator import FingerprintGenerator
from .decision_engine import DecisionEngine

__all__ = [
    "AutomationService",
    "PatternDetector", 
    "FingerprintGenerator",
    "DecisionEngine"
]