"""
Servicio para Gestión de Items de Facturas.

Este servicio maneja la creación, actualización y consulta de items
individuales de facturas.



"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.factura import Factura
from app.models.factura_item import FacturaItem
from app.services.item_normalizer import ItemNormalizerService


logger = logging.getLogger(__name__)


class FacturaItemsService:
    """
    Servicio enterprise para gestión de items de facturas.

    Responsabilidades:
    - Crear items desde datos del XML extractor
    - Actualizar items existentes
    - Eliminar items de una factura
    - Consultar items con filtros
    """

    def __init__(self, db: Session):
        """
        Inicializa el servicio.

        Args:
            db: Sesión de base de datos SQLAlchemy
        """
        self.db = db
        self.normalizer = ItemNormalizerService()

    # ============================================================================
    # CREACIÓN DE ITEMS
    # ============================================================================

    def crear_items_desde_extractor(
        self,
        factura_id: int,
        items_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Crea items de factura desde datos del XML extractor.

        Args:
            factura_id: ID de la factura
            items_data: Lista de dicts con datos de items del extractor

        Returns:
            Dict con resultado:
            {
                'exito': True/False,
                'items_creados': 10,
                'errores': []
            }
        """
        logger.info(f"Creando {len(items_data)} items para factura {factura_id}")

        # Verificar que factura existe
        factura = self.db.query(Factura).get(factura_id)
        if not factura:
            return {
                'exito': False,
                'mensaje': f'Factura {factura_id} no encontrada',
                'items_creados': 0,
                'errores': ['Factura no existe']
            }

        # Eliminar items existentes (si los hay) para evitar duplicados
        self.db.query(FacturaItem).filter(
            FacturaItem.factura_id == factura_id
        ).delete()

        items_creados = []
        errores = []

        for item_data in items_data:
            try:
                # Crear item
                item = self._crear_item_desde_data(factura_id, item_data)
                self.db.add(item)
                items_creados.append(item)

            except Exception as e:
                logger.error(f"Error creando item {item_data.get('numero_linea')}: {str(e)}")
                errores.append({
                    'numero_linea': item_data.get('numero_linea'),
                    'error': str(e)
                })

        # Commit
        try:
            self.db.commit()
            logger.info(f"  {len(items_creados)} items creados para factura {factura_id}")

            return {
                'exito': True,
                'items_creados': len(items_creados),
                'errores': errores
            }

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al guardar items: {str(e)}")
            return {
                'exito': False,
                'mensaje': 'Error de integridad',
                'items_creados': 0,
                'errores': [str(e)]
            }

    def _crear_item_desde_data(
        self,
        factura_id: int,
        item_data: Dict[str, Any]
    ) -> FacturaItem:
        """
        Crea una instancia de FacturaItem desde datos del extractor.

        Args:
            factura_id: ID de la factura
            item_data: Dict con datos del item

        Returns:
            FacturaItem instancia
        """
        # Si no vienen normalizados, normalizarlos
        if not item_data.get('descripcion_normalizada'):
            normalized = self.normalizer.normalizar_item_completo(
                item_data.get('descripcion', '')
            )
            item_data.update(normalized)

        return FacturaItem(
            factura_id=factura_id,
            numero_linea=item_data.get('numero_linea', 1),
            descripcion=item_data.get('descripcion', ''),
            codigo_producto=item_data.get('codigo_producto'),
            codigo_estandar=item_data.get('codigo_estandar'),
            cantidad=item_data.get('cantidad', 1),
            unidad_medida=item_data.get('unidad_medida', 'unidad'),
            precio_unitario=item_data.get('precio_unitario', 0),
            subtotal=item_data.get('subtotal', 0),
            total_impuestos=item_data.get('total_impuestos', 0),
            total=item_data.get('total', 0),
            descuento_porcentaje=item_data.get('descuento_porcentaje'),
            descuento_valor=item_data.get('descuento_valor'),
            descripcion_normalizada=item_data.get('descripcion_normalizada'),
            item_hash=item_data.get('item_hash'),
            categoria=item_data.get('categoria'),
            es_recurrente=item_data.get('es_recurrente', 0)
        )

    # ============================================================================
    # CONSULTAS
    # ============================================================================

    def obtener_items_factura(self, factura_id: int) -> List[FacturaItem]:
        """
        Obtiene todos los items de una factura.

        Args:
            factura_id: ID de la factura

        Returns:
            Lista de FacturaItem ordenados por número de línea
        """
        return self.db.query(FacturaItem).filter(
            FacturaItem.factura_id == factura_id
        ).order_by(FacturaItem.numero_linea).all()

    def contar_items_factura(self, factura_id: int) -> int:
        """
        Cuenta items de una factura.

        Args:
            factura_id: ID de la factura

        Returns:
            Número de items
        """
        return self.db.query(FacturaItem).filter(
            FacturaItem.factura_id == factura_id
        ).count()

    # ============================================================================
    # ELIMINACIÓN
    # ============================================================================

    def eliminar_items_factura(self, factura_id: int) -> int:
        """
        Elimina todos los items de una factura.

        Args:
            factura_id: ID de la factura

        Returns:
            Número de items eliminados
        """
        count = self.db.query(FacturaItem).filter(
            FacturaItem.factura_id == factura_id
        ).delete()

        self.db.commit()

        logger.info(f"Eliminados {count} items de factura {factura_id}")
        return count

    # ============================================================================
    # UTILIDADES
    # ============================================================================

    def verificar_items_factura(self, factura_id: int) -> Dict[str, Any]:
        """
        Verifica el estado de los items de una factura.

        Returns:
            Dict con información de los items
        """
        items = self.obtener_items_factura(factura_id)

        if not items:
            return {
                'tiene_items': False,
                'total_items': 0
            }

        # Calcular estadísticas
        total_items = len(items)
        items_con_codigo = sum(1 for i in items if i.codigo_producto)
        items_recurrentes = sum(1 for i in items if i.es_recurrente)
        items_con_categoria = sum(1 for i in items if i.categoria)

        return {
            'tiene_items': True,
            'total_items': total_items,
            'items_con_codigo': items_con_codigo,
            'items_recurrentes': items_recurrentes,
            'items_con_categoria': items_con_categoria,
            'porcentaje_categorizados': (items_con_categoria / total_items * 100) if total_items > 0 else 0
        }
