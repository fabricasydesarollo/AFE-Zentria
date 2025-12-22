"""
Tipos y estructuras de datos para facturas electrónicas.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class Adjustment:
    """Representa un ajuste monetario (retención, descuento, cargo, etc.)"""
    tipo: str  # 'retencion', 'descuento', 'cargo', etc.
    campo: str  # Nombre del campo de origen
    valor: Decimal
    fuente: str  # 'CDATA', 'XML', 'UBL', 'NOTA'
    
    def get_unique_key(self) -> str:
        """Genera una clave única para evitar duplicación"""
        return f"{self.fuente}:{self.campo}:{self.valor}"


@dataclass
class InvoiceItem:
    """Representa un item de la factura"""
    linea_id: str
    descripcion: str
    cantidad: float
    valor_linea: float
    precio_unitario: float
    codigo_producto: Optional[str] = None
    propiedades_adicionales: Optional[Dict[str, str]] = None


@dataclass
class OrdenCompra:
    """Información de orden de compra"""
    numero_oc: Optional[str] = None
    numero_sap: Optional[str] = None
    fecha_oc: Optional[str] = None


@dataclass
class NotasAdicionales:
    """Notas adicionales categorizadas"""
    centro_costos: Optional[str] = None
    usuario_facturador: Optional[str] = None
    pedido_sap: Optional[str] = None
    observaciones: Optional[str] = None
    medio_pago: Optional[str] = None
    resolucion_facturacion: Optional[str] = None
    estatuto_tributario: Optional[str] = None
    valor_letras: Optional[str] = None


@dataclass
class MonetaryFields:
    """Campos monetarios extraídos de la factura"""
    subtotal: Decimal = Decimal("0.00")
    iva: Decimal = Decimal("0.00")
    total_a_pagar: Decimal = Decimal("0.00")
    payable_amount: Optional[Decimal] = None
    tax_inclusive_amount: Optional[Decimal] = None
    line_extension_amount: Optional[Decimal] = None
    allowance_total_amount: Optional[Decimal] = None
    charge_total_amount: Optional[Decimal] = None
    prepaid_amount: Optional[Decimal] = None
    payable_rounding_amount: Optional[Decimal] = None


@dataclass
class InvoiceData:
    """Datos completos de una factura electrónica"""
    # Campos básicos
    numero_factura: Optional[str] = None
    cufe: Optional[str] = None
    fecha_emision: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    
    # Partes
    nit_proveedor: Optional[str] = None
    razon_social_proveedor: Optional[str] = None
    nit_cliente: Optional[str] = None
    razon_social_cliente: Optional[str] = None
    
    # Valores monetarios
    subtotal: float = 0.0
    iva: float = 0.0
    total_a_pagar: float = 0.0
    
    # Items
    items_resumen: Optional[List[Dict[str, Any]]] = None
    
    # Enriquecimiento
    concepto_principal: Optional[str] = None
    concepto_normalizado: Optional[str] = None
    concepto_hash: Optional[str] = None
    orden_compra: Optional[Dict[str, Any]] = None
    notas_adicionales: Optional[Dict[str, Any]] = None
    tipo_factura: Optional[str] = None
    
    # Procesamiento
    procesamiento_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para compatibilidad"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result