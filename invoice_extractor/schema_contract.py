"""
Schema Contract v2.0.0 para factura_items.

SINGLE SOURCE OF TRUTH entre afe-backend e invoice_extractor.

Este contrato define el esquema oficial de la tabla factura_items
y previene desincronizaciones entre proyectos.

Historial:
- v2.0.0 (2025-12-02): Eliminadas codigo_estandar, descuento_porcentaje, notas
- v1.0.0 (2025-10-09): Versión inicial con 16 campos

Autor: Sistema AFE
Fecha: 2025-12-02
"""
from typing import Dict, Any, List, Tuple

# ============================================================================
# SCHEMA OFICIAL v2.0.0
# ============================================================================

FACTURA_ITEMS_SCHEMA_V2: Dict[str, Dict[str, Any]] = {
    # OBLIGATORIOS
    "factura_id": {
        "type": "BIGINT",
        "nullable": False,
        "comment": "FK a facturas.id"
    },
    "numero_linea": {
        "type": "INT",
        "nullable": False,
        "comment": "Número de línea en XML (orden)"
    },
    "descripcion": {
        "type": "VARCHAR(2000)",
        "nullable": False,
        "comment": "Descripción del item del XML"
    },
    "cantidad": {
        "type": "DECIMAL(15,4)",
        "nullable": False,
        "comment": "Cantidad facturada"
    },
    "precio_unitario": {
        "type": "DECIMAL(15,4)",
        "nullable": False,
        "comment": "Precio por unidad"
    },
    "total_impuestos": {
        "type": "DECIMAL(15,2)",
        "nullable": False,
        "comment": "IVA y otros impuestos"
    },

    # OPCIONALES
    "codigo_producto": {
        "type": "VARCHAR(100)",
        "nullable": True,
        "comment": "Código del proveedor"
    },
    "unidad_medida": {
        "type": "VARCHAR(50)",
        "nullable": True,
        "comment": "unidad, kg, litro, hora, etc."
    },
    "descuento_valor": {
        "type": "DECIMAL(15,2)",
        "nullable": True,
        "comment": "Valor absoluto del descuento"
    },
    "descripcion_normalizada": {
        "type": "VARCHAR(500)",
        "nullable": True,
        "comment": "Para matching automático"
    },
    "item_hash": {
        "type": "VARCHAR(32)",
        "nullable": True,
        "comment": "MD5 para comparación rápida"
    },
    "categoria": {
        "type": "VARCHAR(100)",
        "nullable": True,
        "comment": "software, hardware, servicio, etc."
    },
    "es_recurrente": {
        "type": "TINYINT(1)",
        "nullable": True,
        "comment": "1=mensual, 0=esporádico"
    },

    # GENERATED COLUMNS (NO se incluyen en INSERT)
    # Estas columnas se calculan automáticamente en MySQL
    "_subtotal": {
        "type": "DECIMAL(15,2) GENERATED",
        "nullable": False,
        "comment": "GENERATED: cantidad * precio_unitario - descuento_valor"
    },
    "_total": {
        "type": "DECIMAL(15,2) GENERATED",
        "nullable": False,
        "comment": "GENERATED: subtotal + total_impuestos"
    },
}

# ============================================================================
# CAMPOS DEPRECADOS
# ============================================================================

DEPRECATED_FIELDS: Dict[str, str] = {
    "codigo_estandar": "Eliminado 2025-12-02 (sin uso en backend)",
    "descuento_porcentaje": "Eliminado 2025-12-02 (sin uso, redundante)",
    "notas": "Eliminado 2025-12-02 (sin uso, confusión con nit_configuracion.notas)",
}

# ============================================================================
# VALIDACIÓN
# ============================================================================


def get_insertable_fields() -> List[str]:
    """
    Retorna lista de campos válidos para INSERT.

    Excluye campos GENERATED y campos deprecados.
    """
    return [
        field for field in FACTURA_ITEMS_SCHEMA_V2.keys()
        if not field.startswith("_")  # Excluir GENERATED (_subtotal, _total)
    ]


def validate_insert_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Valida que un diccionario cumpla con el schema v2.0.0.

    Args:
        data: Diccionario con datos para INSERT

    Returns:
        (es_valido, mensaje_error)

    Examples:
        >>> validate_insert_data({"factura_id": 123, "numero_linea": 1, ...})
        (True, "OK")

        >>> validate_insert_data({"factura_id": 123, "codigo_estandar": "EAN123"})
        (False, "Campo 'codigo_estandar' deprecado: Eliminado 2025-12-02...")
    """
    # 1. Verificar campos deprecados
    for field in data.keys():
        if field in DEPRECATED_FIELDS:
            return False, (
                f"❌ Campo '{field}' deprecado: {DEPRECATED_FIELDS[field]}"
            )

    # 2. Verificar campos GENERATED (no deben estar en INSERT)
    generated_fields = [f for f in FACTURA_ITEMS_SCHEMA_V2.keys() if f.startswith("_")]
    for field in data.keys():
        if field in generated_fields:
            return False, (
                f"❌ Campo '{field}' es GENERATED COLUMN - "
                "no debe incluirse en INSERT"
            )

    # 3. Verificar campos obligatorios
    required = [
        field for field, spec in FACTURA_ITEMS_SCHEMA_V2.items()
        if not spec["nullable"] and not field.startswith("_")
    ]

    missing = [f for f in required if f not in data or data[f] is None]
    if missing:
        return False, f"❌ Campos obligatorios faltantes: {missing}"

    # 4. Verificar campos desconocidos
    valid_fields = get_insertable_fields()
    unknown = [f for f in data.keys() if f not in valid_fields]
    if unknown:
        return False, (
            f"⚠️ Campos desconocidos (no están en schema): {unknown}"
        )

    return True, "✅ OK - Schema válido"


def filter_valid_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filtra un diccionario dejando solo campos válidos del schema.

    Útil para limpiar datos antes de INSERT.

    Args:
        data: Diccionario con datos (puede tener campos extra)

    Returns:
        Diccionario limpio con solo campos válidos

    Examples:
        >>> dirty = {
        ...     "factura_id": 123,
        ...     "codigo_estandar": "EAN123",  # DEPRECADO
        ...     "subtotal": 1000,              # GENERATED
        ...     "numero_linea": 1
        ... }
        >>> filter_valid_fields(dirty)
        {'factura_id': 123, 'numero_linea': 1}
    """
    valid_fields = get_insertable_fields()
    return {k: v for k, v in data.items() if k in valid_fields}


# ============================================================================
# CONSTRUCCIÓN DINÁMICA DE SQL
# ============================================================================


def build_insert_sql() -> str:
    """
    Construye SQL de INSERT dinámicamente desde el schema.

    Returns:
        SQL string con placeholders nombrados

    Example:
        INSERT INTO factura_items (factura_id, numero_linea, ...)
        VALUES (:factura_id, :numero_linea, ...)
    """
    fields = get_insertable_fields()
    columns = ", ".join(fields)
    placeholders = ", ".join(f":{field}" for field in fields)

    return f"""
        INSERT INTO factura_items ({columns})
        VALUES ({placeholders})
    """


# ============================================================================
# INFORMACIÓN DE VERSIÓN
# ============================================================================

SCHEMA_VERSION = "2.0.0"
SCHEMA_DATE = "2025-12-02"

MIGRATION_HISTORY = [
    {
        "version": "1.0.0",
        "date": "2025-10-09",
        "migration": "8c6834305516_add_factura_items_table",
        "description": "Creación inicial con 16 campos"
    },
    {
        "version": "2.0.0",
        "date": "2025-12-02",
        "migration": "2d665e89c06b_remove_unused_fields_from_factura_items",
        "description": "Eliminadas 3 columnas: codigo_estandar, descuento_porcentaje, notas"
    }
]


def print_schema_info():
    """Imprime información del schema para debugging."""
    print(f"\n{'='*70}")
    print(f"Schema Contract v{SCHEMA_VERSION} ({SCHEMA_DATE})")
    print(f"{'='*70}")
    print(f"\n📊 Campos activos: {len(get_insertable_fields())}")
    print(f"🗑️  Campos deprecados: {len(DEPRECATED_FIELDS)}")
    print(f"\n✅ Campos válidos para INSERT:")
    for field in get_insertable_fields():
        spec = FACTURA_ITEMS_SCHEMA_V2[field]
        req = "REQUIRED" if not spec["nullable"] else "optional"
        print(f"   - {field:<30} {spec['type']:<20} ({req})")

    print(f"\n❌ Campos deprecados:")
    for field, reason in DEPRECATED_FIELDS.items():
        print(f"   - {field:<30} → {reason}")

    print(f"\n🔧 Generated Columns (excluir de INSERT):")
    for field, spec in FACTURA_ITEMS_SCHEMA_V2.items():
        if field.startswith("_"):
            print(f"   - {field[1:]:<30} {spec['type']}")

    print(f"\n📜 Historial de migraciones:")
    for migration in MIGRATION_HISTORY:
        print(f"   v{migration['version']} ({migration['date']}): {migration['description']}")

    print(f"\n{'='*70}\n")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print_schema_info()

    # Test 1: Validación exitosa
    print("\n🧪 Test 1: Datos válidos")
    valid_data = {
        "factura_id": 123,
        "numero_linea": 1,
        "descripcion": "Test item",
        "cantidad": 1,
        "precio_unitario": 100,
        "total_impuestos": 19,
        "codigo_producto": "PROD-001",
        "unidad_medida": "unidad",
    }
    is_valid, msg = validate_insert_data(valid_data)
    print(f"   Resultado: {msg}")

    # Test 2: Campo deprecado
    print("\n🧪 Test 2: Campo deprecado (debe fallar)")
    invalid_data = {
        **valid_data,
        "codigo_estandar": "EAN-123456"  # DEPRECADO
    }
    is_valid, msg = validate_insert_data(invalid_data)
    print(f"   Resultado: {msg}")

    # Test 3: Campo GENERATED
    print("\n🧪 Test 3: Campo GENERATED (debe fallar)")
    invalid_data2 = {
        **valid_data,
        "subtotal": 100  # GENERATED - no debe estar en INSERT
    }
    is_valid, msg = validate_insert_data(invalid_data2)
    print(f"   Resultado: {msg}")

    # Test 4: Filtrado de campos
    print("\n🧪 Test 4: Filtrado automático de campos")
    dirty_data = {
        "factura_id": 123,
        "numero_linea": 1,
        "descripcion": "Test",
        "cantidad": 1,
        "precio_unitario": 100,
        "total_impuestos": 0,
        "codigo_estandar": "EAN123",  # DEPRECADO
        "subtotal": 100,              # GENERATED
        "campo_inventado": "valor"    # DESCONOCIDO
    }
    clean_data = filter_valid_fields(dirty_data)
    print(f"   Datos originales: {list(dirty_data.keys())}")
    print(f"   Datos limpios: {list(clean_data.keys())}")

    # Test 5: SQL dinámico
    print("\n🧪 Test 5: SQL dinámico generado")
    sql = build_insert_sql()
    print(f"   {sql.strip()[:200]}...")
