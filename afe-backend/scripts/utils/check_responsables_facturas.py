#!/usr/bin/env python3
"""
Script para verificar responsables asignados a las 5 nuevas facturas.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.factura import Factura
from app.models.usuario import Usuario
from app.models.proveedor import Proveedor

def main():
    """Diagnosticar responsables de facturas."""
    print("=" * 80)
    print("DIAGNOSTICO DE RESPONSABLES - FACTURAS NUEVAS")
    print("=" * 80)

    engine = create_engine(settings.database_url)

    with Session(engine) as session:
        # Obtener ultimas 5 facturas creadas
        print("\n[1] BUSCANDO LAS 5 ULTIMAS FACTURAS CREADAS")
        print("-" * 80)

        facturas = session.query(Factura).order_by(
            Factura.creado_en.desc()
        ).limit(5).all()

        if not facturas:
            print("[WARN] No se encontraron facturas")
            return

        print(f"[OK] Se encontraron {len(facturas)} facturas")

        for factura in facturas:
            print(f"\nFactura: {factura.numero_factura} (ID: {factura.id})")
            print(f"  Creada: {factura.creado_en}")
            print(f"  Proveedor: {factura.proveedor.razon_social if factura.proveedor else 'SIN PROVEEDOR'}")

            if factura.proveedor:
                print(f"  NIT Proveedor: {factura.proveedor.nit}")
            else:
                print(f"  NIT Proveedor: NO DISPONIBLE")

            print(f"  responsable_id: {factura.responsable_id}")
            print(f"  estado_asignacion: {factura.estado_asignacion}")

            # Obtener responsable asignado
            if factura.usuario:
                print(f"  Responsable asignado: {factura.usuario.nombre}")
                print(f"    - Usuario: {factura.usuario.usuario}")
                print(f"    - Email: {factura.usuario.email}")
                print(f"    - Activo: {factura.usuario.activo}")
            else:
                print(f"  Responsable: NO ASIGNADO")

            # Verificar asignaciones por NIT
            if factura.proveedor and factura.proveedor.nit:
                from app.models.workflow_aprobacion import AsignacionNitResponsable

                nit = factura.proveedor.nit
                asignaciones = session.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == nit,
                    AsignacionNitResponsable.activo == True
                ).all()

                print(f"\n  Asignaciones NIT {nit}:")
                if asignaciones:
                    for asignacion in asignaciones:
                        resp = asignacion.responsable
                        print(f"    - {resp.nombre} ({resp.email}) - Activo: {resp.activo}")
                else:
                    print(f"    - NO HAY ASIGNACIONES CONFIGURADAS PARA ESTE NIT")

        # Verificar tabla de usuarios activos
        print("\n[2] VERIFICANDO USUARIOS ACTIVOS EN EL SISTEMA")
        print("-" * 80)

        usuarios_activos = session.query(Usuario).filter(
            Usuario.activo == True
        ).all()

        print(f"Total de usuarios activos: {len(usuarios_activos)}")
        for resp in usuarios_activos:
            print(f"  - {resp.nombre} ({resp.usuario}) -> {resp.email} [ID: {resp.id}]")

        if not usuarios_activos:
            print("[WARN] NO HAY USUARIOS ACTIVOS EN EL SISTEMA")

    print("\n" + "=" * 80)
    print("FIN DEL DIAGNOSTICO")
    print("=" * 80)

if __name__ == "__main__":
    main()
