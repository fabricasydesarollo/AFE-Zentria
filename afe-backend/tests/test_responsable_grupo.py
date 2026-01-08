"""
Tests para Asignaciones Responsable-Grupo - Sistema Multi-Tenant

Tests de integración para:
- Asignación de usuarios a grupos
- Listado de responsables de un grupo
- Listado de grupos de un responsable
- Actualización de asignaciones
- Validaciones de seguridad


"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.grupo import Grupo, ResponsableGrupo
from app.models.usuario import Usuario
from app.models.role import Role


# ==================== FIXTURES ====================

@pytest.fixture
def auth_token_admin(db: Session):
    """Token de autenticación para usuario admin."""
    from app.core.security import create_access_token

    rol = db.query(Role).filter(Role.nombre == "admin").first()
    if not rol:
        rol = Role(nombre="admin")
        db.add(rol)
        db.commit()

    usuario = db.query(Usuario).filter(
        Usuario.email == "admin.asignacion@empresa.com"
    ).first()

    if not usuario:
        usuario = Usuario(
            usuario="admin.asignacion",
            email="admin.asignacion@empresa.com",
            nombre="Admin Asignación",
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
def usuario_test(db: Session):
    """Usuario de prueba para asignaciones."""
    usuario = db.query(Usuario).filter(
        Usuario.email == "usuario.test@empresa.com"
    ).first()

    if not usuario:
        # Obtener rol responsable
        rol = db.query(Role).filter(Role.nombre == "responsable").first()
        if not rol:
            rol = Role(nombre="responsable")
            db.add(rol)
            db.commit()

        usuario = Usuario(
            usuario="usuario.test",
            email="usuario.test@empresa.com",
            nombre="Usuario Test",
            hashed_password="hash",
            role_id=rol.id
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    return usuario


@pytest.fixture
def grupo_asignacion_test(db: Session):
    """Grupo para pruebas de asignación."""
    # Limpiar grupos previos
    db.query(Grupo).filter(Grupo.codigo_corto == "TEST_ASIG").delete()
    db.commit()

    grupo = Grupo(
        nombre="GRUPO ASIGNACION TEST",
        codigo_corto="TEST_ASIG",
        descripcion="Grupo para pruebas de asignación",
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
    db.commit()  # commit necesario para TestClient
    db.refresh(grupo)
    return grupo


@pytest.fixture
def limpiar_asignaciones_test(db: Session, grupo_asignacion_test: Grupo):
    """Limpia asignaciones de prueba DESPUÉS de crear el grupo."""
    # Limpiar asignaciones previas del grupo de prueba
    db.query(ResponsableGrupo).filter(
        ResponsableGrupo.grupo_id == grupo_asignacion_test.id
    ).delete()

    db.commit()

    yield

    # Limpiar después
    db.query(ResponsableGrupo).filter(
        ResponsableGrupo.asignado_por == "system_test"
    ).delete()

    db.query(Grupo).filter(
        Grupo.codigo_corto.like("TEST_ASIG%")
    ).delete()

    db.commit()


# ==================== TESTS DE ASIGNACIÓN ====================

@pytest.mark.integration
def test_asignar_responsable_a_grupo(
    client: TestClient,
    auth_token_admin: str,
    usuario_test: Usuario,
    grupo_asignacion_test: Grupo,
    limpiar_asignaciones_test
):
    """Test: Asignar usuario a grupo exitosamente."""
    response = client.post(
        f"/api/v1/grupos/{grupo_asignacion_test.id}/responsables",
        json={
            "responsable_id": usuario_test.id,
            "grupo_id": grupo_asignacion_test.id,
            "activo": True
        },
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["responsable_id"] == usuario_test.id
    assert data["grupo_id"] == grupo_asignacion_test.id
    assert data["activo"] is True
    assert data["asignado_por"] is not None


@pytest.mark.integration
def test_asignar_responsable_duplicado_reactiva(
    client: TestClient,
    auth_token_admin: str,
    usuario_test: Usuario,
    grupo_asignacion_test: Grupo,
    db: Session,
    limpiar_asignaciones_test
):
    """Test: Asignar usuario ya asignado pero inactivo lo reactiva."""
    # Crear asignación inactiva
    asignacion = ResponsableGrupo(
        responsable_id=usuario_test.id,
        grupo_id=grupo_asignacion_test.id,
        activo=False,
        asignado_por="system_test"
    )
    db.add(asignacion)
    db.commit()

    # Intentar asignar de nuevo (debe reactivar)
    response = client.post(
        f"/api/v1/grupos/{grupo_asignacion_test.id}/responsables",
        json={
            "responsable_id": usuario_test.id,
            "grupo_id": grupo_asignacion_test.id,
            "activo": True
        },
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["activo"] is True


@pytest.mark.integration
def test_asignar_a_grupo_inexistente(
    client: TestClient,
    auth_token_admin: str,
    usuario_test: Usuario,
    limpiar_asignaciones_test
):
    """Test: No se puede asignar a grupo que no existe."""
    response = client.post(
        "/api/v1/grupos/99999/responsables",
        json={
            "responsable_id": usuario_test.id,
            "grupo_id": 99999,
            "activo": True
        },
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 400
    assert "no encontrado" in response.json()["detail"].lower()


@pytest.mark.integration
def test_asignar_usuario_inexistente(
    client: TestClient,
    auth_token_admin: str,
    grupo_asignacion_test: Grupo,
    limpiar_asignaciones_test
):
    """Test: No se puede asignar usuario que no existe."""
    response = client.post(
        f"/api/v1/grupos/{grupo_asignacion_test.id}/responsables",
        json={
            "responsable_id": 99999,
            "grupo_id": grupo_asignacion_test.id,
            "activo": True
        },
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 400
    assert "no encontrado" in response.json()["detail"].lower()


# ==================== TESTS DE LISTADO ====================

@pytest.mark.integration
def test_listar_responsables_de_grupo(
    client: TestClient,
    auth_token_admin: str,
    usuario_test: Usuario,
    grupo_asignacion_test: Grupo,
    db: Session,
    limpiar_asignaciones_test
):
    """Test: Listar responsables asignados a un grupo."""
    # Crear asignación
    asignacion = ResponsableGrupo(
        responsable_id=usuario_test.id,
        grupo_id=grupo_asignacion_test.id,
        activo=True,
        asignado_por="system_test"
    )
    db.add(asignacion)
    db.commit()

    # Listar
    response = client.get(
        f"/api/v1/grupos/{grupo_asignacion_test.id}/responsables?activos_only=true",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Verificar que incluye información detallada
    asignacion_encontrada = next((a for a in data if a["responsable_id"] == usuario_test.id), None)
    assert asignacion_encontrada is not None
    assert asignacion_encontrada["responsable_nombre"] == usuario_test.nombre
    assert asignacion_encontrada["responsable_email"] == usuario_test.email
    assert asignacion_encontrada["grupo_nombre"] == grupo_asignacion_test.nombre


@pytest.mark.integration
def test_listar_grupos_de_responsable(
    client: TestClient,
    auth_token_admin: str,
    usuario_test: Usuario,
    grupo_asignacion_test: Grupo,
    db: Session,
    limpiar_asignaciones_test
):
    """Test: Listar grupos asignados a un responsable."""
    # Crear asignación
    asignacion = ResponsableGrupo(
        responsable_id=usuario_test.id,
        grupo_id=grupo_asignacion_test.id,
        activo=True,
        asignado_por="system_test"
    )
    db.add(asignacion)
    db.commit()

    # Listar
    response = client.get(
        f"/api/v1/grupos/responsables/{usuario_test.id}/grupos?activos_only=true",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Verificar que incluye el grupo de prueba
    grupo_encontrado = next((g for g in data if g["grupo_id"] == grupo_asignacion_test.id), None)
    assert grupo_encontrado is not None
    assert grupo_encontrado["grupo_nombre"] == grupo_asignacion_test.nombre


# ==================== TESTS DE ACTUALIZACIÓN ====================

@pytest.mark.integration
def test_actualizar_estado_asignacion(
    client: TestClient,
    auth_token_admin: str,
    usuario_test: Usuario,
    grupo_asignacion_test: Grupo,
    db: Session,
    limpiar_asignaciones_test
):
    """Test: Actualizar estado de una asignación."""
    # Crear asignación activa
    asignacion = ResponsableGrupo(
        responsable_id=usuario_test.id,
        grupo_id=grupo_asignacion_test.id,
        activo=True,
        asignado_por="system_test"
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)

    # Desactivar
    response = client.patch(
        f"/api/v1/grupos/asignaciones/{asignacion.id}",
        json={"activo": False},
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["activo"] is False


@pytest.mark.integration
def test_remover_responsable_de_grupo(
    client: TestClient,
    auth_token_admin: str,
    usuario_test: Usuario,
    grupo_asignacion_test: Grupo,
    db: Session,
    limpiar_asignaciones_test
):
    """Test: Remover (desactivar) responsable de un grupo."""
    # Crear asignación
    asignacion = ResponsableGrupo(
        responsable_id=usuario_test.id,
        grupo_id=grupo_asignacion_test.id,
        activo=True,
        asignado_por="system_test"
    )
    db.add(asignacion)
    db.commit()

    # Remover
    response = client.delete(
        f"/api/v1/grupos/{grupo_asignacion_test.id}/responsables/{usuario_test.id}",
        headers={"Authorization": auth_token_admin}
    )

    assert response.status_code == 204

    # Verificar que fue desactivada (rollback para ver cambios committed por el endpoint)
    db.rollback()  # Descartar transacción local para ver commits del endpoint
    asignacion_actualizada = db.query(ResponsableGrupo).filter(
        ResponsableGrupo.responsable_id == usuario_test.id,
        ResponsableGrupo.grupo_id == grupo_asignacion_test.id
    ).first()
    assert asignacion_actualizada is not None
    assert asignacion_actualizada.activo is False


# ==================== TESTS DE SEGURIDAD ====================

@pytest.mark.integration
def test_asignar_sin_autenticacion(
    client: TestClient,
    usuario_test: Usuario,
    grupo_asignacion_test: Grupo,
    limpiar_asignaciones_test
):
    """Test: No se puede asignar sin autenticación."""
    response = client.post(
        f"/api/v1/grupos/{grupo_asignacion_test.id}/responsables",
        json={
            "responsable_id": usuario_test.id,
            "grupo_id": grupo_asignacion_test.id,
            "activo": True
        }
    )

    assert response.status_code == 401


@pytest.mark.integration
def test_asignar_sin_permisos_admin(
    client: TestClient,
    auth_token_responsable: str,
    usuario_test: Usuario,
    grupo_asignacion_test: Grupo,
    limpiar_asignaciones_test
):
    """Test: Solo admin puede asignar responsables."""
    response = client.post(
        f"/api/v1/grupos/{grupo_asignacion_test.id}/responsables",
        json={
            "responsable_id": usuario_test.id,
            "grupo_id": grupo_asignacion_test.id,
            "activo": True
        },
        headers={"Authorization": auth_token_responsable}
    )

    assert response.status_code == 403
