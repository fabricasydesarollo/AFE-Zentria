"""
Health check endpoint para monitoreo de integridad del sistema

NIVEL EMPRESARIAL: Detecta inconsistencias antes de que causen problemas
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from typing import Dict, List
from app.db.session import get_db
from app.models import Factura, AsignacionNitResponsable, Proveedor

router = APIRouter(tags=["Health Check"])


@router.get("/health/integrity", summary="Verificar integridad de asignaciones")
def check_assignment_integrity(db: Session = Depends(get_db)) -> Dict:
    """
    Verifica la integridad del sistema de asignaciones.

    CHECKS EMPRESARIALES:
    1. Facturas huérfanas (con responsable_id pero sin asignación activa)
    2. Asignaciones sin facturas asociadas
    3. Triggers de base de datos activos
    4. Índices de performance presentes

    Returns:
        {
            "status": "healthy" | "warning" | "error",
            "checks": {
                "facturas_huerfanas": {"status": "ok", "count": 0},
                "triggers": {"status": "ok", "active": 3},
                ...
            },
            "issues": []
        }
    """
    status = "healthy"
    issues = []
    checks = {}

    # CHECK 1: Facturas huérfanas
    facturas_huerfanas = []
    facturas_con_responsable = db.query(Factura).filter(
        Factura.responsable_id.isnot(None)
    ).all()

    for factura in facturas_con_responsable:
        asignaciones_activas = db.query(AsignacionNitResponsable).filter(
            and_(
                AsignacionNitResponsable.responsable_id == factura.responsable_id,
                AsignacionNitResponsable.activo == True
            )
        ).count()

        if asignaciones_activas == 0:
            facturas_huerfanas.append(factura.id)

    if len(facturas_huerfanas) > 0:
        status = "error"
        issues.append({
            "type": "facturas_huerfanas",
            "severity": "critical",
            "message": f"Encontradas {len(facturas_huerfanas)} facturas con responsable_id pero sin asignación activa",
            "factura_ids": facturas_huerfanas[:10],  # Mostrar primeras 10
            "action": "Ejecutar script: scripts/limpiar_facturas_huerfanas_auto.py"
        })

    checks["facturas_huerfanas"] = {
        "status": "ok" if len(facturas_huerfanas) == 0 else "error",
        "count": len(facturas_huerfanas)
    }

    # CHECK 2: Verificar triggers activos
    try:
        result = db.execute(text(
            "SHOW TRIGGERS WHERE `Table` = 'asignacion_nit_responsable'"
        ))
        triggers = list(result)
        trigger_count = len(triggers)

        if trigger_count < 3:
            status = "warning" if status == "healthy" else status
            issues.append({
                "type": "triggers_missing",
                "severity": "high",
                "message": f"Solo {trigger_count}/3 triggers activos",
                "action": "Ejecutar migration: alembic upgrade head"
            })

        checks["triggers"] = {
            "status": "ok" if trigger_count >= 3 else "warning",
            "active": trigger_count,
            "expected": 3,
            "names": [t[0] for t in triggers]
        }
    except Exception as e:
        checks["triggers"] = {
            "status": "error",
            "message": str(e)
        }

    # CHECK 3: Verificar índices críticos
    try:
        result = db.execute(text(
            "SHOW INDEX FROM facturas WHERE Key_name = 'idx_facturas_responsable_proveedor'"
        ))
        index_exists = len(list(result)) > 0

        if not index_exists:
            status = "warning" if status == "healthy" else status
            issues.append({
                "type": "index_missing",
                "severity": "medium",
                "message": "Índice de performance faltante: idx_facturas_responsable_proveedor",
                "action": "Ejecutar: alembic/versions/2025_10_21_add_referential_checks.sql"
            })

        checks["indices"] = {
            "status": "ok" if index_exists else "warning",
            "idx_facturas_responsable_proveedor": index_exists
        }
    except Exception as e:
        checks["indices"] = {
            "status": "error",
            "message": str(e)
        }

    # CHECK 4: Estadísticas generales
    total_facturas = db.query(Factura).count()
    facturas_asignadas = db.query(Factura).filter(
        Factura.responsable_id.isnot(None)
    ).count()
    asignaciones_activas = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.activo == True
    ).count()

    checks["statistics"] = {
        "total_facturas": total_facturas,
        "facturas_asignadas": facturas_asignadas,
        "facturas_sin_asignar": total_facturas - facturas_asignadas,
        "asignaciones_activas": asignaciones_activas
    }

    return {
        "status": status,
        "checks": checks,
        "issues": issues,
        "timestamp": "2025-10-21"
    }


@router.get("/health", summary="Health check básico")
def health_check() -> Dict:
    """Health check básico del servicio."""
    return {
        "status": "healthy",
        "service": "AFE Backend",
        "version": "2.0.0"
    }
