#src/core/app.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import time
import json
import datetime

from src.utils.logger import get_logger
from src.core.config import load_config, Settings
from src.modules.email_reader import EmailReader
# ACTUALIZADO: Usar InvoiceParserFacade directamente
from src.facade.invoice_parser_facade import InvoiceParserFacade as FacturaParser
from src.modules.storage import LocalJSONWriter, WriterInterface

logger = get_logger("App")


class App:
    """
    Aplicación principal para procesamiento de facturas.
    
    Flujo:
    1. Lee correos con facturas adjuntas
    2. Descarga archivos XML
    3. Parsea y extrae datos
    4. Guarda resultados en JSON
    """
    
    def __init__(self, cfg: Settings, writer: WriterInterface | None = None):
        """
        Inicializa la aplicación.
        
        Args:
            cfg: Configuración de la aplicación
            writer: Writer personalizado (opcional, por defecto LocalJSONWriter)
        """
        self.cfg = cfg
        self.writer = writer or LocalJSONWriter()
        self.email_reader = EmailReader(cfg.dict())

    def _validate(self) -> bool:
        """
        Valida la configuración requerida.
        
        Returns:
            True si la configuración es válida, False en caso contrario
        """
        missing = []
        for field in ("TENANT_ID_CORREOS", "CLIENT_ID_CORREOS", "CLIENT_SECRET_CORREOS"):
            if not getattr(self.cfg, field, None):
                missing.append(field)
        
        if missing:
            logger.error("Missing env vars: %s", missing)
            return False
        
        if not self.cfg.users:
            logger.error("settings.json does not contain users")
            return False
        
        return True

    def run(self) -> int:
        """
        Ejecuta el proceso completo de extracción de facturas.

        Returns:
            Código de salida (0 = éxito, 1 = error)
        """
        logger.info("Start process")

        if not self._validate():
            return 1

        # Procesar cada usuario
        for user in self.cfg.users:
            logger.info("Processing user %s", user.email)

            # Procesar cada NIT del usuario
            for idx, nit in enumerate(user.nits):
                try:
                    self._process_nit(user, nit)
                except Exception as e:
                    logger.error(
                        "Error procesando NIT %s para usuario %s: %s",
                        nit, user.email, e
                    )
                    # Continuar con el siguiente NIT en lugar de fallar

                # Agregar delay entre NITs para evitar rate limiting
                if idx < len(user.nits) - 1:
                    delay = 2  # 2 segundos entre NITs
                    logger.debug(
                        "Esperando %ds antes de procesar siguiente NIT",
                        delay
                    )
                    time.sleep(delay)

        logger.info("Process finished")
        return 0
    
    def _process_nit(self, user, nit: str) -> None:
        """
        Procesa facturas para un NIT específico con extracción incremental.
        Maneja checkpoints para rastrear última búsqueda exitosa.

        Args:
            user: Configuración del usuario
            nit: NIT a procesar
        """
        # Usar los nuevos métodos para extracción incremental
        fetch_limit = user.get_fetch_limit()
        top = min(fetch_limit, 1000)  # Máximo permitido por Graph API

        # Obtener fecha de inicio para extracción incremental
        fecha_desde = user.get_fecha_inicio()
        last_days = (
            user.ventana_inicial_dias
            if user.es_primera_ejecucion()
            else None
        )

        if fecha_desde:
            logger.info(
                "Downloading attachments for NIT %s "
                "(INCREMENTAL desde %s, fetch_limit=%d)",
                nit, fecha_desde.isoformat(), fetch_limit
            )
        else:
            logger.info(
                "Downloading attachments for NIT %s "
                "(PRIMERA EJECUCION, ventana=%d días, fetch_limit=%d)",
                nit, last_days, fetch_limit
            )

        saved_files = self.email_reader.download_emails_and_attachments(
            nit,
            user.email,
            top=top,
            last_days=last_days,
            fetch_limit=fetch_limit,
            fecha_desde=fecha_desde
        )

        if not saved_files:
            logger.info(
                "No new files found for NIT %s (sin cambios desde última "
                "búsqueda exitosa)",
                nit
            )
            # Registrar checkpoint incluso sin archivos nuevos
            self._save_checkpoint(user.email, nit)
            return

        logger.info("Processing %d files for NIT %s", len(saved_files), nit)
        batch = self._process_files(saved_files, nit, user.cuenta_id)

        # Guardar consolidado si hay facturas procesadas
        if batch:
            logger.info(
                "Saving consolidated data for NIT %s (%d invoices)",
                nit, len(batch)
            )
            self.writer.save_consolidado(batch, nit)

        # Guardar checkpoint de última búsqueda exitosa
        self._save_checkpoint(user.email, nit)
    
    def _process_files(self, saved_files: List[str], nit: str, cuenta_correo_id: int = None) -> List[Dict[str, Any]]:
        """
        Procesa una lista de archivos XML.
        
        Args:
            saved_files: Lista de rutas a archivos XML
            nit: NIT asociado a las facturas
            
        Returns:
            Lista de facturas procesadas
        """
        batch = []
        errors = 0
        
        for file in saved_files:
            p = Path(file)
            
            # Solo procesar archivos XML
            if p.suffix.lower() != ".xml":
                logger.debug("Skipping non-XML file: %s", p.name)
                continue
            
            try:
                data = self._parse_invoice(p)
                data['cuenta_correo_id'] = cuenta_correo_id
                if data:
                    # Guardar factura individual
                    fn = data.get("numero_factura") or p.stem
                    self.writer.save_factura(data, fn, nit)
                    batch.append(data)
                    logger.debug("Processed invoice: %s", fn)
                else:
                    errors += 1
                    logger.warning("Failed to extract data from %s", p.name)
            except Exception as exc:
                errors += 1
                logger.error("Error processing %s: %s", p.name, exc)
        
        logger.info(
            "NIT %s: Processed %d invoices, %d errors",
            nit, len(batch), errors
        )
        
        return batch
    
    def _parse_invoice(self, xml_path: Path) -> Dict[str, Any] | None:
        """
        Parsea una factura XML.

        Args:
            xml_path: Ruta al archivo XML

        Returns:
            Diccionario con datos de la factura o None si hay error
        """
        # Usar el wrapper de compatibilidad (delega a InvoiceParserFacade)
        parser = FacturaParser(xml_path)

        if not parser.load():
            logger.warning("Could not load XML: %s", xml_path)
            return None

        data = parser.extract()

        if not data:
            logger.warning("Could not extract data from: %s", xml_path)
            return None

        return data

    def _get_checkpoint_file(self, user_email: str, nit: str) -> Path:
        """
        Obtiene la ruta del archivo de checkpoint para un usuario y NIT.

        Args:
            user_email: Email del usuario
            nit: NIT a procesar

        Returns:
            Path al archivo de checkpoint
        """
        checkpoint_dir = Path.cwd() / ".checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        # Crear nombre seguro del archivo
        safe_email = user_email.replace("@", "_at_").replace(".", "_")
        safe_nit = nit.replace("-", "_")
        return checkpoint_dir / f"{safe_email}_{safe_nit}.json"

    def _save_checkpoint(self, user_email: str, nit: str) -> None:
        """
        Guarda checkpoint de última búsqueda exitosa.

        Args:
            user_email: Email del usuario
            nit: NIT procesado
        """
        try:
            checkpoint_file = self._get_checkpoint_file(user_email, nit)
            checkpoint_data = {
                "user_email": user_email,
                "nit": nit,
                "timestamp": datetime.datetime.now().isoformat(),
            }
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint_data, f, indent=2)
            logger.debug(
                "Checkpoint guardado para NIT %s en %s",
                nit, checkpoint_file
            )
        except Exception as e:
            logger.warning(
                "Error guardando checkpoint para NIT %s: %s",
                nit, e
            )

    def _load_checkpoint(
        self, user_email: str, nit: str
    ) -> Dict[str, Any] | None:
        """
        Carga checkpoint de última búsqueda exitosa.

        Args:
            user_email: Email del usuario
            nit: NIT a procesar

        Returns:
            Datos del checkpoint o None si no existe
        """
        try:
            checkpoint_file = self._get_checkpoint_file(user_email, nit)
            if not checkpoint_file.exists():
                return None

            with open(checkpoint_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(
                "Error cargando checkpoint para NIT %s: %s",
                nit, e
            )
            return None
