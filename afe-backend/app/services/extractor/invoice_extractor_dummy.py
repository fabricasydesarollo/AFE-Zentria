# app/services/extractor/invoice_extractor_dummy.py
from app.services.extractor.base import IInvoiceExtractor
from typing import Iterable
from app.schemas.factura import FacturaCreate
from datetime import date

class DummyExtractor(IInvoiceExtractor):
    def extract(self, batch_size: int = 100) -> Iterable[FacturaCreate]:
        # ejemplo: retorna un par de facturas de prueba
        yield FacturaCreate(
            numero_factura="FAC-DUMMY-001",
            fecha_emision=date.today(),
            proveedor_id=None,
            subtotal=1000.00,
            iva=190.00,
            fecha_vencimiento=None,
            cufe="CUFE-DUMMY-0001",
            total_a_pagar=1190.00
        )
