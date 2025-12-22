"""
Extractor de total a pagar definitivo basado en jerarquía de confianza.

Jerarquía de búsqueda (basada en análisis de 494 XMLs reales):

Nivel 1 (PRIORITARIO - CustomFields):
  └─ ValorTotalDocumento (10% de XMLs) - DATOS REALES

Nivel 2 (Estándar UBL - LegalMonetaryTotal):
  ├─ PayableAmount (26% de XMLs)
  ├─ TaxInclusiveAmount (26% de XMLs)
  └─ TaxExclusiveAmount (26% de XMLs)

Nivel 3 (Fallback - CustomFields alternativo):
  └─ Total, Valor Total, etc.

Este extracto NO realiza cálculos, solo extrae valores reales del XML.
"""
from decimal import Decimal
from typing import Optional, List, Tuple
from lxml import etree

from src.core.xml_utils import get_text, safe_decimal, UBL_NAMESPACES
from src.utils.logger import logger


class TotalDefinitivoExtractor:
    """
    Extrae el total a pagar real de un documento de facturación.

    Estrategia:
    1. Buscar CustomFieldExtension (datos reales del usuario)
    2. Buscar LegalMonetaryTotal (estructura standard UBL)
    3. Fallback adicionales (otros campos custom)

    Nunca realiza cálculos. Solo extrae valores presentes en el XML.
    """

    # Jerarquía de búsqueda de PayableAmount
    PAYABLE_AMOUNT_PATHS: List[Tuple[str, str]] = [
        ("CUSTOM_VALOR_TOTAL_DOCUMENTO", ".//ext:ExtensionContent/CustomFieldExtension/CustomFieldExtension[@Name='ValorTotalDocumento']/@Value"),
        ("PAYABLE_AMOUNT", "./cac:LegalMonetaryTotal/cbc:PayableAmount"),
        ("TAX_INCLUSIVE_AMOUNT", "./cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount"),
        ("CUSTOM_TOTAL", ".//ext:ExtensionContent/CustomFieldExtension/CustomFieldExtension[@Name='Total']/@Value"),
    ]

    def __init__(self):
        self.namespaces = UBL_NAMESPACES
        self.tiene_campo_total_neto = False

    def extract(self, root: etree._Element) -> Optional[Decimal]:
        """
        Extrae el total a pagar real del documento.

        Args:
            root: Elemento raíz del documento

        Returns:
            Decimal con el total a pagar, o None si no se encuentra
        """
        # Iterar jerarquía de confianza
        for source_name, xpath in self.PAYABLE_AMOUNT_PATHS:
            valor_str = get_text(root, xpath, self.namespaces)

            if not valor_str:
                continue

            valor = safe_decimal(valor_str)

            if valor is not None and valor > 0:
                # Marcar si encontró campo custom neto
                self.tiene_campo_total_neto = 'CUSTOM_VALOR_TOTAL' in source_name

                logger.info(f"Total a pagar: {valor} (fuente: {source_name})")
                return valor

        logger.warning("No se encontró Total a Pagar en ninguna ubicación esperada")
        return None

    def has_net_total_field(self) -> bool:
        """
        Indica si se encontró un campo custom con total neto (después de retenciones).

        Returns:
            True si el total fue extraído de un campo custom que contiene el total neto
        """
        return self.tiene_campo_total_neto