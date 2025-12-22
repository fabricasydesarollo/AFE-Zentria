"""
Script de mantenimiento de particiones para tabla facturas.

Funciones:
1. Agregar particiones para años futuros automáticamente
2. Verificar particiones existentes
3. Eliminar particiones de años antiguos (opcional)

Uso:
    # Verificar particiones actuales
    python -m app.scripts.manage_partitions --check

    # Agregar partición para próximo año
    python -m app.scripts.manage_partitions --add-next

    # Agregar partición para año específico
    python -m app.scripts.manage_partitions --add-year 2027

    # Eliminar partición antigua (CUIDADO: elimina datos)
    python -m app.scripts.manage_partitions --drop-year 2020
"""

import argparse
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


def get_db():
    """Obtiene sesión de base de datos."""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal(), engine


def check_partitions(db, engine):
    """Muestra particiones actuales de la tabla facturas."""
    print("\n" + "="*90)
    print("PARTICIONES ACTUALES - TABLA FACTURAS")
    print("="*90)

    result = engine.connect().execute(text("""
        SELECT
            PARTITION_NAME,
            PARTITION_DESCRIPTION,
            TABLE_ROWS,
            PARTITION_COMMENT
        FROM INFORMATION_SCHEMA.PARTITIONS
        WHERE TABLE_NAME = 'facturas'
        AND TABLE_SCHEMA = DATABASE()
        ORDER BY PARTITION_ORDINAL_POSITION
    """))

    print(f"{'Partición':<15} {'Rango (<)':<15} {'Filas':<15} {'Comentario':<40}")
    print("-"*90)

    total_rows = 0
    for row in result:
        partition_name = row[0]
        partition_desc = row[1] or 'N/A'
        table_rows = row[2] or 0
        comment = row[3] or ''

        print(f"{partition_name:<15} {partition_desc:<15} {table_rows:<15} {comment:<40}")
        total_rows += table_rows

    print("-"*90)
    print(f"{'TOTAL':<15} {'':<15} {total_rows:<15}")
    print("="*90 + "\n")


def add_partition_for_year(db, engine, year):
    """
    Agrega una nueva partición para un año específico.

    IMPORTANTE: Solo funciona si el año es mayor que todas las particiones existentes
    (excepto p_future). Reorganiza p_future para acomodar el nuevo año.
    """
    print(f"\nAgregando partición para año {year}...")

    try:
        # Reorganizar partición p_future para incluir el nuevo año
        engine.connect().execute(text(f"""
            ALTER TABLE facturas
            REORGANIZE PARTITION p_future INTO (
                PARTITION p{year} VALUES LESS THAN ({year + 1})
                    COMMENT = 'Facturas del año {year}',
                PARTITION p_future VALUES LESS THAN MAXVALUE
                    COMMENT = 'Facturas de años futuros ({year + 1}+)'
            )
        """))

        print(f"Partición p{year} creada exitosamente!")
        print(f"Rango: Facturas con año_factura < {year + 1}")

    except Exception as e:
        print(f"Error al crear partición: {str(e)}")
        print("\nNOTA: Verifica que:")
        print(f"  1. No exista ya una partición para {year}")
        print(f"  2. El año {year} sea mayor que las particiones actuales")
        print(f"  3. La partición p_future existe")


def add_next_year_partition(db, engine):
    """Agrega automáticamente una partición para el próximo año."""
    next_year = datetime.now().year + 1
    print(f"\nCreando partición para próximo año: {next_year}")
    add_partition_for_year(db, engine, next_year)


def drop_partition(db, engine, year):
    """
    Elimina una partición y TODOS sus datos.

    ADVERTENCIA: Esta operación es irreversible y elimina datos permanentemente.
    """
    partition_name = f"p{year}"

    print("\n" + "!"*90)
    print("ADVERTENCIA: OPERACIÓN DESTRUCTIVA")
    print("!"*90)
    print(f"\nEstás a punto de eliminar la partición '{partition_name}'")
    print(f"Esto eliminará PERMANENTEMENTE todas las facturas del año {year}")

    confirm = input(f"\n¿Estás ABSOLUTAMENTE SEGURO? Escribe 'DELETE {year}' para confirmar: ")

    if confirm != f"DELETE {year}":
        print("\nOperación cancelada. No se eliminó ninguna partición.")
        return

    try:
        engine.connect().execute(text(f"""
            ALTER TABLE facturas
            DROP PARTITION {partition_name}
        """))

        print(f"\nPartición {partition_name} eliminada exitosamente.")
        print(f"Todas las facturas del año {year} han sido eliminadas de la base de datos.")

    except Exception as e:
        print(f"\nError al eliminar partición: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description="Gestor de particiones para tabla facturas"
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Mostrar particiones actuales'
    )

    parser.add_argument(
        '--add-next',
        action='store_true',
        help='Agregar partición para próximo año automáticamente'
    )

    parser.add_argument(
        '--add-year',
        type=int,
        help='Agregar partición para año específico'
    )

    parser.add_argument(
        '--drop-year',
        type=int,
        help='ELIMINAR partición de año específico (DESTRUCTIVO)'
    )

    args = parser.parse_args()

    # Si no se pasa ningún argumento, mostrar ayuda
    if not any(vars(args).values()):
        parser.print_help()
        return

    db, engine = get_db()

    try:
        if args.check:
            check_partitions(db, engine)

        if args.add_next:
            add_next_year_partition(db, engine)
            check_partitions(db, engine)

        if args.add_year:
            add_partition_for_year(db, engine, args.add_year)
            check_partitions(db, engine)

        if args.drop_year:
            drop_partition(db, engine, args.drop_year)
            check_partitions(db, engine)

    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    print("\n" + "*"*90)
    print("*  GESTOR DE PARTICIONES - TABLA FACTURAS  *".center(90))
    print("*"*90)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    main()
