"""
API REST para el Flujo de Automatización de Facturas.

Endpoints principales:
- POST /ejecutar-flujo-completo: Ejecuta todo el flujo de automatización
- POST /comparar-aprobar: Ejecuta comparación y aprobación de facturas
- GET /estadisticas-flujo: Obtiene estadísticas del último flujo ejecutado
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from app.db.session import get_db
from app.services.flujo_automatizacion_facturas import FlujoAutomatizacionFacturas


router = APIRouter(prefix="/flujo-automatizacion", tags=["Flujo de Automatización"])


# ============================================================================
# SCHEMAS PYDANTIC
# ============================================================================

class EjecutarFlujoRequest(BaseModel):
    """Request para ejecutar el flujo completo."""
    periodo_analisis: Optional[str] = Field(
        None,
        description="Período a analizar en formato YYYY-MM. Si no se especifica, usa el mes actual"
    )
    solo_proveedores: Optional[List[int]] = Field(
        None,
        description="IDs de proveedores específicos a procesar. Si no se especifica, procesa todos"
    )


class CompararAprobarRequest(BaseModel):
    """Request para comparación y aprobación."""
    periodo_analisis: Optional[str] = Field(
        None,
        description="Período a analizar en formato YYYY-MM"
    )
    solo_proveedores: Optional[List[int]] = Field(
        None,
        description="IDs de proveedores específicos"
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/ejecutar-flujo-completo",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar flujo completo de automatización",
    description="""
    Ejecuta el flujo completo de automatización mensual de facturas:

    **Pasos del flujo:**
    1. Análisis de patrones históricos
    2. Comparación de facturas pendientes con patrones
    3. Aprobación automática o marcado para revisión
    4. Envío de notificaciones a usuarios

    **Uso recomendado:**
    - Ejecutar mensualmente después de marcar las facturas como pagadas
    - Puede ejecutarse manualmente o mediante tarea programada
    """
)
def ejecutar_flujo_completo(
    request: EjecutarFlujoRequest,
    db: Session = Depends(get_db)
):
    """
    Ejecuta el flujo completo de automatización de facturas.
    """
    try:
        flujo = FlujoAutomatizacionFacturas(db)

        # Ejecutar flujo completo
        resultado = flujo.ejecutar_flujo_automatizacion_completo(
            periodo_analisis=request.periodo_analisis,
            solo_proveedores=request.solo_proveedores
        )

        if not resultado['exito']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=resultado.get('mensaje', 'Error desconocido en flujo')
            )

        return {
            "success": True,
            "message": "Flujo de automatización ejecutado exitosamente",
            "data": resultado
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ejecutando flujo de automatización: {str(e)}"
        ) from e


@router.post(
    "/comparar-aprobar",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Comparar y aprobar facturas pendientes",
    description="""
    Compara facturas pendientes con patrones históricos y decide aprobación.

    **Lógica de decisión:**
    1. Para cada factura pendiente, busca su patrón histórico (proveedor + concepto)
    2. Si el patrón es auto-aprobable (TIPO_A o TIPO_B elegible):
       - Calcula desviación del monto actual vs promedio histórico
       - Si está dentro del umbral → Aprueba automáticamente
       - Si excede umbral → Marca para revisión manual
    3. Si no hay patrón histórico → Marca para revisión manual

    **Estados resultantes:**
    - aprobada_auto: Factura aprobada automáticamente
    - en_revision: Factura requiere revisión manual
    """
)
def comparar_aprobar_facturas(
    request: CompararAprobarRequest,
    db: Session = Depends(get_db)
):
    """
    Compara facturas pendientes y aprueba automáticamente cuando sea posible.
    """
    try:
        flujo = FlujoAutomatizacionFacturas(db)

        resultado = flujo.comparar_y_aprobar_facturas_pendientes(
            periodo_analisis=request.periodo_analisis,
            solo_proveedores=request.solo_proveedores
        )

        if not resultado['exito']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=resultado.get('mensaje', 'Error en comparación')
            )

        return {
            "success": True,
            "message": "Comparación y aprobación completada",
            "data": resultado
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en comparación y aprobación: {str(e)}"
        ) from e


@router.get(
    "/estadisticas-flujo",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Obtener estadísticas del flujo",
    description="""
    Retorna estadísticas del flujo de automatización.

    Incluye:
    - Total de facturas procesadas
    - Facturas aprobadas automáticamente
    - Facturas que requieren revisión
    - Tasa de automatización
    - Notificaciones enviadas
    """
)
def obtener_estadisticas_flujo(
    periodo: Optional[str] = Query(None, description="Período en formato YYYY-MM"),
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas del flujo de automatización.
    """
    try:
        from app.models.factura import Factura, EstadoFactura
        from sqlalchemy import func

        # Determinar período
        if not periodo:
            periodo = datetime.now().strftime('%Y-%m')

        # Estadísticas de facturas del período
        total_facturas = db.query(func.count(Factura.id)).filter(
            Factura.periodo_factura == periodo
        ).scalar()

        facturas_aprobadas_auto = db.query(func.count(Factura.id)).filter(
            Factura.periodo_factura == periodo,
            Factura.estado == EstadoFactura.aprobada_auto
        ).scalar()

        facturas_en_revision = db.query(func.count(Factura.id)).filter(
            Factura.periodo_factura == periodo,
            Factura.estado == EstadoFactura.en_revision
        ).scalar()

        facturas_pendientes = db.query(func.count(Factura.id)).filter(
            Factura.periodo_factura == periodo,
            Factura.estado == EstadoFactura.en_revision
        ).scalar()

        facturas_validadas = db.query(func.count(Factura.id)).filter(
            Factura.periodo_factura == periodo,
            Factura.estado == EstadoFactura.validada_contabilidad
        ).scalar()

        # Calcular tasa de automatización
        facturas_procesadas = facturas_aprobadas_auto + facturas_en_revision
        tasa_automatizacion = (
            (facturas_aprobadas_auto / facturas_procesadas * 100)
            if facturas_procesadas > 0 else 0
        )

        return {
            "success": True,
            "data": {
                "periodo": periodo,
                "total_facturas": total_facturas,
                "facturas_aprobadas_auto": facturas_aprobadas_auto,
                "facturas_en_revision": facturas_en_revision,
                "facturas_pendientes": facturas_pendientes,
                "facturas_validadas": facturas_validadas,
                "tasa_automatizacion": round(tasa_automatizacion, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        ) from e
