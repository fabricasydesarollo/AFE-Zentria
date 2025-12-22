"""
Tests para Filtros Multi-Tenant en Facturas y Dashboard

Tests de integración para verificar:
- Filtrado automático por grupo para usuarios no-admin
- Filtrado explícito por grupo_id parameter
- Validación de acceso a grupos
- Aislamiento de datos entre grupos
- Endpoints de Dashboard con multi-tenant

Autor: Sistema AFE Backend
Fecha: 2025-12-03
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.grupo import Grupo, ResponsableGrupo
from app.models.usuario import Usuario
from app.models.role import Role
from app.models.factura import Factura, EstadoFactura
from app.models.proveedor import Proveedor


# ==================== FIXTURES ====================

@pytest.fixture
def auth_token_admin(db: Session):
    """Token admin para tests."""
    from app.core.security import create_access_token

    rol = db.query(Role).filter(Role.nombre == "admin").first()
    if not rol:
        rol = Role(nombre="admin")
        db.add(rol)
        db.commit()

    usuario = db.query(Usuario).filter(Usuario.email == "admin.multitenant@empresa.com").first()
    if not usuario:
        usuario = Usuario(
            usuario="admin.multitenant",
            email="admin.multitenant@empresa.com",
            nombre="Admin Multi-Tenant",
            hashed_password="hash",
            role_id=rol.id
        )
        db.add(usuario)
        db.commit()

    db.commit()
    db.refresh(usuario)
    token = create_access_token(usuario.usuario)
    return f"Bearer {token}"


@pytest.fixture
def usuario_no_admin_test(db: Session):
    """Usuario no-admin para tests de filtrado."""
    from app.core.security import create_access_token

    rol = db.query(Role).filter(Role.nombre == "responsable").first()
    if not rol:
        rol = Role(nombre="responsable")
        db.add(rol)
        db.commit()

    usuario = db.query(Usuario).filter(Usuario.email == "user.multitenant@empresa.com").first()
    if not usuario:
        usuario = Usuario(
            usuario="user.multitenant",
            email="user.multitenant@empresa.com",
            nombre="User Multi-Tenant",
            hashed_password="hash",
            role_id=rol.id
        )
        db.add(usuario)
        db.commit()

    db.commit()
    db.refresh(usuario)

    token = create_access_token(usuario.usuario)
    return {
        "usuario": usuario,
        "token": f"Bearer {token}"
    }


@pytest.fixture
def grupos_test(db: Session):
    """Crea dos grupos de prueba."""
    # Limpiar grupos previos
    db.query(Grupo).filter(Grupo.codigo_corto.in_(["TEST_MT_1", "TEST_MT_2"])).delete()
    db.commit()

    grupo1 = Grupo(
        nombre="GRUPO TEST 1",
        codigo_corto="TEST_MT_1",
        nivel=1,
        ruta_jerarquica="",
        correos_corporativos=[],
        activo=True,
        eliminado=False,
        creado_por="system_test"
    )
    grupo2 = Grupo(
        nombre="GRUPO TEST 2",
        codigo_corto="TEST_MT_2",
        nivel=1,
        ruta_jerarquica="",
        correos_corporativos=[],
        activo=True,
        eliminado=False,
        creado_por="system_test"
    )

    db.add(grupo1)
    db.add(grupo2)
    db.commit()  # commit necesario para TestClient
    db.refresh(grupo1)
    db.refresh(grupo2)

    return {"grupo1": grupo1, "grupo2": grupo2}


@pytest.fixture
def proveedor_test(db: Session):
    """Proveedor de prueba."""
    # Limpiar proveedor previo
    db.query(Proveedor).filter(Proveedor.nit == "900123456-7").delete()
    db.commit()

    proveedor = Proveedor(
        nit="900123456-7",
        razon_social="PROVEEDOR TEST MULTITENANT",
        contacto_email="proveedor@test.com"
    )
    db.add(proveedor)
    db.commit()  # commit necesario para TestClient
    db.refresh(proveedor)
    return proveedor


@pytest.fixture
def facturas_test(db: Session, grupos_test: dict, proveedor_test: Proveedor):
    """Crea facturas de prueba en diferentes grupos."""
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura

    # Limpiar workflows primero (foreign key constraint)
    db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.factura_id.in_(
            db.query(Factura.id).filter(Factura.numero_factura.like("TEST-MT-%"))
        )
    ).delete(synchronize_session=False)

    # Luego limpiar facturas
    db.query(Factura).filter(Factura.numero_factura.like("TEST-MT-%")).delete()
    db.commit()

    # Facturas del grupo 1
    facturas_g1 = []
    for i in range(3):
        factura = Factura(
            numero_factura=f"TEST-MT-G1-{i}",
            fecha_emision=datetime.now().date(),
            cufe=f"CUFE-TEST-MT-G1-{i}",
            proveedor_id=proveedor_test.id,
            grupo_id=grupos_test["grupo1"].id,
            estado=EstadoFactura.en_revision,
            subtotal=1000.0 * (i + 1),
            iva=190.0 * (i + 1),
            total_a_pagar=1190.0 * (i + 1)
        )
        db.add(factura)
        facturas_g1.append(factura)

    # Facturas del grupo 2
    facturas_g2 = []
    for i in range(2):
        factura = Factura(
            numero_factura=f"TEST-MT-G2-{i}",
            fecha_emision=datetime.now().date(),
            cufe=f"CUFE-TEST-MT-G2-{i}",
            proveedor_id=proveedor_test.id,
            grupo_id=grupos_test["grupo2"].id,
            estado=EstadoFactura.en_revision,
            subtotal=2000.0 * (i + 1),
            iva=380.0 * (i + 1),
            total_a_pagar=2380.0 * (i + 1)
        )
        db.add(factura)
        facturas_g2.append(factura)

    db.commit()  # commit necesario para TestClient

    return {"grupo1": facturas_g1, "grupo2": facturas_g2}


@pytest.fixture
def limpiar_datos_multitenant(db: Session):
    """Limpia datos de prueba multi-tenant."""
    # Los otros fixtures ya limpian sus propios datos con flush
    # Este fixture solo es un placeholder para el yield
    yield
    # El rollback de conftest.py limpiará todo


# ==================== TESTS DE FACTURAS MULTI-TENANT ====================

@pytest.mark.integration
def test_admin_puede_filtrar_por_grupo_especifico(
    client: TestClient,
    auth_token_admin: str,
    facturas_test: dict,
    grupos_test: dict,
    limpiar_datos_multitenant
):
    """Test: Admin puede filtrar facturas por grupo específico."""
    response = client.get(
        f"/api/v1/facturas/cursor?grupo_id={grupos_test['grupo1'].id}&limit=100",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()

    # Debe retornar solo facturas del grupo 1
    facturas = data["data"]
    assert len(facturas) == 3  # Las 3 facturas del grupo 1

    # Verificar que todas son del grupo 1
    for factura in facturas:
        assert factura["grupo_id"] == grupos_test["grupo1"].id


@pytest.mark.integration
def test_admin_sin_filtro_ve_todas_las_facturas(
    client: TestClient,
    auth_token_admin: str,
    facturas_test: dict,
    limpiar_datos_multitenant
):
    """Test: Admin sin filtro de grupo ve todas las facturas."""
    response = client.get(
        "/api/v1/facturas/cursor?limit=100",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()

    # Debe incluir facturas de ambos grupos
    facturas = data["data"]
    grupos_ids = {f["grupo_id"] for f in facturas if f["numero_factura"].startswith("TEST-MT-")}

    # Debe tener facturas de ambos grupos
    assert len(grupos_ids) == 2


@pytest.mark.integration
def test_usuario_no_admin_solo_ve_sus_grupos(
    client: TestClient,
    usuario_no_admin_test: dict,
    grupos_test: dict,
    facturas_test: dict,
    db: Session,
    limpiar_datos_multitenant
):
    """Test: Usuario no-admin solo ve facturas de sus grupos asignados."""
    # Asignar usuario solo al grupo 1
    asignacion = ResponsableGrupo(
        responsable_id=usuario_no_admin_test["usuario"].id,
        grupo_id=grupos_test["grupo1"].id,
        activo=True,
        asignado_por="system_test"
    )
    db.add(asignacion)
    db.commit()

    # Consultar facturas (sin especificar grupo_id)
    response = client.get(
        "/api/v1/facturas/cursor?limit=100",
        headers={"Authorization": usuario_no_admin_test["token"]}
    )

    assert response.status_code == 200
    data = response.json()

    # Debe ver solo facturas del grupo 1
    facturas = data["data"]
    facturas_test_mt = [f for f in facturas if f["numero_factura"].startswith("TEST-MT-")]

    # Solo facturas del grupo 1
    for factura in facturas_test_mt:
        assert factura["grupo_id"] == grupos_test["grupo1"].id


@pytest.mark.integration
def test_usuario_no_puede_acceder_grupo_no_asignado(
    client: TestClient,
    usuario_no_admin_test: dict,
    grupos_test: dict,
    facturas_test: dict,
    db: Session,
    limpiar_datos_multitenant
):
    """Test: Usuario no puede acceder a grupo no asignado."""
    # Asignar usuario solo al grupo 1
    asignacion = ResponsableGrupo(
        responsable_id=usuario_no_admin_test["usuario"].id,
        grupo_id=grupos_test["grupo1"].id,
        activo=True,
        asignado_por="system_test"
    )
    db.add(asignacion)
    db.commit()

    # Intentar acceder al grupo 2
    response = client.get(
        f"/api/v1/facturas/cursor?grupo_id={grupos_test['grupo2'].id}&limit=100",
        headers={"Authorization": usuario_no_admin_test["token"]}
    )

    assert response.status_code == 403
    assert "no tiene acceso" in response.json()["detail"].lower()


# ==================== TESTS DE DASHBOARD MULTI-TENANT ====================

@pytest.mark.integration
def test_dashboard_mes_actual_con_filtro_grupo(
    client: TestClient,
    auth_token_admin: str,
    grupos_test: dict,
    facturas_test: dict,
    limpiar_datos_multitenant
):
    """Test: Dashboard mes actual filtra por grupo correctamente."""
    response = client.get(
        f"/api/v1/dashboard/mes-actual?grupo_id={grupos_test['grupo1'].id}",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()

    # Verificar que facturas son solo del grupo 1
    facturas = data["facturas"]
    facturas_test_mt = [f for f in facturas if f["numero_factura"].startswith("TEST-MT-")]

    for factura in facturas_test_mt:
        assert factura["grupo_id"] == grupos_test["grupo1"].id


@pytest.mark.integration
def test_dashboard_historico_con_filtro_grupo(
    client: TestClient,
    auth_token_admin: str,
    grupos_test: dict,
    facturas_test: dict,
    limpiar_datos_multitenant
):
    """Test: Dashboard histórico filtra por grupo correctamente."""
    mes_actual = datetime.now().month
    anio_actual = datetime.now().year

    response = client.get(
        f"/api/v1/dashboard/historico?mes={mes_actual}&anio={anio_actual}&grupo_id={grupos_test['grupo2'].id}",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()

    # Verificar que facturas son solo del grupo 2
    facturas = data["facturas"]
    facturas_test_mt = [f for f in facturas if f["numero_factura"].startswith("TEST-MT-")]

    for factura in facturas_test_mt:
        assert factura["grupo_id"] == grupos_test["grupo2"].id


@pytest.mark.integration
def test_alerta_mes_con_filtro_grupo(
    client: TestClient,
    auth_token_admin: str,
    grupos_test: dict,
    facturas_test: dict,
    limpiar_datos_multitenant
):
    """Test: Alerta de mes filtra por grupo correctamente."""
    response = client.get(
        f"/api/v1/dashboard/alerta-mes?grupo_id={grupos_test['grupo1'].id}",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()

    # Debe retornar datos de alerta (estructura válida)
    assert "mostrar_alerta" in data
    assert "dias_restantes" in data
    assert "facturas_pendientes" in data


# ==================== TESTS DE ENDPOINT /ALL ====================

@pytest.mark.integration
def test_endpoint_all_con_filtro_grupo(
    client: TestClient,
    auth_token_admin: str,
    grupos_test: dict,
    facturas_test: dict,
    limpiar_datos_multitenant
):
    """Test: Endpoint /all filtra por grupo correctamente."""
    response = client.get(
        f"/api/v1/facturas/all?grupo_id={grupos_test['grupo1'].id}",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    facturas = response.json()

    # Filtrar solo facturas de prueba
    facturas_test_mt = [f for f in facturas if f["numero_factura"].startswith("TEST-MT-")]

    # Debe tener exactamente las 3 facturas del grupo 1
    assert len(facturas_test_mt) == 3

    # Todas deben ser del grupo 1
    for factura in facturas_test_mt:
        assert factura["grupo_id"] == grupos_test["grupo1"].id


# ==================== TESTS DE AISLAMIENTO DE DATOS ====================

@pytest.mark.integration
def test_aislamiento_completo_entre_grupos(
    client: TestClient,
    usuario_no_admin_test: dict,
    grupos_test: dict,
    facturas_test: dict,
    db: Session,
    limpiar_datos_multitenant
):
    """Test: Usuarios de diferentes grupos no ven datos de otros grupos."""
    # Asignar usuario solo al grupo 2
    asignacion = ResponsableGrupo(
        responsable_id=usuario_no_admin_test["usuario"].id,
        grupo_id=grupos_test["grupo2"].id,
        activo=True,
        asignado_por="system_test"
    )
    db.add(asignacion)
    db.commit()

    # Obtener facturas
    response = client.get(
        "/api/v1/facturas/all",
        headers={"Authorization": usuario_no_admin_test["token"]}
    )

    assert response.status_code == 200
    facturas = response.json()

    # Filtrar solo facturas de prueba
    facturas_test_mt = [f for f in facturas if f["numero_factura"].startswith("TEST-MT-")]

    # NO debe ver ninguna factura del grupo 1
    for factura in facturas_test_mt:
        assert factura["grupo_id"] != grupos_test["grupo1"].id
        assert factura["grupo_id"] == grupos_test["grupo2"].id
