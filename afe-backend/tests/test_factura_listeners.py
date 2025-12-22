"""
Test Suite: Event Listeners de Factura

Verifica que la sincronización automática de accion_por funciona correctamente.

Casos de prueba:
1. Cambio de responsable_id → actualiza accion_por
2. Cambio de estado a 'aprobada_auto' → accion_por = 'Sistema Automático'
3. Cambio de estado a 'aprobada' → accion_por = nombre del responsable
4. Cambio de estado a 'en_revision' → accion_por = NULL

Fecha: 2025-12-15
"""

import pytest
from sqlalchemy.orm import Session
from app.models.factura import Factura, EstadoFactura
from app.models.usuario import Usuario
from app.models.role import Role
from datetime import date, datetime
from decimal import Decimal


@pytest.fixture
def test_usuario(db: Session):
    """Crea un usuario de prueba."""
    role = db.query(Role).filter(Role.nombre == "responsable").first()
    if not role:
        role = Role(nombre="responsable", descripcion="Responsable de facturas")
        db.add(role)
        db.commit()

    usuario = Usuario(
        usuario="test_listener",
        nombre="Test Listener User",
        email="test.listener@example.com",
        hashed_password="dummy_hash",
        role_id=role.id,
        activo=True
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@pytest.fixture
def test_factura(db: Session):
    """Crea una factura de prueba."""
    factura = Factura(
        numero_factura=f"TEST-LISTENER-{datetime.now().timestamp()}",
        cufe="CUFE-TEST-LISTENER",
        nit_emisor="900123456",
        nombre_emisor="Proveedor Test",
        total_a_pagar=Decimal("1000000.00"),
        fecha_emision=date.today(),
        estado=EstadoFactura.en_revision,
        accion_por=None  # Inicialmente vacío
    )
    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura


class TestFacturaListeners:
    """Tests para event listeners de sincronización automática."""

    def test_aprobacion_automatica_asigna_sistema_automatico(
        self,
        db: Session,
        test_factura: Factura
    ):
        """
        TEST 1: Al cambiar estado a 'aprobada_auto',
        accion_por debe ser 'Sistema Automático' automáticamente.
        """
        # ANTES: factura en revisión sin accion_por
        assert test_factura.estado == EstadoFactura.en_revision
        assert test_factura.accion_por is None

        # ACCIÓN: Cambiar a aprobada_auto
        test_factura.estado = EstadoFactura.aprobada_auto
        db.commit()
        db.refresh(test_factura)

        # VERIFICAR: accion_por debe ser 'Sistema Automático'
        assert test_factura.accion_por == 'Sistema Automático', (
            f"accion_por debería ser 'Sistema Automático', "
            f"pero es: {test_factura.accion_por}"
        )

    def test_aprobacion_manual_asigna_nombre_responsable(
        self,
        db: Session,
        test_factura: Factura,
        test_usuario: Usuario
    ):
        """
        TEST 2: Al cambiar estado a 'aprobada' con responsable_id,
        accion_por debe ser el nombre del responsable.
        """
        # CONFIGURAR: Asignar responsable
        test_factura.responsable_id = test_usuario.id
        db.commit()

        # ACCIÓN: Cambiar a aprobada
        test_factura.estado = EstadoFactura.aprobada
        db.commit()
        db.refresh(test_factura)

        # VERIFICAR: accion_por debe ser el nombre del usuario
        assert test_factura.accion_por == test_usuario.nombre, (
            f"accion_por debería ser '{test_usuario.nombre}', "
            f"pero es: {test_factura.accion_por}"
        )

    def test_cambio_responsable_actualiza_accion_por(
        self,
        db: Session,
        test_factura: Factura,
        test_usuario: Usuario
    ):
        """
        TEST 3: Al cambiar responsable_id en una factura aprobada,
        accion_por debe actualizarse con el nuevo responsable.
        """
        # CONFIGURAR: Factura aprobada con un responsable
        test_factura.responsable_id = test_usuario.id
        test_factura.estado = EstadoFactura.aprobada
        db.commit()
        db.refresh(test_factura)

        # VERIFICAR estado inicial
        assert test_factura.accion_por == test_usuario.nombre

        # CREAR segundo usuario
        role = db.query(Role).filter(Role.nombre == "responsable").first()
        nuevo_usuario = Usuario(
            usuario="test_listener_2",
            nombre="Nuevo Responsable",
            email="nuevo.responsable@example.com",
            hashed_password="dummy_hash",
            role_id=role.id,
            activo=True
        )
        db.add(nuevo_usuario)
        db.commit()

        # ACCIÓN: Cambiar responsable
        test_factura.responsable_id = nuevo_usuario.id
        db.commit()
        db.refresh(test_factura)

        # VERIFICAR: accion_por debe actualizarse
        assert test_factura.accion_por == nuevo_usuario.nombre, (
            f"accion_por debería ser '{nuevo_usuario.nombre}', "
            f"pero es: {test_factura.accion_por}"
        )

    def test_cambio_a_revision_limpia_accion_por(
        self,
        db: Session,
        test_factura: Factura,
        test_usuario: Usuario
    ):
        """
        TEST 4: Al cambiar estado a 'en_revision',
        accion_por debe limpiarse (NULL).
        """
        # CONFIGURAR: Factura aprobada con accion_por
        test_factura.responsable_id = test_usuario.id
        test_factura.estado = EstadoFactura.aprobada
        db.commit()
        db.refresh(test_factura)

        # VERIFICAR estado inicial
        assert test_factura.accion_por == test_usuario.nombre

        # ACCIÓN: Devolver a revisión
        test_factura.estado = EstadoFactura.en_revision
        db.commit()
        db.refresh(test_factura)

        # VERIFICAR: accion_por debe ser NULL
        assert test_factura.accion_por is None, (
            f"accion_por debería ser NULL en estado 'en_revision', "
            f"pero es: {test_factura.accion_por}"
        )

    def test_rechazo_asigna_nombre_responsable(
        self,
        db: Session,
        test_factura: Factura,
        test_usuario: Usuario
    ):
        """
        TEST 5: Al cambiar estado a 'rechazada' con responsable_id,
        accion_por debe ser el nombre del responsable.
        """
        # CONFIGURAR: Asignar responsable
        test_factura.responsable_id = test_usuario.id
        db.commit()

        # ACCIÓN: Rechazar factura
        test_factura.estado = EstadoFactura.rechazada
        db.commit()
        db.refresh(test_factura)

        # VERIFICAR: accion_por debe ser el nombre del usuario
        assert test_factura.accion_por == test_usuario.nombre, (
            f"accion_por debería ser '{test_usuario.nombre}', "
            f"pero es: {test_factura.accion_por}"
        )

    def test_insert_aprobada_auto_asigna_sistema_automatico(
        self,
        db: Session
    ):
        """
        TEST 6: Al crear (INSERT) una factura con estado 'aprobada_auto',
        accion_por debe ser 'Sistema Automático' automáticamente.
        """
        # ACCIÓN: Crear factura directamente como aprobada_auto
        factura = Factura(
            numero_factura=f"TEST-INSERT-{datetime.now().timestamp()}",
            cufe="CUFE-TEST-INSERT",
            nit_emisor="900123456",
            nombre_emisor="Proveedor Test",
            total_a_pagar=Decimal("1000000.00"),
            fecha_emision=date.today(),
            estado=EstadoFactura.aprobada_auto,
            accion_por=None  # Inicialmente vacío
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)

        # VERIFICAR: accion_por debe ser 'Sistema Automático'
        assert factura.accion_por == 'Sistema Automático', (
            f"Al crear factura con estado 'aprobada_auto', "
            f"accion_por debería ser 'Sistema Automático', "
            f"pero es: {factura.accion_por}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
