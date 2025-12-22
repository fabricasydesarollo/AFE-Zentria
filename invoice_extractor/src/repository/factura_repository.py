from sqlalchemy import text
import json

class FacturaRepository:
    def __init__(self, session):
        self.session = session

    def insert_factura(self, factura):
        """
        Inserta una factura en la base de datos.

        IMPORTANTE: Este INSERT está sincronizado con el modelo actualizado
        en afe-backend/app/models/factura.py (22 campos).

        Cambios 2025-10-10:
        - Eliminados campos obsoletos (concepto_*, items_resumen, orden_compra_*, etc.)
        - Estructura limpia con solo campos esenciales
        - Items ahora en tabla dedicada factura_items
        """
        insert_sql = text("""
            INSERT INTO facturas (
                numero_factura, cufe, fecha_emision, fecha_vencimiento,
                proveedor_id, subtotal, iva, retenciones, total_a_pagar,
                confianza_automatica, motivo_decision, estado
            ) VALUES (
                :numero_factura, :cufe, :fecha_emision, :fecha_vencimiento,
                :proveedor_id, :subtotal, :iva, :retenciones, :total_a_pagar,
                :confianza_automatica, :motivo_decision, :estado
            )
            ON DUPLICATE KEY UPDATE
                retenciones = VALUES(retenciones),
                total_a_pagar = VALUES(total_a_pagar),
                confianza_automatica = VALUES(confianza_automatica),
                motivo_decision = VALUES(motivo_decision)
        """)
        result = self.session.execute(insert_sql, factura)

        # Retornar el ID de la factura insertada o actualizada
        if result.lastrowid:
            return result.lastrowid
        else:
            # Si fue UPDATE (ON DUPLICATE KEY), buscar el ID por CUFE
            select_sql = text("SELECT id FROM facturas WHERE cufe = :cufe")
            result = self.session.execute(select_sql, {"cufe": factura["cufe"]})
            return result.scalar()
