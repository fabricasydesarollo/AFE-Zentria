# src/modules/storage.py

from __future__ import annotations
import json
import tempfile
import os
from decimal import Decimal
from pathlib import Path
from typing import Protocol, Union, Dict, Any, List
from src.utils.logger import logger
from src.utils.deduplication import make_factura_key, deduplicate_facturas, load_index_from_file


class WriterInterface(Protocol):
    def save_factura(self, factura: dict, filename: str, nit: str) -> None:
        ...

    def save_consolidado(self, batch: list, nit: str) -> None:
        ...



class DecimalEncoder(json.JSONEncoder):
    """
    Serializa Decimal como string con 2 decimales para precisión monetaria.
    """
    def default(self, o):
        if isinstance(o, Decimal):
            quant = o.quantize(Decimal("0.01"))
            return format(quant, "f")
        return super().default(o)

class LocalJSONWriter:
    """
    Escritor local de JSON que evita duplicados y realiza escritura atómica.
    - Mantiene .index.json en la carpeta del NIT con {clave_unica: filename}
    - Al guardar factura individual comprueba el index y evita reescritura si ya existe.
    - Al guardar consolidado combina lo ya existente en disco con el batch y deduplica.
    """
    INDEX_FILENAME = ".index.json"

    def __init__(self, output_dir: Union[str, Path] = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _nit_dir(self, nit: str) -> Path:
        d = self.output_dir / str(nit)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _index_path(self, nit: str) -> Path:
        return self._nit_dir(nit) / self.INDEX_FILENAME

    def _load_index(self, nit: str) -> Dict[str, str]:
        p = self._index_path(nit)
        return load_index_from_file(p)

    def _save_index(self, nit: str, index: Dict[str, str]) -> None:
        p = self._index_path(nit)
        try:
            self._atomic_write_json(p, json.dumps(index, ensure_ascii=False, indent=2))
        except Exception as exc:
            logger.error("No se pudo guardar el índice para NIT %s: %s", nit, exc)

    @staticmethod
    def _atomic_write_json(path: Path, data: str) -> None:
        dirpath = path.parent
        dirpath.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=str(dirpath))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.replace(tmp_path, str(path))
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def save_factura(self, factura: dict, filename: str, nit: str) -> None:
        """
        Guarda la factura en output/<nit>/<filename>.json si su clave única no está en el índice.
        Escritura atómica y actualiza el índice con la nueva clave -> filename.
        """
        nit_dir = self._nit_dir(nit)
        index = self._load_index(nit)
        key = make_factura_key(factura)
        existing = index.get(key)
        if existing:
            logger.info("Factura duplicada detectada para NIT %s (clave=%s). Archivo existente: %s. Se omite guardado.",
                        nit, key, existing)
            return
        base_name = str(filename)
        target = nit_dir / f"{base_name}.json"
        counter = 1
        while target.exists():
            candidate_name = f"{base_name}__{counter}.json"
            target = nit_dir / candidate_name
            counter += 1
        try:
            json_text = json.dumps(factura, ensure_ascii=False, indent=2, cls=DecimalEncoder)
            self._atomic_write_json(target, json_text)
            index[key] = target.name
            self._save_index(nit, index)
            logger.info("Factura guardada: %s (clave=%s)", target, key)
        except Exception as exc:
            logger.error("Error guardando factura %s para NIT %s: %s", target, nit, exc)

    def save_consolidado(self, batch: list, nit: str) -> None:
        """
        Guarda consolidado.json con la unión de lo existente en disco y el batch, deduplicado.
        Escritura atómica y bloqueo simple.
        """
        nit_dir = self._nit_dir(nit)
        consolidated_path = nit_dir / "consolidado.json"
        existing: List[Dict[str, Any]] = []
        if consolidated_path.exists():
            try:
                with open(consolidated_path, "r", encoding="utf-8") as fh:
                    existing = json.load(fh)
            except Exception as exc:
                logger.warning("No se pudo leer consolidado existente para NIT %s: %s. Se reemplazará.", nit, exc)
                existing = []
        combined = existing + list(batch)
        deduped = deduplicate_facturas(combined)
        try:
            json_text = json.dumps(deduped, ensure_ascii=False, indent=2, cls=DecimalEncoder)
            self._atomic_write_json(consolidated_path, json_text)
            logger.info("Consolidado guardado en %s (facturas=%d)", consolidated_path, len(deduped))
        except Exception as exc:
            logger.error("Error guardando consolidado NIT %s: %s", nit, exc)
