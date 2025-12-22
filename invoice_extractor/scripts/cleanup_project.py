#!/usr/bin/env python3
"""
Script de limpieza del proyecto invoice_extractor
Identifica y opcionalmente elimina código redundante, obsoleto y archivos innecesarios
"""

import os
from pathlib import Path
from typing import List, Dict, Set
import ast

class ProjectCleaner:
    """Analiza y limpia el proyecto de forma inteligente"""

    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.src = self.root / "src"
        self.issues: List[Dict] = []

    def analyze(self):
        """Analiza el proyecto y genera reporte de limpieza"""
        print("="*80)
        print("ANÁLISIS DE LIMPIEZA DEL PROYECTO")
        print("="*80)

        self._check_redundant_files()
        self._check_unused_imports()
        self._check_empty_files()
        self._check_duplicate_logic()
        self._check_deprecated_patterns()

        self._print_report()

    def _check_redundant_files(self):
        """Identifica archivos redundantes"""
        print("\n[1] Buscando archivos redundantes...")

        redundant_patterns = {
            "src/models/factura_parser.py": "Usar invoice_parser_facade.py en su lugar",
            "src/core/app.py": "Verificar si está en uso o es código viejo",
            "src/modules/auth.py": "¿Se usa autenticación?",
        }

        for file_path, reason in redundant_patterns.items():
            full_path = self.root / file_path
            if full_path.exists():
                self.issues.append({
                    "type": "REDUNDANT_FILE",
                    "severity": "MEDIUM",
                    "path": str(full_path),
                    "reason": reason
                })

    def _check_unused_imports(self):
        """Busca imports que ya no se usan"""
        print("[2] Buscando imports obsoletos...")

        deprecated_imports = [
            "from src.calculation",
            "import src.calculation",
            "TotalCalculator",
            "AdjustmentDetector",
        ]

        for py_file in self.src.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                for deprecated in deprecated_imports:
                    if deprecated in content:
                        self.issues.append({
                            "type": "DEPRECATED_IMPORT",
                            "severity": "HIGH",
                            "path": str(py_file),
                            "detail": f"Contiene: {deprecated}"
                        })
            except Exception as e:
                pass

    def _check_empty_files(self):
        """Identifica archivos vacíos o casi vacíos"""
        print("[3] Buscando archivos vacíos...")

        for py_file in self.src.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8').strip()
                lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]

                if len(lines) <= 3 and py_file.name != '__init__.py':
                    self.issues.append({
                        "type": "EMPTY_FILE",
                        "severity": "LOW",
                        "path": str(py_file),
                        "detail": f"Solo {len(lines)} líneas de código"
                    })
            except Exception:
                pass

    def _check_duplicate_logic(self):
        """Busca lógica duplicada"""
        print("[4] Buscando lógica duplicada...")

        # Campos duplicados en múltiples lugares
        duplicate_fields = {
            "version_algoritmo": [
                "src/models/factura.py",
                "src/repository/factura_repository.py (ELIMINADO ✓)",
                "procesamiento_info JSON"
            ]
        }

        for field, locations in duplicate_fields.items():
            self.issues.append({
                "type": "DUPLICATE_FIELD",
                "severity": "MEDIUM",
                "field": field,
                "locations": locations,
                "recommendation": "Mantener solo en procesamiento_info JSON"
            })

    def _check_deprecated_patterns(self):
        """Busca patrones deprecados en el código"""
        print("[5] Buscando patrones deprecados...")

        deprecated_patterns = {
            r"total.*=.*subtotal.*\+.*iva": "CÁLCULO DE TOTALES (PROHIBIDO)",
            r"def.*calculate.*total": "Función de cálculo (usar extracción)",
            r"\.calculate\(": "Llamada a método calculate()",
        }

        import re
        for py_file in self.src.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                for pattern, description in deprecated_patterns.items():
                    if re.search(pattern, content, re.IGNORECASE):
                        self.issues.append({
                            "type": "DEPRECATED_PATTERN",
                            "severity": "CRITICAL",
                            "path": str(py_file),
                            "pattern": description
                        })
            except Exception:
                pass

    def _print_report(self):
        """Imprime reporte de problemas encontrados"""
        print("\n" + "="*80)
        print("REPORTE DE LIMPIEZA")
        print("="*80)

        by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
        for issue in self.issues:
            by_severity[issue["severity"]].append(issue)

        total = len(self.issues)
        print(f"\nTotal de problemas encontrados: {total}\n")

        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            issues = by_severity[severity]
            if not issues:
                continue

            icon = {"CRITICAL": "[!]", "HIGH": "[!!]", "MEDIUM": "[*]", "LOW": "[i]"}
            print(f"\n{icon[severity]} {severity} ({len(issues)} problemas)")
            print("-" * 80)

            for i, issue in enumerate(issues, 1):
                print(f"\n{i}. {issue['type']}")
                if 'path' in issue:
                    print(f"   Archivo: {issue['path']}")
                if 'reason' in issue:
                    print(f"   Razón: {issue['reason']}")
                if 'detail' in issue:
                    print(f"   Detalle: {issue['detail']}")
                if 'recommendation' in issue:
                    print(f"   Recomendación: {issue['recommendation']}")

    def generate_cleanup_script(self, output_path: str = "PLAN_LIMPIEZA.md"):
        """Genera un plan de limpieza en Markdown"""

        plan = f"""# Plan de Limpieza del Proyecto
## Generado automáticamente

**Total de problemas:** {len(self.issues)}

## Prioridad 1: CRÍTICO 🚨

Acciones inmediatas requeridas:

"""
        critical = [i for i in self.issues if i["severity"] == "CRITICAL"]
        for issue in critical:
            plan += f"- [ ] **{issue['type']}**: {issue.get('path', 'N/A')}\n"
            plan += f"  - {issue.get('pattern', issue.get('detail', 'N/A'))}\n\n"

        plan += "\n## Prioridad 2: ALTA ⚠️\n\nDeben resolverse pronto:\n\n"
        high = [i for i in self.issues if i["severity"] == "HIGH"]
        for issue in high:
            plan += f"- [ ] **{issue['type']}**: {issue.get('path', 'N/A')}\n"
            plan += f"  - {issue.get('detail', 'N/A')}\n\n"

        plan += "\n## Prioridad 3: MEDIA ⚡\n\nMejorarían la calidad del código:\n\n"
        medium = [i for i in self.issues if i["severity"] == "MEDIUM"]
        for issue in medium:
            plan += f"- [ ] **{issue['type']}**: {issue.get('path', issue.get('field', 'N/A'))}\n"
            if 'locations' in issue:
                plan += f"  - Ubicaciones: {', '.join(issue['locations'])}\n"
            if 'recommendation' in issue:
                plan += f"  - Acción: {issue['recommendation']}\n"
            plan += "\n"

        plan += "\n## Acciones Recomendadas\n\n"
        plan += """
### 1. Eliminar Código Obsoleto
```bash
# Revisar y eliminar si no se usan:
rm -f src/models/factura_parser.py  # Si está obsoleto
rm -f src/core/app.py               # Si no se usa
```

### 2. Limpieza de Base de Datos
```sql
-- Eliminar columna redundante (cuando sea seguro)
ALTER TABLE facturas DROP COLUMN version_algoritmo;
```

### 3. Consolidar Modelos
- Eliminar campos duplicados
- Unificar lógica en un solo lugar

### 4. Actualizar Documentación
- Eliminar referencias a módulos deprecados
- Actualizar diagramas de arquitectura

### 5. Tests
- Eliminar tests de módulos deprecados
- Actualizar tests con nueva arquitectura
"""

        output = Path(output_path)
        output.write_text(plan, encoding='utf-8')
        print(f"\n✓ Plan de limpieza generado: {output}")


def main():
    """Ejecuta el análisis de limpieza"""
    project_root = Path(__file__).parent.parent

    cleaner = ProjectCleaner(str(project_root))
    cleaner.analyze()
    cleaner.generate_cleanup_script()

    print("\n" + "="*80)
    print("PRÓXIMOS PASOS:")
    print("="*80)
    print("""
1. Revisar el archivo PLAN_LIMPIEZA.md generado
2. Hacer backup antes de eliminar archivos
3. Ejecutar limpieza gradualmente (por prioridad)
4. Correr tests después de cada cambio
5. Hacer commit de cada grupo de cambios

COMANDO SEGURO PARA EMPEZAR:
  git status  # Ver qué archivos tienes sin commitear
  git add .   # Agregar cambios actuales
  git commit -m "Checkpoint antes de limpieza"
    """)


if __name__ == "__main__":
    main()
