import sys
sys.path.append('.')

from app.database import SessionLocal
from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow, TipoAprobacion
from sqlalchemy import func

db = SessionLocal()

print("\n=== ANÁLISIS DE WORKFLOWS ===\n")

# Contar por estado
print(" Workflows por Estado:")
estados = db.query(
    WorkflowAprobacionFactura.estado,
    func.count(WorkflowAprobacionFactura.id)
).group_by(WorkflowAprobacionFactura.estado).all()

for estado, count in estados:
    print(f"  {estado.value}: {count}")

# Contar aprobadas automáticas
print("\n Workflows Aprobados Automáticamente:")
aprobadas_auto = db.query(WorkflowAprobacionFactura).filter(
    WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_AUTO
).count()
print(f"  Total: {aprobadas_auto}")

# Contar por tipo de aprobación
print("\n Por Tipo de Aprobación:")
tipos = db.query(
    WorkflowAprobacionFactura.tipo_aprobacion,
    func.count(WorkflowAprobacionFactura.id)
).group_by(WorkflowAprobacionFactura.tipo_aprobacion).all()

for tipo, count in tipos:
    valor = tipo.value if tipo else "NULL"
    print(f"  {valor}: {count}")

# Verificar campo aprobada
print("\n Campo 'aprobada':")
aprobadas = db.query(WorkflowAprobacionFactura).filter(
    WorkflowAprobacionFactura.aprobada == True
).count()
print(f"  aprobada=True: {aprobadas}")

# Contar facturas por estado
print("\n Facturas por Estado:")
from app.models.factura import Factura, EstadoFactura

facturas_estados = db.query(
    Factura.estado,
    func.count(Factura.id)
).group_by(Factura.estado).all()

for estado, count in facturas_estados:
    print(f"  {estado.value}: {count}")

# Verificar sincronización
print("\n Verificación de Sincronización:")
workflows_aprobados_auto = db.query(WorkflowAprobacionFactura).filter(
    WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_AUTO
).all()

facturas_aprobadas_auto = set()
for w in workflows_aprobados_auto:
    facturas_aprobadas_auto.add(w.factura_id)

print(f"  Workflows en APROBADA_AUTO: {len(workflows_aprobados_auto)}")
print(f"  Facturas únicas con workflow APROBADA_AUTO: {len(facturas_aprobadas_auto)}")

# Verificar cuántas facturas tienen estado aprobada_auto
facturas_bd_aprobadas_auto = db.query(Factura).filter(
    Factura.estado == EstadoFactura.APROBADA_AUTO
).count()
print(f"  Facturas en BD con estado APROBADA_AUTO: {facturas_bd_aprobadas_auto}")

db.close()
