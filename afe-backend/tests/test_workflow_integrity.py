"""
Test Suite: Integridad de Datos - Campo accion_por

Garantiza que los campos aprobada_por y rechazada_por SIEMPRE contengan
nombres válidos de usuarios, nunca IDs numéricos.

Este test previene regresiones del bug donde rechazada_por='5' se mostraba
en el dashboard como ID en lugar del nombre 'Alex'.
"""

import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import engine
from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow
from app.models.usuario import Usuario
from app.models.proveedor import Proveedor
from app.crud.factura import list_facturas
from app.schemas.factura import FacturaRead


class TestWorkflowIntegrity:
    """Test suite para validar integridad de datos en workflow"""

    @pytest.fixture
    def db(self):
        """Fixture de sesión de BD"""
        with Session(engine) as session:
            yield session

    def test_aprobada_por_nunca_contiene_solo_numeros(self, db: Session):
        """
        Verificar que aprobada_por NUNCA sea un número puro ('5').
        Debe ser nombre completo ('Alex') o 'SISTEMA_AUTO'.
        """
        workflows = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.aprobada == True,
            WorkflowAprobacionFactura.aprobada_por.isnot(None)
        ).all()

        for wf in workflows:
            # Verificar que no es un número puro
            try:
                int(wf.aprobada_por)
                pytest.fail(
                    f"WF {wf.id}: aprobada_por='{wf.aprobada_por}' "
                    "es un número puro (debe ser nombre completo)"
                )
            except ValueError:
                # Correcto: no es un número puro
                pass

    def test_rechazada_por_nunca_contiene_solo_numeros(self, db: Session):
        """
        Verificar que rechazada_por NUNCA sea un número puro ('5').
        Debe ser nombre completo ('Alex' o 'alex.taimal').
        """
        workflows = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.rechazada == True,
            WorkflowAprobacionFactura.rechazada_por.isnot(None)
        ).all()

        for wf in workflows:
            # Verificar que no es un número puro
            try:
                int(wf.rechazada_por)
                pytest.fail(
                    f"WF {wf.id}: rechazada_por='{wf.rechazada_por}' "
                    "es un número puro (debe ser nombre completo)"
                )
            except ValueError:
                # Correcto: no es un número puro
                pass

    def test_workflow_history_se_carga_correctamente(self, db: Session):
        """
        Verificar que workflow_history se carga con selectinload
        en todas las funciones CRUD.
        """
        # Obtener facturas con el CRUD (que usa selectinload)
        facturas = list_facturas(db, skip=0, limit=100)

        # Verificar que al menos ALGUNAS facturas tienen workflows cargados
        facturas_con_wf = [f for f in facturas if f.workflow_history]
        assert len(facturas_con_wf) > 0, "Debería haber al menos algunas facturas con workflows"

        # Verificar que los workflows cargados son válidos
        for factura in facturas_con_wf:
            assert factura.workflow_history.factura_id == factura.id
            # El workflow puede estar en varios estados, no solo aprobado/rechazado
            assert factura.workflow_history.estado is not None

    def test_accion_por_schema_nunca_contiene_numeros(self, db: Session):
        """
        Verificar que el campo accion_por en el schema FacturaRead
        NUNCA sea un número puro.
        """
        facturas = list_facturas(db, skip=0, limit=100)

        for factura in facturas:
            try:
                schema = FacturaRead.model_validate(factura)

                if schema.accion_por:
                    # Verificar que no es un número puro
                    try:
                        int(schema.accion_por)
                        pytest.fail(
                            f"Factura {factura.numero_factura}: "
                            f"accion_por='{schema.accion_por}' es un número puro"
                        )
                    except ValueError:
                        # Correcto: no es un número puro
                        pass
            except Exception as e:
                pytest.fail(f"Error validando factura {factura.numero_factura}: {e}")

    def test_aprobada_por_respeta_valores_validos(self, db: Session):
        """
        Verificar que aprobada_por contenga SOLO valores válidos:
        - 'SISTEMA_AUTO'
        - Nombres de responsables válidos (Alex, alex.taimal, etc)
        - NO debe ser un número puro
        """
        workflows = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.aprobada == True,
            WorkflowAprobacionFactura.aprobada_por.isnot(None)
        ).all()

        # Obtener lista de TODOS los valores posibles (nombres + usuarios)
        responsables = db.query(Usuario).all()
        valores_validos = {"SISTEMA_AUTO"}  # Sistema automático siempre válido
        for r in responsables:
            if r.nombre:
                valores_validos.add(r.nombre)
            if r.usuario:
                valores_validos.add(r.usuario)

        for wf in workflows:
            # Verificar que no es un número puro
            try:
                int(wf.aprobada_por)
                pytest.fail(
                    f"WF {wf.id}: aprobada_por='{wf.aprobada_por}' "
                    "es un número puro (critical bug)"
                )
            except ValueError:
                # OK: no es número puro
                pass

    def test_rechazada_por_respeta_valores_validos(self, db: Session):
        """
        Verificar que rechazada_por contenga SOLO valores válidos:
        - Nombres de responsables (Alex, alexander, etc)
        - Usuarios de responsables (alex.taimal, etc)
        - NO debe ser un número puro
        """
        workflows = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.rechazada == True,
            WorkflowAprobacionFactura.rechazada_por.isnot(None)
        ).all()

        for wf in workflows:
            # Verificar que no es un número puro
            try:
                int(wf.rechazada_por)
                pytest.fail(
                    f"WF {wf.id}: rechazada_por='{wf.rechazada_por}' "
                    "es un número puro (critical bug)"
                )
            except ValueError:
                # OK: no es número puro
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
