from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.proveedor import Proveedor

db = SessionLocal()

# Buscar facturas del NIT 811030191-9
facturas = db.query(Factura).join(Proveedor).filter(
    Proveedor.nit == '811030191-9'
).all()

print('=' * 100)
print(f'TOTAL FACTURAS EN BD PARA NIT 811030191-9: {len(facturas)}')
print('=' * 100)

# Mostrar primeras 5
for i, f in enumerate(facturas[:5], 1):
    print(f'\n{i}. Factura ID: {f.id}')
    print(f'   Número: {f.numero_factura}')
    print(f'   Estado: {f.estado}')
    print(f'   Monto: ${f.total_calculado:,.2f}' if f.total_calculado else '   Monto: N/A')
    if f.cufe:
        print(f'   CUFE: {f.cufe[:40]}...')
    else:
        print(f'   CUFE: Sin CUFE')

db.close()
