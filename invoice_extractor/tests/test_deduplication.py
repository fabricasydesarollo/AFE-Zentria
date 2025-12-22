import pytest
from src.utils.deduplication import deduplicate_facturas

def test_deduplicate_facturas():
    facturas = [
        {"numero_factura": "A", "cufe": "1"},
        {"numero_factura": "A", "cufe": "1"},
        {"numero_factura": "B", "cufe": "2"},
    ]
    dedup = deduplicate_facturas(facturas)
    assert len(dedup) == 2
    assert any(f["numero_factura"] == "A" for f in dedup)
    assert any(f["numero_factura"] == "B" for f in dedup)
