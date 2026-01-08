"""
Servicio de comparación de items de facturas.

Compara items de facturas contra históricos para detectar
anomalías, cambios de precios y nuevos servicios.
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
    """Servicio para comparación granular de items de facturas."""

    def __init__(self, db: Session):
        self.db = db
        self.normalizer = ItemNormalizerService()

        self.UMBRAL_PRECIO_MODERADO = 15.0
        self.UMBRAL_PRECIO_ALTO = 30.0
        self.UMBRAL_CANTIDAD_MODERADO = 20.0
        self.UMBRAL_CANTIDAD_ALTO = 50.0

    def comparar_factura_vs_historial(
        self,
        factura_id: int,
        meses_historico: int = 12
    ) -> Dict[str, Any]:
        """Compara items de factura contra histórico del proveedor."""
        logger.info(f"Comparando factura {factura_id} vs histórico...")

        factura = self.db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            raise ValueError(f"Factura {factura_id} no encontrada")

        if not factura.items:
            logger.warning(f"Factura {factura_id} no tiene items")
            return self._resultado_vacio()

        fecha_limite = factura.fecha_emision - timedelta(days=meses_historico * 30)

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
        """Compara un item individual contra su histórico."""
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

        items_historicos = self._buscar_items_historicos(
            proveedor_id=factura.proveedor_id,
            item_hash=item.item_hash,
            fecha_limite=fecha_limite,
            fecha_actual=factura.fecha_emision
        )

        if not items_historicos:
            resultado['alertas'].append({
                'tipo': 'item_nuevo',
                'severidad': 'media',
                'mensaje': f"Item sin historial previo: '{item.descripcion[:50]}...'",
                'requiere_aprobacion_manual': True
            })
            return resultado

        resultado['tiene_historial'] = True
        resultado['historial'] = self._calcular_estadisticas_historico(items_historicos)

        alertas_precio = self._comparar_precio_unitario(
            item,
            resultado['historial']
        )
        resultado['alertas'].extend(alertas_precio)

        alertas_cantidad = self._comparar_cantidad(
            item,
            resultado['historial']
        )
        resultado['alertas'].extend(alertas_cantidad)

        return resultado

    def _buscar_items_historicos(
        self,
        proveedor_id: int,
        item_hash: str,
        fecha_limite: datetime,
        fecha_actual: datetime
    ) -> List[FacturaItem]:
        """Busca items históricos del mismo tipo."""
        if not item_hash:
            return []

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
        """Calcula estadísticas del histórico de items."""
        if not items_historicos:
            return None

        precios = [float(item.precio_unitario) for item in items_historicos]
        cantidades = [float(item.cantidad) for item in items_historicos]

        precio_promedio = sum(precios) / len(precios)
        precio_min = min(precios)
        precio_max = max(precios)

        if len(precios) > 1:
            varianza_precio = sum((p - precio_promedio) ** 2 for p in precios) / len(precios)
            precio_desv = varianza_precio ** 0.5
        else:
            precio_desv = 0

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

    def _comparar_precio_unitario(
        self,
        item: FacturaItem,
        historial: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Compara precio unitario actual vs histórico."""
        alertas = []

        precio_actual = float(item.precio_unitario)
        precio_promedio = historial['precio_promedio']

        if precio_promedio > 0:
            desviacion = abs((precio_actual - precio_promedio) / precio_promedio * 100)

            if desviacion >= self.UMBRAL_PRECIO_ALTO:
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
        """Compara cantidad actual vs histórico."""
        alertas = []

        cantidad_actual = float(item.cantidad)
        cantidad_promedio = historial['cantidad_promedio']

        if cantidad_promedio > 0:
            desviacion = abs((cantidad_actual - cantidad_promedio) / cantidad_promedio * 100)

            if desviacion >= self.UMBRAL_CANTIDAD_ALTO:
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
                    'requiere_aprobacion_manual': False
                })

        return alertas

    def _calcular_recomendacion(
        self,
        items_ok: List[Dict],
        items_con_alertas: List[Dict],
        nuevos_items: List[Dict]
    ) -> tuple:
        """Calcula la recomendación final y confianza."""
        total_items = len(items_ok) + len(items_con_alertas) + len(nuevos_items)

        if total_items == 0:
            return ('aprobar_auto', 0.0)

        alertas_criticas = sum(
            1 for item in items_con_alertas
            for alerta in item['alertas']
            if alerta['severidad'] == 'alta'
        )

        if alertas_criticas > 0 or len(nuevos_items) > 0:
            recomendacion = 'en_revision'

            porcentaje_ok = len(items_ok) / total_items * 100
            confianza = min(porcentaje_ok, 50.0)

        else:
            recomendacion = 'aprobar_auto'

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
