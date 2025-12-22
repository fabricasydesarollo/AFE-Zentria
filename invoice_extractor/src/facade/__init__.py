# src/facade/__init__.py
"""
Módulo facade - Punto de entrada unificado para parseo de facturas.
"""
from src.facade.invoice_parser_facade import InvoiceParserFacade

__all__ = [
    'InvoiceParserFacade',
]