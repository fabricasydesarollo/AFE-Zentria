# tests/test_factura.py
# Pruebas mínimas de integración (requieren DB en estado test)
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_and_docs():
    r = client.get("/docs")
    assert r.status_code == 200
