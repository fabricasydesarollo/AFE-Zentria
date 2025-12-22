"""
Router administrativo para sincronización y mantenimiento
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.db.session import get_db
from app.core.security import require_role
from app.models.usuario import Usuario
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.utils.logger import logger

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post(
    "/sincronizar-facturas",
    summary="Sincronizar facturas con asignaciones de NITs",
    description="Reasigna TODAS las facturas basado en los NITs asignados en AsignacionNitResponsable"
)
def sincronizar_facturas(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """
    Sincroniza las facturas con las asignaciones de NITs.

    Cada factura será asignada al usuario cuyo NIT coincida
    con el proveedor de la factura en AsignacionNitResponsable.

    Retorna:
    - Total de facturas actualizadas
    - Total de facturas que ya estaban correctas
    - Detalles por responsable
    """
    try:
        usuarios = db.query(Usuario).all()

        total_actualizadas = 0
        total_ignoradas = 0
        detalles = []

        for resp in usuarios:
            # Obtener NITs asignados
            asignaciones = db.query(AsignacionNitResponsable.nit).filter(
                AsignacionNitResponsable.responsable_id == resp.id,
                AsignacionNitResponsable.activo == True
            ).all()

            nits_asignados = [nit for (nit,) in asignaciones if nit]

            if not nits_asignados:
                detalles.append({
                    "responsable": resp.nombre,
                    "actualizadas": 0,
                    "ignoradas": 0,
                    "nota": "Sin NITs asignados"
                })
                continue

            # Obtener proveedores con esos NITs
            proveedor_ids = db.query(Proveedor.id).filter(
                Proveedor.nit.in_(nits_asignados)
            ).all()
            proveedor_ids = [pid for (pid,) in proveedor_ids]

            if not proveedor_ids:
                detalles.append({
                    "responsable": resp.nombre,
                    "actualizadas": 0,
                    "ignoradas": 0,
                    "nota": f"{len(nits_asignados)} NITs pero sin proveedores en BD"
                })
                continue

            # Obtener facturas de esos proveedores
            facturas = db.query(Factura).filter(
                Factura.proveedor_id.in_(proveedor_ids)
            ).all()

            # Actualizar asignaciones
            actualizadas = 0
            ignoradas = 0

            for factura in facturas:
                if factura.responsable_id != resp.id:
                    factura.responsable_id = resp.id
                    actualizadas += 1
                else:
                    ignoradas += 1

            if actualizadas > 0:
                db.flush()

            detalles.append({
                "responsable": resp.nombre,
                "nits_asignados": len(nits_asignados),
                "proveedores": len(proveedor_ids),
                "facturas_totales": len(facturas),
                "actualizadas": actualizadas,
                "ignoradas": ignoradas
            })

            total_actualizadas += actualizadas
            total_ignoradas += ignoradas

        # Commit
        db.commit()

        logger.info(f"Sincronización completada por {current_user.usuario}: {total_actualizadas} actualizadas, {total_ignoradas} ignoradas")

        return {
            "exito": True,
            "total_actualizadas": total_actualizadas,
            "total_ignoradas": total_ignoradas,
            "detalles": detalles
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error en sincronización: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sincronizando: {str(e)}"
        )


@router.get(
    "/distribucion-facturas",
    summary="Ver distribución actual de facturas",
    description="Muestra cuántas facturas tiene asignado cada responsable"
)
def ver_distribucion_facturas(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """
    Retorna la distribución actual de facturas por responsable.
    """
    try:
        usuarios = db.query(Usuario).all()

        distribucion = []
        total_global = 0

        for resp in usuarios:
            total = db.query(func.count(Factura.id)).filter(
                Factura.responsable_id == resp.id
            ).scalar()

            asignaciones = db.query(func.count(AsignacionNitResponsable.id)).filter(
                AsignacionNitResponsable.responsable_id == resp.id,
                AsignacionNitResponsable.activo == True
            ).scalar()

            distribucion.append({
                "responsable_id": resp.id,
                "responsable_nombre": resp.nombre,
                "usuario": resp.usuario,
                "facturas": total,
                "nits_asignados": asignaciones
            })

            total_global += total

        return {
            "total_facturas": total_global,
            "usuarios": distribucion
        }

    except Exception as e:
        logger.error(f"Error obteniendo distribución: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo distribución: {str(e)}"
        )
