"""
Validador de consistencia matemática de datos monetarios.

REGLA CRÍTICA (2025-11-23):
====================================
PayableAmount del XML es la FUENTE DE VERDAD ABSOLUTA.
NUNCA se modifica automáticamente para cálculos de pago.

Modelo de Negocio Colombia:
- Retenciones se DECLARAN a autoridades tributarias
- Retenciones NO se restan del pago al proveedor
- PayableAmount = lo que REALMENTE paga el cliente

Funciones:
- validate(): Solo VALIDA consistencia, no modifica
- detect_and_correct_payable_amount(): Solo REGISTRA para auditoría,
  nunca auto-corrige valores

Tolerancia: $0.01 (un centavo, para rounding)
====================================
"""
from decimal import Decimal
from typing import Dict, Any, Optional

from src.utils.logger import logger


class MonetaryConsistencyValidator:
    """
    Valida que los componentes monetarios de una factura sean matemáticamente consistentes.

    Usa la ecuación:
    SUBTOTAL + IVA - RETENCIONES = TOTAL A PAGAR

    Con tolerancia de $0.01 para rounding.
    """

    TOLERANCE = Decimal('0.01')  # Un centavo

    @staticmethod
    def validate(
        subtotal: Optional[Decimal],
        iva: Optional[Decimal],
        retenciones: Optional[Decimal],
        total_a_pagar: Optional[Decimal]
    ) -> Dict[str, Any]:
        """
        Valida la consistencia matemática de los componentes.

        Args:
            subtotal: Base imponible (LineExtensionAmount)
            iva: Total de impuestos (TaxAmount)
            retenciones: Total de retenciones (WithholdingTaxTotal)
            total_a_pagar: Total a pagar extraído del XML (PayableAmount)

        Returns:
            Dict con resultado de validación:
            {
                'es_valido': bool,
                'mensaje': str,
                'diferencia': Decimal,
                'datos_completos': bool
            }
        """
        # Verificar que todos los datos estén disponibles
        if subtotal is None or iva is None or total_a_pagar is None:
            return {
                'es_valido': False,
                'mensaje': 'Datos monetarios incompletos para validación',
                'datos_completos': False
            }

        # Retenciones son opcionales (muchas facturas no tienen)
        ret = retenciones if retenciones is not None else Decimal('0')

        # Ecuación principal
        calculado = subtotal + iva - ret

        # Comparar con tolerancia
        diferencia = abs(calculado - total_a_pagar)

        if diferencia <= MonetaryConsistencyValidator.TOLERANCE:
            return {
                'es_valido': True,
                'mensaje': 'Consistencia matemática correcta',
                'datos_completos': True,
                'diferencia': diferencia
            }
        else:
            return {
                'es_valido': False,
                'mensaje': (
                    f'Inconsistencia matemática: '
                    f'calculado ${calculado} vs reportado ${total_a_pagar}'
                ),
                'datos_completos': True,
                'diferencia': diferencia,
                'calculado': calculado,
                'reportado': total_a_pagar
            }

    @staticmethod
    def detect_and_correct_payable_amount(
        subtotal: Optional[Decimal],
        iva: Optional[Decimal],
        retenciones: Optional[Decimal],
        payable: Optional[Decimal]
    ) -> Dict[str, Any]:
        """
        CAMBIO CRÍTICO DE POLÍTICA (2025-11-23):

        YA NO auto-corrige PayableAmount. En su lugar:
        - CONFÍA en el PayableAmount del XML como fuente de verdad absoluta
        - REGISTRA la presencia de retenciones para auditoría
        - NUNCA modifica valores para cálculos de pago

        Contexto:
            - Las retenciones se DECLARAN a autoridades tributarias
            - NO se restan automáticamente del pago al proveedor
            - El PayableAmount del XML es lo que REALMENTE se paga

        Args:
            subtotal: LineExtensionAmount (base imponible)
            iva: Total de impuestos
            retenciones: Total de retenciones (WithholdingTaxTotal)
            payable: PayableAmount del XML (FUENTE DE VERDAD)

        Returns:
            Dict con análisis (sin correcciones automáticas):
            {
                'payable_corregido': Decimal - SIEMPRE igual a payable (sin cambios)
                'fue_corregido': bool - SIEMPRE False (nunca modifica)
                'razon': str - explicación
                'analisis': Dict - información de auditoría
            }
        """
        if subtotal is None or iva is None or payable is None:
            return {
                'payable_corregido': payable,
                'fue_corregido': False,
                'razon': 'Datos incompletos para validación'
            }

        ret = retenciones if retenciones is not None else Decimal('0')
        tax_inclusive = subtotal + iva

        # NUNCA corregir automáticamente
        # Solo registrar información para auditoría
        analisis = {
            'subtotal_extraido': subtotal,
            'iva_extraido': iva,
            'total_bruto': tax_inclusive,
            'retenciones_declaradas': ret,
            'payable_amount_xml': payable,
            'tiene_retenciones': ret > Decimal('0'),
        }

        # Detectar si PayableAmount coincide con bruto (sin retenciones restadas)
        if ret > Decimal('0') and abs(payable - tax_inclusive) < MonetaryConsistencyValidator.TOLERANCE:
            analisis['patron_detectado'] = 'PAYABLE_SIN_RETENCIONES_RESTADAS'
            analisis['nota'] = (
                'PayableAmount = Subtotal + IVA (retenciones no restadas). '
                'Esto es CORRECTO según negocio colombiano.'
            )

        # Retornar SIEMPRE sin cambios
        return {
            'payable_corregido': payable,  # ← NUNCA se modifica
            'fue_corregido': False,  # ← SIEMPRE False
            'razon': 'PayableAmount del XML es la fuente de verdad. Sin correcciones automáticas aplicadas.',
            'analisis': analisis
        }

    @staticmethod
    def log_validation(result: Dict[str, Any], documento_id: str = "UNKNOWN") -> None:
        """
        Registra el resultado de la validación en logs.

        Args:
            result: Resultado de validate()
            documento_id: ID del documento para logging
        """
        if result.get('es_valido'):
            logger.info(
                f"[{documento_id}] Validación OK - "
                f"Diferencia: ${result.get('diferencia', Decimal('0'))}"
            )
        else:
            if not result.get('datos_completos'):
                logger.warning(
                    f"[{documento_id}] Validación incompleta - "
                    f"{result.get('mensaje')}"
                )
            else:
                logger.error(
                    f"[{documento_id}] Inconsistencia detectada - "
                    f"{result.get('mensaje')}"
                )
