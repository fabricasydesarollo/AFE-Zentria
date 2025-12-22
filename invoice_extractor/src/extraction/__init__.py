# src/extraction/__init__.py
"""
Módulo extraction - Extractores especializados de datos.
"""
from src.extraction.monetary_extractor import MonetaryForensicExtractor
from src.extraction.basic_extractor import BasicFieldExtractor
from src.extraction.items_extractor import ItemsExtractor
from src.extraction.additional_extractors import (
    OrdenCompraExtractor,
    NotasAdicionalesExtractor
)
from src.extraction.total_extractor import TotalDefinitivoExtractor

# Compat: exponer el extractor forense bajo el nombre antiguo
MonetaryExtractor = MonetaryForensicExtractor

__all__ = [
    'MonetaryExtractor',
    'BasicFieldExtractor',
    'ItemsExtractor',
    'OrdenCompraExtractor',
    'NotasAdicionalesExtractor',
    'TotalDefinitivoExtractor',
]
