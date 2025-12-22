"""
Utilidades para cursor-based pagination empresarial.

Este módulo proporciona helpers para implementar paginación basada en cursores,
optimizada para datasets grandes (10k+ registros).
"""
import base64
from typing import Optional, Tuple
from datetime import datetime


def encode_cursor(timestamp: datetime, entity_id: int) -> str:
    """
    Codifica un cursor usando timestamp + ID para paginación.

    El cursor combina fecha de emisión + ID para garantizar:
    - Ordenamiento consistente
    - Unicidad absoluta
    - Navegación bidireccional

    Args:
        timestamp: Fecha de emisión de la factura
        entity_id: ID único de la factura

    Returns:
        String base64 del cursor (ejemplo: "MjAyNS0xMC0wOFQxMDowMDowMHwxMjM0NQ==")
    """
    cursor_str = f"{timestamp.isoformat()}|{entity_id}"
    return base64.b64encode(cursor_str.encode()).decode()


def decode_cursor(cursor: str) -> Optional[Tuple[datetime, int]]:
    """
    Decodifica un cursor en sus componentes (timestamp, id).

    Args:
        cursor: String base64 del cursor

    Returns:
        Tupla (datetime, int) o None si el cursor es inválido
    """
    try:
        decoded = base64.b64decode(cursor.encode()).decode()
        timestamp_str, entity_id_str = decoded.split('|')
        timestamp = datetime.fromisoformat(timestamp_str)
        entity_id = int(entity_id_str)
        return timestamp, entity_id
    except (ValueError, AttributeError):
        return None


def build_cursor_from_factura(factura) -> str:
    """
    Construye un cursor a partir de una factura.

    Args:
        factura: Objeto Factura con fecha_emision e id

    Returns:
        Cursor codificado en base64
    """
    return encode_cursor(factura.fecha_emision, factura.id)
