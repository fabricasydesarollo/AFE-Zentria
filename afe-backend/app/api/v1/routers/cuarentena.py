"""API Router para Gestión de Cuarentena de Facturas."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.db.session import get_db
from app.services.cuarentena_service import CuarentenaService
from app.core.security import require_role
from app.models.usuario import Usuario

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cuarentena",
    tags=["Cuarentena"]
)


@router.get(
    "/resumen",
    summary="Resumen ejecutivo de facturas en cuarentena",
    description="Obtiene resumen completo de facturas en cuarentena agrupadas por grupo/NIT con métricas de impacto"
)
def obtener_resumen_cuarentena(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(["superadmin", "admin"]))
) -> Dict[str, Any]:
    """Resumen ejecutivo de cuarentena."""
    try:

        service = CuarentenaService(db)
        resumen = service.obtener_resumen_cuarentena()

        logger.info(
            f"Resumen de cuarentena solicitado",
            extra={
                "usuario_id": current_user.id,
                "rol": current_user.rol.value,
                "total_facturas": resumen.get("total", 0)
            }
        )

        return resumen

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error obteniendo resumen de cuarentena: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener resumen de cuarentena"
        )


@router.get(
    "/grupo/{grupo_id}",
    summary="Facturas en cuarentena de un grupo específico",
    description="Obtiene lista detallada de facturas en cuarentena de un grupo"
)
def obtener_facturas_grupo(
    grupo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(["superadmin", "admin"]))
) -> Dict[str, Any]:
    """Facturas en cuarentena de un grupo."""
    try:

        service = CuarentenaService(db)
        facturas = service.obtener_facturas_cuarentena(grupo_id=grupo_id)

        return {
            "grupo_id": grupo_id,
            "total_facturas": len(facturas),
            "facturas": [
                {
                    "id": f.id,
                    "numero_factura": f.numero_factura,
                    "fecha_emision": str(f.fecha_emision),
                    "total_a_pagar": float(f.total_a_pagar or 0),
                    "proveedor": f.proveedor.nombre if f.proveedor else None,
                    "nit": f.proveedor.nit if f.proveedor else None,
                    "cufe": f.cufe
                }
                for f in facturas
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error obteniendo facturas del grupo {grupo_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener facturas del grupo {grupo_id}"
        )


@router.post(
    "/liberar/{grupo_id}",
    summary="Liberar facturas de un grupo",
    description="Libera TODAS las facturas en cuarentena de un grupo (se ejecuta automáticamente al asignar responsables)"
)
def liberar_facturas_grupo(
    grupo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(["superadmin", "admin"]))
) -> Dict[str, Any]:
    """Libera facturas de un grupo en cuarentena."""
    try:

        service = CuarentenaService(db)
        resultado = service.liberar_facturas_grupo(grupo_id)

        if not resultado.get('exito'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=resultado.get('error', 'Error al liberar facturas')
            )

        logger.info(
            f"Liberación de cuarentena ejecutada",
            extra={
                "grupo_id": grupo_id,
                "usuario_id": current_user.id,
                "facturas_liberadas": resultado.get("facturas_liberadas", 0)
            }
        )

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error liberando facturas del grupo {grupo_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al liberar facturas del grupo {grupo_id}"
        )
