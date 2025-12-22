"""
Extractor de campos monetarios desde CustomFieldExtension.

Prioridad MÁXIMA: Si existen CustomFields con datos monetarios,
estos contienen los DATOS REALES de la factura.

Basado en análisis de 494 XMLs reales:
- 48 XMLs (10%) tienen CustomFieldExtension con campos monetarios
- ValorTotalDocumento: valor REAL a pagar (después de retenciones)
- Subtotal, Iva, TotalRetencion: desglose detallado

PRIORIDAD DE BÚSQUEDA:
1. ValorTotalDocumento (datos reales netos)
2. Total (campo custom alternativo)
3. Subtotal, Iva, TotalRetencion (desglose)
"""
from decimal import Decimal
from typing import Dict, Any, Optional
from lxml import etree

from src.core.xml_utils import get_text, safe_decimal, UBL_NAMESPACES
from src.utils.logger import logger


class CustomFieldMonetaryExtractor:
    """
    Extrae valores monetarios desde CustomFieldExtension.

    Estos campos tienen PRIORIDAD máxima porque contienen
    los datos reales que el usuario capturó en el sistema.
    """

    # Mapeo de campos custom a tipos de datos
    MONETARY_FIELD_MAPPING = {
        'ValorTotalDocumento': 'total_a_pagar',
        'Total': 'total_a_pagar_alt',
        'Subtotal': 'subtotal',
        'Iva': 'iva',
        'Impoconsumo': 'impuesto_consumo',
        'TotalRetencion': 'total_retenciones',
        'Descuento': 'descuento',
    }

    def __init__(self):
        self.namespaces = UBL_NAMESPACES

    def extract_all(self, root: etree._Element) -> Dict[str, Any]:
        """
        Extrae TODOS los valores monetarios de CustomFieldExtension.

        Args:
            root: Elemento raíz del documento

        Returns:
            Dict con campos encontrados: {
                'tiene_custom_fields': bool,
                'total_a_pagar': Decimal | None,
                'subtotal': Decimal | None,
                'iva': Decimal | None,
                'total_retenciones': Decimal | None,
                'otros': {campo: valor, ...}
            }
        """
        custom_fields = self._get_all_custom_fields(root)

        if not custom_fields:
            return {'tiene_custom_fields': False}

        resultado = {
            'tiene_custom_fields': True,
            'total_a_pagar': None,
            'subtotal': None,
            'iva': None,
            'total_retenciones': None,
            'otros': {}
        }

        # Procesar campos monetarios mapeados
        for campo_custom, valor in custom_fields.items():
            valor_decimal = safe_decimal(valor)

            if valor_decimal is None:
                continue

            # Priorizar campos principales
            if campo_custom == 'ValorTotalDocumento':
                resultado['total_a_pagar'] = valor_decimal
                logger.debug(f"Custom: ValorTotalDocumento = {valor_decimal}")

            elif campo_custom == 'Total' and resultado['total_a_pagar'] is None:
                resultado['total_a_pagar'] = valor_decimal
                logger.debug(f"Custom: Total (alt) = {valor_decimal}")

            elif campo_custom == 'Subtotal':
                resultado['subtotal'] = valor_decimal
                logger.debug(f"Custom: Subtotal = {valor_decimal}")

            elif campo_custom == 'Iva':
                resultado['iva'] = valor_decimal
                logger.debug(f"Custom: Iva = {valor_decimal}")

            elif campo_custom == 'TotalRetencion':
                resultado['total_retenciones'] = valor_decimal
                logger.debug(f"Custom: TotalRetencion = {valor_decimal}")

            else:
                # Campos adicionales
                resultado['otros'][campo_custom] = valor_decimal

        return resultado

    def has_monetary_fields(self, root: etree._Element) -> bool:
        """
        Verifica si el documento tiene CustomFieldExtension con datos monetarios.

        Args:
            root: Elemento raíz del documento

        Returns:
            True si existen CustomFields monetarios
        """
        custom_fields = self._get_all_custom_fields(root)

        # Verificar si hay al menos un campo monetario
        for campo in custom_fields.keys():
            if campo in self.MONETARY_FIELD_MAPPING:
                return True

        return False

    def get_total_a_pagar(self, root: etree._Element) -> Optional[Decimal]:
        """
        Extrae SOLO el total a pagar de CustomFields.

        Búsqueda en orden:
        1. ValorTotalDocumento (prioritario)
        2. Total (alternativo)

        Args:
            root: Elemento raíz del documento

        Returns:
            Decimal con el total a pagar, o None si no existe
        """
        custom_fields = self._get_all_custom_fields(root)

        # Intentar ValorTotalDocumento (PRIORITARIO)
        if 'ValorTotalDocumento' in custom_fields:
            valor = safe_decimal(custom_fields['ValorTotalDocumento'])
            if valor is not None and valor > 0:
                return valor

        # Fallback: Total
        if 'Total' in custom_fields:
            valor = safe_decimal(custom_fields['Total'])
            if valor is not None and valor > 0:
                return valor

        return None

    def _get_all_custom_fields(self, root: etree._Element) -> Dict[str, str]:
        """
        Extrae TODOS los CustomFieldExtension como diccionario.

        Estructura esperada:
        ext:ExtensionContent/CustomFieldExtension/CustomFieldExtension[@Name='...']/@Value

        Args:
            root: Elemento raíz del documento

        Returns:
            Dict {nombre_campo: valor, ...}
        """
        custom_fields = {}

        try:
            # Buscar extensiones
            ext_contents = root.xpath(
                './/ext:ExtensionContent',
                namespaces=self.namespaces
            )

            for ext in ext_contents:
                # Nivel 1: CustomFieldExtension (contenedor)
                for child in ext:
                    if 'CustomFieldExtension' in str(child.tag):
                        # Nivel 2: CustomFieldExtension (individual)
                        for inner in child:
                            if 'CustomFieldExtension' in str(inner.tag):
                                name = inner.get('Name')
                                value = inner.get('Value')

                                if name and value:
                                    custom_fields[name] = value

        except Exception as exc:
            logger.warning(f"Error extrayendo CustomFields: {exc}")

        return custom_fields
