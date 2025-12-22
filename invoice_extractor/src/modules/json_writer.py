# src/modules/json_writer.py
from __future__ import annotations
import json
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List
from src.utils.logger import logger
from src.utils.deduplication import deduplicate_facturas

class DecimalEncoder(json.JSONEncoder):
    """
    Serializa Decimal como string con 2 decimales para precisión monetaria.
    Si prefieres float, cambia a float(o), pero puede perder precisión.
    """
    def default(self, o):
        if isinstance(o, Decimal):
            quant = o.quantize(Decimal("0.01"))
            return format(quant, "f")
        return super().default(o)


class JSONWriter:
    """
    Encargado de persistir facturas y consolidados en formato JSON.
    Ahora organiza los archivos en subcarpetas por NIT.
    """

    def __init__(self, output_dir: Path = Path("output")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------
    def _nit_dir(self, nit: str | int) -> Path:
        """
        Devuelve la carpeta para un NIT dentro de output/.
        La crea si no existe.
        """
        nit_dir = self.output_dir / str(nit)
        nit_dir.mkdir(parents=True, exist_ok=True)
        return nit_dir

    # --------------------------------------------------------------
    def save_factura(self, factura: Dict[str, Any], filename: str, nit: str | int) -> None:
        """
        Guarda una factura individual en JSON dentro de la carpeta del NIT.
        """
        path = self._nit_dir(nit) / f"{filename}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(factura, f, cls=DecimalEncoder, ensure_ascii=False, indent=2)
            logger.info("Factura guardada en JSON: %s", path)
        except (OSError, ValueError) as e:
            logger.error("Error guardando factura en JSON %s: %s", filename, e)

    # --------------------------------------------------------------
    def save_consolidado(self, batch: List[Dict[str, Any]], nit: str | int) -> None:
        """
        Guarda el consolidado de facturas en la carpeta del NIT, eliminando duplicados exactos usando deduplicate_facturas.
        """
        deduplicado = deduplicate_facturas(batch)
        path = self._nit_dir(nit) / "consolidado.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(deduplicado, f, cls=DecimalEncoder, ensure_ascii=False, indent=2)
            logger.info("Consolidado guardado en JSON: %s", path)
        except (OSError, ValueError) as e:
            logger.error("Error guardando consolidado del NIT %s: %s", nit, e)
