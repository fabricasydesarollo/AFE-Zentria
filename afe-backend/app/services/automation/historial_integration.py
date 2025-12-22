"""
Módulo de integración entre automation_service y patrones_facturas.

Proporciona funciones helper para:
- Buscar patrones históricos en patrones_facturas
- Enriquecer decisiones con datos históricos
- Ajustar scores de confianza según tipo de patrón (TIPO_A/B/C)
- Validar montos contra rangos históricos


Fecha: 2025-10-08
"""

import hashlib
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.factura import Factura
from app.models.patrones_facturas import PatronesFacturas, TipoPatron


logger = logging.getLogger(__name__)


class PatronesIntegrationHelper:
    """
    Helper class para integrar patrones_facturas con el sistema de automatización.
    """

    @staticmethod
    def buscar_patron_historico(
        db: Session,
        factura: Factura
    ) -> Optional[PatronesFacturas]:
        """
        Busca un patrón histórico en patrones_facturas que coincida con la factura.

        Estrategia de búsqueda (en orden de prioridad):
        1. Por proveedor_id + concepto_hash (si existe)
        2. Por proveedor_id + concepto_normalizado
        3. Por proveedor_id + hash generado del concepto_principal

        Args:
            db: Sesión de base de datos
            factura: Factura a buscar

        Returns:
            PatronesFacturas si encuentra match, None si no
        """
        if not factura.proveedor_id:
            return None

        # Prioridad 1: Buscar por concepto_hash existente
        if factura.concepto_hash:
            patron = db.query(PatronesFacturas).filter(
                PatronesFacturas.proveedor_id == factura.proveedor_id,
                PatronesFacturas.concepto_hash == factura.concepto_hash
            ).first()

            if patron:
                logger.info(
                    "Patrón histórico encontrado por hash para factura %d",
                    factura.id
                )
                return patron

        # Prioridad 2: Buscar por concepto_normalizado
        if factura.concepto_normalizado:
            concepto_hash = hashlib.md5(
                factura.concepto_normalizado.encode('utf-8')
            ).hexdigest()

            patron = db.query(PatronesFacturas).filter(
                PatronesFacturas.proveedor_id == factura.proveedor_id,
                PatronesFacturas.concepto_hash == concepto_hash
            ).first()

            if patron:
                logger.info(
                    "Patrón histórico encontrado por concepto normalizado "
                    "para factura %d",
                    factura.id
                )
                return patron

        # Prioridad 3: Generar hash del concepto_principal
        if factura.concepto_principal:
            concepto_normalizado = PatronesIntegrationHelper._normalizar_concepto(
                factura.concepto_principal
            )
            concepto_hash = hashlib.md5(
                concepto_normalizado.encode('utf-8')
            ).hexdigest()

            patron = db.query(PatronesFacturas).filter(
                PatronesFacturas.proveedor_id == factura.proveedor_id,
                PatronesFacturas.concepto_hash == concepto_hash
            ).first()

            if patron:
                logger.info(
                    "Patrón histórico encontrado por concepto principal "
                    "para factura %d",
                    factura.id
                )
                return patron

        logger.debug("No se encontró patrón histórico para factura %d", factura.id)
        return None

    @staticmethod
    def _normalizar_concepto(concepto: str) -> str:
        """Normaliza un concepto para búsqueda."""
        concepto = concepto.lower().strip()
        concepto = concepto.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        concepto = concepto.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
        return concepto[:200]

    @staticmethod
    def calcular_ajuste_confianza(
        patron_historico: Optional[PatronesFacturas],
        monto_factura: Decimal
    ) -> Dict[str, Any]:
        """
        Calcula ajuste de confianza basado en el patrón histórico.

        Reglas de ajuste:
        - TIPO_A (fijo): +30% confianza si monto está dentro de ±15%
        - TIPO_B (fluctuante): +20% confianza si monto está dentro del rango esperado
        - TIPO_C (excepcional): -20% confianza, requiere revisión manual

        Args:
            patron_historico: Patrón histórico encontrado (o None)
            monto_factura: Monto de la factura a validar

        Returns:
            Diccionario con ajuste de confianza y razón
        """
        if not patron_historico:
            return {
                'ajuste_confianza': 0.0,
                'razon': 'Sin patrón histórico',
                'tiene_patron': False,
                'tipo_patron': None
            }

        # TIPO_A: Valores fijos (CV < 5%)
        if patron_historico.tipo_patron == TipoPatron.TIPO_A:
            variacion_pct = abs(
                float(monto_factura - patron_historico.monto_promedio) /
                float(patron_historico.monto_promedio)
            ) * 100

            if variacion_pct <= 15:
                return {
                    'ajuste_confianza': 0.30,
                    'razon': f'TIPO_A: Monto dentro del rango esperado (±15%), variación: {variacion_pct:.1f}%',
                    'tiene_patron': True,
                    'tipo_patron': 'TIPO_A',
                    'puede_auto_aprobar': patron_historico.puede_aprobar_auto == 1,
                    'monto_promedio_historico': float(patron_historico.monto_promedio),
                    'variacion_porcentaje': variacion_pct
                }
            else:
                return {
                    'ajuste_confianza': -0.10,
                    'razon': f'TIPO_A: Monto fuera del rango esperado, variación: {variacion_pct:.1f}%',
                    'tiene_patron': True,
                    'tipo_patron': 'TIPO_A',
                    'puede_auto_aprobar': False,
                    'monto_promedio_historico': float(patron_historico.monto_promedio),
                    'variacion_porcentaje': variacion_pct,
                    'requiere_revision': True
                }

        # TIPO_B: Valores fluctuantes predecibles (CV < 30%)
        elif patron_historico.tipo_patron == TipoPatron.TIPO_B:
            # Verificar si está dentro del rango esperado (±2 desviaciones estándar)
            if patron_historico.rango_inferior and patron_historico.rango_superior:
                dentro_rango = (
                    patron_historico.rango_inferior <= monto_factura <= patron_historico.rango_superior
                )

                if dentro_rango:
                    return {
                        'ajuste_confianza': 0.20,
                        'razon': 'TIPO_B: Monto dentro del rango estadístico esperado',
                        'tiene_patron': True,
                        'tipo_patron': 'TIPO_B',
                        'puede_auto_aprobar': patron_historico.puede_aprobar_auto == 1,
                        'monto_promedio_historico': float(patron_historico.monto_promedio),
                        'rango_inferior': float(patron_historico.rango_inferior),
                        'rango_superior': float(patron_historico.rango_superior)
                    }
                else:
                    return {
                        'ajuste_confianza': -0.05,
                        'razon': 'TIPO_B: Monto fuera del rango estadístico esperado',
                        'tiene_patron': True,
                        'tipo_patron': 'TIPO_B',
                        'puede_auto_aprobar': False,
                        'monto_promedio_historico': float(patron_historico.monto_promedio),
                        'rango_inferior': float(patron_historico.rango_inferior),
                        'rango_superior': float(patron_historico.rango_superior),
                        'requiere_revision': True
                    }

        # TIPO_C: Valores excepcionales (CV > 30%)
        elif patron_historico.tipo_patron == TipoPatron.TIPO_C:
            return {
                'ajuste_confianza': -0.20,
                'razon': 'TIPO_C: Patrón excepcional, alta variabilidad histórica',
                'tiene_patron': True,
                'tipo_patron': 'TIPO_C',
                'puede_auto_aprobar': False,
                'requiere_revision': True,
                'monto_promedio_historico': float(patron_historico.monto_promedio),
                'coeficiente_variacion': float(patron_historico.coeficiente_variacion)
            }

        return {
            'ajuste_confianza': 0.0,
            'razon': 'Patrón histórico sin clasificación válida',
            'tiene_patron': True,
            'tipo_patron': 'DESCONOCIDO'
        }

    @staticmethod
    def generar_metadata_patron(
        patron_historico: Optional[PatronesFacturas]
    ) -> Dict[str, Any]:
        """
        Genera metadata descriptiva del patrón histórico.

        Args:
            patron_historico: Patrón histórico encontrado

        Returns:
            Diccionario con metadata del patrón
        """
        if not patron_historico:
            return {
                'tiene_patron_historico': False
            }

        return {
            'tiene_patron_historico': True,
            'tipo_patron': patron_historico.tipo_patron.value,
            'pagos_analizados': patron_historico.pagos_analizados,
            'meses_con_pagos': patron_historico.meses_con_pagos,
            'monto_promedio': float(patron_historico.monto_promedio),
            'monto_minimo': float(patron_historico.monto_minimo),
            'monto_maximo': float(patron_historico.monto_maximo),
            'desviacion_estandar': float(patron_historico.desviacion_estandar),
            'coeficiente_variacion': float(patron_historico.coeficiente_variacion),
            'frecuencia_detectada': patron_historico.frecuencia_detectada,
            'puede_aprobar_auto': patron_historico.puede_aprobar_auto == 1,
            'umbral_alerta': float(patron_historico.umbral_alerta) if patron_historico.umbral_alerta else None,
            'fecha_ultimo_analisis': patron_historico.fecha_analisis.isoformat() if patron_historico.fecha_analisis else None,
            'version_algoritmo': patron_historico.version_algoritmo
        }

    @staticmethod
    def validar_monto_contra_historial(
        patron_historico: Optional[PatronesFacturas],
        monto_factura: Decimal,
        umbral_alerta_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Valida el monto de la factura contra el historial.

        Args:
            patron_historico: Patrón histórico
            monto_factura: Monto de la factura a validar
            umbral_alerta_pct: Umbral de alerta personalizado (None = usar del patrón)

        Returns:
            Resultado de la validación con alertas si corresponde
        """
        if not patron_historico:
            return {
                'validado': False,
                'razon': 'Sin historial para validar'
            }

        # Calcular desviación porcentual
        desviacion_pct = abs(
            float(monto_factura - patron_historico.monto_promedio) /
            float(patron_historico.monto_promedio)
        ) * 100

        # Usar umbral del patrón o uno personalizado
        umbral = umbral_alerta_pct or float(patron_historico.umbral_alerta or 30.0)

        alertas = []

        # Validar según tipo de patrón
        if patron_historico.tipo_patron == TipoPatron.TIPO_A:
            # Para TIPO_A, desviación >15% es crítica
            if desviacion_pct > 15:
                alertas.append({
                    'nivel': 'CRITICO',
                    'mensaje': f'Desviación significativa en patrón fijo: {desviacion_pct:.1f}% (esperado <15%)'
                })

        elif patron_historico.tipo_patron == TipoPatron.TIPO_B:
            # Para TIPO_B, validar contra rango esperado
            if patron_historico.rango_inferior and patron_historico.rango_superior:
                if monto_factura < patron_historico.rango_inferior:
                    alertas.append({
                        'nivel': 'ADVERTENCIA',
                        'mensaje': f'Monto por debajo del rango esperado: ${monto_factura:,.2f} < ${patron_historico.rango_inferior:,.2f}'
                    })
                elif monto_factura > patron_historico.rango_superior:
                    alertas.append({
                        'nivel': 'ADVERTENCIA',
                        'mensaje': f'Monto por encima del rango esperado: ${monto_factura:,.2f} > ${patron_historico.rango_superior:,.2f}'
                    })

        # Validar umbral de alerta general
        if desviacion_pct > umbral:
            alertas.append({
                'nivel': 'ADVERTENCIA',
                'mensaje': f'Desviación supera umbral de alerta: {desviacion_pct:.1f}% > {umbral:.1f}%'
            })

        return {
            'validado': True,
            'desviacion_porcentaje': desviacion_pct,
            'umbral_aplicado': umbral,
            'dentro_rango': len(alertas) == 0,
            'alertas': alertas,
            'monto_esperado': float(patron_historico.monto_promedio),
            'monto_actual': float(monto_factura)
        }
