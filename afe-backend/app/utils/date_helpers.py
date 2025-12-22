"""
Utilidades profesionales para manejo de fechas y períodos.

Módulo de uso empresarial para operaciones comunes con fechas.
Centralizado para evitar redundancia.

Nivel: Fortune 500 Enterprise
Autor:  Backend Development Team
"""

from datetime import datetime, date
from typing import Union, Tuple
from sqlalchemy import func, and_
from sqlalchemy.orm import Session


class DateHelper:
    """
    Clase estática con utilidades de fecha de nivel enterprise.

    Principios:
    - Una sola fuente de verdad para operaciones con fechas
    - Métodos reutilizables en toda la aplicación
    - Documentación clara y ejemplos
    """

    @staticmethod
    def get_periodo_from_date(fecha: Union[datetime, date]) -> str:
        """
        Obtiene el período (YYYY-MM) de una fecha.

        IMPORTANTE: Esta es la ÚNICA forma de calcular período en todo el sistema.
        Garantiza consistencia.

        Args:
            fecha: datetime.date o datetime.datetime

        Returns:
            str: Período en formato "YYYY-MM"

        Ejemplo:
            >>> from datetime import date
            >>> DateHelper.get_periodo_from_date(date(2025, 11, 15))
            '2025-11'
        """
        if isinstance(fecha, datetime):
            return fecha.strftime('%Y-%m')
        elif isinstance(fecha, date):
            return datetime.combine(fecha, datetime.min.time()).strftime('%Y-%m')
        else:
            raise TypeError(f"Se esperaba date o datetime, se recibió {type(fecha)}")

    @staticmethod
    def get_current_periodo() -> str:
        """
        Obtiene el período actual (YYYY-MM).

        Returns:
            str: Período actual en formato "YYYY-MM"

        Ejemplo:
            >>> DateHelper.get_current_periodo()
            '2025-11'
        """
        return datetime.now().strftime('%Y-%m')

    @staticmethod
    def get_previous_periodo(periodo: str) -> str:
        """
        Obtiene el período anterior al especificado.

        Args:
            periodo: str en formato "YYYY-MM"

        Returns:
            str: Período anterior en formato "YYYY-MM"

        Ejemplo:
            >>> DateHelper.get_previous_periodo('2025-11')
            '2025-10'
            >>> DateHelper.get_previous_periodo('2025-01')
            '2024-12'
        """
        year, month = map(int, periodo.split('-'))

        if month == 1:
            return f"{year - 1}-12"
        else:
            return f"{year}-{month - 1:02d}"

    @staticmethod
    def create_periodo_filter(fecha_column, periodo: str):
        """
        Crea un filtro SQLAlchemy para filtrar por período.

        IMPORTANTE: Usar esta función en lugar de hacer comparaciones directas
        de campos que no existen.

        Args:
            fecha_column: Columna SQLAlchemy de tipo Date/DateTime
            periodo: str en formato "YYYY-MM"

        Returns:
            Condición SQLAlchemy para usar en .filter()

        Ejemplo:
            >>> query = db.query(Factura).filter(
            ...     DateHelper.create_periodo_filter(Factura.fecha_emision, '2025-11')
            ... )
        """
        year, month = map(int, periodo.split('-'))

        return and_(
            func.year(fecha_column) == year,
            func.month(fecha_column) == month
        )

    @staticmethod
    def create_periodo_range_filter(fecha_column, desde_periodo: str, hasta_periodo: str):
        """
        Crea un filtro para rango de períodos.

        Args:
            fecha_column: Columna SQLAlchemy de tipo Date/DateTime
            desde_periodo: str en formato "YYYY-MM"
            hasta_periodo: str en formato "YYYY-MM"

        Returns:
            Condición SQLAlchemy para usar en .filter()

        Ejemplo:
            >>> query = db.query(Factura).filter(
            ...     DateHelper.create_periodo_range_filter(
            ...         Factura.fecha_emision,
            ...         '2025-01',
            ...         '2025-11'
            ...     )
            ... )
        """
        desde_year, desde_month = map(int, desde_periodo.split('-'))
        hasta_year, hasta_month = map(int, hasta_periodo.split('-'))

        desde_date = date(desde_year, desde_month, 1)
        # Calcular último día del mes
        if hasta_month == 12:
            hasta_date = date(hasta_year + 1, 1, 1)
        else:
            hasta_date = date(hasta_year, hasta_month + 1, 1)

        return fecha_column.between(desde_date, hasta_date)

    @staticmethod
    def get_date_range_for_periodo(periodo: str) -> Tuple[date, date]:
        """
        Obtiene el rango de fechas (primer y último día) de un período.

        Args:
            periodo: str en formato "YYYY-MM"

        Returns:
            Tupla con (primer_dia, ultimo_dia) del período

        Ejemplo:
            >>> primer, ultimo = DateHelper.get_date_range_for_periodo('2025-11')
            >>> print(primer)  # 2025-11-01
            >>> print(ultimo)  # 2025-11-30
        """
        year, month = map(int, periodo.split('-'))

        primer_dia = date(year, month, 1)

        if month == 12:
            ultimo_dia = date(year + 1, 1, 1)
        else:
            ultimo_dia = date(year, month + 1, 1)

        # Retornar un día antes del primer día del siguiente mes
        ultimo_dia = date(ultimo_dia.year, ultimo_dia.month, ultimo_dia.day) - __import__('datetime').timedelta(days=1)

        return primer_dia, ultimo_dia
