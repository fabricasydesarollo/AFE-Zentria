"""
Tests para endpoints de Grupos - Sistema Multi-Tenant

Tests de integración para:
- CRUD de grupos
- Jerarquía de grupos
- Validaciones de negocio
- Soft delete
- Control de acceso


"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.grupo import Grupo, ResponsableGrupo
from app.models.usuario import Usuario
from app.models.role import Role


# ==================== FIXTURES ESPECÍFICOS ====================

@pytest.fixture
def auth_token_admin(db: Session):
    """Token de autenticación para usuario admin."""
    # Buscar o crear rol admin
    rol = db.query(Role).filter(Role.nombre == "admin").first()
    if not rol:
        rol = Role(nombre="admin")
        db.add(rol)
        db.flush()

    # Buscar o crear usuario admin
    usuario = db.query(Usuario).filter(
        Usuario.email == "admin.test@empresa.com"
    ).first()

    if not usuario:
        usuario = Usuario(
            usuario="admin.test",
            email="admin.test@empresa.com",
            nombre="Admin Test",
            hashed_password="hash",
            role_id=rol.id
        )
        db.add(usuario)
        db.flush()

    db.commit()
    db.refresh(usuario)

    from app.core.security import create_access_token
    token = create_access_token(usuario.usuario)
    return f"Bearer {token}"


@pytest.fixture
def grupo_test(db: Session, limpiar_grupos_test):
    """Grupo de prueba raíz."""
    grupo = Grupo(
        nombre="GRUPO TEST RAIZ",
        codigo_corto="TEST_RAIZ",
        descripcion="Grupo de prueba raíz",
        nivel=1,
        ruta_jerarquica="",
        correos_corporativos=[],
        permite_subsedes=True,
        max_nivel_subsedes=3,
        activo=True,
        eliminado=False,
        creado_por="system_test"
    )
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


@pytest.fixture
def grupo_hijo_test(db: Session, grupo_test: Grupo, limpiar_grupos_test):
    """Grupo hijo de prueba."""
    grupo = Grupo(
        nombre="GRUPO TEST HIJO",
        codigo_corto="TEST_HIJO",
        descripcion="Grupo de prueba hijo",
        grupo_padre_id=grupo_test.id,
        nivel=2,
        ruta_jerarquica=f"{grupo_test.id}/",
        correos_corporativos=[],
        permite_subsedes=True,
        max_nivel_subsedes=2,
        activo=True,
        eliminado=False,
        creado_por="system_test"
    )
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


@pytest.fixture
def limpiar_grupos_test(db: Session):
    """Limpia grupos de prueba antes y después de cada test."""
    # Limpiar antes
    db.query(Grupo).filter(
        Grupo.codigo_corto.like("TEST_%")
    ).delete()
    db.commit()

    yield

    # Limpiar después
    db.query(Grupo).filter(
        Grupo.codigo_corto.like("TEST_%")
    ).delete()
    db.commit()


# ==================== TESTS DE CRUD ====================

@pytest.mark.integration
def test_crear_grupo_raiz(client: TestClient, auth_token_admin: str, limpiar_grupos_test):
    """Test: Crear grupo raíz exitosamente."""
    response = client.post(
        "/api/v1/grupos/",
        json={
            "nombre": "GRUPO TEST NUEVO",
            "codigo_corto": "TEST_NUEVO",
            "descripcion": "Grupo de prueba nuevo",
            "permite_subsedes": True,
            "max_nivel_subsedes": 3,
            "activo": True
        },
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "GRUPO TEST NUEVO"
    assert data["codigo_corto"] == "TEST_NUEVO"
    assert data["nivel"] == 1
    assert data["grupo_padre_id"] is None
    assert data["activo"] is True
    assert data["eliminado"] is False


@pytest.mark.integration
def test_crear_grupo_hijo(client: TestClient, auth_token_admin: str, grupo_test: Grupo, limpiar_grupos_test):
    """Test: Crear grupo hijo de un grupo existente."""
    response = client.post(
        "/api/v1/grupos/",
        json={
            "nombre": "GRUPO TEST HIJO 2",
            "codigo_corto": "TEST_HIJO_2",
            "descripcion": "Grupo hijo de prueba",
            "grupo_padre_id": grupo_test.id,
            "permite_subsedes": True,
            "max_nivel_subsedes": 2,
            "activo": True
        },
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "GRUPO TEST HIJO 2"
    assert data["nivel"] == 2
    assert data["grupo_padre_id"] == grupo_test.id
    # Verificar que tiene ruta jerárquica (formato puede variar)
    assert data["ruta_jerarquica"] is not None
    assert len(data["ruta_jerarquica"]) > 0


@pytest.mark.integration
def test_crear_grupo_codigo_duplicado(client: TestClient, auth_token_admin: str, grupo_test: Grupo):
    """Test: No se puede crear grupo con código duplicado."""
    response = client.post(
        "/api/v1/grupos/",
        json={
            "nombre": "GRUPO DUPLICADO",
            "codigo_corto": grupo_test.codigo_corto,  # Código ya existe
            "descripcion": "Intentando duplicar",
            "activo": True
        },
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 400
    assert "ya existe" in response.json()["detail"].lower()


@pytest.mark.integration
def test_listar_grupos(client: TestClient, auth_token_admin: str, grupo_test: Grupo, grupo_hijo_test: Grupo):
    """Test: Listar grupos con paginación."""
    response = client.get(
        "/api/v1/grupos/?skip=0&limit=100",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "grupos" in data
    assert data["total"] >= 2  # Al menos los 2 grupos de prueba


@pytest.mark.integration
def test_obtener_grupo_por_id(client: TestClient, auth_token_admin: str, grupo_test: Grupo):
    """Test: Obtener grupo específico por ID."""
    response = client.get(
        f"/api/v1/grupos/{grupo_test.id}",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == grupo_test.id
    assert data["codigo_corto"] == grupo_test.codigo_corto
    assert data["nombre"] == grupo_test.nombre


@pytest.mark.integration
def test_actualizar_grupo(client: TestClient, auth_token_admin: str, grupo_test: Grupo):
    """Test: Actualizar datos de un grupo."""
    response = client.put(
        f"/api/v1/grupos/{grupo_test.id}",
        json={
            "nombre": "GRUPO TEST ACTUALIZADO",
            "descripcion": "Descripción actualizada"
        },
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "GRUPO TEST ACTUALIZADO"
    assert data["descripcion"] == "Descripción actualizada"


@pytest.mark.integration
def test_soft_delete_grupo(client: TestClient, auth_token_admin: str, grupo_test: Grupo):
    """Test: Soft delete de grupo sin hijos."""
    response = client.delete(
        f"/api/v1/grupos/{grupo_test.id}",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["eliminado"] is True
    assert data["activo"] is False
    assert data["fecha_eliminacion"] is not None


@pytest.mark.integration
def test_restaurar_grupo(client: TestClient, auth_token_admin: str, grupo_test: Grupo, db: Session):
    """Test: Restaurar grupo eliminado."""
    # Primero eliminar el grupo
    grupo_test.eliminado = True
    grupo_test.activo = False
    db.commit()

    # Luego restaurar
    response = client.post(
        f"/api/v1/grupos/{grupo_test.id}/restore",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["eliminado"] is False
    assert data["activo"] is True
    assert data["fecha_eliminacion"] is None


# ==================== TESTS DE JERARQUÍA ====================

@pytest.mark.integration
def test_listar_grupos_raiz(client: TestClient, auth_token_admin: str, grupo_test: Grupo):
    """Test: Listar solo grupos raíz (nivel 1)."""
    response = client.get(
        "/api/v1/grupos/raiz?activos_only=true",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Todos los grupos deben ser nivel 1
    for grupo in data:
        assert grupo["nivel"] == 1
        assert grupo["grupo_padre_id"] is None


@pytest.mark.integration
def test_listar_hijos_de_grupo(client: TestClient, auth_token_admin: str, grupo_test: Grupo, grupo_hijo_test: Grupo):
    """Test: Listar hijos directos de un grupo."""
    response = client.get(
        f"/api/v1/grupos/{grupo_test.id}/hijos?activos_only=true",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Verificar que al menos incluye al grupo hijo de prueba
    hijo_ids = [g["id"] for g in data]
    assert grupo_hijo_test.id in hijo_ids


@pytest.mark.integration
def test_obtener_arbol_jerarquico(client: TestClient, auth_token_admin: str, grupo_test: Grupo, grupo_hijo_test: Grupo):
    """Test: Obtener árbol jerárquico completo."""
    response = client.get(
        "/api/v1/grupos/arbol",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Debe incluir tanto padres como hijos
    grupo_ids = [g["id"] for g in data]
    assert grupo_test.id in grupo_ids
    assert grupo_hijo_test.id in grupo_ids


# ==================== TESTS DE VALIDACIONES ====================

@pytest.mark.integration
def test_crear_grupo_sin_autenticacion(client: TestClient, limpiar_grupos_test):
    """Test: No se puede crear grupo sin autenticación."""
    response = client.post(
        "/api/v1/grupos/",
        json={
            "nombre": "GRUPO SIN AUTH",
            "codigo_corto": "TEST_NO_AUTH",
            "activo": True
        }
    )

    assert response.status_code == 401


@pytest.mark.integration
def test_crear_grupo_sin_permisos(client: TestClient, auth_token_responsable: str, limpiar_grupos_test):
    """Test: Usuario responsable no puede crear grupos."""
    response = client.post(
        "/api/v1/grupos/",
        json={
            "nombre": "GRUPO SIN PERMISOS",
            "codigo_corto": "TEST_NO_PERM",
            "activo": True
        },
        headers={"Authorization": auth_token_responsable}
    )

    assert response.status_code == 403


@pytest.mark.integration
def test_no_puede_eliminar_grupo_con_hijos_activos(client: TestClient, auth_token_admin: str, grupo_test: Grupo, grupo_hijo_test: Grupo):
    """Test: No se puede eliminar grupo con hijos activos."""
    response = client.delete(
        f"/api/v1/grupos/{grupo_test.id}",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 400
    assert "subsedes activas" in response.json()["detail"].lower()
