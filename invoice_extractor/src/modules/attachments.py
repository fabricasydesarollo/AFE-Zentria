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

def save_attachment(
    content: Union[bytes, memoryview],
    filename: str,
    nit: str,
    correo_id: str,
    cufe: str = None
) -> Path | None:
    """
    Guarda un adjunto en adjuntos/<nit>/ con nomenclatura ESTANDARIZADA.

    ARQUITECTURA 2025-12-27:
    ========================
    - Si se provee CUFE → renombra a {CUFE}.{ext} (nomenclatura estándar)
    - Si NO hay CUFE → guarda temporalmente con hash (se renombrará después)

    Se deduplica por hash SHA256 del contenido.

    Args:
        content: Contenido del archivo en bytes
        filename: Nombre original del archivo (del proveedor)
        nit: NIT del proveedor
        correo_id: ID del correo de origen
        cufe: CUFE de la factura (opcional, pero REQUERIDO para nomenclatura estándar)

    Returns:
        Path del archivo guardado, o None si era duplicado

    Ejemplos:
        # XML con CUFE → Nomenclatura estándar
        save_attachment(xml_bytes, "FACTURA.xml", "800136505", "msg123", cufe="08001365...")
        Resultado: adjuntos/800136505/08001365050512500067543abc123def456.xml

        # PDF sin CUFE → Temporal (se renombrará al procesar XML)
        save_attachment(pdf_bytes, "DOC.pdf", "800136505", "msg123", cufe=None)
        Resultado: adjuntos/800136505/temp_abc12345_DOC.pdf
    """
    nit_s = _sanitize_folder_name(nit)
    folder = ADJUNTOS_ROOT / nit_s
    folder.mkdir(parents=True, exist_ok=True)

    index_path = folder / INDEX_FILENAME
    index = _load_index(index_path)

    content_bytes = bytes(content)
    key = _sha256(content_bytes)

    # === DEDUPLICACIÓN CON MIGRACIÓN AUTOMÁTICA ===
    extension = Path(filename).suffix.lower()

    if key in index:
        existing_filename = index[key]
        existing_path = folder / existing_filename

        # Si el archivo existente tiene nomenclatura temporal Y ahora tenemos CUFE válido,
        # RENOMBRAR al estándar profesional
        if (existing_filename.startswith("temp_") and
            cufe and
            extension in ['.pdf', '.xml'] and
            existing_path.exists()):

            cufe_sanitized = cufe.lower().strip()
            nuevo_nombre = f"{cufe_sanitized}{extension}"
            nuevo_path = folder / nuevo_nombre

            # Renombrar archivo temporal a nomenclatura estándar
            try:
                # Verificar si el archivo destino ya existe
                if nuevo_path.exists():
                    # Verificar si tienen el mismo contenido
                    hash_destino = _sha256(nuevo_path.read_bytes())

                    if hash_destino == key:
                        # El archivo con nombre correcto ya existe con el mismo contenido
                        # Eliminar el temp_* y actualizar índice
                        existing_path.unlink()
                        index[key] = nuevo_nombre
                        _save_index(index_path, index)

                        logger.info(
                            "🔄 LIMPIADO: %s (archivo correcto %s ya existía)",
                            existing_filename, nuevo_nombre
                        )
                        return nuevo_path
                    else:
                        # Contenido diferente - no debería pasar, pero por seguridad
                        logger.error(
                            "⚠️ CONFLICTO: %s existe pero con contenido diferente",
                            nuevo_nombre
                        )
                        return existing_path if existing_path.exists() else None

                # Si no existe, hacer el rename normal
                existing_path.rename(nuevo_path)

                # Actualizar índice con nuevo nombre
                index[key] = nuevo_nombre
                _save_index(index_path, index)

                logger.info(
                    "🔄 MIGRADO: %s → %s (hash=%s...)",
                    existing_filename, nuevo_nombre, key[:8]
                )
                return nuevo_path

            except Exception as e:
                logger.error(
                    "❌ Error renombrando %s a %s: %s",
                    existing_filename, nuevo_nombre, e
                )
                # Si falla el renombre, continuar con el archivo existente
                return existing_path if existing_path.exists() else None

        # Archivo ya existe con nomenclatura correcta (no es temp_*)
        logger.info(
            "📋 Adjunto duplicado detectado para NIT=%s (hash=%s). Ya existe como %s",
            nit, key[:8], existing_filename
        )
        return existing_path if existing_path.exists() else None

    # === NOMENCLATURA ESTANDARIZADA (2025-12-27) ===
    # (extension ya definida arriba en línea 82)

    if cufe and extension in ['.pdf', '.xml']:
        # ✅ NOMENCLATURA ESTÁNDAR: {CUFE}.{extension}
        cufe_sanitized = cufe.lower().strip()
        nombre_estandar = f"{cufe_sanitized}{extension}"
        filepath = folder / nombre_estandar

        logger.info(
            "✅ Guardando con nomenclatura estándar: %s → %s",
            filename, nombre_estandar
        )

        # Detectar colisión (mismo CUFE, archivo ya existe)
        if filepath.exists():
            # Verificar si es el mismo contenido
            existing_hash = _sha256(filepath.read_bytes())

            if existing_hash == key:
                # Mismo contenido, mismo CUFE → Es un duplicado legítimo
                logger.info(
                    "📋 Archivo con mismo CUFE y contenido ya existe: %s",
                    nombre_estandar
                )
                index[key] = filepath.name
                _save_index(index_path, index)
                return None  # Ya existe, no guardar
            else:
                # ⚠️ COLISIÓN: Mismo CUFE pero contenido diferente (caso ANORMAL)
                logger.error(
                    "🚨 COLISIÓN CRÍTICA: CUFE %s... ya existe con contenido DIFERENTE. "
                    "Esto NO debería ocurrir (CUFE debe ser único por factura).",
                    cufe[:20]
                )
                # Agregar sufijo de versión para no perder datos
                counter = 1
                while filepath.exists():
                    nombre_colision = f"{cufe_sanitized}_v{counter}{extension}"
                    filepath = folder / nombre_colision
                    counter += 1

                logger.warning(
                    "⚠️ Guardando versión alternativa: %s",
                    filepath.name
                )

    else:
        # ⚠️ FALLBACK: Sin CUFE o archivo no estándar (.zip, etc.)
        # Guardar temporalmente con hash del contenido
        if cufe is None and extension in ['.pdf', '.xml']:
            # Archivo PDF/XML sin CUFE → Temporal (se renombrará después)
            hash_prefix = key[:8]
            nombre_temporal = f"temp_{hash_prefix}_{_sanitize_folder_name(filename)}"
            filepath = folder / nombre_temporal

            logger.warning(
                "⚠️ Guardando temporalmente sin CUFE (tipo=%s): %s → %s",
                extension, filename, nombre_temporal
            )
        else:
            # Otros tipos de archivo (.zip, etc.) → Nombre sanitizado
            filepath = folder / _sanitize_folder_name(filename)
            counter = 1
            while filepath.exists():
                filepath = folder / f"{counter}_{_sanitize_folder_name(filename)}"
                counter += 1

            logger.debug(
                "📦 Guardando archivo no estándar (tipo=%s): %s",
                extension, filename
            )

    # === GUARDAR ARCHIVO ===
    with open(filepath, "wb") as fh:
        fh.write(content_bytes)

    # Actualizar índice de deduplicación
    index[key] = filepath.name
    _save_index(index_path, index)

    logger.info("💾 Archivo guardado: %s (hash=%s...)", filepath.name, key[:8])
    return filepath
