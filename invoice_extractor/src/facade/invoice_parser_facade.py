# src/facade/invoice_parser_facade.py 

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import time
from decimal import Decimal, ROUND_HALF_UP

from src.utils.logger import logger
from src.core.xml_parser import XMLParser
from src.extraction.monetary_extractor import MonetaryForensicExtractor
from src.extraction.basic_extractor import BasicFieldExtractor
from src.extraction.items_extractor import ItemsExtractor
from src.extraction.additional_extractors import OrdenCompraExtractor, NotasAdicionalesExtractor
from src.extraction.total_extractor import TotalDefinitivoExtractor
from src.extraction.retenciones_extractor import RetencionesExtractor
from src.extraction.custom_field_extractor import CustomFieldMonetaryExtractor
from src.enrichment.invoice_enricher import InvoiceEnricher
from src.validation.intelligent_reconciler import IntelligentReconciler
from src.validation.monetary_validator import MonetaryConsistencyValidator

class InvoiceParserFacade:
    """
    Fachada unificada y REESTRUCTURADA para el parseo de facturas.
    Utiliza un extractor de total definitivo para garantizar 100% de precisión.
    """

    def __init__(
        self,
        xml_path: Path,
        # Se pueden inyectar dependencias para testing si es necesario
    ):
        self.xml_path = xml_path
        # tipo genérico para evitar dependencia directa de lxml aquí
        self.invoice_tree: Optional[Any] = None
        self.start_time: float = 0.0

        # --- COMPOSICIÓN DE EXTRACTORES ---
        self.xml_parser = XMLParser()
        self.basic_extractor = BasicFieldExtractor()
        self.monetary_forensic_extractor = MonetaryForensicExtractor()
        self.monetary_extractor = self.monetary_forensic_extractor
        self.items_extractor = ItemsExtractor()
        self.orden_compra_extractor = OrdenCompraExtractor()
        self.notas_extractor = NotasAdicionalesExtractor()
        self.invoice_enricher = InvoiceEnricher()
        # --- EXTRACTORES DE DATOS MONETARIOS ---
        self.custom_field_extractor = CustomFieldMonetaryExtractor()
        self.total_extractor = TotalDefinitivoExtractor()
        self.retenciones_extractor = RetencionesExtractor()
        # --- VALIDADORES ---
        self.monetary_validator = MonetaryConsistencyValidator()
        self.reconciler = IntelligentReconciler()

    def load(self) -> bool:
        """Carga y valida el archivo XML."""
        self.invoice_tree = self.xml_parser.parse_from_path(self.xml_path)
        return self.invoice_tree is not None

    def extract(self) -> Optional[Dict[str, Any]]:
        """
        Orquesta la extracción de todos los datos de la factura.
        """
        if self.invoice_tree is None:
            logger.error(f"El XML no está cargado. Llama a .load() primero en {self.xml_path}")
            return None

        self.start_time = time.time()
        
        try:
            # --- 1. Extracción de datos base ---
            basic_data = self.basic_extractor.extract_all(self.invoice_tree)

            # --- 2. EXTRACCIÓN DE COMPONENTES MONETARIOS (PRIMERO - para inferencia) ---
            componentes_monetarios = self.monetary_forensic_extractor.extract_all_components(
                self.invoice_tree
            )

            # --- 3. EXTRACCIÓN DEL TOTAL OFICIAL (SIN CÁLCULOS) ---
            total_oficial = self.total_extractor.extract(self.invoice_tree)

            # --- 4. EXTRACCIÓN DE RETENCIONES CON INFERENCIA (CRÍTICO) ---
            # Se pasan componentes_monetarios y total_oficial para permitir
            # el cálculo inferencial cuando las retenciones no están explícitas
            retenciones = self.retenciones_extractor.extract(
                self.invoice_tree,
                componentes_monetarios=componentes_monetarios,
                total_oficial=total_oficial
            )

            # --- 5. VALIDACIÓN (NO CÁLCULO) ---
            validation_info = self._reconcile_totals(total_oficial, componentes_monetarios)

            # --- 6. Ensamblaje de datos ---
            items_resumen = self.items_extractor.extract_items_resumen(self.invoice_tree)
            concepto = self.invoice_enricher.generate_concepto_principal(items_resumen)

            # VALORES FINALES: EXTRAÍDOS DIRECTAMENTE DEL XML, JAMÁS CALCULADOS
            subtotal = componentes_monetarios.get('line_extension_amount', Decimal("0.0"))
            iva = componentes_monetarios.get('total_impuestos_calculado', Decimal("0.0"))
            # IMPORTANTE: El total a pagar SIEMPRE es el valor extraído, nunca calculado
            total_final = total_oficial if total_oficial is not None else Decimal("0.0")

            # === CORRECCIÓN CRÍTICA (2025-12-22): RESTAR RETENCIONES ===
            # PROBLEMA ORIGINAL: PayableAmount del XML NO incluye descuento de retenciones
            # SOLUCIÓN: Total a Pagar Real = PayableAmount - Retenciones
            #
            # Contexto Empresarial Colombiano:
            # - PayableAmount en XML = Subtotal + IVA (Total Bruto)
            # - Retenciones (ReteICA, Retefuente, ReteIVA) se RESTAN del pago
            # - Total a Pagar REAL = Total Bruto - Retenciones
            #
            # Ejemplo Real (Factura KION):
            # - Subtotal: $86,420,243.28
            # - IVA: $16,460,998.72
            # - Total Bruto (PayableAmount XML): $102,881,242.00
            # - Retenciones: $4,310,724.05 (Retefuente + ReteICA)
            # - Total a Pagar REAL: $98,570,517.95 ✅

            total_final_corregido = total_final - retenciones

            logger.info(
                f"Total a pagar calculado: PayableAmount={total_final} - Retenciones={retenciones} = {total_final_corregido}"
            )

            # === AUDITORÍA DE PAYABLE (REGISTRAR INFORMACIÓN) ===
            correccion_payable = self.monetary_validator.detect_and_correct_payable_amount(
                subtotal=subtotal,
                iva=iva,
                retenciones=retenciones,
                payable=total_final
            )

            # === NOMENCLATURA ESTÁNDAR (2025-12-27 - ARQUITECTURA PROFESIONAL) ===
            # Con la nueva arquitectura de nomenclatura estandarizada por CUFE:
            # - XMLs se guardan como: {CUFE}.xml
            # - PDFs se guardan como: {CUFE}.pdf
            # - Lookup es O(1) directo, sin búsqueda necesaria
            #
            # IMPORTANTE: Esta implementación asume que attachments.py ya implementó
            # la nomenclatura estándar. Si el PDF se guardó con nomenclatura antigua,
            # el campo pdf_filename será None y invoice_pdf_service usará fallbacks.

            cufe = basic_data.get("cufe")

            if cufe:
                # ✅ NOMENCLATURA ESTÁNDAR: {CUFE}.pdf
                pdf_filename_estandar = f"{cufe.lower()}.pdf"

                # Validar que el PDF existe en disco (verificación de consistencia)
                pdf_path = self.xml_path.parent / pdf_filename_estandar

                if pdf_path.exists():
                    pdf_filename = pdf_filename_estandar
                    logger.debug(
                        "✅ PDF con nomenclatura estándar verificado: %s",
                        pdf_filename_estandar
                    )
                else:
                    # ⚠️ PDF no encontrado con nomenclatura estándar
                    # Posibles causas:
                    # 1. PDF llegó en email diferente (aún no descargado)
                    # 2. PDF tiene nomenclatura antigua (pre-migración)
                    # 3. No hay PDF para esta factura

                    logger.warning(
                        "⚠️ PDF esperado no encontrado: %s. "
                        "Posiblemente llegó en email diferente o tiene nomenclatura antigua.",
                        pdf_filename_estandar
                    )

                    # Guardar NULL en BD → invoice_pdf_service usará fallbacks
                    pdf_filename = None
            else:
                # ❌ XML sin CUFE (caso excepcional)
                logger.error(
                    "❌ XML sin CUFE: %s. No se puede determinar PDF con nomenclatura estándar.",
                    self.xml_path
                )
                pdf_filename = None

            final_data = {
                **basic_data,
                "subtotal": float(subtotal),
                "iva": float(iva),
                "retenciones": float(retenciones),
                "total_a_pagar": float(total_final_corregido),
                "pdf_filename": pdf_filename,  # Nombre del PDF para lookup O(1)
                "items_resumen": items_resumen,
                "concepto_principal": concepto,
                "concepto_normalizado": self.invoice_enricher.normalize_concepto(concepto),
                "concepto_hash": self.invoice_enricher.generate_concepto_hash(
                    self.invoice_enricher.normalize_concepto(concepto)
                ),
                "orden_compra": self.orden_compra_extractor.extract(self.invoice_tree),
                "notas_adicionales": self.notas_extractor.extract(self.invoice_tree),
                "tipo_factura": self.invoice_enricher.classify_invoice_type(
                    items_resumen, basic_data.get("razon_social_proveedor")
                ),
                "procesamiento_info": self._get_processing_info(
                    validation_info=validation_info,
                    correccion_payable=correccion_payable
                )
            }
            return final_data

        except Exception as exc:
            logger.error(f"Error fatal durante la extracción en {self.xml_path}: {exc}", exc_info=True)
            return None
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Retorna un pequeño resumen del documento y los campos monetarios extraídos.
        Usable sin ejecutar extract()."""
        if self.invoice_tree is None:
            return {"error": "Invoice not loaded"}
        try:
            monetary = self.monetary_forensic_extractor.extract_all_components(self.invoice_tree)
            return {
                "xml_path": str(self.xml_path),
                "total_items": self.items_extractor.get_total_items_count(self.invoice_tree),
                "monetary_fields": {k: float(v) for k, v in monetary.items()}
            }
        except Exception as exc:
            logger.error("Error getting processing summary: %s", exc)
            return {"error": str(exc)}

    def _get_processing_info(
        self,
        validation_info: Optional[Dict[str, Any]] = None,
        correccion_payable: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Genera metadatos sobre el proceso de extracción y correcciones aplicadas."""
        end_time = time.time()
        info: Dict[str, Any] = {
            "fecha_procesamiento": datetime.now().isoformat(),
            "version_algoritmo": "v5.1.0-CorreccionUBL21",
            "tiempo_procesamiento_ms": int((end_time - self.start_time) * 1000),
        }
        if validation_info is not None:
            info["validation"] = validation_info

        # CAMBIO CRÍTICO (2025-11-23):
        # Ya NO se aplican correcciones automáticas.
        # Solo registrar información de auditoría
        if correccion_payable is not None:
            info["correccion_aplicada"] = {
                "fue_aplicada": False,
                "razon": correccion_payable.get('razon', 'PayableAmount del XML es fuente de verdad'),
                "analisis_auditoría": correccion_payable.get('analisis', {})
            }

        return info

    def _reconcile_totals(
        self,
        total_oficial: Optional[Decimal],
        componentes: Dict[str, Decimal]
    ) -> Dict[str, Any]:
        """Valida consistencia interna del XML usando el reconciliador inteligente.

        IMPORTANTE: Esta función NO CALCULA ni MODIFICA el total extraído.
        Usa IntelligentReconciler para detectar inconsistencias en el XML.

        Retorna un dict con el estado y análisis de consistencia.
        """
        if total_oficial is None:
            return {
                "status": "FALLO_CRITICO",
                "mensaje": "No se pudo extraer un total a pagar oficial del XML.",
                "total_oficial_extraido": None,
                "componentes_extraidos": {k: float(v) for k, v in componentes.items()}
            }

        # Usar reconciliador inteligente para validar consistencia interna del XML
        tax_inclusive = componentes.get('tax_inclusive_amount', Decimal("0.0"))
        payable = componentes.get('payable_amount', Decimal("0.0"))
        retenciones = componentes.get('total_retenciones_calculado', Decimal("0.0"))

        # Verificar si el total extractor encontró un campo con total neto
        tiene_campo_neto = self.total_extractor.has_net_total_field()

        reconciliation_report = self.reconciler.reconcile_xml_only(
            tax_inclusive_amount=tax_inclusive,
            payable_amount=payable,
            retenciones_declaradas=retenciones,
            tiene_campo_total_neto=tiene_campo_neto
        )

        # Generar reporte de fuente primaria
        xml_values = {
            'subtotal': componentes.get('line_extension_amount', Decimal("0.0")),
            'iva': componentes.get('total_impuestos_calculado', Decimal("0.0")),
            'retenciones': retenciones,
            'tax_inclusive_amount': tax_inclusive,
            'payable_amount': payable
        }

        dual_source_report = self.reconciler.generate_dual_source_report(xml_values)

        return {
            "status": reconciliation_report.status.value,
            "mensaje": reconciliation_report.mensaje,
            "nivel_alerta": reconciliation_report.alert_level.value,
            "requiere_revision": reconciliation_report.requires_review,
            "total_oficial_extraido": float(total_oficial),
            "componentes_extraidos": {k: float(v) for k, v in componentes.items()},
            "fuente_primaria_xml": dual_source_report["fuente_primaria_xml"]
        }