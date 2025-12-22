"""
Configuración central de pytest y fixtures compartidas para todos los tests.

Proporciona:
- Cliente HTTP de prueba
- Sesión de base de datos de prueba
- Autenticación de usuarios de prueba
- Limpieza automática de datos
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db, SessionLocal
from app.core.security import create_access_token
from app.models.usuario import Usuario
from app.models.role import Role


# ==================== FIXTURES GLOBALES ====================

@pytest.fixture
def client():
    """Cliente HTTP para pruebas de endpoints."""
    return TestClient(app)


@pytest.fixture
def db():
    """Sesión de base de datos para pruebas.

    Proporciona una sesión de prueba con rollback automático
    después de cada test para mantener la BD limpia.
    """
    # Obtener sesión
    session = SessionLocal()

    yield session

    # Rollback automático después del test
    session.rollback()
    session.close()


@pytest.fixture
def auth_token_contador(db: Session):
    """Token de autenticación para usuario contador.

    Crea o recupera un usuario contador de prueba y devuelve
    un token JWT válido para usar en headers.
    """
    # Buscar o crear rol contador
    rol = db.query(Role).filter(Role.nombre == "contador").first()
    if not rol:
        rol = Role(nombre="contador")
        db.add(rol)
        db.flush()

    # Buscar o crear usuario contador
    usuario = db.query(Usuario).filter(
        Usuario.email == "contador.test@empresa.com"
    ).first()

    if not usuario:
        usuario = Usuario(
            usuario="contador.test",
            email="contador.test@empresa.com",
            nombre="Contador Test",
            hashed_password="hash",  # En tests, la contraseña no se valida
            role_id=rol.id
        )
        db.add(usuario)
        db.flush()

    db.commit()
    db.refresh(usuario)

    # Generar token
    token = create_access_token(usuario.usuario)
    return f"Bearer {token}"


@pytest.fixture
def auth_token_responsable(db: Session):
    """Token de autenticación para usuario responsable.

    Devuelve un token para un usuario con rol responsable.
    """
    # Buscar o crear rol responsable
    rol = db.query(Role).filter(Role.nombre == "responsable").first()
    if not rol:
        rol = Role(nombre="responsable")
        db.add(rol)
        db.flush()

    # Buscar o crear usuario responsable
    usuario = db.query(Usuario).filter(
        Usuario.email == "responsable.test@empresa.com"
    ).first()

    if not usuario:
        usuario = Usuario(
            usuario="responsable.test",
            email="responsable.test@empresa.com",
            nombre="Usuario Test",
            hashed_password="hash",
            role_id=rol.id
        )
        db.add(usuario)
        db.flush()

    db.commit()
    db.refresh(usuario)

    # Generar token
    token = create_access_token(usuario.usuario)
    return f"Bearer {token}"


@pytest.fixture
def limpiar_facturas_test(db: Session):
    """Limpia facturas de prueba antes y después de cada test.

    Busca y elimiza todas las facturas con números que comienzan con "TEST-"
    para garantizar estado limpio.
    """
    from app.models.factura import Factura

    # Limpiar antes
    db.query(Factura).filter(
        Factura.numero_factura.like("TEST-%")
    ).delete()
    db.commit()

    yield

    # Limpiar después
    db.query(Factura).filter(
        Factura.numero_factura.like("TEST-%")
    ).delete()
    db.commit()


# ==================== CONFIGURACIÓN DE PYTEST ====================

def pytest_configure(config):
    """Configuración inicial de pytest.

    Define marcadores personalizados para categorizar tests.
    """
    config.addinivalue_line(
        "markers",
        "integration: pruebas de integración (requieren BD real)"
    )
    config.addinivalue_line(
        "markers",
        "unit: pruebas unitarias (pueden usar mocks)"
    )
    config.addinivalue_line(
        "markers",
        "slow: pruebas que tardan más tiempo"
    )
    config.addinivalue_line(
        "markers",
        "payment: pruebas del sistema de pagos"
    )
