"""
Extractor de items (líneas) de facturas electrónicas.
"""
from typing import Optional, List, Dict, Any
from lxml import etree

from src.utils.logger import logger
from src.core.xml_utils import get_text, get_nodes, safe_float, UBL_NAMESPACES


class ItemsExtractor:
    """Extrae información de los items de la factura"""
    
    def __init__(self):
        self.namespaces = UBL_NAMESPACES
    
    def extract_items_resumen(
        self,
        root: etree._Element,
        max_items: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Extrae resumen de items de la factura.
        
        Args:
            root: Elemento raíz de la factura
            max_items: Número máximo de items a retornar (ordenados por valor)
            
        Returns:
            Lista de items o None si no hay items
        """
        try:
            items = []
            line_nodes = get_nodes(root, "./cac:InvoiceLine", self.namespaces)
            
            for line_node in line_nodes:
                item = self._extract_single_item(line_node, len(items) + 1)
                if item:
                    items.append(item)
            
            if not items:
                return None
            
            # Ordenar por valor de línea (descendente) y retornar top N
            items_sorted = sorted(items, key=lambda x: x["valor_linea"], reverse=True)
            return items_sorted[:max_items]
            
        except Exception as exc:
            logger.warning(f"Error extracting items: {exc}")
            return None
    
    def _extract_single_item(
        self,
        line_node: etree._Element,
        default_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Extrae información de un solo item.
        
        Args:
            line_node: Nodo InvoiceLine
            default_id: ID por defecto si no se encuentra
            
        Returns:
            Diccionario con datos del item o None
        """
        try:
            item_node = line_node.find("./cac:Item", self.namespaces)
            if item_node is None:
                return None
            
            price_node = line_node.find("./cac:Price", self.namespaces)
            
            # Extraer datos básicos
            cantidad = safe_float(get_text(line_node, "./cbc:InvoicedQuantity", self.namespaces))
            valor_linea = safe_float(get_text(line_node, "./cbc:LineExtensionAmount", self.namespaces))
            precio_unitario = 0.0
            
            if price_node is not None:
                precio_unitario = safe_float(get_text(price_node, "./cbc:PriceAmount", self.namespaces))
            
            # Extraer propiedades adicionales
            propiedades_adicionales = self._extract_additional_properties(item_node)
            
            return {
                "linea_id": get_text(line_node, "./cbc:ID", self.namespaces) or str(default_id),
                "descripcion": get_text(item_node, "./cbc:Description", self.namespaces) or "",
                "cantidad": cantidad,
                "valor_linea": valor_linea,
                "precio_unitario": precio_unitario,
                "codigo_producto": get_text(
                    item_node, "./cac:StandardItemIdentification/cbc:ID", self.namespaces
                ),
                "propiedades_adicionales": propiedades_adicionales if propiedades_adicionales else None
            }
            
        except Exception as exc:
            logger.warning(f"Error extracting single item: {exc}")
            return None
    
    def _extract_additional_properties(self, item_node: etree._Element) -> Dict[str, str]:
        """
        Extrae propiedades adicionales del item.
        
        Args:
            item_node: Nodo Item
            
        Returns:
            Diccionario con propiedades adicionales
        """
        propiedades = {}
        prop_nodes = get_nodes(item_node, "./cac:AdditionalItemProperty", self.namespaces)
        
        for prop_node in prop_nodes:
            nombre = get_text(prop_node, "./cbc:Name", self.namespaces)
            valor = get_text(prop_node, "./cbc:Value", self.namespaces)
            
            if nombre and valor:
                propiedades[nombre] = valor
        
        return propiedades
    
    def get_total_items_count(self, root: etree._Element) -> int:
        """
        Obtiene el número total de items en la factura.

        Args:
            root: Elemento raíz de la factura

        Returns:
            Número de items
        """
        line_nodes = get_nodes(root, "./cac:InvoiceLine", self.namespaces)
        return len(line_nodes)

    def extract_all_items_completo(
        self,
        root: etree._Element
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Extrae TODOS los items de la factura con información completa.

        Esta versión enterprise incluye:
        - Impuestos por item
        - Descuentos
        - Códigos estándar
        - Unidad de medida
        - Todos los campos necesarios para factura_items

        Args:
            root: Elemento raíz de la factura

        Returns:
            Lista de todos los items o None si no hay items
        """
        try:
            items = []
            line_nodes = get_nodes(root, "./cac:InvoiceLine", self.namespaces)

            for idx, line_node in enumerate(line_nodes, start=1):
                item = self._extract_single_item_completo(line_node, idx)
                if item:
                    items.append(item)

            return items if items else None

        except Exception as exc:
            logger.warning(f"Error extracting all items completo: {exc}")
            return None

    def _extract_single_item_completo(
        self,
        line_node: etree._Element,
        numero_linea: int
    ) -> Optional[Dict[str, Any]]:
        """
        Extrae información completa de un solo item (enterprise version).

        Args:
            line_node: Nodo InvoiceLine
            numero_linea: Número de línea

        Returns:
            Diccionario con todos los datos del item
        """
        try:
            item_node = line_node.find("./cac:Item", self.namespaces)
            if item_node is None:
                return None

            price_node = line_node.find("./cac:Price", self.namespaces)

            # ============================================================
            # DATOS BÁSICOS
            # ============================================================
            descripcion = get_text(item_node, "./cbc:Description", self.namespaces) or ""

            # Cantidad y unidad de medida
            cantidad_text = get_text(line_node, "./cbc:InvoicedQuantity", self.namespaces)
            cantidad = safe_float(cantidad_text)

            # Extraer unidad de medida del atributo
            cantidad_node = line_node.find("./cbc:InvoicedQuantity", self.namespaces)
            unidad_medida = None
            if cantidad_node is not None:
                unidad_medida = cantidad_node.get("unitCode")

            # ============================================================
            # CÓDIGOS
            # ============================================================
            # Código del vendedor
            codigo_producto = get_text(
                item_node, "./cac:SellersItemIdentification/cbc:ID", self.namespaces
            )

            # NOTA: codigo_estandar eliminado (SCHEMA v2.0.0 - 2025-12-02)
            # Antes: StandardItemIdentification/ID (EAN, UNSPSC) - columna no existe en BD

            # ============================================================
            # PRECIOS Y MONTOS
            # ============================================================
            subtotal = safe_float(get_text(line_node, "./cbc:LineExtensionAmount", self.namespaces))

            precio_unitario = 0.0
            if price_node is not None:
                precio_unitario = safe_float(get_text(price_node, "./cbc:PriceAmount", self.namespaces))

            # ============================================================
            # DESCUENTOS
            # ============================================================
            descuento_valor = 0.0
            # NOTA: descuento_porcentaje eliminado (SCHEMA v2.0.0 - 2025-12-02)
            # Solo se mantiene descuento_valor absoluto

            allowance_nodes = get_nodes(line_node, "./cac:AllowanceCharge", self.namespaces)
            for allow_node in allowance_nodes:
                charge_indicator = get_text(allow_node, "./cbc:ChargeIndicator", self.namespaces)
                if charge_indicator == "false":  # Es descuento
                    descuento_valor = safe_float(get_text(allow_node, "./cbc:Amount", self.namespaces))
                    # MultiplierFactorNumeric ya no se extrae (descuento_porcentaje eliminado)

            # ============================================================
            # IMPUESTOS
            # ============================================================
            total_impuestos = 0.0

            tax_total_node = line_node.find("./cac:TaxTotal", self.namespaces)
            if tax_total_node is not None:
                total_impuestos = safe_float(get_text(tax_total_node, "./cbc:TaxAmount", self.namespaces))

            # ============================================================
            # TOTAL DEL ITEM
            # ============================================================
            total = subtotal + total_impuestos - descuento_valor

            # ============================================================
            # NORMALIZACIÓN (para matching)
            # ============================================================
            from src.services.item_normalizer_service import ItemNormalizerService
            normalizer = ItemNormalizerService()
            normalized_data = normalizer.normalizar_item_completo(descripcion)

            # SCHEMA v2.0.0 (2025-12-02): Eliminadas codigo_estandar, descuento_porcentaje
            return {
                # Identificación
                "numero_linea": numero_linea,
                "descripcion": descripcion,

                # Códigos
                "codigo_producto": codigo_producto,

                # Cantidades
                "cantidad": cantidad,
                "unidad_medida": unidad_medida or "unidad",

                # Precios
                "precio_unitario": precio_unitario,
                "subtotal": subtotal,
                "total_impuestos": total_impuestos,
                "total": total,

                # Descuentos
                "descuento_valor": descuento_valor if descuento_valor > 0 else None,

                # Normalización
                "descripcion_normalizada": normalized_data['descripcion_normalizada'],
                "item_hash": normalized_data['item_hash'],
                "categoria": normalized_data['categoria'],
                "es_recurrente": normalized_data['es_recurrente']
            }

        except Exception as exc:
            logger.warning(f"Error extracting single item completo: {exc}")
            return None