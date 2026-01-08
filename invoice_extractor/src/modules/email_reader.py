# src/modules/email_reader.py
from __future__ import annotations
import base64
import io
import zipfile
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta

from src.utils.logger import logger
from src.utils.nit_utils import completar_nit_con_dv
from src.modules.auth import GraphAuth
from src.modules.graph_client import get_user_messages, get_message_attachments, get_attachment_content_binary
from src.modules.attachments import save_attachment


class EmailReader:
    
    # Magic bytes para identificación de tipos de archivo
    MAGIC_BYTES = {
        'pdf': b'%PDF-',
        'xml': b'<?xml',
        'xml_alt': b'<Invoice',
        'xml_alt2': b'<ApplicationResponse',
        'zip': b'PK\x03\x04',
        'zip_empty': b'PK\x05\x06',
        'zip_spanned': b'PK\x07\x08'
    }
    
    # Tamaños máximos permitidos (en bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_ZIP_SIZE = 100 * 1024 * 1024  # 100 MB
    
    # Extensiones permitidas
    ALLOWED_EXTENSIONS = {'.pdf', '.xml', '.zip'}
    
    def __init__(self, cfg: Dict[str, Any], timeout: int = 60):
        self.timeout = timeout
        self.auth = GraphAuth(
            cfg["TENANT_ID_CORREOS"],
            cfg["CLIENT_ID_CORREOS"],
            cfg["CLIENT_SECRET_CORREOS"],
            timeout=timeout,
        )

        # Estadísticas de procesamiento
        self.stats = {
            'archivos_procesados': 0,
            'archivos_rechazados': 0,
            'archivos_guardados': 0,
            'razones_rechazo': {}
        }


    def _extract_nit_base(self, nit: str) -> str:
        """
        Extrae la parte base del NIT (sin digito verificador).

        Maneja formatos:
        - "800185347-6" -> "800185347"
        - "800185347" -> "800185347"

        Args:
            nit: NIT en cualquier formato

        Returns:
            NIT base sin digito verificador
        """
        if not nit:
            return ""
        if "-" in nit:
            return nit.split("-")[0]
        return nit

    def _filter_for_nit(
        self,
        nit: str,
        last_days: Optional[int] = None,
        fecha_desde: Optional[datetime] = None
    ) -> str:
        """
        Genera una expresión de filtro OData para buscar mensajes que contengan el NIT.
        NO incluye '&$filter=' ya que será agregado por el cliente Graph.

        Args:
            nit: NIT a buscar
            last_days: Días hacia atrás (usado solo si fecha_desde no está presente)
            fecha_desde: Fecha específica desde la cual buscar (extracción incremental)
        """
        since_clause = ""

        if fecha_desde:
            # Extracción incremental: usar fecha específica
            dt_str = fecha_desde.strftime("%Y-%m-%dT%H:%M:%SZ")
            since_clause = f" and receivedDateTime ge {dt_str}"
            logger.info("Usando extracción incremental desde: %s", dt_str)
        elif last_days:
            # Fallback: usar ventana de días
            dt = (datetime.now(timezone.utc) - timedelta(days=last_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            since_clause = f" and receivedDateTime ge {dt}"
            logger.info("Usando ventana de %d días desde: %s", last_days, dt)

        # Devolver solo la expresión del filtro
        # Extraer NIT base (sin digito verificador) para busqueda flexible
        nit_base = self._extract_nit_base(nit)

        # Buscar ambos formatos: con y sin digito verificador
        # Esto es critico para compatibilidad con correos historicos
        filter_expr = (
            f"(contains(subject, '{nit}') or contains(body/content, '{nit}') or "
            f"contains(subject, '{nit_base}') or contains(body/content, '{nit_base}'))"
        )

        return f"{filter_expr}{since_clause}"

    def _validate_file_type(self, content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Valida el tipo de archivo mediante magic bytes y extensión.
        
        Args:
            content: Contenido binario del archivo
            filename: Nombre del archivo
            
        Returns:
            Tuple[bool, Optional[str]]: (es_válido, razón_rechazo)
        """
        # Verificar tamaño
        size = len(content)
        if size > self.MAX_FILE_SIZE:
            return False, f"Archivo excede tamaño máximo: {size} bytes > {self.MAX_FILE_SIZE} bytes"
        
        if size == 0:
            return False, "Archivo vacío"
        
        # Verificar extensión
        extension = self._get_file_extension(filename)
        if extension not in self.ALLOWED_EXTENSIONS:
            return False, f"Extensión no permitida: {extension}"
        
        # Validar magic bytes según extensión
        if extension == '.pdf':
            return self._validate_pdf(content)
        elif extension == '.xml':
            return self._validate_xml(content)
        elif extension == '.zip':
            return self._validate_zip(content)
        
        return False, "Tipo de archivo no reconocido"

    def _get_file_extension(self, filename: str) -> str:
        """Obtiene la extensión del archivo en minúsculas."""
        import os
        return os.path.splitext(filename.lower())[1]

    def _validate_pdf(self, content: bytes) -> Tuple[bool, Optional[str]]:
        """Valida que el contenido sea realmente un PDF."""
        if not content.startswith(self.MAGIC_BYTES['pdf']):
            return False, "Archivo con extensión .pdf no contiene magic bytes de PDF"
        
        # Verificación adicional: buscar marcadores EOF de PDF
        if b'%%EOF' not in content[-1024:]:
            logger.warning("PDF sin marcador EOF válido, posible corrupción")
        
        return True, None

    def _validate_xml(self, content: bytes) -> Tuple[bool, Optional[str]]:
        """Valida que el contenido sea realmente un XML."""
        # Verificar declaración XML o tags de factura electrónica
        has_xml_declaration = content.startswith(self.MAGIC_BYTES['xml'])
        has_invoice_tag = content.startswith(self.MAGIC_BYTES['xml_alt'])
        has_response_tag = content.startswith(self.MAGIC_BYTES['xml_alt2'])
        
        if not (has_xml_declaration or has_invoice_tag or has_response_tag):
            # Verificar si hay espacios/BOM antes de la declaración XML
            content_stripped = content.lstrip()
            if not content_stripped.startswith(self.MAGIC_BYTES['xml']):
                return False, "Archivo con extensión .xml no contiene estructura XML válida"
        
        # Validación adicional: verificar que sea XML bien formado
        try:
            # Solo verificar primeros 1KB para eficiencia
            sample = content[:1024].decode('utf-8', errors='ignore')
            if '<' not in sample or '>' not in sample:
                return False, "Archivo .xml no contiene tags XML"
        except Exception:
            return False, "Archivo .xml con encoding inválido"
        
        return True, None

    def _validate_zip(self, content: bytes) -> Tuple[bool, Optional[str]]:
        """Valida que el contenido sea realmente un ZIP."""
        # Verificar magic bytes de ZIP
        valid_zip_signatures = [
            self.MAGIC_BYTES['zip'],
            self.MAGIC_BYTES['zip_empty'],
            self.MAGIC_BYTES['zip_spanned']
        ]
        
        if not any(content.startswith(sig) for sig in valid_zip_signatures):
            return False, "Archivo con extensión .zip no contiene magic bytes de ZIP"
        
        # Verificar tamaño específico para ZIP
        if len(content) > self.MAX_ZIP_SIZE:
            return False, f"ZIP excede tamaño máximo: {len(content)} > {self.MAX_ZIP_SIZE}"
        
        # Validar que sea un ZIP válido intentando abrirlo
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Verificar que no esté corrupto
                if zf.testzip() is not None:
                    return False, "ZIP corrupto detectado"
                
                # Verificar que contenga archivos
                if len(zf.namelist()) == 0:
                    return False, "ZIP vacío (sin archivos)"
                
        except zipfile.BadZipFile:
            return False, "ZIP inválido o corrupto"
        except Exception as exc:
            return False, f"Error validando ZIP: {exc}"
        
        return True, None

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitiza el nombre de archivo para prevenir path traversal y caracteres peligrosos.
        
        Args:
            filename: Nombre original del archivo
            
        Returns:
            str: Nombre sanitizado
        """
        import re
        import os
        
        # Remover path (tomar solo basename)
        filename = os.path.basename(filename)
        
        # Remover caracteres peligrosos
        filename = re.sub(r'[^\w\s\-\.]', '_', filename)
        
        # Prevenir nombres vacíos o que empiecen con punto
        if not filename or filename.startswith('.'):
            filename = f"attachment_{filename}"
        
        # Limitar longitud
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:190] + ext
        
        return filename

    def _extract_cufe_from_xml_quick(self, content: bytes) -> Optional[str]:
        """
        Extrae el CUFE del XML sin parseo completo (método rápido).

        El CUFE es el identificador único de la factura electrónica (UUID DIAN).
        Se encuentra en el tag <cbc:UUID> del XML.

        Args:
            content: Contenido del archivo XML en bytes

        Returns:
            CUFE normalizado (lowercase, sin guiones) o None si no se encuentra

        Ejemplos:
            <cbc:UUID>08001365050512500067543abc123def456</cbc:UUID>
            Retorna: "08001365050512500067543abc123def456"
        """
        try:
            # Decodificar contenido a string
            content_str = content.decode('utf-8', errors='ignore')

            # Buscar tag <cbc:UUID> con regex
            # Patrón: <cbc:UUID [atributos opcionales]>VALOR</cbc:UUID>
            import re
            pattern = r'<cbc:UUID[^>]*>([a-f0-9\-]+)</cbc:UUID>'
            match = re.search(pattern, content_str, re.IGNORECASE)

            if match:
                # Normalizar CUFE: lowercase, sin guiones
                cufe_raw = match.group(1)
                cufe_normalized = cufe_raw.replace('-', '').lower().strip()

                logger.debug(
                    "✅ CUFE extraído rápidamente: %s... (longitud: %d)",
                    cufe_normalized[:20], len(cufe_normalized)
                )

                return cufe_normalized

            # No se encontró tag UUID
            logger.warning("⚠️ No se encontró tag <cbc:UUID> en XML")
            return None

        except UnicodeDecodeError as e:
            logger.warning("⚠️ Error decodificando XML como UTF-8: %s", e)
            return None
        except Exception as e:
            logger.error("❌ Error extrayendo CUFE del XML: %s", e, exc_info=True)
            return None

    def download_emails_and_attachments(
        self,
        nit: str,
        user_id: str,
        top: int = 50,
        last_days: Optional[int] = None,
        fetch_limit: Optional[int] = None,
        fecha_desde: Optional[datetime] = None
    ) -> List[str]:
        """
        Descarga correos y adjuntos con validación de seguridad.

        Args:
            nit: NIT del proveedor a buscar
            user_id: ID del usuario de correo
            top: Cantidad de mensajes por página
            last_days: Filtrar mensajes de últimos N días (solo si fecha_desde no está presente)
            fetch_limit: Límite de mensajes a procesar
            fecha_desde: Fecha específica desde la cual extraer (extracción incremental)

        Returns:
            List[str]: Rutas de archivos guardados exitosamente
        """
        # Resetear estadísticas
        self.stats = {
            'archivos_procesados': 0,
            'archivos_rechazados': 0,
            'archivos_guardados': 0,
            'razones_rechazo': {}
        }

        token = self.auth.get_token()
        filter_q = self._filter_for_nit(nit, last_days, fecha_desde)
        logger.info("Buscando mensajes para user=%s nit=%s", user_id, nit)
        
        select_fields = "id,subject,receivedDateTime,from,toRecipients,hasAttachments"
        messages = get_user_messages(
            token=token,
            user_id=user_id,
            top=top,
            filter_query=filter_q,
            select=select_fields,
            timeout=self.timeout,
            max_messages=fetch_limit
        )

        logger.info("Mensajes recuperados: %d", len(messages))
        for idx, m in enumerate(messages):
            logger.debug(
                "Mensaje[%d]: id=%s, subject=%s, hasAttachments=%s", 
                idx, m.get("id"), m.get("subject"), m.get("hasAttachments")
            )

        saved_files: List[str] = []
        processed = 0
        
        for m in messages:
            if fetch_limit is not None and processed >= fetch_limit:
                logger.info("Límite de procesamiento alcanzado: %d", fetch_limit)
                break
                
            if not m.get("hasAttachments"):
                continue
                
            message_id = m["id"]
            try:
                attachments = get_message_attachments(
                    token=token,
                    user_id=user_id,
                    message_id=message_id,
                    timeout=self.timeout
                )
            except Exception as exc:
                logger.warning(
                    "Error getting attachments for %s: %s", message_id, exc
                )
                continue

            saved = self._process_attachments(attachments, nit, message_id, user_id, token)
            saved_files.extend(saved)
            processed += 1

        # Log de estadísticas finales
        logger.info("=" * 60)
        logger.info("ESTADÍSTICAS DE PROCESAMIENTO")
        logger.info("=" * 60)
        logger.info("Archivos procesados: %d", self.stats['archivos_procesados'])
        logger.info("Archivos guardados: %d", self.stats['archivos_guardados'])
        logger.info("Archivos rechazados: %d", self.stats['archivos_rechazados'])
        
        if self.stats['razones_rechazo']:
            logger.info("Razones de rechazo:")
            for razon, count in self.stats['razones_rechazo'].items():
                logger.info("  - %s: %d", razon, count)
        
        logger.info("=" * 60)
        
        return saved_files

    def _process_attachments(
        self, attachments: List[dict], nit: str, message_id: str, user_id: str, token: str
    ) -> List[str]:
        """
        Procesa adjuntos con validación de seguridad.

        ESTRATEGIA DUAL:
        - ESTRATEGIA 1: Intentar obtener contentBytes directamente (adjuntos regulares)
        - ESTRATEGIA 2: Si no hay contentBytes, descargar vía /$value (adjuntos inline)

        Args:
            attachments: Lista de adjuntos del mensaje
            nit: NIT del proveedor
            message_id: ID del mensaje
            user_id: ID del usuario para descargas inline
            token: Bearer token OAuth2 para descargas inline

        Returns:
            List[str]: Rutas de archivos guardados
        """
        saved: List[str] = []

        for att in attachments:
            name = att.get("name", "adjunto_sin_nombre")
            att_id = att.get("id")
            self.stats['archivos_procesados'] += 1

            content = None

            # ESTRATEGIA 1: Intentar obtener contentBytes directamente
            if "contentBytes" in att:
                try:
                    content = base64.b64decode(att["contentBytes"])
                    logger.debug("Estrategia 1 exitosa para %s", name)
                except Exception as exc:
                    logger.warning("Error decodificando base64 para %s: %s", name, exc)
                    self._register_rejection("Error decodificando base64")
                    continue

            # ESTRATEGIA 2: Si no hay contentBytes, descargar vía /$value (adjuntos inline)
            elif att_id:
                logger.debug("Estrategia 1 falló para %s, intentando Estrategia 2 (/$value)", name)
                try:
                    content = get_attachment_content_binary(
                        token=token,
                        user_id=user_id,
                        message_id=message_id,
                        attachment_id=att_id,
                        timeout=self.timeout
                    )

                    if content:
                        logger.debug("Estrategia 2 exitosa para %s via /$value", name)
                    else:
                        logger.warning("Estrategia 2 falló para %s: no se pudo descargar via /$value", name)
                        self._register_rejection("No se pudo descargar adjunto inline")
                        continue

                except Exception as exc:
                    logger.warning("Error en Estrategia 2 para %s: %s", name, exc)
                    self._register_rejection("Error descargando adjunto inline")
                    continue
            else:
                logger.debug("Adjunto %s sin contentBytes ni ID disponible", name)
                self._register_rejection("Sin contentBytes ni ID de adjunto")
                continue

            # Si no tenemos contenido, pasar al siguiente adjunto
            if not content:
                continue

            # Sanitizar nombre de archivo
            safe_name = self._sanitize_filename(name)

            # Validar tipo de archivo
            is_valid, rejection_reason = self._validate_file_type(content, safe_name)

            if not is_valid:
                logger.warning(
                    "Archivo rechazado '%s' (mensaje: %s): %s",
                    safe_name, message_id, rejection_reason
                )
                self._register_rejection(rejection_reason)
                continue

            lname = safe_name.lower()

            # Procesar según tipo de archivo
            if lname.endswith(".zip"):
                saved.extend(self._handle_zip(content, nit, message_id, safe_name))
            elif lname.endswith((".pdf", ".xml")):
                # === EXTRACCIÓN DE CUFE (2025-12-27 - NOMENCLATURA ESTANDARIZADA) ===
                # Si es XML, extraer CUFE rápidamente para renombrar con nomenclatura estándar
                cufe = None
                if lname.endswith(".xml"):
                    cufe = self._extract_cufe_from_xml_quick(content)
                    if cufe:
                        logger.info(
                            "✅ CUFE extraído para nomenclatura estándar: %s...",
                            cufe[:20]
                        )

                # Guardar con nomenclatura estándar (pasando CUFE si se extrajo)
                path = save_attachment(content, safe_name, nit, message_id, cufe=cufe)
                if path:  # ignorar duplicados
                    logger.info("Saved %s", path)
                    saved.append(str(path))
                    self.stats['archivos_guardados'] += 1
            else:
                logger.debug("Ignored attachment %s (tipo no soportado)", safe_name)
                self._register_rejection("Tipo de archivo no soportado")

        return saved

    def _handle_zip(self, zip_bytes: bytes, nit: str, message_id: str, zip_name: str) -> List[str]:
        """
        Maneja archivos ZIP con validación de seguridad y procesamiento por lotes.

        ESTRATEGIA (2025-12-27 - PROCESAMIENTO POR LOTES):
        ===================================================
        1. Extraer TODOS los archivos del ZIP en memoria
        2. Identificar el XML y extraer el CUFE (fuente de verdad)
        3. Usar ese CUFE para guardar AMBOS archivos (XML + PDF) con nomenclatura estándar
        4. Garantizar atomicidad: Si hay PDF + XML, ambos se guardan con el mismo CUFE

        Args:
            zip_bytes: Contenido del ZIP
            nit: NIT del proveedor
            message_id: ID del mensaje
            zip_name: Nombre del archivo ZIP

        Returns:
            List[str]: Rutas de archivos extraídos
        """
        saved: List[str] = []

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                # FASE 1: Extraer TODOS los archivos del ZIP en memoria
                archivos_zip = {}  # {nombre_sanitizado: contenido_bytes}

                for inner in zf.infolist():
                    safe_inner_name = self._sanitize_filename(inner.filename)

                    if not safe_inner_name.lower().endswith((".pdf", ".xml")):
                        logger.debug("Ignored file in ZIP: %s", safe_inner_name)
                        continue

                    # Leer contenido
                    try:
                        data = zf.read(inner)
                    except Exception as exc:
                        logger.warning(
                            "Error reading %s from ZIP %s: %s",
                            safe_inner_name, zip_name, exc
                        )
                        continue

                    # Validar contenido extraído
                    is_valid, rejection_reason = self._validate_file_type(data, safe_inner_name)

                    if not is_valid:
                        logger.warning(
                            "Archivo en ZIP rechazado '%s' (ZIP: %s): %s",
                            safe_inner_name, zip_name, rejection_reason
                        )
                        self._register_rejection(f"En ZIP: {rejection_reason}")
                        continue

                    # Guardar en memoria para procesamiento por lotes
                    archivos_zip[safe_inner_name] = data

                # FASE 2: Identificar XML y extraer CUFE (fuente de verdad)
                cufe_extraido = None

                for nombre, contenido in archivos_zip.items():
                    if nombre.lower().endswith(".xml"):
                        cufe_extraido = self._extract_cufe_from_xml_quick(contenido)
                        if cufe_extraido:
                            logger.info(
                                "✅ CUFE extraído de XML en ZIP: %s...",
                                cufe_extraido[:20]
                            )
                            break  # Usar el primer XML con CUFE válido

                # FASE 3: Guardar TODOS los archivos con el mismo CUFE
                for nombre, contenido in archivos_zip.items():
                    # Usar el CUFE extraído del XML para TODOS los archivos del ZIP
                    # (incluyendo el PDF hermano)
                    p = save_attachment(contenido, nombre, nit, message_id, cufe=cufe_extraido)
                    if p:  # ignorar duplicados
                        logger.info("Extracted %s from ZIP %s", p, zip_name)
                        saved.append(str(p))
                        self.stats['archivos_guardados'] += 1

        except zipfile.BadZipFile as exc:
            logger.error("Corrupt ZIP in message %s (nombre: %s): %s", message_id, zip_name, exc)
            self._register_rejection("ZIP corrupto")
        except Exception as exc:
            logger.error("Error processing ZIP %s: %s", zip_name, exc)
            self._register_rejection(f"Error procesando ZIP: {type(exc).__name__}")

        return saved

    def _register_rejection(self, reason: str):
        """Registra una razón de rechazo en las estadísticas."""
        self.stats['archivos_rechazados'] += 1
        if reason in self.stats['razones_rechazo']:
            self.stats['razones_rechazo'][reason] += 1
        else:
            self.stats['razones_rechazo'][reason] = 1

    def get_processing_stats(self) -> Dict[str, Any]:
        """Retorna las estadísticas de procesamiento actual."""
        return self.stats.copy()