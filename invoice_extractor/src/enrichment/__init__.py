# src/enrichment/__init__.py
"""
Módulo enrichment - Enriquecimiento y clasificación de facturas.
"""
from src.enrichment.invoice_enricher import InvoiceEnricher

__all__ = [
    'InvoiceEnricher',
]
