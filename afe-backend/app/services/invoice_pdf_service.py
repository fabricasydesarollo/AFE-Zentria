# app/services/invoice_pdf_service.py
"""Servicio para acceder a PDFs y XMLs almacenados por invoice_extractor."""

import os
from pathlib import Path
from typing import Optional, Dict, Tuple
import xml.etree.ElementTree as ET
from app.models.factura import Factura
from app.utils.logger import logger


class InvoicePDFService:
    """Servicio para acceder a PDFs y XMLs de facturas desde invoice_extractor."""

    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent.parent / "invoice_extractor" / "adjuntos"

        if not self.base_path.exists():
            logger.warning(
                f"Directorio de invoice_extractor no encontrado: {self.base_path}. "
                f"Los PDFs no estarán disponibles."
            )

    def get_pdf_path(self, factura: Factura) -> Optional[Path]:
        """Construye la ruta al PDF de una factura con múltiples estrategias de búsqueda."""
        if not factura:
            logger.warning("Factura es None")
            return None

        if not factura.proveedor or not factura.proveedor.nit:
            logger.warning(
                f"Factura {factura.id} sin proveedor/NIT asignado",
                extra={"factura_id": factura.id}
            )
            return None

        nit = factura.proveedor.nit

        # Seguridad: prevenir path traversal
        if ".." in nit or "/" in nit or "\\" in nit:
            logger.error(f"Intento de path traversal detectado en NIT: {nit}")
            return None

        nit_dir = self.base_path / nit

        if not nit_dir.exists():
            logger.warning(
                f"Directorio del NIT no encontrado: {nit_dir}",
                extra={"factura_id": factura.id, "nit": nit}
            )
            return None

        # ESTRATEGIA 0: Lookup directo con pdf_filename (O(1))
        if factura.pdf_filename:
            pdf_path = nit_dir / factura.pdf_filename

            if pdf_path.exists() and self._is_safe_path(pdf_path):
                logger.info(
                    f"PDF encontrado vía pdf_filename (O(1) - nomenclatura estándar)",
                    extra={
                        "factura_id": factura.id,
                        "numero_factura": factura.numero_factura,
                        "pdf_filename": factura.pdf_filename,
                        "estrategia": "pdf_filename_directo"
                    }
                )
                return pdf_path
            else:
                logger.warning(
                    f"pdf_filename en BD pero archivo no existe: {factura.pdf_filename}",
                    extra={
                        "factura_id": factura.id,
                        "numero_factura": factura.numero_factura,
                        "pdf_filename": factura.pdf_filename
                    }
                )

        # ESTRATEGIA 1: Buscar con CUFE directo
        if factura.cufe:
            cufe_lower = factura.cufe.lower()
            pdf_path_directo = nit_dir / f"{cufe_lower}.pdf"

            if pdf_path_directo.exists() and self._is_safe_path(pdf_path_directo):
                logger.info(
                    f"PDF encontrado con CUFE directo (nomenclatura estándar)",
                    extra={
                        "factura_id": factura.id,
                        "numero_factura": factura.numero_factura,
                        "estrategia": "cufe_estandar"
                    }
                )
                return pdf_path_directo

            # Fallback a nomenclatura legacy con prefijo "fv"
            pdf_path_legacy = nit_dir / f"fv{cufe_lower}.pdf"

            if pdf_path_legacy.exists() and self._is_safe_path(pdf_path_legacy):
                logger.info(
                    f"PDF encontrado con nomenclatura LEGACY (prefijo fv)",
                    extra={
                        "factura_id": factura.id,
                        "numero_factura": factura.numero_factura,
                        "estrategia": "cufe_legacy_fv"
                    }
                )
                return pdf_path_legacy

        # ESTRATEGIA 2: Buscar con número de factura
        if factura.numero_factura:
            pdf_path_directo = nit_dir / f"{factura.numero_factura}.pdf"

            if pdf_path_directo.exists() and self._is_safe_path(pdf_path_directo):
                logger.info(
                    f"PDF encontrado con nomenclatura estandarizada",
                    extra={
                        "factura_id": factura.id,
                        "numero_factura": factura.numero_factura,
                        "estrategia": "nomenclatura_estandarizada"
                    }
                )
                return pdf_path_directo

            # Fallback a nomenclatura legacy con prefijos
            for prefix in ['fv', 'ad']:
                pdf_path_legacy = nit_dir / f"{prefix}{factura.numero_factura.lower()}.pdf"

                if pdf_path_legacy.exists() and self._is_safe_path(pdf_path_legacy):
                    logger.info(
                        f"PDF encontrado con nomenclatura legacy (prefijo {prefix})",
                        extra={
                            "factura_id": factura.id,
                            "numero_factura": factura.numero_factura,
                            "estrategia": f"legacy_prefix_{prefix}"
                        }
                    )
                    return pdf_path_legacy

        # ESTRATEGIA 3: Escanear directorio buscando match
        if factura.numero_factura:
            try:
                numero_limpio = factura.numero_factura.lower().replace("-", "").replace(" ", "")

                for pdf_file in nit_dir.glob("fv*.pdf"):
                    filename_lower = pdf_file.stem.lower()

                    if numero_limpio in filename_lower:
                        if self._is_safe_path(pdf_file):
                            logger.info(
                                f"PDF encontrado por escaneo (match parcial)",
                                extra={
                                    "factura_id": factura.id,
                                    "numero_factura": factura.numero_factura,
                                    "archivo_encontrado": pdf_file.name,
                                    "estrategia": "escaneo_directorio"
                                }
                            )
                            return pdf_file
            except Exception as e:
                logger.error(f"Error escaneando directorio {nit_dir}: {e}")

        # ESTRATEGIA 4: Parsear XMLs y buscar por CUFE
        if factura.cufe:
            try:
                pdf_path = self._find_pdf_by_xml_matching(nit_dir, factura.cufe)
                if pdf_path:
                    logger.info(
                        f"PDF encontrado parseando XMLs (CUFE match)",
                        extra={
                            "factura_id": factura.id,
                            "numero_factura": factura.numero_factura,
                            "archivo_encontrado": pdf_path.name,
                            "estrategia": "xml_parsing_cufe_match"
                        }
                    )
                    return pdf_path
            except Exception as e:
                logger.error(
                    f"Error en estrategia 4 (XML parsing): {e}",
                    extra={"factura_id": factura.id, "nit_dir": str(nit_dir)}
                )

        logger.warning(
            f"PDF no encontrado después de múltiples estrategias de búsqueda",
            extra={
                "factura_id": factura.id,
                "numero_factura": factura.numero_factura,
                "nit": nit,
                "cufe": factura.cufe[:50] if factura.cufe else None,
                "estrategias_intentadas": ["cufe_completo", "numero_factura", "escaneo_directorio"],
                "directorio": str(nit_dir)
            }
        )
        return None

    def _find_pdf_by_xml_matching(self, nit_dir: Path, cufe_buscado: str) -> Optional[Path]:
        """Encuentra PDF parseando XMLs y comparando UUIDs."""
        cufe_lower = cufe_buscado.lower().strip()

        for xml_file in nit_dir.glob("ad*.xml"):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                uuid_element = None

                for ns in [
                    '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}UUID',
                    'UUID',
                    '{*}UUID'
                ]:
                    uuid_element = root.find(f'.//{ns}')
                    if uuid_element is not None and uuid_element.text:
                        break

                if uuid_element is None or not uuid_element.text:
                    for elem in root.iter():
                        if elem.tag.endswith('UUID') and elem.text:
                            uuid_element = elem
                            break

                if uuid_element is not None and uuid_element.text:
                    uuid_xml = uuid_element.text.lower().strip()

                    if uuid_xml == cufe_lower:
                        xml_base = xml_file.stem
                        if xml_base.startswith('ad'):
                            pdf_base = 'fv' + xml_base[2:]
                            pdf_path = nit_dir / f"{pdf_base}.pdf"

                            if pdf_path.exists() and self._is_safe_path(pdf_path):
                                logger.info(
                                    "Match encontrado: XML UUID coincide con CUFE",
                                    extra={
                                        "xml_file": xml_file.name,
                                        "pdf_file": pdf_path.name,
                                        "cufe": cufe_buscado[:50]
                                    }
                                )
                                return pdf_path

            except ET.ParseError as e:
                logger.warning("XML mal formado, saltando: %s (error: %s)", xml_file.name, str(e))
                continue
            except Exception as e:
                logger.error("Error procesando XML %s: %s", xml_file.name, str(e))
                continue

        return None

    def _is_safe_path(self, pdf_path: Path) -> bool:
        """Verifica que el path esté dentro del base_path (prevención de path traversal)."""
        try:
            resolved_path = pdf_path.resolve()
            resolved_base = self.base_path.resolve()

            if not str(resolved_path).startswith(str(resolved_base)):
                logger.error(
                    "Path traversal detectado: %s",
                    resolved_path,
                    extra={"base_path": str(resolved_base)}
                )
                return False

            return True
        except Exception as e:
            logger.error("Error validando path %s: %s", pdf_path, e)
            return False

    def get_pdf_content(self, factura: Factura) -> Optional[bytes]:
        """Lee el contenido completo del PDF de una factura."""
        pdf_path = self.get_pdf_path(factura)

        if not pdf_path:
            return None

        try:
            with open(pdf_path, 'rb') as f:
                content = f.read()

            logger.info(
                f"PDF leído exitosamente: {len(content)} bytes",
                extra={
                    "factura_id": factura.id,
                    "file_size_bytes": len(content),
                    "file_size_mb": round(len(content) / (1024 * 1024), 2)
                }
            )
            return content

        except PermissionError as e:
            logger.error(
                f"Sin permisos para leer PDF: {pdf_path}",
                extra={"factura_id": factura.id, "error": str(e)}
            )
            return None

        except Exception as e:
            logger.error(
                f"Error leyendo PDF {pdf_path}: {str(e)}",
                extra={"factura_id": factura.id, "error_type": type(e).__name__}
            )
            return None

    def get_xml_path(self, factura: Factura) -> Optional[Path]:
        """Construye la ruta al XML de una factura electrónica."""
        if not factura or not factura.proveedor or not factura.cufe:
            return None

        nit = factura.proveedor.nit
        cufe_lower = factura.cufe.lower()

        # Seguridad: prevenir path traversal
        if ".." in nit or "/" in nit or "\\" in nit:
            logger.error(f"Intento de path traversal detectado en NIT: {nit}")
            return None

        xml_path = self.base_path / nit / f"ad{cufe_lower}.xml"

        try:
            xml_path = xml_path.resolve()
            if not str(xml_path).startswith(str(self.base_path.resolve())):
                logger.error(f"Path traversal detectado: {xml_path}")
                return None
        except Exception:
            return None

        return xml_path if xml_path.exists() else None

    def get_xml_content(self, factura: Factura) -> Optional[bytes]:
        """Lee el contenido del XML de una factura electrónica."""
        xml_path = self.get_xml_path(factura)

        if not xml_path:
            return None

        try:
            with open(xml_path, 'rb') as f:
                content = f.read()

            logger.info(
                f"XML leído exitosamente: {len(content)} bytes",
                extra={"factura_id": factura.id, "file_size_bytes": len(content)}
            )
            return content

        except Exception as e:
            logger.error(
                f"Error leyendo XML {xml_path}: {str(e)}",
                extra={"factura_id": factura.id}
            )
            return None

    def get_document_info(self, factura: Factura) -> Dict[str, any]:
        """Obtiene información sobre los documentos de una factura sin leerlos completamente."""
        result = {
            "pdf": {
                "exists": False,
                "path": None,
                "size_bytes": 0,
                "size_mb": 0.0,
                "filename": None
            },
            "xml": {
                "exists": False,
                "path": None,
                "size_bytes": 0,
                "size_kb": 0.0,
                "filename": None
            }
        }

        pdf_path = self.get_pdf_path(factura)
        if pdf_path:
            try:
                file_size = pdf_path.stat().st_size
                result["pdf"] = {
                    "exists": True,
                    "path": str(pdf_path),
                    "size_bytes": file_size,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                    "filename": pdf_path.name
                }
            except Exception as e:
                logger.error(f"Error obteniendo info de PDF: {e}")

        xml_path = self.get_xml_path(factura)
        if xml_path:
            try:
                file_size = xml_path.stat().st_size
                result["xml"] = {
                    "exists": True,
                    "path": str(xml_path),
                    "size_bytes": file_size,
                    "size_kb": round(file_size / 1024, 2),
                    "filename": xml_path.name
                }
            except Exception as e:
                logger.error(f"Error obteniendo info de XML: {e}")

        return result

    def validate_storage_availability(self) -> Tuple[bool, str]:
        """Valida que el storage de invoice_extractor esté disponible."""
        if not self.base_path.exists():
            return False, f"Directorio no encontrado: {self.base_path}"

        if not os.access(self.base_path, os.R_OK):
            return False, f"Sin permisos de lectura: {self.base_path}"

        try:
            nit_folders = [d for d in self.base_path.iterdir() if d.is_dir()]
            total_pdfs = sum(1 for nit_folder in nit_folders
                           for f in nit_folder.glob("fv*.pdf"))

            return True, f"Storage OK. {len(nit_folders)} NITs, {total_pdfs} PDFs disponibles"

        except Exception as e:
            return False, f"Error escaneando storage: {str(e)}"
