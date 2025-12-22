# src/validation/intelligent_reconciler.py

"""
Reconciliador Inteligente para detectar discrepancias entre XML y valores esperados.
NO CALCULA valores, solo COMPARA y ANALIZA.
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from enum import Enum

class DiscrepancyType(Enum):
    """Tipos de discrepancias detectables"""
    MATCH = "MATCH"
    RETENCION_NO_DECLARADA = "RETENCION_NO_DECLARADA_XML"
    RETENCION_MAYOR_ESPERADA = "RETENCION_MAYOR_A_LA_ESPERADA"
    ANTICIPO_APLICADO = "ANTICIPO_APLICADO"
    DESCUENTO_NO_DECLARADO = "DESCUENTO_NO_DECLARADO"
    RETENCIONES_SIN_CAMPO_NETO = "RETENCIONES_DECLARADAS_SIN_CAMPO_TOTAL_NETO"
    ERROR_CRITICO = "ERROR_CRITICO_DISCREPANCIA_INEXPLICABLE"

class AlertLevel(Enum):
    """Niveles de alerta"""
    NONE = "NONE"
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ReconciliationReport:
    """Reporte de reconciliación entre valores extraídos"""

    def __init__(
        self,
        status: DiscrepancyType,
        alert_level: AlertLevel,
        requires_review: bool,
        mensaje: str,
        discrepancia: Decimal,
        analisis: Dict[str, Any]
    ):
        self.status = status
        self.alert_level = alert_level
        self.requires_review = requires_review
        self.mensaje = mensaje
        self.discrepancia = discrepancia
        self.analisis = analisis

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "nivel_alerta": self.alert_level.value,
            "requiere_revision_manual": self.requires_review,
            "mensaje": self.mensaje,
            "discrepancia": float(self.discrepancia),
            "analisis": self.analisis
        }

class IntelligentReconciler:
    """
    Reconciliador inteligente que compara valores extraídos del XML
    con valores externos (PDF, bases de datos, etc.) para detectar discrepancias.

    IMPORTANTE: Esta clase NO CALCULA valores, solo los COMPARA y ANALIZA.
    """

    # Tolerancia para diferencias por redondeo (1 peso)
    TOLERANCIA_CENTAVOS = Decimal("1.00")

    def __init__(self):
        pass

    def reconcile_xml_only(
        self,
        tax_inclusive_amount: Decimal,
        payable_amount: Decimal,
        retenciones_declaradas: Decimal,
        tiene_campo_total_neto: bool = False
    ) -> ReconciliationReport:
        """
        Reconcilia los valores internos del XML para detectar inconsistencias.

        Formula esperada:
        PayableAmount = TaxInclusiveAmount - Retenciones - Anticipos

        Args:
            tax_inclusive_amount: Total con IVA incluido
            payable_amount: Total a pagar neto
            retenciones_declaradas: Suma de retenciones declaradas en XML
            tiene_campo_total_neto: Si el XML tiene un campo explícito con el total neto después de retenciones

        Returns:
            ReconciliationReport con el análisis
        """
        # CASO ESPECIAL: Retenciones declaradas pero SIN campo de total neto explícito
        # En UBL 2.1 DIAN estándar, PayableAmount NO resta automáticamente WithholdingTaxTotal
        if retenciones_declaradas > 0 and not tiene_campo_total_neto:
            # PayableAmount = TaxInclusiveAmount (no resta retenciones)
            if abs(payable_amount - tax_inclusive_amount) <= self.TOLERANCIA_CENTAVOS:
                return ReconciliationReport(
                    status=DiscrepancyType.RETENCIONES_SIN_CAMPO_NETO,
                    alert_level=AlertLevel.HIGH,
                    requires_review=True,
                    mensaje=f"REQUIERE REVISIÓN MANUAL: XML tiene retenciones declaradas ({retenciones_declaradas}) pero NO tiene campo explícito con total neto. PayableAmount={payable_amount} (bruto). Total real a pagar debe obtenerse de PDF u otra fuente.",
                    discrepancia=retenciones_declaradas,
                    analisis={
                        "tax_inclusive_amount": float(tax_inclusive_amount),
                        "payable_amount": float(payable_amount),
                        "retenciones_declaradas": float(retenciones_declaradas),
                        "total_bruto_xml": float(payable_amount),
                        "total_neto_esperado": float(payable_amount - retenciones_declaradas),
                        "consistencia": "XML_INCOMPLETO",
                        "razon": "Proveedor no incluyó campo custom ValorTotalDocumento con el total neto",
                        "accion_requerida": "Verificar total neto en PDF o solicitar al proveedor que incluya campo custom"
                    }
                )

        # La diferencia DEBE ser las retenciones (si todo está correcto)
        diferencia_esperada = tax_inclusive_amount - payable_amount
        diferencia_real = retenciones_declaradas

        discrepancia = diferencia_esperada - diferencia_real

        if abs(discrepancia) <= self.TOLERANCIA_CENTAVOS:
            return ReconciliationReport(
                status=DiscrepancyType.MATCH,
                alert_level=AlertLevel.NONE,
                requires_review=False,
                mensaje=f"Los valores del XML son consistentes: TaxInclusive={tax_inclusive_amount}, Payable={payable_amount}, Retenciones={retenciones_declaradas}",
                discrepancia=Decimal("0.0"),
                analisis={
                    "tax_inclusive_amount": float(tax_inclusive_amount),
                    "payable_amount": float(payable_amount),
                    "retenciones_declaradas": float(retenciones_declaradas),
                    "consistencia": "CORRECTA"
                }
            )
        else:
            return ReconciliationReport(
                status=DiscrepancyType.ERROR_CRITICO,
                alert_level=AlertLevel.CRITICAL,
                requires_review=True,
                mensaje=f"INCONSISTENCIA EN XML: La diferencia entre TaxInclusive y Payable ({diferencia_esperada}) no coincide con las retenciones declaradas ({diferencia_real})",
                discrepancia=discrepancia,
                analisis={
                    "tax_inclusive_amount": float(tax_inclusive_amount),
                    "payable_amount": float(payable_amount),
                    "retenciones_declaradas": float(retenciones_declaradas),
                    "diferencia_esperada": float(diferencia_esperada),
                    "consistencia": "INCORRECTA"
                }
            )

    def reconcile_xml_vs_external(
        self,
        total_xml: Decimal,
        total_externo: Decimal,
        retenciones_externas: Optional[Decimal] = None,
        fuente_externa: str = "PDF"
    ) -> ReconciliationReport:
        """
        Compara el total extraído del XML con un valor externo (PDF, base de datos, etc.)

        Args:
            total_xml: Total extraído del XML oficial
            total_externo: Total obtenido de fuente externa
            retenciones_externas: Retenciones detectadas en la fuente externa
            fuente_externa: Nombre de la fuente (PDF, DB, etc.)

        Returns:
            ReconciliationReport con el análisis
        """
        discrepancia = total_xml - total_externo

        # Caso 1: Match perfecto
        if abs(discrepancia) <= self.TOLERANCIA_CENTAVOS:
            return ReconciliationReport(
                status=DiscrepancyType.MATCH,
                alert_level=AlertLevel.INFO,
                requires_review=False,
                mensaje=f"✓ Valores coinciden: XML=${total_xml:,.2f} = {fuente_externa}=${total_externo:,.2f}",
                discrepancia=Decimal("0.0"),
                analisis={
                    "total_xml": float(total_xml),
                    f"total_{fuente_externa.lower()}": float(total_externo),
                    "match": "PERFECTO"
                }
            )

        # Caso 2: Discrepancia explicable por retenciones
        if retenciones_externas and abs(discrepancia - retenciones_externas) <= self.TOLERANCIA_CENTAVOS:
            return ReconciliationReport(
                status=DiscrepancyType.RETENCION_NO_DECLARADA,
                alert_level=AlertLevel.HIGH,
                requires_review=True,
                mensaje=f"⚠ RETENCIONES NO DECLARADAS EN XML: {fuente_externa} muestra retenciones de ${retenciones_externas:,.2f} que NO están en el XML oficial. XML=${total_xml:,.2f}, {fuente_externa}=${total_externo:,.2f}",
                discrepancia=discrepancia,
                analisis={
                    "total_xml": float(total_xml),
                    f"total_{fuente_externa.lower()}": float(total_externo),
                    "retenciones_externas": float(retenciones_externas),
                    "explicacion": "La diferencia corresponde a retenciones aplicadas fuera del XML",
                    "accion_requerida": "Validar con proveedor si retenciones deben estar en XML o son aplicadas externamente",
                    "valor_contabilidad": float(total_xml),
                    "valor_tesoreria": float(total_externo)
                }
            )

        # Caso 3: XML es menor que externo (posible descuento/anticipo no declarado)
        if discrepancia < 0:
            return ReconciliationReport(
                status=DiscrepancyType.DESCUENTO_NO_DECLARADO,
                alert_level=AlertLevel.WARNING,
                requires_review=True,
                mensaje=f"⚠ XML muestra valor MENOR: XML=${total_xml:,.2f} < {fuente_externa}=${total_externo:,.2f}. Diferencia: ${abs(discrepancia):,.2f}",
                discrepancia=discrepancia,
                analisis={
                    "total_xml": float(total_xml),
                    f"total_{fuente_externa.lower()}": float(total_externo),
                    "tipo_anomalia": "XML_MENOR_QUE_EXTERNO",
                    "posibles_causas": ["Descuento no declarado", "Anticipo aplicado", "Error en fuente externa"]
                }
            )

        # Caso 4: Discrepancia inexplicable
        return ReconciliationReport(
            status=DiscrepancyType.ERROR_CRITICO,
            alert_level=AlertLevel.CRITICAL,
            requires_review=True,
            mensaje=f"🚨 DISCREPANCIA CRÍTICA INEXPLICABLE: XML=${total_xml:,.2f} vs {fuente_externa}=${total_externo:,.2f}. Diferencia: ${abs(discrepancia):,.2f}",
            discrepancia=discrepancia,
            analisis={
                "total_xml": float(total_xml),
                f"total_{fuente_externa.lower()}": float(total_externo),
                "tipo_anomalia": "DISCREPANCIA_INEXPLICABLE",
                "accion_urgente": "BLOQUEAR procesamiento y revisar manualmente",
                "posibles_causas": ["Error en XML", "Error en fuente externa", "Manipulación", "Factura incorrecta"]
            }
        )

    def generate_dual_source_report(
        self,
        xml_values: Dict[str, Decimal],
        external_values: Optional[Dict[str, Decimal]] = None
    ) -> Dict[str, Any]:
        """
        Genera un reporte completo con valores de ambas fuentes y análisis.

        Args:
            xml_values: Diccionario con valores extraídos del XML
            external_values: Diccionario con valores de fuente externa (opcional)

        Returns:
            Diccionario con estructura de doble fuente
        """
        report: Dict[str, Any] = {
            "fuente_primaria_xml": {
                "subtotal": float(xml_values.get('subtotal', 0)),
                "iva": float(xml_values.get('iva', 0)),
                "retenciones_declaradas": float(xml_values.get('retenciones', 0)),
                "total_bruto": float(xml_values.get('tax_inclusive_amount', 0)),
                "total_neto_oficial": float(xml_values.get('payable_amount', 0)),
                "fuente": "XML_DIAN",
                "confiabilidad": "100%"
            }
        }

        if external_values:
            report["fuente_secundaria_externa"] = {
                "total_visual": float(external_values.get('total', 0)),
                "retenciones_externas": float(external_values.get('retenciones', 0)),
                "fuente": external_values.get('fuente', 'DESCONOCIDA'),
                "confiabilidad": "REQUIERE_VALIDACION"
            }

            # Realizar reconciliación
            reconciliation = self.reconcile_xml_vs_external(
                total_xml=xml_values.get('tax_inclusive_amount', Decimal("0")),
                total_externo=external_values.get('total', Decimal("0")),
                retenciones_externas=external_values.get('retenciones'),
                fuente_externa=external_values.get('fuente', 'EXTERNA')
            )

            report["reconciliacion"] = reconciliation.to_dict()

            # Decisión del sistema
            if reconciliation.status == DiscrepancyType.MATCH:
                valor_decidido = float(xml_values.get('tax_inclusive_amount', 0))
                razon = "Valores coinciden, usar XML oficial"
            else:
                valor_decidido = float(xml_values.get('tax_inclusive_amount', 0))
                razon = "XML es fuente oficial tributaria (independiente de discrepancias)"

            report["decision_sistema"] = {
                "total_registrado_contable": valor_decidido,
                "razon": razon,
                "nota": "El XML SIEMPRE es la fuente oficial para propósitos tributarios"
            }

        return report
