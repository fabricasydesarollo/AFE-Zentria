# src/extraction/monetary_extractor.py (versión forense)

"""
Extractor forense de TODOS los componentes monetarios de una factura UBL.
Su objetivo es recolectar la evidencia para el proceso de reconciliación.
"""
from decimal import Decimal
from typing import Dict
from lxml import etree

from src.core.xml_utils import get_text, get_nodes, safe_decimal, UBL_NAMESPACES

class MonetaryForensicExtractor:
    """
    Extrae un desglose completo de todos los valores monetarios
    para su posterior validación y reconciliación.
    """
    
    def __init__(self):
        self.namespaces = UBL_NAMESPACES

    def extract_all_components(self, root: etree._Element) -> Dict[str, Decimal]:
        """
        Extrae un diccionario con todos los componentes monetarios identificables.
        """
        components = {}

        # 1. Totales Generales (LegalMonetaryTotal)
        legal_total_path = "./cac:LegalMonetaryTotal/"
        components['line_extension_amount'] = self._extract_field(root, f"{legal_total_path}cbc:LineExtensionAmount")
        components['tax_exclusive_amount'] = self._extract_field(root, f"{legal_total_path}cbc:TaxExclusiveAmount")
        components['tax_inclusive_amount'] = self._extract_field(root, f"{legal_total_path}cbc:TaxInclusiveAmount")
        components['allowance_total_amount'] = self._extract_field(root, f"{legal_total_path}cbc:AllowanceTotalAmount")
        components['charge_total_amount'] = self._extract_field(root, f"{legal_total_path}cbc:ChargeTotalAmount")
        components['prepaid_amount'] = self._extract_field(root, f"{legal_total_path}cbc:PrepaidAmount")
        components['payable_amount'] = self._extract_field(root, f"{legal_total_path}cbc:PayableAmount")

        # 2. Suma de Impuestos (IVA, INC, etc.)
        tax_total_nodes = get_nodes(root, "./cac:TaxTotal", self.namespaces)
        total_impuestos = Decimal("0.0")
        for node in tax_total_nodes:
            tax_amount = self._extract_field(node, "./cbc:TaxAmount")
            if tax_amount:
                total_impuestos += tax_amount
        components['total_impuestos_calculado'] = total_impuestos

        # 3. Suma de Retenciones (ReteFuente, ReteICA, ReteIVA)
        withholding_tax_nodes = get_nodes(root, "./cac:WithholdingTaxTotal", self.namespaces)
        total_retenciones = Decimal("0.0")
        for node in withholding_tax_nodes:
            tax_amount = self._extract_field(node, "./cbc:TaxAmount")
            if tax_amount:
                total_retenciones += tax_amount
        components['total_retenciones_calculado'] = total_retenciones

        return {k: v for k, v in components.items() if v is not None}

    def _extract_field(self, root: etree._Element, xpath: str) -> Decimal | None:
        """Extrae un campo monetario de forma segura."""
        value_str = get_text(root, xpath, self.namespaces)
        return safe_decimal(value_str)


# Compatibilidad: exponer bajo el nombre histórico
MonetaryExtractor = MonetaryForensicExtractor