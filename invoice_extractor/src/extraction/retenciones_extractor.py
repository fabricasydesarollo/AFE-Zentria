# src/extraction/retenciones_extractor.py

"""

PATRONES SOPORTADOS:
- Patrón A: CustomField 'TotalRetencion' (más confiable)
- Patrón B: WithholdingTaxTotal estándar UBL
- Patrón C: Cálculo inferencial cuando hay diferencia matemática
- Patrón D: Sin retenciones (0.0)

FILOSOFÍA:
- Total a pagar: SIEMPRE extraído del XML, NUNCA calculado
- Retenciones: PRIMERO extraer, si falla INFERIR matemáticamente
- Validación: Comparar que subtotal + iva - retenciones = total_oficial
"""
from decimal import Decimal
from typing import Optional, Dict
from lxml import etree

from src.core.xml_utils import get_text, get_nodes, safe_decimal, UBL_NAMESPACES
from src.utils.logger import logger


class RetencionesExtractor:
    """Extrae retenciones con soporte multi-patrón y cálculo inferencial."""

    def __init__(self):
        self.namespaces = UBL_NAMESPACES
        self._last_extraction_method: Optional[str] = None

    def extract(
        self,
        root: etree._Element,
        componentes_monetarios: Optional[Dict[str, Decimal]] = None,
        total_oficial: Optional[Decimal] = None
    ) -> Decimal:
        """
        Extrae el total de retenciones con jerarquía de confianza + inferencia.

        IMPORTANTE: El total_oficial ya fue extraído del XML. Esta función
        solo extrae/infiere las retenciones para que la ecuación sea coherente:
        subtotal + iva - retenciones = total_oficial

        Args:
            root: Elemento raíz del XML
            componentes_monetarios: Dict con subtotal, iva, etc. (para inferencia)
            total_oficial: Total a pagar YA EXTRAÍDO del XML (para inferencia)

        Returns:
            Decimal con el total de retenciones (nunca None, mínimo 0.0)
        """

        # PRIORIDAD 1: CustomField 'TotalRetencion'
        retencion_custom = self._extract_from_custom_field(root)
        if retencion_custom is not None and retencion_custom > 0:
            self._last_extraction_method = "CustomField"
            logger.info(
                f"Retenciones: {retencion_custom} (fuente: CustomField)"
            )
            return retencion_custom

        # PRIORIDAD 2: WithholdingTaxTotal
        retencion_withholding = self._extract_from_withholding_tax_total(root)
        if retencion_withholding is not None and retencion_withholding > 0:
            self._last_extraction_method = "WithholdingTaxTotal"
            logger.info(
                f"Retenciones: {retencion_withholding} (fuente: WithholdingTaxTotal)"
            )
            return retencion_withholding

        # PRIORIDAD 3: Inferencia matemática (CRÍTICO PARA CASOS EDGE)
        # Si subtotal + iva != total_oficial, entonces hay retenciones implícitas
        if componentes_monetarios and total_oficial:
            retencion_inferida = self._calculate_inferential_retenciones(
                componentes_monetarios,
                total_oficial
            )
            if retencion_inferida is not None and retencion_inferida > 0:
                self._last_extraction_method = "Inferencia_Matematica"
                logger.warning(
                    f"Retenciones INFERIDAS matemáticamente: {retencion_inferida} "
                    f"(cálculo: [subtotal+iva] - [total_oficial]). "
                    f"Las retenciones no están explícitas en el XML pero se calculan "
                    f"por diferencia para mantener coherencia."
                )
                return retencion_inferida

        # Sin retenciones
        self._last_extraction_method = "Sin_Retenciones"
        logger.debug("Sin retenciones en la factura")
        return Decimal("0.0")

    def get_last_extraction_method(self) -> Optional[str]:
        """Retorna el método usado en la última extracción (para auditoría)."""
        return self._last_extraction_method

    def _extract_from_custom_field(self, root: etree._Element) -> Optional[Decimal]:
        """Extrae 'TotalRetencion' de CustomFieldExtension (Patrón A - 15%)."""
        for element in root.iter():
            if 'CustomFieldExtension' in str(element.tag):
                for child in element:
                    if 'CustomFieldExtension' in str(child.tag):
                        name = child.get('Name')
                        if name == 'TotalRetencion':
                            value = child.get('Value')
                            if value:
                                return safe_decimal(value)
        return None

    def _extract_from_withholding_tax_total(
        self,
        root: etree._Element
    ) -> Optional[Decimal]:
        """Suma retenciones desde WithholdingTaxTotal (Patrón B - 14%)."""
        withholding_nodes = get_nodes(
            root,
            "./cac:WithholdingTaxTotal",
            self.namespaces
        )

        if not withholding_nodes:
            return None

        total = Decimal("0.0")
        for node in withholding_nodes:
            tax_amount_str = get_text(node, "./cbc:TaxAmount", self.namespaces)
            tax_amount = safe_decimal(tax_amount_str)
            if tax_amount:
                total += tax_amount

        return total if total > 0 else None

    def _calculate_inferential_retenciones(
        self,
        componentes_monetarios: Dict[str, Decimal],
        total_oficial: Decimal
    ) -> Optional[Decimal]:
        """
        Calcula retenciones por inferencia matemática (Patrón C - NUEVO).

        Lógica: Si (subtotal + iva) > total_oficial, entonces:
        retenciones = (subtotal + iva) - total_oficial

        Esto solo se aplica cuando:
        1. No se encontraron retenciones explícitas en el XML
        2. Hay una diferencia significativa (> 1 peso por tolerancia)
        3. La diferencia es positiva (no negativa)

        Args:
            componentes_monetarios: Dict con subtotal, iva extraídos
            total_oficial: Total a pagar extraído del XML

        Returns:
            Decimal con retenciones inferidas o None si no aplica
        """
        subtotal = componentes_monetarios.get('line_extension_amount', Decimal("0.0"))
        iva = componentes_monetarios.get('total_impuestos_calculado', Decimal("0.0"))

        # Calcular el total bruto esperado
        total_bruto = subtotal + iva

        # Calcular la diferencia
        diferencia = total_bruto - total_oficial

        # Tolerancia de 1 peso (por redondeos)
        TOLERANCIA = Decimal("1.0")

        # Si la diferencia es significativa y positiva, son retenciones
        if diferencia > TOLERANCIA:
            return diferencia

        return None
