"""
Extractores de información adicional: orden de compra y notas.
"""
from typing import Optional, Dict, Any
from lxml import etree
import re

from src.utils.logger import logger
from src.core.xml_utils import get_text, get_nodes, UBL_NAMESPACES


class OrdenCompraExtractor:
    """Extrae información de orden de compra"""
    
    def __init__(self):
        self.namespaces = UBL_NAMESPACES
    
    def extract(self, root: etree._Element) -> Optional[Dict[str, Any]]:
        """
        Extrae información de orden de compra.
        
        Args:
            root: Elemento raíz de la factura
            
        Returns:
            Diccionario con datos de OC o None
        """
        try:
            orden_compra = {}
            
            # Buscar en OrderReference
            orden_ref_node = root.find(".//cac:OrderReference", self.namespaces)
            if orden_ref_node is not None:
                orden_compra["numero_oc"] = get_text(orden_ref_node, "./cbc:ID", self.namespaces)
                orden_compra["numero_sap"] = get_text(orden_ref_node, "./cbc:SalesOrderID", self.namespaces)
                orden_compra["fecha_oc"] = get_text(orden_ref_node, "./cbc:IssueDate", self.namespaces)
            
            # Si no se encontró, buscar en notas
            if not orden_compra.get("numero_oc"):
                self._extract_from_notes(root, orden_compra)
            
            return orden_compra if any(orden_compra.values()) else None
            
        except Exception as exc:
            logger.warning(f"Error extracting purchase order: {exc}")
            return None
    
    def _extract_from_notes(self, root: etree._Element, orden_compra: Dict[str, Any]) -> None:
        """Busca información de OC en las notas"""
        note_nodes = get_nodes(root, "./cbc:Note", self.namespaces)
        
        for note_node in note_nodes:
            if not note_node.text:
                continue
            
            nota = note_node.text.strip()
            
            # Buscar patrón de orden de compra
            oc_match = re.search(r"OC\s*(\d+)", nota, re.IGNORECASE)
            if oc_match:
                orden_compra["numero_oc"] = oc_match.group(1)
            
            # Buscar SAP
            if "pedidosap:" in nota:
                sap_number = nota.split("pedidosap:")[1].strip()
                orden_compra["numero_sap"] = sap_number


class NotasAdicionalesExtractor:
    """Extrae y categoriza notas adicionales"""
    
    def __init__(self):
        self.namespaces = UBL_NAMESPACES
    
    def extract(self, root: etree._Element) -> Optional[Dict[str, Any]]:
        """
        Extrae y categoriza las notas adicionales.
        
        Args:
            root: Elemento raíz de la factura
            
        Returns:
            Diccionario con notas categorizadas o None
        """
        try:
            notas = {}
            note_nodes = get_nodes(root, "./cbc:Note", self.namespaces)
            
            for note_node in note_nodes:
                if not note_node.text:
                    continue
                
                nota = note_node.text.strip()
                self._categorize_note(nota, notas)
            
            return notas if notas else None
            
        except Exception as exc:
            logger.warning(f"Error extracting additional notes: {exc}")
            return None
    
    def _categorize_note(self, nota: str, notas: Dict[str, Any]) -> None:
        """
        Categoriza una nota según su contenido.
        
        Args:
            nota: Texto de la nota
            notas: Diccionario donde almacenar la nota categorizada
        """
        # Centro de costos
        if "CENTROCOSTOS:" in nota:
            notas["centro_costos"] = nota.split("CENTROCOSTOS:")[1].strip()
        
        # Usuario facturador
        elif "Usuario facturador:" in nota:
            notas["usuario_facturador"] = nota.split("Usuario facturador:")[1].strip()
        
        # Pedido SAP
        elif "pedidosap:" in nota:
            notas["pedido_sap"] = nota.split("pedidosap:")[1].strip()
        
        # Observaciones
        elif "notas:" in nota:
            notas["observaciones"] = nota.split("notas:")[1].strip()
        
        # Medio de pago
        elif "mediodepago:" in nota:
            notas["medio_pago"] = nota.split("mediodepago:")[1].strip()
        
        # Resolución de facturación
        elif "Resolucionfac:" in nota:
            notas["resolucion_facturacion"] = nota.split("Resolucionfac:")[1].strip()
        
        # Estatuto tributario
        elif "Estatuto:" in nota:
            notas["estatuto_tributario"] = nota.split("Estatuto:")[1].strip()
        
        # Valor en letras
        elif "letras:" in nota:
            notas["valor_letras"] = nota.split("letras:")[1].strip()