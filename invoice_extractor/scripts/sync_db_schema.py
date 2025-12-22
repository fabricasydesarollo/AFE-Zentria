#!/usr/bin/env python3
"""
Script para verificar y sincronizar el esquema de la base de datos con las migraciones de Alembic.

Este script debe ejecutarse antes de ingestar facturas para asegurarse de que el esquema
de la base de datos está actualizado con todas las migraciones de afe-backend.

Uso:
    python scripts/sync_db_schema.py [--check-only]

Opciones:
    --check-only: Solo verifica el esquema sin aplicar cambios
"""

import sys
import os
from pathlib import Path

# Agregar la raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from src.core.config import load_config
from src.utils.logger import get_logger


# Campos esperados según las migraciones de afe-backend
EXPECTED_FIELDS = {
    'facturas': [
        'id', 'numero_factura', 'fecha_emision', 'cliente_id', 'proveedor_id',
        'subtotal', 'iva', 'total', 'moneda', 'estado', 'fecha_vencimiento',
        'observaciones', 'cufe', 'total_a_pagar', 'responsable_id',
        'aprobada_automaticamente', 'creado_por', 'creado_en', 'actualizado_en',
        # Campos de aprobación/rechazo
        'aprobado_por', 'fecha_aprobacion', 'rechazado_por', 'fecha_rechazo', 'motivo_rechazo',
        # Campos de automatización
        'concepto_principal', 'concepto_normalizado', 'concepto_hash', 'tipo_factura',
        'items_resumen', 'orden_compra_numero', 'orden_compra_sap',
        'patron_recurrencia', 'confianza_automatica', 'factura_referencia_id', 'motivo_decision',
        'procesamiento_info', 'notas_adicionales', 'fecha_procesamiento_auto', 'version_algoritmo',
        # Campos de período
        'año_factura', 'mes_factura', 'periodo_factura',
    ],
    'proveedores': [
        'id', 'nit', 'razon_social', 'area', 'contacto_email', 'telefono', 'direccion', 'creado_en'
    ],
    'clientes': [
        'id', 'nit', 'razon_social', 'contacto_email', 'telefono', 'direccion', 'creado_en'
    ]
}


def check_schema(engine, logger):
    """
    Verifica que el esquema de la base de datos tenga todos los campos esperados.

    Returns:
        dict: Diccionario con el resultado de la verificación
            {
                'is_valid': bool,
                'missing_fields': dict,
                'extra_fields': dict,
                'errors': list
            }
    """
    inspector = inspect(engine)
    result = {
        'is_valid': True,
        'missing_fields': {},
        'extra_fields': {},
        'errors': []
    }

    logger.info("=" * 70)
    logger.info("VERIFICACIÓN DE ESQUEMA DE BASE DE DATOS")
    logger.info("=" * 70)

    # Verificar cada tabla
    for table_name, expected_columns in EXPECTED_FIELDS.items():
        logger.info(f"\n📋 Verificando tabla: {table_name}")

        # Verificar que la tabla existe
        if not inspector.has_table(table_name):
            error = f"❌ Tabla '{table_name}' no existe en la base de datos"
            logger.error(error)
            result['errors'].append(error)
            result['is_valid'] = False
            continue

        # Obtener columnas actuales
        actual_columns = [col['name'] for col in inspector.get_columns(table_name)]

        # Verificar campos faltantes
        missing = set(expected_columns) - set(actual_columns)
        if missing:
            result['missing_fields'][table_name] = list(missing)
            result['is_valid'] = False
            logger.warning(f"  ⚠️  Campos faltantes en '{table_name}': {', '.join(sorted(missing))}")

        # Verificar campos extra (no es un error, solo informativo)
        extra = set(actual_columns) - set(expected_columns)
        if extra:
            result['extra_fields'][table_name] = list(extra)
            logger.info(f"  ℹ️  Campos adicionales en '{table_name}': {', '.join(sorted(extra))}")

        # Todo OK
        if not missing and not extra:
            logger.info(f"  ✅ Tabla '{table_name}' correctamente sincronizada ({len(actual_columns)} campos)")

    # Resumen final
    logger.info("\n" + "=" * 70)
    if result['is_valid']:
        logger.info("✅ ESQUEMA VÁLIDO: La base de datos está sincronizada")
    else:
        logger.error("❌ ESQUEMA INVÁLIDO: Se requieren migraciones")
        logger.error("\n⚠️  ACCIÓN REQUERIDA:")
        logger.error("   1. Ir al directorio del backend: cd ../afe-backend")
        logger.error("   2. Aplicar migraciones de Alembic: alembic upgrade head")
        logger.error("   3. Volver a ejecutar este script para verificar")
    logger.info("=" * 70)

    return result


def print_migration_guide(logger):
    """Imprime una guía para aplicar las migraciones."""
    logger.info("\n" + "=" * 70)
    logger.info("GUÍA PARA SINCRONIZAR BASE DE DATOS")
    logger.info("=" * 70)
    logger.info("""
Las migraciones de Alembic están en el proyecto afe-backend.
Para sincronizar tu base de datos local:

1. Ir al directorio del backend:
   cd ../afe-backend

2. Verificar el estado actual de las migraciones:
   alembic current

3. Ver migraciones pendientes:
   alembic history

4. Aplicar TODAS las migraciones:
   alembic upgrade head

5. Volver al proyecto invoice_extractor:
   cd ../invoice_extractor

6. Ejecutar nuevamente este script para verificar:
   python scripts/sync_db_schema.py

NOTA: Si trabajas en múltiples equipos, asegúrate de aplicar las migraciones
      en TODOS los equipos antes de ejecutar la ingesta.
    """)
    logger.info("=" * 70)


def main():
    logger = get_logger("SyncDBSchema")

    # Verificar si solo queremos hacer check
    check_only = '--check-only' in sys.argv

    try:
        # Cargar configuración
        cfg = load_config()
        engine = create_engine(cfg.database_url, pool_pre_ping=True)

        # Verificar esquema
        result = check_schema(engine, logger)

        # Si no es válido, mostrar guía
        if not result['is_valid']:
            print_migration_guide(logger)
            return 1

        logger.info("\n✅ ¡Todo listo! Puedes ejecutar la ingesta de facturas.")
        return 0

    except Exception as exc:
        logger.error(f"Error verificando esquema: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
