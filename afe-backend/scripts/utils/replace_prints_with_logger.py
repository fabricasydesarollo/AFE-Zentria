#!/usr/bin/env python3
"""
Script para reemplazar print() por logger en archivos Python.
Solo modifica archivos que tienen prints y agrega imports necesarios.
"""
import re
from pathlib import Path
from typing import List, Tuple


def has_logger_import(content: str) -> bool:
    """Verifica si el archivo ya tiene logger importado."""
    patterns = [
        r'^import\s+logging',
        r'^from\s+.*\s+import\s+.*logging',
        r'^logger\s*=',
    ]
    for pattern in patterns:
        if re.search(pattern, content, re.MULTILINE):
            return True
    return False


def add_logger_import(content: str) -> str:
    """Agrega import de logging si no existe."""
    if has_logger_import(content):
        return content

    # Buscar la última línea de imports
    lines = content.split('\n')
    last_import_idx = -1

    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i

    # Insertar después del último import
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, 'import logging')
        lines.insert(last_import_idx + 2, '')
        lines.insert(last_import_idx + 3, 'logger = logging.getLogger(__name__)')
    else:
        # Si no hay imports, agregar al principio después del docstring
        insert_idx = 0
        if lines and lines[0].startswith('"""') or lines[0].startswith("'''"):
            # Buscar el final del docstring
            for i in range(1, len(lines)):
                if lines[i].endswith('"""') or lines[i].endswith("'''"):
                    insert_idx = i + 1
                    break
        lines.insert(insert_idx, 'import logging')
        lines.insert(insert_idx + 1, '')
        lines.insert(insert_idx + 2, 'logger = logging.getLogger(__name__)')
        lines.insert(insert_idx + 3, '')

    return '\n'.join(lines)


def replace_prints(content: str) -> Tuple[str, int]:
    """Reemplaza print() por logger apropiado."""
    count = 0

    # Patrones de print con diferentes niveles
    replacements = [
        (r'print\(f"\s*(.+?)"\)', r'logger.error(f"\1")', 'error'),
        (r'print\(f"⚠️\s*(.+?)"\)', r'logger.warning(f"\1")', 'warning'),
        (r'print\(f"✅\s*(.+?)"\)', r'logger.info(f"\1")', 'info'),
        (r'print\("\s*(.+?)"\)', r'logger.error("\1")', 'error'),
        (r'print\("⚠️\s*(.+?)"\)', r'logger.warning("\1")', 'warning'),
        (r'print\("✅\s*(.+?)"\)', r'logger.info("\1")', 'info'),
    ]

    new_content = content
    for pattern, replacement, level in replacements:
        new_content, n = re.subn(pattern, replacement, new_content)
        count += n

    # Prints genéricos - usar logger.info por defecto
    generic_patterns = [
        (r'print\(f"(.+?)"\)', r'logger.info(f"\1")'),
        (r'print\("(.+?)"\)', r'logger.info("\1")'),
        (r"print\(f'(.+?)'\)", r"logger.info(f'\1')"),
        (r"print\('(.+?)'\)", r"logger.info('\1')"),
    ]

    for pattern, replacement in generic_patterns:
        new_content, n = re.subn(pattern, replacement, new_content)
        count += n

    return new_content, count


def process_file(file_path: Path) -> bool:
    """Procesa un archivo y retorna True si se modificó."""
    try:
        content = file_path.read_text(encoding='utf-8')

        # Verificar si tiene prints
        if not re.search(r'^\s*print\(', content, re.MULTILINE):
            return False

        # Agregar logger si no existe
        new_content = add_logger_import(content)

        # Reemplazar prints
        new_content, count = replace_prints(new_content)

        if count > 0:
            file_path.write_text(new_content, encoding='utf-8')
            print(f"✓ {file_path.relative_to(file_path.parent.parent.parent)}: {count} prints reemplazados")
            return True

        return False
    except Exception as e:
        print(f"✗ Error procesando {file_path}: {e}")
        return False


def main():
    """Procesa todos los archivos Python en app/."""
    base_dir = Path(__file__).parent.parent.parent / 'app'

    files_to_process = [
        'services/workflow_automatico.py',
        'services/clasificacion_proveedores.py',
        'api/v1/routers/workflow.py',
        'tasks/automation_tasks.py',
        'tasks/analisis_patrones_task.py',
        'services/notificaciones.py',
        'services/microsoft_oauth_service.py',
        'services/analisis_patrones.py',
    ]

    modified = 0
    for file_rel in files_to_process:
        file_path = base_dir / file_rel
        if file_path.exists():
            if process_file(file_path):
                modified += 1

    print(f"\n{modified} archivos modificados")


if __name__ == '__main__':
    main()
