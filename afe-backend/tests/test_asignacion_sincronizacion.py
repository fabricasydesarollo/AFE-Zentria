"""
Tests de integración para sincronización Asignaciones ↔ Facturas

NIVEL EMPRESARIAL: Garantiza que la sincronización funcione correctamente
"""
import pytest
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import Factura, AsignacionNitResponsable, Proveedor, Usuario


class TestAsignacionSincronizacion:
    """Tests de sincronización automática entre asignaciones y facturas."""

    @pytest.fixture
    def db(self) -> Session:
        """Fixture de base de datos."""
        db = SessionLocal()
        yield db
        db.close()

    def test_crear_asignacion_asigna_facturas_automaticamente(self, db: Session):
        """
        TEST CRÍTICO: Al crear asignación, facturas deben asignarse automáticamente.

        Escenario:
        1. Hay facturas sin responsable para un NIT
        2. Se crea asignación NIT → Usuario
        3. Las facturas deben asignarse automáticamente al responsable
        """
        # Arrange: Buscar un NIT con facturas sin responsable
        nit_test = "800185449"  # AVIDANTI S.A.S.
        responsable_id = 1  # Alexander

        # Limpiar facturas de prueba
        proveedores = db.query(Proveedor).filter(
            Proveedor.nit.like(f'{nit_test}%')
        ).all()

        for proveedor in proveedores:
            db.query(Factura).filter(
                Factura.proveedor_id == proveedor.id
            ).update({Factura.responsable_id: None})

        db.commit()

        # Verificar estado inicial
        facturas_sin_responsable_antes = db.query(Factura).join(Proveedor).filter(
            Proveedor.nit.like(f'{nit_test}%'),
            Factura.responsable_id.is_(None)
        ).count()

        assert facturas_sin_responsable_antes > 0, "Debe haber facturas sin responsable para probar"

        # Act: Crear asignación
        asignacion = AsignacionNitResponsable(
            nit=nit_test,
            responsable_id=responsable_id,
            activo=True
        )
        db.add(asignacion)
        db.commit()

        # Refrescar para obtener cambios
        db.expire_all()

        # Assert: Verificar que facturas se asignaron
        facturas_asignadas = db.query(Factura).filter(
            Factura.responsable_id == responsable_id
        ).join(Proveedor).filter(
            Proveedor.nit.like(f'{nit_test}%')
        ).count()

        assert facturas_asignadas == facturas_sin_responsable_antes, \
            f"Todas las {facturas_sin_responsable_antes} facturas deben asignarse al responsable"

        # Cleanup
        db.delete(asignacion)
        db.commit()

    def test_eliminar_asignacion_desasigna_facturas_automaticamente(self, db: Session):
        """
        TEST CRÍTICO: Al eliminar asignación, facturas deben desasignarse automáticamente.

        Escenario:
        1. Hay asignación activa con facturas asignadas
        2. Se marca asignación como inactiva (soft delete)
        3. Las facturas deben perder su responsable_id automáticamente
        """
        # Arrange: Crear asignación y asignar facturas
        nit_test = "800185449"
        responsable_id = 1

        asignacion = AsignacionNitResponsable(
            nit=nit_test,
            responsable_id=responsable_id,
            activo=True
        )
        db.add(asignacion)
        db.commit()

        # Asignar facturas manualmente para la prueba
        proveedores = db.query(Proveedor).filter(
            Proveedor.nit.like(f'{nit_test}%')
        ).all()

        for proveedor in proveedores:
            db.query(Factura).filter(
                Factura.proveedor_id == proveedor.id
            ).update({Factura.responsable_id: responsable_id})

        db.commit()

        # Verificar estado inicial
        facturas_asignadas_antes = db.query(Factura).filter(
            Factura.responsable_id == responsable_id
        ).join(Proveedor).filter(
            Proveedor.nit.like(f'{nit_test}%')
        ).count()

        assert facturas_asignadas_antes > 0, "Debe haber facturas asignadas para probar"

        # Act: Soft delete de asignación
        asignacion.activo = False
        db.commit()

        # Refrescar para obtener cambios
        db.expire_all()

        # Assert: Verificar que facturas se desasignaron
        facturas_asignadas_despues = db.query(Factura).filter(
            Factura.responsable_id == responsable_id
        ).join(Proveedor).filter(
            Proveedor.nit.like(f'{nit_test}%')
        ).count()

        assert facturas_asignadas_despues == 0, \
            "Todas las facturas deben desasignarse al eliminar la asignación"

        # Cleanup
        db.delete(asignacion)
        db.commit()

    def test_restaurar_asignacion_reasigna_facturas_automaticamente(self, db: Session):
        """
        TEST CRÍTICO: Al restaurar asignación, facturas deben reasignarse automáticamente.

        Escenario:
        1. Hay asignación inactiva
        2. Se reactiva asignación (activo = True)
        3. Las facturas del NIT deben asignarse automáticamente
        """
        # Arrange: Crear asignación inactiva
        nit_test = "800185449"
        responsable_id = 1

        asignacion = AsignacionNitResponsable(
            nit=nit_test,
            responsable_id=responsable_id,
            activo=False  # Inactiva
        )
        db.add(asignacion)
        db.commit()

        # Verificar que facturas están sin responsable
        proveedores = db.query(Proveedor).filter(
            Proveedor.nit.like(f'{nit_test}%')
        ).all()

        for proveedor in proveedores:
            db.query(Factura).filter(
                Factura.proveedor_id == proveedor.id
            ).update({Factura.responsable_id: None})

        db.commit()

        # Act: Restaurar asignación
        asignacion.activo = True
        db.commit()

        # Refrescar para obtener cambios
        db.expire_all()

        # Assert: Verificar que facturas se reasignaron
        facturas_reasignadas = db.query(Factura).filter(
            Factura.responsable_id == responsable_id
        ).join(Proveedor).filter(
            Proveedor.nit.like(f'{nit_test}%')
        ).count()

        assert facturas_reasignadas > 0, \
            "Las facturas deben reasignarse al restaurar la asignación"

        # Cleanup
        db.delete(asignacion)
        db.commit()

    def test_no_hay_facturas_huerfanas_en_sistema(self, db: Session):
        """
        TEST DE INTEGRIDAD: No deben existir facturas con responsable_id sin asignación activa.

        Este test verifica que el sistema mantiene consistencia:
        - Si factura tiene responsable_id, debe existir asignación activa correspondiente
        """
        # Obtener todas las facturas con responsable
        facturas_asignadas = db.query(Factura).filter(
            Factura.responsable_id.isnot(None)
        ).all()

        facturas_huerfanas = []

        for factura in facturas_asignadas:
            # Verificar si existe asignación activa para este responsable
            asignaciones_activas = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.responsable_id == factura.responsable_id,
                AsignacionNitResponsable.activo == True
            ).count()

            if asignaciones_activas == 0:
                facturas_huerfanas.append(factura.id)

        assert len(facturas_huerfanas) == 0, \
            f"Encontradas {len(facturas_huerfanas)} facturas huérfanas (con responsable_id pero sin asignación activa): {facturas_huerfanas}"


# ============================================================================
# COMANDOS PARA EJECUTAR TESTS
# ============================================================================
# pytest tests/test_asignacion_sincronizacion.py -v
# pytest tests/test_asignacion_sincronizacion.py::TestAsignacionSincronizacion::test_crear_asignacion_asigna_facturas_automaticamente -v
# ============================================================================
