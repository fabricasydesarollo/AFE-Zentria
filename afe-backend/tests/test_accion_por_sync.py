"""
Test para validar la sincronización automática de ACCION_POR.

ARQUITECTURA:
    - RESPONSABLE: quién está asignado a revisar (de asignaciones NIT)
    - ESTADO: estado actual de la factura
    - ACCION_POR: quién hizo el último cambio de estado (desde DB, sincronizado)

Este test garantiza que ACCION_POR siempre refleja quién aprobó/rechazó,
NUNCA es manual, y se sincroniza automáticamente desde workflow.
"""
import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.factura import Factura, EstadoFactura
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario
from app.models.workflow_aprobacion import (
    WorkflowAprobacionFactura,
    EstadoFacturaWorkflow,
    TipoAprobacion,
)
from app.services.workflow_automatico import WorkflowAutomaticoService
from app.crud.factura import list_facturas
from app.schemas.factura import FacturaRead


@pytest.fixture
def test_data(db: Session):
    """Crea datos de prueba para los tests."""
    # Crear proveedor
    proveedor = Proveedor(
        nit="123456789",
        razon_social="Test Proveedor SAS",
        email="test@proveedor.com",
    )
    db.add(proveedor)
    db.flush()

    # Crear responsables
    responsable1 = Usuario(
        nombre="Juan Perez",
        usuario="juan.perez",
        email="juan@empresa.com",
        area="TI",
    )
    responsable2 = Usuario(
        nombre="Maria Garcia",
        usuario="maria.garcia",
        email="maria@empresa.com",
        area="Finanzas",
    )
    db.add_all([responsable1, responsable2])
    db.flush()

    # Crear factura
    factura = Factura(
        numero_factura="FACT-2025-001",
        fecha_emision=datetime.now().date(),
        proveedor_id=proveedor.id,
        subtotal=Decimal("1000.00"),
        iva=Decimal("190.00"),
        total_a_pagar=Decimal("1190.00"),
        cufe="test-cufe-123",
        responsable_id=responsable1.id,
        estado=EstadoFactura.pendiente,
    )
    db.add(factura)
    db.flush()

    # Crear workflow
    workflow = WorkflowAprobacionFactura(
        factura_id=factura.id,
        nit_proveedor=proveedor.nit,
        responsable_id=responsable1.id,
        area_responsable="TI",
        estado=EstadoFacturaWorkflow.RECIBIDA,
        tipo_aprobacion=TipoAprobacion.MANUAL,
    )
    db.add(workflow)
    db.commit()

    return {
        "proveedor": proveedor,
        "responsable1": responsable1,
        "responsable2": responsable2,
        "factura": factura,
        "workflow": workflow,
    }


class TestAccionPorSync:
    """Tests para validar sincronización de ACCION_POR."""

    def test_accion_por_sincroniza_en_aprobacion_manual(self, db: Session, test_data):
        """
        TEST 1: Verificar que accion_por se sincroniza automáticamente
        cuando se aprueba una factura manualmente.

        ESCENARIO:
            1. Factura en estado PENDIENTE
            2. Usuario aprueba manualmente
            3. accion_por debe = nombre del usuario (Juan Perez)
        """
        factura = test_data["factura"]
        workflow = test_data["workflow"]
        responsable = test_data["responsable1"]

        # Ejecutar aprobación manual
        servicio = WorkflowAutomaticoService(db)
        resultado = servicio.aprobar_manual(
            workflow_id=workflow.id,
            aprobado_por=responsable.nombre,
            observaciones="Aprobada por test",
        )

        # Verificar resultado
        assert resultado["estado"] == EstadoFacturaWorkflow.APROBADA_MANUAL.value

        # Actualizar referencias desde DB
        db.refresh(factura)

        # VALIDAR: accion_por debe ser sincronizado automáticamente
        assert (
            factura.accion_por == responsable.nombre
        ), f"accion_por={factura.accion_por}, esperado={responsable.nombre}"
        assert (
            factura.estado == EstadoFactura.aprobada
        ), f"estado={factura.estado}, esperado=aprobada"
        assert (
            factura.aprobado_por == responsable.nombre
        ), "aprobado_por no se sincronizó"

    def test_accion_por_sincroniza_en_rechazo(self, db: Session, test_data):
        """
        TEST 2: Verificar que accion_por se sincroniza en rechazo.

        ESCENARIO:
            1. Factura en estado PENDIENTE
            2. Usuario rechaza la factura
            3. accion_por debe = nombre del usuario (Maria Garcia)
        """
        factura = test_data["factura"]
        workflow = test_data["workflow"]
        responsable = test_data["responsable2"]

        # Ejecutar rechazo
        servicio = WorkflowAutomaticoService(db)
        resultado = servicio.rechazar(
            workflow_id=workflow.id,
            rechazado_por=responsable.nombre,
            motivo="Validación fallida",
            detalle="Items no coinciden",
        )

        # Verificar resultado
        assert resultado["estado"] == EstadoFacturaWorkflow.RECHAZADA.value

        # Actualizar referencias desde DB
        db.refresh(factura)

        # VALIDAR: accion_por debe ser sincronizado automáticamente
        assert (
            factura.accion_por == responsable.nombre
        ), f"accion_por={factura.accion_por}, esperado={responsable.nombre}"
        assert (
            factura.estado == EstadoFactura.rechazada
        ), f"estado={factura.estado}, esperado=rechazada"
        assert (
            factura.rechazado_por == responsable.nombre
        ), "rechazado_por no se sincronizó"

    def test_accion_por_se_sincroniza_automaticamente_no_manual(
        self, db: Session, test_data
    ):
        """
        TEST 3: Verificar que accion_por NUNCA es asignado manualmente.

        REGLA EMPRESARIAL CRÍTICA:
            - accion_por se sincroniza SIEMPRE desde workflow
            - Si cambias usuario, accion_por debe reflejar el usuario actual
            - No hay campo manual en el formulario

        VALIDACIÓN:
            1. Actualizar factura.accion_por manualmente (simular hack)
            2. Aprobar factura con usuario diferente
            3. accion_por debe ser SOBRESCRITO con el usuario actual
        """
        factura = test_data["factura"]
        workflow = test_data["workflow"]
        responsable1 = test_data["responsable1"]
        responsable2 = test_data["responsable2"]

        # Intentar contaminar el dato (simular manipulación manual)
        factura.accion_por = "USUARIO_HACKEADO"
        db.commit()

        # Ejecutar aprobación legítima con otro usuario
        servicio = WorkflowAutomaticoService(db)
        resultado = servicio.aprobar_manual(
            workflow_id=workflow.id,
            aprobado_por=responsable2.nombre,  # Diferente al responsable original
            observaciones="Aprobada por usuario 2",
        )

        # Actualizar referencias desde DB
        db.refresh(factura)

        # VALIDAR: accion_por debe ser SOBRESCRITO con el nuevo usuario
        assert (
            factura.accion_por == responsable2.nombre
        ), f"accion_por NO fue sobrescrito. Valor: {factura.accion_por}"
        assert (
            factura.accion_por != "USUARIO_HACKEADO"
        ), "accion_por fue mantenido de manipulación previa"

    def test_accion_por_en_aprobacion_automatica(self, db: Session, test_data):
        """
        TEST 4: Verificar que accion_por se asigna correctamente
        para aprobaciones automáticas.

        ESCENARIO:
            1. Factura cumple criterios de aprobación automática
            2. sistema_aprobador automático ejecuta aprobación
            3. accion_por debe = "SISTEMA DE AUTOMATIZACIÓN"
        """
        factura = test_data["factura"]
        workflow = test_data["workflow"]

        # Configurar factura para aprobación automática
        factura.confianza_automatica = Decimal("0.98")
        db.commit()

        # Ejecutar aprobación automática
        servicio = WorkflowAutomaticoService(db)
        resultado = servicio._aprobar_automaticamente(
            workflow=workflow, factura=factura
        )

        # Actualizar referencias desde DB
        db.refresh(factura)

        # VALIDAR: accion_por debe ser "SISTEMA DE AUTOMATIZACIÓN"
        assert (
            factura.accion_por == "SISTEMA DE AUTOMATIZACIÓN"
        ), f"accion_por={factura.accion_por}, esperado=SISTEMA DE AUTOMATIZACIÓN"
        assert (
            factura.estado == EstadoFactura.aprobada_auto
        ), f"estado={factura.estado}, esperado=aprobada_auto"

    def test_accion_por_en_schema_siempre_consistente(self, db: Session, test_data):
        """
        TEST 5: Verificar que el schema FacturaRead SIEMPRE retorna
        accion_por consistente (desde DB, no calculado).

        VALIDACIÓN:
            1. Aprobar factura manualmente
            2. Leer factura vía schema FacturaRead
            3. accion_por en schema debe = accion_por en DB
        """
        factura = test_data["factura"]
        workflow = test_data["workflow"]
        responsable = test_data["responsable1"]

        # Aprobación manual
        servicio = WorkflowAutomaticoService(db)
        servicio.aprobar_manual(
            workflow_id=workflow.id,
            aprobado_por=responsable.nombre,
        )

        # Leer factura vía CRUD
        facturas = list_facturas(db=db)
        factura_leida = next(f for f in facturas if f.id == factura.id)

        # Convertir a schema
        factura_schema = FacturaRead.model_validate(factura_leida)

        # VALIDAR: schema debe reflejar el valor de DB
        assert (
            factura_schema.accion_por == responsable.nombre
        ), f"Schema accion_por={factura_schema.accion_por}, DB={factura_leida.accion_por}"
        assert (
            factura_schema.accion_por is not None
        ), "accion_por es None en schema"

    def test_accion_por_diferencia_responsable_vs_accion_por(
        self, db: Session, test_data
    ):
        """
        TEST 6: Verificar que RESPONSABLE y ACCION_POR son campos distintos.

        ARQUITECTURA CRÍTICA:
            - RESPONSABLE: quién está ASIGNADO a revisar (no cambia)
            - ACCION_POR: quién APROBÓ/RECHAZÓ (puede ser diferente)

        ESCENARIO:
            1. Factura asignada a Juan (responsable_id = Juan)
            2. Maria aprueba la factura (accion_por = Maria)
            3. Deben ser DISTINTOS
        """
        factura = test_data["factura"]
        workflow = test_data["workflow"]
        responsable_asignado = test_data["responsable1"]  # Juan
        quien_aprueба = test_data["responsable2"]  # Maria

        # Verificar estado inicial
        assert (
            factura.responsable_id == responsable_asignado.id
        ), "Usuario inicial no es Juan"

        # Maria aprueba (aunque estaba asignada a Juan)
        servicio = WorkflowAutomaticoService(db)
        servicio.aprobar_manual(
            workflow_id=workflow.id,
            aprobado_por=quien_aprueба.nombre,
        )

        # Actualizar referencias
        db.refresh(factura)

        # VALIDAR: Usuario != ACCION_POR
        assert (
            factura.responsable_id == responsable_asignado.id
        ), "responsable_id no debería cambiar"
        assert (
            factura.accion_por == quien_aprueба.nombre
        ), f"accion_por debería ser {quien_aprueба.nombre}"
        assert (
            responsable_asignado.nombre != quien_aprueба.nombre
        ), "Test inválido: responsables tienen el mismo nombre"

    def test_accion_por_nunca_vacio_despues_aprobacion(
        self, db: Session, test_data
    ):
        """
        TEST 7: Verificar que accion_por NUNCA es vacío después de aprobación.

        REGLA: Una vez que la factura es aprobada o rechazada,
        accion_por SIEMPRE debe tener un valor.
        """
        factura = test_data["factura"]
        workflow = test_data["workflow"]
        responsable = test_data["responsable1"]

        # ANTES: accion_por debe ser NULL
        assert factura.accion_por is None, "accion_por debe ser None inicialmente"

        # APROBACIÓN
        servicio = WorkflowAutomaticoService(db)
        servicio.aprobar_manual(
            workflow_id=workflow.id,
            aprobado_por=responsable.nombre,
        )

        # DESPUÉS: accion_por NUNCA debe ser NULL
        db.refresh(factura)
        assert (
            factura.accion_por is not None
        ), "accion_por es None después de aprobación"
        assert (
            factura.accion_por != ""
        ), "accion_por es string vacío después de aprobación"
        assert (
            len(factura.accion_por.strip()) > 0
        ), "accion_por es whitespace después de aprobación"
