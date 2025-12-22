"""
Extractor de campos básicos de facturas electrónicas.
"""
from typing import Optional, Dict, Any
from lxml import etree

from src.core.xml_utils import get_text, UBL_NAMESPACES
from src.utils.nit_utils import completar_nit_con_dv


class BasicFieldExtractor:
    """Extrae campos básicos de identificación y partes de la factura"""
    
    def __init__(self):
        self.namespaces = UBL_NAMESPACES
    
    def extract_all(self, root: etree._Element) -> Dict[str, Any]:
        """
        Extrae todos los campos básicos de la factura.
        
        Args:
            root: Elemento raíz de la factura
            
        Returns:
            Diccionario con campos básicos
        """
        return {
            "numero_factura": self.extract_invoice_number(root),
            "cufe": self.extract_cufe(root),
            "fecha_emision": self.extract_issue_date(root),
            "fecha_vencimiento": self.extract_due_date(root),
            "nit_proveedor": self.extract_supplier_nit(root),
            "razon_social_proveedor": self.extract_supplier_name(root),
            "nit_cliente": self.extract_customer_nit(root),
            "razon_social_cliente": self.extract_customer_name(root)
        }
    
    def extract_invoice_number(self, root: etree._Element) -> Optional[str]:
        """Extrae el número de factura"""
        return get_text(root, "./cbc:ID", self.namespaces)
    
    def extract_cufe(self, root: etree._Element) -> Optional[str]:
        """Extrae el CUFE (UUID)"""
        return get_text(root, "./cbc:UUID", self.namespaces)
    
    def extract_issue_date(self, root: etree._Element) -> Optional[str]:
        """Extrae la fecha de emisión"""
        return get_text(root, "./cbc:IssueDate", self.namespaces)
    
    def extract_due_date(self, root: etree._Element) -> Optional[str]:
        """Extrae la fecha de vencimiento (intenta múltiples rutas)"""
        # Ruta 1: DueDate directo
        due_date = get_text(root, "./cbc:DueDate", self.namespaces)
        if due_date:
            return due_date
        
        # Ruta 2: En PaymentTerms
        due_date = get_text(
            root, ".//cac:PaymentTerms/cbc:PaymentDueDate", self.namespaces
        )
        if due_date:
            return due_date
        
        # Ruta 3: En PaymentMeans
        due_date = get_text(
            root, ".//cac:PaymentMeans/cbc:PaymentDueDate", self.namespaces
        )
        return due_date
    
    def extract_supplier_nit(self, root: etree._Element) -> Optional[str]:
        """
        Extrae el NIT del proveedor (con dígito de verificación).

        Soporta múltiples formatos de factura:
        - Factura estándar: AccountingSupplierParty
        - AttachedDocument: SenderParty
        """
        # Intentar ruta estándar (Invoice/CreditNote/DebitNote)
        nit = get_text(
            root,
            ".//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            self.namespaces
        )

        # Si no se encuentra, intentar AttachedDocument format (SenderParty)
        if not nit:
            nit = get_text(
                root,
                ".//cac:SenderParty/cac:PartyTaxScheme/cbc:CompanyID",
                self.namespaces
            )

        return completar_nit_con_dv(nit) if nit else None
    
    def extract_supplier_name(self, root: etree._Element) -> Optional[str]:
        """
        Extrae la razón social del proveedor.

        Soporta múltiples formatos de factura:
        - Factura estándar: AccountingSupplierParty
        - AttachedDocument: SenderParty
        """
        # Ruta 1: PartyLegalEntity (factura estándar)
        name = get_text(
            root,
            ".//cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName",
            self.namespaces
        )
        if name:
            return name

        # Ruta 2: PartyTaxScheme (factura estándar)
        name = get_text(
            root,
            ".//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:RegistrationName",
            self.namespaces
        )
        if name:
            return name

        # Ruta 3: SenderParty/PartyTaxScheme (AttachedDocument)
        return get_text(
            root,
            ".//cac:SenderParty/cac:PartyTaxScheme/cbc:RegistrationName",
            self.namespaces
        )
    
    def extract_customer_nit(self, root: etree._Element) -> Optional[str]:
        """
        Extrae el NIT del cliente (con dígito de verificación).

        Soporta múltiples formatos de factura:
        - Factura estándar: AccountingCustomerParty
        - AttachedDocument: ReceiverParty
        """
        # Intentar ruta estándar (Invoice/CreditNote/DebitNote)
        nit = get_text(
            root,
            ".//cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            self.namespaces
        )

        # Si no se encuentra, intentar AttachedDocument format (ReceiverParty)
        if not nit:
            nit = get_text(
                root,
                ".//cac:ReceiverParty/cac:PartyTaxScheme/cbc:CompanyID",
                self.namespaces
            )

        return completar_nit_con_dv(nit) if nit else None
    
    def extract_customer_name(self, root: etree._Element) -> Optional[str]:
        """
        Extrae la razón social del cliente.

        Soporta múltiples formatos de factura:
        - Factura estándar: AccountingCustomerParty
        - AttachedDocument: ReceiverParty
        """
        # Ruta 1: PartyLegalEntity (factura estándar)
        name = get_text(
            root,
            ".//cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName",
            self.namespaces
        )
        if name:
            return name

        # Ruta 2: PartyTaxScheme (factura estándar)
        name = get_text(
            root,
            ".//cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:RegistrationName",
            self.namespaces
        )
        if name:
            return name

        # Ruta 3: ReceiverParty/PartyTaxScheme (AttachedDocument)
        return get_text(
            root,
            ".//cac:ReceiverParty/cac:PartyTaxScheme/cbc:RegistrationName",
            self.namespaces
        )