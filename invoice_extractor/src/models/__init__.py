# src/models/__init__.py

"""
Módulo models - Tipos de datos y estructuras.
"""
from src.models.invoice_types import (
    Adjustment,
    InvoiceItem,
    OrdenCompra,
    NotasAdicionales,
    MonetaryFields,
    InvoiceData
)
# DEPRECADO: FacturaParser eliminado - usar InvoiceParserFacade directamente
from src.facade.invoice_parser_facade import InvoiceParserFacade as FacturaParser

__all__ = [
    # Dataclasses
    'Adjustment',
    'InvoiceItem',
    'OrdenCompra',
    'NotasAdicionales',
    'MonetaryFields',
    'InvoiceData',

    # Parser (alias de compatibilidad - deprecado)
    'FacturaParser',
]
