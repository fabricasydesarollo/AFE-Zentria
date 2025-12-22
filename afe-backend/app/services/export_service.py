"""
Servicio de exportación de facturas a CSV/Excel.

Este servicio permite generar reportes completos sin límites de paginación,
ideal para análisis empresarial y auditorías.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from io import StringIO, BytesIO
import csv
from datetime import datetime

from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.models.workflow_aprobacion import AsignacionNitResponsable
from sqlalchemy import and_, desc


def export_facturas_to_csv(
    db: Session,
    nit: Optional[str] = None,
    responsable_id: Optional[int] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    estado: Optional[str] = None,
    max_records: int = 50000  # Límite de seguridad
) -> str:
    """
    Exporta facturas a formato CSV.

    Args:
        db: Sesión de base de datos
        nit: Filtro por NIT de proveedor
        responsable_id: Filtro por responsable (permisos)
        fecha_desde: Fecha inicial del rango
        fecha_hasta: Fecha final del rango
        estado: Filtro por estado
        max_records: Límite máximo de registros (seguridad)

    Returns:
        String con contenido CSV
    """
    # Construir query base
    query = db.query(Factura).join(Proveedor)

    # Aplicar filtros
    if responsable_id:
        # Obtener NITs asignados al usuario
        nits_asignados = db.query(AsignacionNitResponsable.nit).filter(
            and_(
                AsignacionNitResponsable.responsable_id == responsable_id,
                AsignacionNitResponsable.activo == True
            )
        )
        query = query.filter(Proveedor.nit.in_(nits_asignados))

    if nit:
        query = query.filter(Proveedor.nit == nit)

    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)

    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)

    if estado:
        query = query.filter(Factura.estado == estado)

    # Ordenar cronológicamente
    query = query.order_by(
        desc(Factura.fecha_emision),
        desc(Factura.id)
    )

    # Limitar registros para seguridad
    facturas = query.limit(max_records).all()

    # Generar CSV
    output = StringIO()
    writer = csv.writer(output)

    # Escribir encabezados (actualizado sin campos obsoletos)
    headers = [
        'ID',
        'Número Factura',
        'CUFE',
        'Fecha Emisión',
        'Año',
        'Mes',
        'NIT Proveedor',
        'Nombre Proveedor',
        'Subtotal',
        'IVA',
        'Total',
        'Estado',
        'Cantidad Items',
        'Fecha Vencimiento',
        'Aprobado Por',
        'Fecha Aprobación',
        'Creado En'
    ]
    writer.writerow(headers)

    # Escribir datos
    for factura in facturas:
        # Calcular año/mes desde fecha_emision
        año = factura.fecha_emision.year if factura.fecha_emision else ''
        mes = factura.fecha_emision.month if factura.fecha_emision else ''

        # Contar items de la factura
        cantidad_items = len(factura.items) if factura.items else 0

        row = [
            factura.id,
            factura.numero_factura,
            factura.cufe or '',
            factura.fecha_emision.strftime('%Y-%m-%d') if factura.fecha_emision else '',
            año,
            mes,
            factura.proveedor.nit if factura.proveedor else '',
            factura.proveedor.razon_social if factura.proveedor else '',
            float(factura.subtotal or 0),
            float(factura.iva or 0),
            float(factura.total_a_pagar or 0),
            factura.estado.value if hasattr(factura.estado, 'value') else str(factura.estado),
            cantidad_items,
            factura.fecha_vencimiento.strftime('%Y-%m-%d') if factura.fecha_vencimiento else '',
            factura.aprobado_por_workflow or '',
            factura.fecha_aprobacion_workflow.strftime('%Y-%m-%d %H:%M:%S') if factura.fecha_aprobacion_workflow else '',
            factura.creado_en.strftime('%Y-%m-%d %H:%M:%S') if factura.creado_en else ''
        ]
        writer.writerow(row)

    return output.getvalue()


def get_export_metadata(
    db: Session,
    responsable_id: Optional[int] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
) -> dict:
    """
    Obtiene metadata del dataset a exportar.

    Returns:
        Dict con total de registros, rango de fechas, etc.
    """
    query = db.query(Factura).join(Proveedor)

    if responsable_id:
        # Obtener NITs asignados al usuario
        nits_asignados = db.query(AsignacionNitResponsable.nit).filter(
            and_(
                AsignacionNitResponsable.responsable_id == responsable_id,
                AsignacionNitResponsable.activo == True
            )
        )
        query = query.filter(Proveedor.nit.in_(nits_asignados))

    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)

    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)

    total = query.count()

    return {
        "total_registros": total,
        "fecha_desde": fecha_desde.strftime('%Y-%m-%d') if fecha_desde else None,
        "fecha_hasta": fecha_hasta.strftime('%Y-%m-%d') if fecha_hasta else None,
        "timestamp_generacion": datetime.utcnow().isoformat()
    }
