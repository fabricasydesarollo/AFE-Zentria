"""
Repositorio para gestión de items de facturas.

Este repositorio maneja la persistencia de los items/líneas individuales
de cada factura en la tabla factura_items.

Autor: Sistema AFE
Fecha: 2025-10-10
"""
from sqlalchemy import text
from src.utils.logger import get_logger


class FacturaItemRepository:
    """Repositorio para operaciones CRUD de items de facturas."""

    def __init__(self, session):
        """
        Inicializa el repositorio.

        Args:
            session: Sesión de SQLAlchemy para transacciones de BD
        """
        self.session = session
        self.logger = get_logger("FacturaItemRepository")

    def insert_item(self, item_dict):
        """
        Inserta un item de factura en la base de datos.

        Args:
            item_dict: Diccionario con los datos del item

        Campos requeridos:
            - factura_id: ID de la factura padre
            - numero_linea: Número de línea en la factura
            - descripcion: Descripción del item
            - cantidad: Cantidad facturada
            - precio_unitario: Precio unitario
            - total_impuestos: Total de impuestos

        Campos calculados automáticamente (GENERATED COLUMNS):
            - subtotal: Calculado como (cantidad * precio_unitario - descuento_valor)
            - total: Calculado como (subtotal + total_impuestos)

        Campos opcionales:
            - codigo_producto: Código del producto del proveedor
            - unidad_medida: Unidad de medida
            - descuento_valor: Valor del descuento
            - descripcion_normalizada: Descripción normalizada
            - item_hash: Hash MD5 para comparación
            - categoria: Categoría del item
            - es_recurrente: Si es recurrente (0 o 1)

        NOTA: Columnas eliminadas en afe-backend (2025-11-25):
            - codigo_estandar, descuento_porcentaje, notas
            Ver: REPORTE_TECNICO_SINCRONIZACION_SCHEMA_2025-12-02.md

        Raises:
            Exception: Si hay error al insertar
        """
        try:
            # Excluir columnas generadas (subtotal, total) del INSERT
            # Estas se calculan automáticamente en MySQL
            # SCHEMA v2.0.0 (2025-12-02): Eliminadas codigo_estandar, descuento_porcentaje, notas
            sql = text("""
                INSERT INTO factura_items (
                    factura_id, numero_linea, descripcion, codigo_producto,
                    cantidad, unidad_medida, precio_unitario,
                    total_impuestos, descuento_valor,
                    descripcion_normalizada, item_hash,
                    categoria, es_recurrente
                ) VALUES (
                    :factura_id, :numero_linea, :descripcion, :codigo_producto,
                    :cantidad, :unidad_medida, :precio_unitario,
                    :total_impuestos, :descuento_valor,
                    :descripcion_normalizada, :item_hash,
                    :categoria, :es_recurrente
                )
            """)

            self.session.execute(sql, item_dict)
            self.logger.debug(
                f"Item insertado: Factura {item_dict['factura_id']}, "
                f"Línea {item_dict['numero_linea']}"
            )

        except Exception as e:
            self.logger.error(
                f"Error insertando item (factura_id={item_dict.get('factura_id')}, "
                f"linea={item_dict.get('numero_linea')}): {e}"
            )
            raise

    def insert_items_batch(self, items_list):
        """
        Inserta múltiples items en una sola operación.

        Args:
            items_list: Lista de diccionarios con datos de items

        Returns:
            int: Número de items insertados

        Raises:
            Exception: Si hay error al insertar
        """
        try:
            count = 0
            for item_dict in items_list:
                self.insert_item(item_dict)
                count += 1

            self.logger.info(f"Insertados {count} items en lote")
            return count

        except Exception as e:
            self.logger.error(f"Error insertando lote de items: {e}")
            raise

    def delete_items_by_factura(self, factura_id):
        """
        Elimina todos los items de una factura.

        Args:
            factura_id: ID de la factura

        Returns:
            int: Número de items eliminados
        """
        try:
            sql = text("DELETE FROM factura_items WHERE factura_id = :factura_id")
            result = self.session.execute(sql, {"factura_id": factura_id})

            count = result.rowcount
            self.logger.info(f"Eliminados {count} items de factura {factura_id}")
            return count

        except Exception as e:
            self.logger.error(f"Error eliminando items de factura {factura_id}: {e}")
            raise

    def get_items_by_factura(self, factura_id):
        """
        Obtiene todos los items de una factura.

        Args:
            factura_id: ID de la factura

        Returns:
            list: Lista de items (como diccionarios)
        """
        try:
            sql = text("""
                SELECT * FROM factura_items
                WHERE factura_id = :factura_id
                ORDER BY numero_linea
            """)

            result = self.session.execute(sql, {"factura_id": factura_id})
            items = [dict(row._mapping) for row in result]

            self.logger.debug(f"Obtenidos {len(items)} items de factura {factura_id}")
            return items

        except Exception as e:
            self.logger.error(f"Error obteniendo items de factura {factura_id}: {e}")
            raise
