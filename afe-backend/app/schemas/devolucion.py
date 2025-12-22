# app/schemas/devolucion.py
"""
Schemas para devolución de facturas por contabilidad.

Cuando un contador procesa una factura aprobada y encuentra algún problema
(falta información, datos incorrectos, etc.), puede devolverla al proveedor
solicitando correcciones.


Fecha: 2025-11-18
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DevolucionRequest(BaseModel):
    """
    Request para devolver una factura al proveedor.

    El contador debe especificar el motivo de la devolución para que
    el proveedor sepa qué corregir.
    """

    observaciones: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Motivo de la devolución (requerido, mínimo 10 caracteres)"
    )

    notificar_proveedor: bool = Field(
        True,
        description="Enviar email al proveedor (default: true)"
    )

    notificar_responsable: bool = Field(
        True,
        description="Enviar email al usuario que aprobó (default: true)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "observaciones": "Falta especificar el centro de costos del departamento de IT. Por favor incluir esta información en las observaciones de la factura.",
                "notificar_proveedor": True,
                "notificar_responsable": True
            }
        }


class DevolucionResponse(BaseModel):
    """
    Response después de procesar una devolución.
    """

    success: bool = Field(
        ...,
        description="Indica si la devolución fue exitosa"
    )

    factura_id: int = Field(
        ...,
        description="ID de la factura devuelta"
    )

    numero_factura: str = Field(
        ...,
        description="Número de la factura devuelta"
    )

    estado_anterior: str = Field(
        ...,
        description="Estado anterior de la factura"
    )

    estado_nuevo: str = Field(
        ...,
        description="Nuevo estado de la factura (devuelta)"
    )

    notificaciones_enviadas: int = Field(
        ...,
        description="Número de notificaciones enviadas"
    )

    destinatarios: list[str] = Field(
        default_factory=list,
        description="Lista de emails notificados"
    )

    mensaje: str = Field(
        ...,
        description="Mensaje descriptivo del resultado"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp de la devolución"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "factura_id": 123,
                "numero_factura": "CBOX566",
                "estado_anterior": "aprobada",
                "estado_nuevo": "devuelta_contabilidad",
                "notificaciones_enviadas": 2,
                "destinatarios": [
                    "proveedor@empresa.com",
                    "responsable@empresa.com"
                ],
                "mensaje": "Factura devuelta exitosamente. Se notificó al proveedor y al usuario.",
                "timestamp": "2025-11-18T10:30:00"
            }
        }
