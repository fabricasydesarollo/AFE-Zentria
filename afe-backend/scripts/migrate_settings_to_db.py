#!/usr/bin/env python3
"""
Script de Migración: settings.json -> Base de Datos

Migra la configuración de correos desde el archivo settings.json
al nuevo sistema de base de datos.

Uso:
    python scripts/migrate_settings_to_db.py [ruta_al_settings.json]
"""
import sys
import json
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.crud.email_config import (
    create_cuenta_correo,
    get_cuenta_correo_by_email,
    bulk_create_nits,
)
from app.schemas.email_config import CuentaCorreoCreate


def migrate_settings_to_db(settings_path: str, created_by: str = "admin"):
    """
    Migra la configuración desde settings.json a la base de datos.

    Args:
        settings_path: Ruta al archivo settings.json
        created_by: Usuario que realiza la migración
    """
    # Leer el archivo settings.json
    with open(settings_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)

    db = SessionLocal()

    try:
        migrated_accounts = 0
        migrated_nits = 0
        skipped_accounts = 0

        print(f">> Iniciando migracion desde {settings_path}")
        print(f"   Cuentas a migrar: {len(settings['users'])}\n")

        for user in settings['users']:
            email = user['email']

            # Verificar si la cuenta ya existe
            existing = get_cuenta_correo_by_email(db, email)
            if existing:
                print(f"!!  Cuenta ya existe: {email}")
                print(f"   -> Saltando (usa el frontend para actualizar)")
                skipped_accounts += 1
                continue

            # Crear la cuenta de correo
            cuenta_data = CuentaCorreoCreate(
                email=email,
                nombre_descriptivo=_extract_nombre_from_email(email),
                fetch_limit=user.get('fetch_limit', 500),
                fetch_days=user.get('fetch_days', 90),
                activa=True,
                organizacion=_extract_organizacion_from_email(email),
                creada_por=created_by,
            )

            cuenta = create_cuenta_correo(db, cuenta_data)
            migrated_accounts += 1

            print(f"OK Cuenta creada: {email}")
            print(f"   -> ID: {cuenta.id}")
            print(f"   -> Organización: {cuenta.organizacion}")
            print(f"   -> Límite de búsqueda: {cuenta.fetch_limit} correos / {cuenta.fetch_days} días")

            # Crear NITs en bulk
            if user.get('nits'):
                agregados, duplicados, detalles = bulk_create_nits(
                    db, cuenta.id, user['nits'], created_by
                )

                migrated_nits += agregados
                print(f"   -> NITs agregados: {agregados}")
                if duplicados > 0:
                    print(f"   -> NITs duplicados (ignorados): {duplicados}")

            print()

        db.commit()

        print("="*60)
        print("[OK] MIGRACIÓN COMPLETADA")
        print("="*60)
        print(f"Cuentas migradas:    {migrated_accounts}")
        print(f"Cuentas saltadas:    {skipped_accounts}")
        print(f"NITs totales:        {migrated_nits}")
        print()
        print(">> Accede al panel de administración:")
        print("   http://localhost:5173/email-config")
        print()

        return True

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] ERROR durante la migración: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


def _extract_nombre_from_email(email: str) -> str:
    """Extrae un nombre descriptivo del email"""
    # facturacion.electronica@angiografiadecolombia.com -> Angiografía de Colombia
    domain = email.split('@')[1].split('.')[0]

    nombres = {
        'angiografiadecolombia': 'Angiografía de Colombia',
        'avidanti': 'Avidanti',
        'diacorsoacha': 'Diacor Soacha',
    }

    return nombres.get(domain, domain.capitalize())


def _extract_organizacion_from_email(email: str) -> str:
    """Extrae el código de organización del email"""
    domain = email.split('@')[1].split('.')[0]

    organizaciones = {
        'angiografiadecolombia': 'ANGIOGRAFIA',
        'avidanti': 'AVIDANTI',
        'diacorsoacha': 'DIACOR',
    }

    return organizaciones.get(domain, domain.upper())


def main():
    """Punto de entrada principal"""
    if len(sys.argv) < 2:
        print("[ERROR] Error: Debes proporcionar la ruta al archivo settings.json")
        print()
        print("Uso:")
        print(f"  python {sys.argv[0]} <ruta_al_settings.json>")
        print()
        print("Ejemplo:")
        print(f"  python {sys.argv[0]} settings.json")
        print(f"  python {sys.argv[0]} ../afe_frontend/settings.json")
        sys.exit(1)

    settings_path = sys.argv[1]

    if not Path(settings_path).exists():
        print(f"[ERROR] Error: El archivo '{settings_path}' no existe")
        sys.exit(1)

    # Ejecutar migración
    success = migrate_settings_to_db(settings_path)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
