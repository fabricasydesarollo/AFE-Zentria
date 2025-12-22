from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from decimal import Decimal

class ItemResumen(BaseModel):
    """Modelo para items resumidos de la factura"""
    linea_id: str
    descripcion: str
    cantidad: float
    valor_linea: float
    precio_unitario: float
    codigo_producto: Optional[str] = None
    propiedades_adicionales: Optional[Dict[str, str]] = None

class OrdenCompra(BaseModel):
    """Modelo para información de orden de compra"""
    numero_oc: Optional[str] = None
    numero_sap: Optional[str] = None
    fecha_oc: Optional[str] = None

class NotasAdicionales(BaseModel):
    """Modelo para notas adicionales extraídas"""
    centro_costos: Optional[str] = None
    usuario_facturador: Optional[str] = None
    pedido_sap: Optional[str] = None
    observaciones: Optional[str] = None
    medio_pago: Optional[str] = None
    resolucion_facturacion: Optional[str] = None
    estatuto_tributario: Optional[str] = None
    valor_letras: Optional[str] = None

class ProcesamientoInfo(BaseModel):
    """Modelo para información técnica del procesamiento"""
    fecha_procesamiento: Optional[str] = None
    version_algoritmo: Optional[str] = None
    tiempo_procesamiento_ms: Optional[int] = None
    errores_encontrados: Optional[List[str]] = None

class Factura(BaseModel):
    """
    Modelo de datos para facturas electrónicas DIAN.

    Incluye validación automática de coherencia matemática para prevenir
    errores de constraint en base de datos.
    """
    # Campos básicos existentes
    numero_factura: str
    cufe: str
    fecha_emision: str
    fecha_vencimiento: str
    nit_proveedor: Optional[str] = None  # Algunos XMLs pueden no tener NIT
    razon_social_proveedor: str
    nit_cliente: Optional[str] = None  # Algunos XMLs pueden no tener NIT
    razon_social_cliente: str
    subtotal: float
    iva: float
    retenciones: float = 0.0  # Retenciones aplicadas (extraídas o inferidas)
    total_a_pagar: float

    @field_validator('total_a_pagar')
    @classmethod
    def validate_total_coherencia(cls, v, info):
        """
        Validación CRÍTICA: Verifica coherencia matemática antes de llegar a la DB.

        Esta validación previene el error:
        "Check constraint 'chk_facturas_total_coherente' is violated"

        Acepta DOS casos válidos según estructura DIAN:

        CASO 1 (Normal): total_a_pagar = subtotal + iva - retenciones
          - XML tiene PayableAmount DESPUÉS de restar retenciones

        CASO 2 (RETENCIONES_DECLARADAS_SIN_CAMPO_TOTAL_NETO): total_a_pagar = subtotal + iva
          - XML tiene retenciones en WithholdingTaxTotal
          - PERO PayableAmount NO las resta (es el total BRUTO)
          - Esto es válido según DIAN para ciertos tipos de factura

        Raises:
            ValueError: Si NINGUNA de las dos fórmulas se cumple
        """
        if info.data:
            subtotal = info.data.get('subtotal', 0.0)
            iva = info.data.get('iva', 0.0)
            retenciones = info.data.get('retenciones', 0.0)

            # Tolerancia de 1 peso para redondeos
            TOLERANCIA = 1.0

            # CASO 1: Fórmula estándar (retenciones restadas)
            total_caso1 = subtotal + iva - retenciones
            diferencia_caso1 = abs(v - total_caso1)
            cumple_caso1 = diferencia_caso1 <= TOLERANCIA

            # CASO 2: Fórmula sin restar retenciones (PayableAmount bruto)
            # Solo aplica si hay retenciones declaradas
            total_caso2 = subtotal + iva
            diferencia_caso2 = abs(v - total_caso2)
            cumple_caso2 = diferencia_caso2 <= TOLERANCIA and retenciones > 0

            # Debe cumplir al menos UNO de los dos casos
            if not (cumple_caso1 or cumple_caso2):
                raise ValueError(
                    f"Coherencia matemática violada en factura. "
                    f"Total a pagar ({v:,.2f}) no coincide con NINGUNA fórmula válida:\n"
                    f"  CASO 1 (retenciones restadas): subtotal + iva - retenciones = {total_caso1:,.2f} "
                    f"(diferencia: {diferencia_caso1:,.2f})\n"
                    f"  CASO 2 (retenciones NO restadas): subtotal + iva = {total_caso2:,.2f} "
                    f"(diferencia: {diferencia_caso2:,.2f})\n"
                    f"Valores: subtotal={subtotal:,.2f}, iva={iva:,.2f}, "
                    f"retenciones={retenciones:,.2f}\n"
                    f"Tolerancia: ±{TOLERANCIA} peso"
                )

        return v

