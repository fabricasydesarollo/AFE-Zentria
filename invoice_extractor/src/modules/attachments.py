# src/attachments.py
from __future__ import annotations
from pathlib import Path
import re
import hashlib
import json
from typing import Union, Dict
from src.utils.logger import logger

ADJUNTOS_ROOT = Path("adjuntos")
INDEX_FILENAME = ".attachments_index.json"


def _sanitize_folder_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", str(name))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_index(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_index(path: Path, index: Dict[str, str]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)

def save_attachment(content: Union[bytes, memoryview], filename: str, nit: str, correo_id: str) -> Path | None:
    """
    Guarda un adjunto en adjuntos/<nit>/ evitando duplicados.
    Se deduplica por hash SHA256 del contenido.
    Devuelve la ruta del archivo si se guardó, o None si era duplicado.
    """
    nit_s = _sanitize_folder_name(nit)
    folder = ADJUNTOS_ROOT / nit_s
    folder.mkdir(parents=True, exist_ok=True)

    index_path = folder / INDEX_FILENAME
    index = _load_index(index_path)

    content_bytes = bytes(content)
    key = _sha256(content_bytes)

    if key in index:
        logger.info(
            "Adjunto duplicado detectado para NIT=%s (hash=%s). Ya existe como %s",
            nit, key, index[key]
        )
        return None

    filepath = folder / _sanitize_folder_name(filename)
    counter = 1
    while filepath.exists():
        filepath = folder / f"{counter}_{_sanitize_folder_name(filename)}"
        counter += 1

    with open(filepath, "wb") as fh:
        fh.write(content_bytes)

    index[key] = filepath.name
    _save_index(index_path, index)

    logger.debug("Attachment saved %s (hash=%s)", filepath, key)
    return filepath
