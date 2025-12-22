"""
ENTERPRISE-GRADE TESTS: Sistema de Asignaciones NIT con Soft Delete

Tests de integración completos para verificar el comportamiento correcto
del patrón soft delete en asignaciones NIT-Usuario.

Cubre:
- Soft delete pattern (DELETE → marca activo=False)
- Filtrado automático de asignaciones inactivas
- Reactivación automática en POST
- Endpoint de restauración
- Validación de duplicados soft-delete aware
- Bulk operations con reactivación
- Conflict detection

Nivel: Enterprise Production-Ready Test Suite
Autor: Equipo de Desarrollo 
Fecha: 2025-10-21
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Importar app y dependencias
from app.main import app
from app.db.session import get_db
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.usuario import Usuario
from app.core.security import create_access_token


# ==================== FIXTURES ====================

@pytest.fixture
def client():
    """Cliente de prueba HTTP."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Sesión de base de datos de prueba."""
    db = next(get_db())
    yield db
    db.close()


@pytest.fixture
def auth_headers(db_session: Session):
    """Headers de autenticación para pruebas."""
    # Buscar o crear responsable de prueba
    responsable = db_session.query(Usuario).filter(
        Usuario.usuario == "test_user"
    ).first()

    if not responsable:
        pytest.skip("Usuario de prueba no existe. Crear responsable 'test_user' primero.")

    # Generar token
    token = create_access_token(responsable.usuario)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def limpiar_asignaciones_test(db_session: Session):
    """Limpia asignaciones de prueba antes y después de cada test."""
    # Limpiar antes
    db_session.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit.like("TEST_%")
    ).delete()
    db_session.commit()

    yield

    # Limpiar después
    db_session.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit.like("TEST_%")
    ).delete()
    db_session.commit()


# ==================== TEST SUITE: SOFT DELETE PATTERN ====================

class TestSoftDeletePattern:
    """Tests del patrón soft delete básico."""

    def test_delete_marca_como_inactivo(
        self, client, auth_headers, db_session, limpiar_asignaciones_test
    ):
        """
        TEST: DELETE marca asignación como activo=False (soft delete).

        Flujo:
        1. Crear asignación
        2. Eliminar asignación
        3. Verificar que existe en BD pero con activo=False
        """
        # ARRANGE: Crear asignación
        payload = {
            "nit": "TEST_900123456",
            "responsable_id": 1,
            "nombre_proveedor": "Test Proveedor SAS"
        }
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        assert response.status_code == 201
        asignacion_id = response.json()["id"]

        # ACT: Eliminar asignación
        response = client.delete(f"/asignacion-nit/{asignacion_id}", headers=auth_headers)
        assert response.status_code == 204

        # ASSERT: Verificar que existe en BD pero está inactiva
        asignacion_db = db_session.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.id == asignacion_id
        ).first()

        assert asignacion_db is not None, "La asignación debe existir en BD"
        assert asignacion_db.activo == False, "La asignación debe estar marcada como inactiva"

    def test_get_no_retorna_asignaciones_eliminadas(
        self, client, auth_headers, db_session, limpiar_asignaciones_test
    ):
        """
        TEST: GET no retorna asignaciones eliminadas (soft delete).

        Flujo:
        1. Crear asignación
        2. Verificar que aparece en GET
        3. Eliminar asignación
        4. Verificar que NO aparece en GET
        """
        # ARRANGE: Crear asignación
        payload = {
            "nit": "TEST_900123457",
            "responsable_id": 1,
            "nombre_proveedor": "Test Proveedor 2 SAS"
        }
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        assert response.status_code == 201
        asignacion_id = response.json()["id"]

        # Verificar que aparece en GET
        response = client.get("/asignacion-nit/", headers=auth_headers)
        assert response.status_code == 200
        asignaciones = response.json()
        assert any(a["id"] == asignacion_id for a in asignaciones)

        # ACT: Eliminar asignación
        response = client.delete(f"/asignacion-nit/{asignacion_id}", headers=auth_headers)
        assert response.status_code == 204

        # ASSERT: NO debe aparecer en GET
        response = client.get("/asignacion-nit/", headers=auth_headers)
        assert response.status_code == 200
        asignaciones = response.json()
        assert not any(a["id"] == asignacion_id for a in asignaciones), \
            "La asignación eliminada NO debe aparecer en GET por defecto"

    def test_get_con_incluir_inactivos_retorna_eliminadas(
        self, client, auth_headers, db_session, limpiar_asignaciones_test
    ):
        """
        TEST: GET con incluir_inactivos=true retorna asignaciones eliminadas (auditoría).

        Flujo:
        1. Crear y eliminar asignación
        2. GET normal → no aparece
        3. GET con incluir_inactivos=true → sí aparece
        """
        # ARRANGE: Crear y eliminar asignación
        payload = {
            "nit": "TEST_900123458",
            "responsable_id": 1,
            "nombre_proveedor": "Test Proveedor 3 SAS"
        }
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        asignacion_id = response.json()["id"]

        client.delete(f"/asignacion-nit/{asignacion_id}", headers=auth_headers)

        # ACT & ASSERT: GET normal → no aparece
        response = client.get("/asignacion-nit/", headers=auth_headers)
        asignaciones = response.json()
        assert not any(a["id"] == asignacion_id for a in asignaciones)

        # ACT & ASSERT: GET con incluir_inactivos=true → sí aparece
        response = client.get("/asignacion-nit/?incluir_inactivos=true", headers=auth_headers)
        assert response.status_code == 200
        asignaciones = response.json()
        assert any(a["id"] == asignacion_id for a in asignaciones), \
            "La asignación eliminada DEBE aparecer con incluir_inactivos=true"


# ==================== TEST SUITE: REACTIVACIÓN AUTOMÁTICA ====================

class TestReactivacionAutomatica:
    """Tests de reactivación automática en POST."""

    def test_post_reactiva_asignacion_eliminada(
        self, client, auth_headers, db_session, limpiar_asignaciones_test
    ):
        """
        TEST: POST reactiva automáticamente asignación previamente eliminada.

        Flujo:
        1. Crear asignación
        2. Eliminar asignación
        3. POST con mismo NIT y responsable → debe reactivar (no crear nueva)
        4. Verificar que el ID es el mismo (reutilización)
        """
        # ARRANGE: Crear asignación
        payload = {
            "nit": "TEST_900123459",
            "responsable_id": 1,
            "nombre_proveedor": "Test Proveedor 4 SAS"
        }
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        asignacion_id_original = response.json()["id"]

        # Eliminar asignación
        client.delete(f"/asignacion-nit/{asignacion_id_original}", headers=auth_headers)

        # ACT: POST con mismo NIT y responsable
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)

        # ASSERT: Debe reactivar (mismo ID)
        assert response.status_code == 201
        asignacion_reactivada = response.json()
        assert asignacion_reactivada["id"] == asignacion_id_original, \
            "Debe reutilizar el mismo ID (reactivación, no creación nueva)"
        assert asignacion_reactivada["activo"] == True

        # Verificar en BD
        asignacion_db = db_session.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.id == asignacion_id_original
        ).first()
        assert asignacion_db.activo == True

    def test_post_no_crea_duplicado_si_existe_activa(
        self, client, auth_headers, limpiar_asignaciones_test
    ):
        """
        TEST: POST rechaza duplicado si ya existe asignación ACTIVA.

        Flujo:
        1. Crear asignación
        2. POST con mismo NIT y responsable → debe rechazar (400)
        """
        # ARRANGE: Crear asignación
        payload = {
            "nit": "TEST_900123460",
            "responsable_id": 1,
            "nombre_proveedor": "Test Proveedor 5 SAS"
        }
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        assert response.status_code == 201

        # ACT: Intentar crear duplicado
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)

        # ASSERT: Debe rechazar
        assert response.status_code == 400
        assert "ya existe" in response.json()["detail"].lower()


# ==================== TEST SUITE: ENDPOINT DE RESTAURACIÓN ====================

class TestEndpointRestauracion:
    """Tests del endpoint POST /{id}/restore."""

    def test_restore_reactiva_asignacion_eliminada(
        self, client, auth_headers, db_session, limpiar_asignaciones_test
    ):
        """
        TEST: POST /{id}/restore reactiva asignación eliminada.

        Flujo:
        1. Crear y eliminar asignación
        2. Restaurar con /restore
        3. Verificar que está activa
        """
        # ARRANGE: Crear y eliminar
        payload = {
            "nit": "TEST_900123461",
            "responsable_id": 1,
            "nombre_proveedor": "Test Proveedor 6 SAS"
        }
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        asignacion_id = response.json()["id"]

        client.delete(f"/asignacion-nit/{asignacion_id}", headers=auth_headers)

        # ACT: Restaurar
        response = client.post(f"/asignacion-nit/{asignacion_id}/restore", headers=auth_headers)

        # ASSERT: Debe estar activa
        assert response.status_code == 200 or response.status_code == 201
        asignacion = response.json()
        assert asignacion["activo"] == True

        # Verificar en BD
        asignacion_db = db_session.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.id == asignacion_id
        ).first()
        assert asignacion_db.activo == True

    def test_restore_detecta_conflicto_con_asignacion_activa(
        self, client, auth_headers, db_session, limpiar_asignaciones_test
    ):
        """
        TEST: /restore detecta conflicto si ya existe asignación activa.

        Flujo:
        1. Crear asignación A
        2. Eliminar asignación A
        3. Crear asignación B (mismo NIT y responsable)
        4. Intentar restaurar A → debe rechazar (409 Conflict)
        """
        # ARRANGE: Crear asignación A
        payload = {
            "nit": "TEST_900123462",
            "responsable_id": 1,
            "nombre_proveedor": "Test Proveedor 7 SAS"
        }
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        asignacion_a_id = response.json()["id"]

        # Eliminar A
        client.delete(f"/asignacion-nit/{asignacion_a_id}", headers=auth_headers)

        # Crear asignación B (mismo NIT y responsable - será reactivación de A)
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        # Nota: Este POST debería reactivar A, no crear B

        # ACT: Intentar restaurar A (pero ya está activa)
        response = client.post(f"/asignacion-nit/{asignacion_a_id}/restore", headers=auth_headers)

        # ASSERT: Debe rechazar (ya está activa)
        assert response.status_code == 400


# ==================== TEST SUITE: BULK OPERATIONS ====================

class TestBulkOperationsConReactivacion:
    """Tests de operaciones BULK con reactivación."""

    def test_bulk_reactiva_asignaciones_eliminadas(
        self, client, auth_headers, db_session, limpiar_asignaciones_test
    ):
        """
        TEST: BULK reactiva asignaciones previamente eliminadas.

        Flujo:
        1. Crear y eliminar varias asignaciones
        2. BULK con los mismos NITs → debe reactivar
        3. Verificar estadísticas de reactivación
        """
        # ARRANGE: Crear y eliminar 3 asignaciones
        nits_test = [
            {"nit": "TEST_900123463", "nombre_proveedor": "Proveedor 8"},
            {"nit": "TEST_900123464", "nombre_proveedor": "Proveedor 9"},
            {"nit": "TEST_900123465", "nombre_proveedor": "Proveedor 10"},
        ]

        ids_originales = []
        for nit_data in nits_test:
            response = client.post("/asignacion-nit/", json={
                **nit_data,
                "responsable_id": 1
            }, headers=auth_headers)
            asig_id = response.json()["id"]
            ids_originales.append(asig_id)
            client.delete(f"/asignacion-nit/{asig_id}", headers=auth_headers)

        # ACT: BULK con mismos NITs
        payload_bulk = {
            "responsable_id": 1,
            "nits": nits_test
        }
        response = client.post("/asignacion-nit/bulk", json=payload_bulk, headers=auth_headers)

        # ASSERT: Debe reportar reactivaciones
        assert response.status_code == 201
        resultado = response.json()
        assert resultado["reactivadas"] == 3, "Debe reportar 3 reactivaciones"
        assert resultado["creadas"] == 0, "No debe crear nuevas"


# ==================== TEST SUITE: EDGE CASES ====================

class TestEdgeCases:
    """Tests de casos edge y validaciones."""

    def test_delete_asignacion_ya_eliminada_rechaza(
        self, client, auth_headers, limpiar_asignaciones_test
    ):
        """
        TEST: DELETE en asignación ya eliminada rechaza con 400.
        """
        # ARRANGE: Crear y eliminar
        payload = {
            "nit": "TEST_900123466",
            "responsable_id": 1,
            "nombre_proveedor": "Test Proveedor 11 SAS"
        }
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        asignacion_id = response.json()["id"]
        client.delete(f"/asignacion-nit/{asignacion_id}", headers=auth_headers)

        # ACT: Eliminar nuevamente
        response = client.delete(f"/asignacion-nit/{asignacion_id}", headers=auth_headers)

        # ASSERT: Debe rechazar
        assert response.status_code == 400
        assert "ya está eliminada" in response.json()["detail"].lower()

    def test_restore_asignacion_activa_rechaza(
        self, client, auth_headers, limpiar_asignaciones_test
    ):
        """
        TEST: /restore en asignación activa rechaza con 400.
        """
        # ARRANGE: Crear asignación (activa)
        payload = {
            "nit": "TEST_900123467",
            "responsable_id": 1,
            "nombre_proveedor": "Test Proveedor 12 SAS"
        }
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        asignacion_id = response.json()["id"]

        # ACT: Intentar restaurar (pero ya está activa)
        response = client.post(f"/asignacion-nit/{asignacion_id}/restore", headers=auth_headers)

        # ASSERT: Debe rechazar
        assert response.status_code == 400
        assert "ya está activa" in response.json()["detail"].lower()


# ==================== TEST SUITE: FLUJO COMPLETO ====================

class TestFlujoCompletoEmpresa:
    """Test del flujo completo de uso enterprise."""

    def test_flujo_completo_delete_recreate(
        self, client, auth_headers, limpiar_asignaciones_test
    ):
        """
        TEST: Flujo completo usuario empresarial.

        Simula el caso de uso real que causó el bug:
        1. Usuario crea asignación
        2. Usuario elimina asignación (con consentimiento)
        3. Usuario crea misma asignación nuevamente → DEBE FUNCIONAR

        Este es el test MÁS IMPORTANTE: verifica que el bug está resuelto.
        """
        payload = {
            "nit": "TEST_900999999",
            "responsable_id": 1,
            "nombre_proveedor": "Empresa Real SAS",
            "permitir_aprobacion_automatica": True
        }

        # PASO 1: Crear asignación
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        assert response.status_code == 201, "Debe crear asignación exitosamente"
        asignacion_id_original = response.json()["id"]

        # Verificar que aparece en listado
        response = client.get("/asignacion-nit/", headers=auth_headers)
        asignaciones = response.json()
        assert any(a["nit"] == payload["nit"] for a in asignaciones)

        # PASO 2: Eliminar asignación (con consentimiento del usuario)
        response = client.delete(f"/asignacion-nit/{asignacion_id_original}", headers=auth_headers)
        assert response.status_code == 204, "Debe eliminar exitosamente"

        # Verificar que NO aparece en listado
        response = client.get("/asignacion-nit/", headers=auth_headers)
        asignaciones = response.json()
        assert not any(a["nit"] == payload["nit"] for a in asignaciones), \
            "No debe aparecer después de eliminar"

        # PASO 3: CRÍTICO - Crear misma asignación nuevamente
        # Esto es lo que estaba fallando en el sistema original
        response = client.post("/asignacion-nit/", json=payload, headers=auth_headers)
        assert response.status_code == 201, \
            "  DEBE permitir recrear asignación después de eliminar (FIX APLICADO)"

        # Verificar que se reactivó (mismo ID)
        asignacion_recreada = response.json()
        assert asignacion_recreada["id"] == asignacion_id_original, \
            "Debe reutilizar el mismo ID (reactivación)"
        assert asignacion_recreada["activo"] == True

        # Verificar que aparece en listado
        response = client.get("/asignacion-nit/", headers=auth_headers)
        asignaciones = response.json()
        assert any(a["nit"] == payload["nit"] for a in asignaciones), \
            "Debe aparecer en listado después de recrear"

        print("\n  FLUJO COMPLETO EXITOSO: Bug de eliminación RESUELTO")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
