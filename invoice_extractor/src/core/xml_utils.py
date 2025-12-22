"""
Utilidades para manejo de XML y parseo de facturas electrónicas UBL 2.1.
"""
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict, Any
from pathlib import Path
from lxml import etree

from src.utils.logger import logger


# Namespaces UBL 2.1 estándar
UBL_NAMESPACES = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'sts': 'dian:gov:co:facturaelectronica:Structures-2-1',
    'ds': 'http://www.w3.org/2000/09/xmldsig#'
}


def get_text(element: etree._Element, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> str:
    """
    Extrae texto de un elemento usando XPath de manera segura.
    
    Args:
        element: Elemento XML base
        xpath: Expresión XPath
        namespaces: Namespaces a usar (por defecto UBL_NAMESPACES)
        
    Returns:
        Texto del elemento o cadena vacía si no existe
    """
    if namespaces is None:
        namespaces = UBL_NAMESPACES
    
    try:
        nodes = element.xpath(xpath, namespaces=namespaces)
        if nodes and hasattr(nodes[0], 'text') and nodes[0].text:
            return nodes[0].text.strip()
    except Exception as e:
        logger.warning(f"Error extrayendo texto con XPath '{xpath}': {e}")
    
    return ""


def get_nodes(element: etree._Element, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> List[etree._Element]:
    """
    Obtiene lista de nodos usando XPath de manera segura.
    
    Args:
        element: Elemento XML base
        xpath: Expresión XPath
        namespaces: Namespaces a usar (por defecto UBL_NAMESPACES)
        
    Returns:
        Lista de elementos encontrados
    """
    if namespaces is None:
        namespaces = UBL_NAMESPACES
    
    try:
        nodes = element.xpath(xpath, namespaces=namespaces)
        return [node for node in nodes if isinstance(node, etree._Element)]
    except Exception as e:
        logger.warning(f"Error obteniendo nodos con XPath '{xpath}': {e}")
        return []


def get_attribute(element: etree._Element, attr_name: str) -> str:
    """
    Obtiene un atributo de un elemento de manera segura.
    
    Args:
        element: Elemento XML
        attr_name: Nombre del atributo
        
    Returns:
        Valor del atributo o cadena vacía
    """
    try:
        return element.get(attr_name, "").strip()
    except Exception as e:
        logger.warning(f"Error obteniendo atributo '{attr_name}': {e}")
        return ""


def safe_decimal(value: Any, default: Decimal = Decimal("0.00")) -> Decimal:
    """
    Convierte un valor a Decimal de manera segura.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si falla la conversión
        
    Returns:
        Decimal del valor o valor por defecto
    """
    if value is None:
        return default
    
    try:
        if isinstance(value, Decimal):
            return value
        
        # Limpiar el texto de caracteres no numéricos comunes
        if isinstance(value, str):
            # Remover espacios y caracteres especiales comunes
            cleaned = value.strip().replace(",", "").replace("$", "").replace(" ", "")
            
            # Si está vacío después de limpiar
            if not cleaned:
                return default
            
            return Decimal(cleaned)
        
        return Decimal(str(value))
        
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.warning(f"Error convirtiendo '{value}' a Decimal: {e}")
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Convierte un valor a float de manera segura.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si falla la conversión
        
    Returns:
        Float del valor o valor por defecto
    """
    try:
        decimal_value = safe_decimal(value)
        return float(decimal_value)
    except Exception as e:
        logger.warning(f"Error convirtiendo '{value}' a float: {e}")
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Convierte un valor a int de manera segura.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si falla la conversión
        
    Returns:
        Int del valor o valor por defecto
    """
    try:
        if isinstance(value, int):
            return value
        
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return default
            
            # Remover decimales si los hay
            if "." in cleaned:
                cleaned = cleaned.split(".")[0]
            
            return int(cleaned)
        
        return int(float(value))
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Error convirtiendo '{value}' a int: {e}")
        return default


def extract_cdata_content(element: etree._Element) -> str:
    """
    Extrae contenido CDATA de un elemento XML.
    
    Args:
        element: Elemento XML que puede contener CDATA
        
    Returns:
        Contenido CDATA o texto normal del elemento
    """
    try:
        # Obtener todo el contenido, incluyendo CDATA
        content = ""
        
        if element.text:
            content += element.text
        
        # Procesar nodos hijos para encontrar CDATA
        for child in element:
            if child.text:
                content += child.text
            if child.tail:
                content += child.tail
        
        return content.strip()
        
    except Exception as e:
        logger.warning(f"Error extrayendo CDATA: {e}")
        return element.text.strip() if element.text else ""


def find_element_by_text_content(element: etree._Element, target_text: str, tag_name: Optional[str] = None) -> Optional[etree._Element]:
    """
    Busca un elemento por su contenido de texto.
    
    Args:
        element: Elemento base para la búsqueda
        target_text: Texto a buscar
        tag_name: Nombre del tag a filtrar (opcional)
        
    Returns:
        Primer elemento que contenga el texto o None
    """
    try:
        for elem in element.iter():
            if tag_name and elem.tag != tag_name:
                continue
            
            if elem.text and target_text.lower() in elem.text.lower():
                return elem
        
        return None
        
    except Exception as e:
        logger.warning(f"Error buscando elemento por texto '{target_text}': {e}")
        return None


def get_all_text_content(element: etree._Element) -> str:
    """
    Obtiene todo el contenido de texto de un elemento y sus hijos.
    
    Args:
        element: Elemento XML
        
    Returns:
        Todo el texto concatenado
    """
    try:
        return " ".join(element.itertext()).strip()
    except Exception as e:
        logger.warning(f"Error obteniendo todo el texto: {e}")
        return ""


def validate_required_elements(element: etree._Element, required_xpaths: List[str], namespaces: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
    """
    Valida que elementos requeridos estén presentes.
    
    Args:
        element: Elemento XML base
        required_xpaths: Lista de XPaths requeridos
        namespaces: Namespaces a usar
        
    Returns:
        Diccionario con estado de validación por XPath
    """
    if namespaces is None:
        namespaces = UBL_NAMESPACES
    
    validation_results = {}
    
    for xpath in required_xpaths:
        try:
            nodes = element.xpath(xpath, namespaces=namespaces)
            validation_results[xpath] = len(nodes) > 0
        except Exception as e:
            logger.warning(f"Error validando XPath '{xpath}': {e}")
            validation_results[xpath] = False
    
    return validation_results


def clean_xml_text(text: str) -> str:
    """
    Limpia texto extraído de XML removiendo caracteres problemáticos.
    
    Args:
        text: Texto a limpiar
        
    Returns:
        Texto limpio
    """
    if not text:
        return ""
    
    # Remover caracteres de control y normalizar espacios
    cleaned = " ".join(text.split())
    
    # Remover caracteres especiales problemáticos
    cleaned = cleaned.replace("\r", "").replace("\n", " ").replace("\t", " ")
    
    return cleaned.strip()


def safe_parse_xml(xml_source) -> Optional[etree._Element]:
    """
    Parsea XML de manera segura desde archivo o bytes.
    
    Args:
        xml_source: Ruta de archivo (str/Path) o contenido XML (bytes/str)
        
    Returns:
        Elemento raíz del XML o None si hay error
    """
    try:
        parser = etree.XMLParser(recover=True, strip_cdata=False)
        
        if isinstance(xml_source, (str, Path)):
            # Parsear desde archivo
            tree = etree.parse(str(xml_source), parser)
            return tree.getroot()
        else:
            # Parsear desde bytes o string
            if isinstance(xml_source, str):
                xml_source = xml_source.encode('utf-8')
            return etree.fromstring(xml_source, parser)
            
    except Exception as e:
        logger.error(f"Error parseando XML: {e}")
        return None


def get_element_tree_info(element: etree._Element) -> Dict[str, Any]:
    """
    Obtiene información de diagnóstico de un elemento XML.
    Útil para debugging.
    
    Args:
        element: Elemento XML
        
    Returns:
        Diccionario con información del elemento
    """
    info = {
        "tag": element.tag,
        "text": element.text,
        "attributes": dict(element.attrib),
        "children_count": len(element),
        "children_tags": [child.tag for child in element]
    }
    
    return info
