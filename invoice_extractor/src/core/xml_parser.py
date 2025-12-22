"""
Parser especializado para XML de facturas electrónicas UBL 2.1.
Maneja Invoices, CreditNotes, DebitNotes y formatos custom.
Soporta tanto documentos directos como embebidos en AttachedDocument (CDATA).
"""
from pathlib import Path
from typing import Optional
from lxml import etree

from src.utils.logger import logger
from src.core.xml_utils import safe_parse_xml, get_text, UBL_NAMESPACES


class XMLParser:
    """
    Parser robusto para documentos de facturación electrónica.

    Reconoce y parsea:
    - Invoices (UBL 2.1)
    - Credit Notes (UBL 2.1)
    - Debit Notes (UBL 2.1)
    - Formatos custom con campos monetarios

    Soporta dos formatos:
    1. AttachedDocument con documento embebido en CDATA (80% de los casos)
    2. Documento directo como raíz XML (20% de los casos)
    """

    # Tipos de documento soportados
    DOCUMENT_TYPES = ['Invoice', 'CreditNote', 'DebitNote']

    def __init__(self):
        self.namespaces = UBL_NAMESPACES

    def parse_from_path(self, xml_path: Path) -> Optional[etree._Element]:
        """
        Parsea XML desde archivo.

        Args:
            xml_path: Ruta al archivo XML

        Returns:
            Elemento raíz del documento o None si no se puede parsear
        """
        try:
            root = safe_parse_xml(str(xml_path))
            return self._extract_document_element(root)
        except Exception as exc:
            logger.error(f"Error parsing XML from {xml_path}: {exc}")
            return None

    def parse_from_bytes(self, xml_bytes: bytes) -> Optional[etree._Element]:
        """
        Parsea XML desde bytes.

        Args:
            xml_bytes: Contenido XML en bytes

        Returns:
            Elemento raíz del documento o None si no se puede parsear
        """
        try:
            root = safe_parse_xml(xml_bytes)
            return self._extract_document_element(root)
        except Exception as exc:
            logger.error(f"Error parsing XML from bytes: {exc}")
            return None

    def _extract_document_element(self, root: etree._Element) -> Optional[etree._Element]:
        """
        Extrae el elemento de documento, manejando ambos formatos (directo y embebido).

        Casos:
        1. AttachedDocument con CDATA embebido → parsear CDATA
        2. Documento directo (Invoice, CreditNote, etc.) → retornar raíz

        Args:
            root: Elemento raíz del XML parseado

        Returns:
            Elemento del documento o None si no se encuentra
        """
        # Caso 1: AttachedDocument con documento embebido en CDATA
        if 'AttachedDocument' in root.tag:
            doc_element = self._extract_from_attached_document(root)
            if doc_element is not None:
                return doc_element

        # Caso 2: Documento directo
        if self._is_valid_document_root(root):
            return root

        logger.warning(f"No se pudo extraer documento válido de: {root.tag}")
        return None

    def _extract_from_attached_document(self, root: etree._Element) -> Optional[etree._Element]:
        """
        Extrae documento embebido en CDATA dentro de AttachedDocument.

        Ubicación estándar: cac:Attachment/cac:ExternalReference/cbc:Description
        """
        try:
            cdata = get_text(
                root,
                ".//cac:Attachment/cac:ExternalReference/cbc:Description",
                self.namespaces
            )

            if not cdata:
                return None

            # Parsear CDATA como XML
            doc_element = etree.fromstring(cdata.encode("utf-8"))

            if self._is_valid_document_root(doc_element):
                logger.debug(f"Documento extraído de CDATA: {doc_element.tag}")
                return doc_element

        except etree.XMLSyntaxError as exc:
            logger.warning(f"Error al parsear CDATA como XML: {exc}")
        except Exception as exc:
            logger.warning(f"Error extrayendo documento de CDATA: {exc}")

        return None

    def _is_valid_document_root(self, element: etree._Element) -> bool:
        """
        Valida que el elemento sea un documento de facturación reconocido.

        Debe:
        1. Ser uno de los tipos soportados (Invoice, CreditNote, DebitNote)
        2. Tener campos monetarios (LegalMonetaryTotal o CustomFields)
        """
        if element is None:
            return False

        # Verificar tipo de documento
        is_known_type = any(dtype in element.tag for dtype in self.DOCUMENT_TYPES)

        if not is_known_type:
            return False

        # Verificar que tenga datos monetarios
        has_legal_monetary = bool(element.xpath('.//cac:LegalMonetaryTotal', namespaces=self.namespaces))
        has_custom_fields = bool(element.xpath(
            './/ext:ExtensionContent//CustomFieldExtension[@Name="ValorTotalDocumento"]',
            namespaces=self.namespaces
        ))

        return has_legal_monetary or has_custom_fields

    def get_document_metadata(self, doc_element: etree._Element) -> dict:
        """
        Extrae metadatos básicos del documento.

        Args:
            doc_element: Elemento del documento

        Returns:
            Dict con ID, UUID, fecha de emisión y tipo
        """
        return {
            "id": get_text(doc_element, "./cbc:ID", self.namespaces),
            "uuid": get_text(doc_element, "./cbc:UUID", self.namespaces),
            "issue_date": get_text(doc_element, "./cbc:IssueDate", self.namespaces),
            "document_type": doc_element.tag.split('}')[-1] if '}' in doc_element.tag else doc_element.tag
        }