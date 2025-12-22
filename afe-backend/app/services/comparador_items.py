"""
Servicio de Comparación Inteligente de Items de Facturas.

Este servicio compara items de facturas actuales contra históricos
para detectar anomalías, cambios de precios y nuevos servicios.


Fecha: 2025-10-09
"""

import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.factura import Factura
from app.models.factura_item import FacturaItem
from app.services.item_normalizer import ItemNormalizerService


logger = logging.getLogger(__name__)


class ComparadorItemsService:
    """
    Servicio enterprise para comparación granular de items de facturas.

    Funcionalidad:
    - Compara item por item contra histórico
    - Detecta cambios de precios unitarios
    - Detecta nuevos items sin historial
    - Detecta cambios en cantidades
    - Genera alertas con severidad
    - Calcula confianza para aprobación automática
    """

    def __init__(self, db: Session):
        """
        Inicializa el comparador.

        Args:
            db: Sesión de base de datos SQLAlchemy
        """
        self.db = db
        self.normalizer = ItemNormalizerService()

        # Umbrales de alerta (configurables)
        self.UMBRAL_PRECIO_MODERADO = 15.0  # % variación precio
        self.UMBRAL_PRECIO_ALTO = 30.0      # % variación crítica
        self.UMBRAL_CANTIDAD_MODERADO = 20.0  # % variación cantidad
        self.UMBRAL_CANTIDAD_ALTO = 50.0    # % variación crítica

    # ============================================================================
    # COMPARACIÓN PRINCIPAL
    # ============================================================================

    def comparar_factura_vs_historial(
        self,
        factura_id: int,
        meses_historico: int = 12
    ) -> Dict[str, Any]:
        """
        Compara todos los items de una factura contra histórico del proveedor.

        Args:
            factura_id: ID de la factura a analizar
            meses_historico: Ventana de meses históricos a considerar

        Returns:
            Dict con:
            - items_analizados: total de items
            - items_ok: items sin anomalías
            - items_con_alertas: items con alertas
            - alertas: lista de alertas detalladas
            - nuevos_items: items sin historial
            - recomendacion: aprobar_auto / en_revision
            - confianza: 0-100
        """
        logger.info(f"Comparando factura {factura_id} vs histórico...")

        # Obtener factura con items
        factura = self.db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            raise ValueError(f"Factura {factura_id} no encontrada")

        if not factura.items:
            logger.warning(f"Factura {factura_id} no tiene items")
            return self._resultado_vacio()

        # Calcular fecha límite para histórico
        fecha_limite = factura.fecha_emision - timedelta(days=meses_historico * 30)

        # Comparar cada item
        items_ok = []
        items_con_alertas = []
        alertas = []
        nuevos_items = []

        for item in factura.items:
            resultado_item = self._comparar_item_individual(
                item,
                factura,
                fecha_limite
            )

            if resultado_item['tiene_historial']:
                if resultado_item['alertas']:
                    items_con_alertas.append(resultado_item)
                    alertas.extend(resultado_item['alertas'])
                else:
                    items_ok.append(resultado_item)
            else:
                nuevos_items.append(resultado_item)

        # Calcular recomendación final
        recomendacion, confianza = self._calcular_recomendacion(
            items_ok,
            items_con_alertas,
            nuevos_items
        )

        return {
            'factura_id': factura_id,
            'items_analizados': len(factura.items),
            'items_ok': len(items_ok),
            'items_con_alertas': len(items_con_alertas),
            'nuevos_items_count': len(nuevos_items),
            'alertas': alertas,
            'nuevos_items': nuevos_items,
            'detalles_items_ok': items_ok,
            'detalles_items_alertas': items_con_alertas,
            'recomendacion': recomendacion,
            'confianza': confianza,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _comparar_item_individual(
        self,
        item: FacturaItem,
        factura: Factura,
        fecha_limite: datetime
    ) -> Dict[str, Any]:
        """
        Compara un item individual contra su histórico.

        Returns:
            Dict con análisis del item
        """
        resultado = {
            'item_id': item.id,
            'numero_linea': item.numero_linea,
            'descripcion': item.descripcion,
            'cantidad_actual': float(item.cantidad),
            'precio_unitario_actual': float(item.precio_unitario),
            'total_actual': float(item.total),
            'tiene_historial': False,
            'alertas': [],
            'historial': None
        }

        # Buscar items similares en facturas anteriores del mismo proveedor
        items_historicos = self._buscar_items_historicos(
            proveedor_id=factura.proveedor_id,
            item_hash=item.item_hash,
            fecha_limite=fecha_limite,
            fecha_actual=factura.fecha_emision
        )

        if not items_historicos:
            # Item nuevo sin historial
            resultado['alertas'].append({
                'tipo': 'item_nuevo',
                'severidad': 'media',
                'mensaje': f"Item sin historial previo: '{item.descripcion[:50]}...'",
                'requiere_aprobacion_manual': True
            })
            return resultado

        # Tiene historial - analizar estadísticas
        resultado['tiene_historial'] = True
        resultado['historial'] = self._calcular_estadisticas_historico(items_historicos)

        # Comparar precio unitario
        alertas_precio = self._comparar_precio_unitario(
            item,
            resultado['historial']
        )
        resultado['alertas'].extend(alertas_precio)

        # Comparar cantidad
        alertas_cantidad = self._comparar_cantidad(
            item,
            resultado['historial']
        )
        resultado['alertas'].extend(alertas_cantidad)

        return resultado

    # ============================================================================
    # BÚSQUEDA Y ESTADÍSTICAS
    # ============================================================================

    def _buscar_items_historicos(
        self,
        proveedor_id: int,
        item_hash: str,
        fecha_limite: datetime,
        fecha_actual: datetime
    ) -> List[FacturaItem]:
        """
        Busca items históricos del mismo tipo.

        Returns:
            Lista de FacturaItem históricos
        """
        if not item_hash:
            return []

        # Query: Items del mismo proveedor, mismo hash, en ventana de tiempo
        items = self.db.query(FacturaItem).join(Factura).filter(
            and_(
                Factura.proveedor_id == proveedor_id,
                FacturaItem.item_hash == item_hash,
                Factura.fecha_emision >= fecha_limite,
                Factura.fecha_emision < fecha_actual
            )
        ).order_by(Factura.fecha_emision.desc()).all()

        return items

    def _calcular_estadisticas_historico(
        self,
        items_historicos: List[FacturaItem]
    ) -> Dict[str, Any]:
        """
        Calcula estadísticas del histórico de items.

        Returns:
            Dict con promedio, min, max, desv. estándar
        """
        if not items_historicos:
            return None

        # Extraer precios y cantidades
        precios = [float(item.precio_unitario) for item in items_historicos]
        cantidades = [float(item.cantidad) for item in items_historicos]

        # Calcular estadísticas de precio
        precio_promedio = sum(precios) / len(precios)
        precio_min = min(precios)
        precio_max = max(precios)

        # Desviación estándar
        if len(precios) > 1:
            varianza_precio = sum((p - precio_promedio) ** 2 for p in precios) / len(precios)
            precio_desv = varianza_precio ** 0.5
        else:
            precio_desv = 0

        # Estadísticas de cantidad
        cantidad_promedio = sum(cantidades) / len(cantidades)
        cantidad_min = min(cantidades)
        cantidad_max = max(cantidades)

        return {
            'veces_facturado': len(items_historicos),
            'precio_promedio': precio_promedio,
            'precio_min': precio_min,
            'precio_max': precio_max,
            'precio_desv_std': precio_desv,
            'cantidad_promedio': cantidad_promedio,
            'cantidad_min': cantidad_min,
            'cantidad_max': cantidad_max,
            'ultimo_precio': precios[0] if precios else None,
            'ultima_cantidad': cantidades[0] if cantidades else None
        }

    # ============================================================================
    # COMPARACIONES ESPECÍFICAS
    # ============================================================================

    def _comparar_precio_unitario(
        self,
        item: FacturaItem,
        historial: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Compara precio unitario actual vs histórico.

        Returns:
            Lista de alertas (si hay)
        """
        alertas = []

        precio_actual = float(item.precio_unitario)
        precio_promedio = historial['precio_promedio']

        # Calcular desviación porcentual
        if precio_promedio > 0:
            desviacion = abs((precio_actual - precio_promedio) / precio_promedio * 100)

            if desviacion >= self.UMBRAL_PRECIO_ALTO:
                # ALERTA CRÍTICA
                alertas.append({
                    'tipo': 'precio_variacion_alta',
                    'severidad': 'alta',
                    'mensaje': (
                        f"Precio unitario varió {desviacion:.1f}% "
                        f"(${precio_actual:,.2f} vs promedio ${precio_promedio:,.2f})"
                    ),
                    'precio_actual': precio_actual,
                    'precio_esperado': precio_promedio,
                    'desviacion_porcentual': desviacion,
                    'requiere_aprobacion_manual': True
                })

            elif desviacion >= self.UMBRAL_PRECIO_MODERADO:
                # ALERTA MODERADA
                alertas.append({
                    'tipo': 'precio_variacion_moderada',
                    'severidad': 'media',
                    'mensaje': (
                        f"Precio unitario varió {desviacion:.1f}% "
                        f"(${precio_actual:,.2f} vs promedio ${precio_promedio:,.2f})"
                    ),
                    'precio_actual': precio_actual,
                    'precio_esperado': precio_promedio,
                    'desviacion_porcentual': desviacion,
                    'requiere_aprobacion_manual': True
                })

        return alertas

    def _comparar_cantidad(
        self,
        item: FacturaItem,
        historial: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Compara cantidad actual vs histórico.

        Returns:
            Lista de alertas (si hay)
        """
        alertas = []

        cantidad_actual = float(item.cantidad)
        cantidad_promedio = historial['cantidad_promedio']

        # Calcular desviación porcentual
        if cantidad_promedio > 0:
            desviacion = abs((cantidad_actual - cantidad_promedio) / cantidad_promedio * 100)

            if desviacion >= self.UMBRAL_CANTIDAD_ALTO:
                # ALERTA CRÍTICA
                alertas.append({
                    'tipo': 'cantidad_variacion_alta',
                    'severidad': 'alta',
                    'mensaje': (
                        f"Cantidad varió {desviacion:.1f}% "
                        f"({cantidad_actual:,.2f} vs promedio {cantidad_promedio:,.2f})"
                    ),
                    'cantidad_actual': cantidad_actual,
                    'cantidad_esperada': cantidad_promedio,
                    'desviacion_porcentual': desviacion,
                    'requiere_aprobacion_manual': True
                })

            elif desviacion >= self.UMBRAL_CANTIDAD_MODERADO:
                # ALERTA MODERADA
                alertas.append({
                    'tipo': 'cantidad_variacion_moderada',
                    'severidad': 'media',
                    'mensaje': (
                        f"Cantidad varió {desviacion:.1f}% "
                        f"({cantidad_actual:,.2f} vs promedio {cantidad_promedio:,.2f})"
                    ),
                    'cantidad_actual': cantidad_actual,
                    'cantidad_esperada': cantidad_promedio,
                    'desviacion_porcentual': desviacion,
                    'requiere_aprobacion_manual': False  # Solo informativa
                })

        return alertas

    # ============================================================================
    # RECOMENDACIÓN FINAL
    # ============================================================================

    def _calcular_recomendacion(
        self,
        items_ok: List[Dict],
        items_con_alertas: List[Dict],
        nuevos_items: List[Dict]
    ) -> tuple:
        """
        Calcula la recomendación final y confianza.

        Returns:
            (recomendacion: str, confianza: float)
        """
        total_items = len(items_ok) + len(items_con_alertas) + len(nuevos_items)

        if total_items == 0:
            return ('aprobar_auto', 0.0)

        # Contar alertas críticas
        alertas_criticas = sum(
            1 for item in items_con_alertas
            for alerta in item['alertas']
            if alerta['severidad'] == 'alta'
        )

        # Decidir recomendación
        if alertas_criticas > 0 or len(nuevos_items) > 0:
            # Requiere revisión manual
            recomendacion = 'en_revision'

            # Calcular confianza (baja si hay muchas alertas)
            porcentaje_ok = len(items_ok) / total_items * 100
            confianza = min(porcentaje_ok, 50.0)  # Max 50% si requiere revisión

        else:
            # Puede aprobar automáticamente
            recomendacion = 'aprobar_auto'

            # Confianza alta si todos OK
            porcentaje_ok = len(items_ok) / total_items * 100

            if porcentaje_ok == 100:
                confianza = 95.0
            elif porcentaje_ok >= 90:
                confianza = 85.0
            else:
                confianza = 70.0

        return (recomendacion, confianza)

    def _resultado_vacio(self) -> Dict[str, Any]:
        """Retorna resultado vacío cuando no hay items."""
        return {
            'items_analizados': 0,
            'items_ok': 0,
            'items_con_alertas': 0,
            'nuevos_items_count': 0,
            'alertas': [],
            'nuevos_items': [],
            'detalles_items_ok': [],
            'detalles_items_alertas': [],
            'recomendacion': 'en_revision',
            'confianza': 0.0
        }
