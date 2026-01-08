import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from src.core.config import load_config
from src.services.factura_service import FacturaService
from src.utils.logger import get_logger


class IngestService:
    """
    Servicio de ingesta de facturas a base de datos con manejo robusto de transacciones.
    
    MEJORAS IMPLEMENTADAS:
    - Commits por batch para evitar pérdida masiva de datos
    - Rollback automático en caso de error
    - Logging detallado de progreso y errores
    - Manejo de excepciones granular
    - Estadísticas de ingesta al finalizar
    """
    
    # Configuración de batch
    DEFAULT_BATCH_SIZE = 50
    
    def __init__(self, cfg, batch_size: int = None):
        self.cfg = cfg
        self.logger = get_logger("IngestService")
        self.output_dir = getattr(cfg, "OUTPUT_DIR", "output")
        self.batch_size = batch_size or getattr(cfg, "INGEST_BATCH_SIZE", self.DEFAULT_BATCH_SIZE)
        
        # Inicializar motor de base de datos
        try:
            self.engine = create_engine(
                cfg.database_url,
                pool_pre_ping=True,  # Verificar conexiones antes de usar
                pool_recycle=3600,   # Reciclar conexiones cada hora
                echo=False           # Cambiar a True para debug SQL
            )
            self.Session = sessionmaker(bind=self.engine)
            self.logger.info("Motor de base de datos inicializado correctamente")
        except Exception as exc:
            self.logger.error("Error inicializando motor de base de datos: %s", exc)
            raise

    def ingest_to_db(self) -> dict:
        """
        Ingesta facturas desde archivos JSON consolidados a la base de datos.
        
        Returns:
            dict: Estadísticas de la ingesta con formato:
                {
                    'total_procesadas': int,
                    'total_exitosas': int,
                    'total_fallidas': int,
                    'nits_procesados': list,
                    'errores': list
                }
        """
        # Estadísticas de ingesta
        stats = {
            'total_procesadas': 0,
            'total_exitosas': 0,
            'total_fallidas': 0,
            'nits_procesados': [],
            'errores': []
        }
        
        # Verificar que el directorio de salida existe
        if not os.path.exists(self.output_dir):
            self.logger.warning("Directorio de salida no existe: %s", self.output_dir)
            return stats
        
        # Listar todos los NITs con datos
        nit_dirs = [d for d in os.listdir(self.output_dir) 
                    if os.path.isdir(os.path.join(self.output_dir, d))]
        
        if not nit_dirs:
            self.logger.warning("No se encontraron directorios de NIT en: %s", self.output_dir)
            return stats
        
        self.logger.info("Iniciando ingesta de facturas. NITs encontrados: %d", len(nit_dirs))
        self.logger.info("Tamaño de batch configurado: %d facturas", self.batch_size)
        
        # Procesar cada NIT
        for nit in nit_dirs:
            try:
                nit_stats = self._ingest_nit(nit)
                stats['total_procesadas'] += nit_stats['procesadas']
                stats['total_exitosas'] += nit_stats['exitosas']
                stats['total_fallidas'] += nit_stats['fallidas']
                stats['nits_procesados'].append(nit)
                
                if nit_stats['errores']:
                    stats['errores'].extend(nit_stats['errores'])
                    
            except Exception as exc:
                error_msg = f"Error procesando NIT {nit}: {exc}"
                self.logger.error(error_msg, exc_info=True)
                stats['errores'].append(error_msg)
        
        # Log de resumen final
        self.logger.info("=" * 60)
        self.logger.info("RESUMEN DE INGESTA")
        self.logger.info("=" * 60)
        self.logger.info("NITs procesados: %d", len(stats['nits_procesados']))
        self.logger.info("Facturas procesadas: %d", stats['total_procesadas'])
        self.logger.info("Facturas exitosas: %d", stats['total_exitosas'])
        self.logger.info("Facturas fallidas: %d", stats['total_fallidas'])
        
        if stats['errores']:
            self.logger.warning("Errores encontrados: %d", len(stats['errores']))
            for i, error in enumerate(stats['errores'][:10], 1):  # Mostrar primeros 10
                self.logger.warning("  [%d] %s", i, error)
            if len(stats['errores']) > 10:
                self.logger.warning("  ... y %d errores más", len(stats['errores']) - 10)
        
        self.logger.info("=" * 60)
        
        return stats

    def _ingest_nit(self, nit: str) -> dict:
        """
        Ingesta facturas de un NIT específico con commits por batch.
        
        Args:
            nit: Identificador del NIT a procesar
            
        Returns:
            dict: Estadísticas de la ingesta del NIT
        """
        nit_stats = {
            'procesadas': 0,
            'exitosas': 0,
            'fallidas': 0,
            'errores': []
        }
        
        nit_path = os.path.join(self.output_dir, nit)
        consolidado_path = os.path.join(nit_path, "consolidado.json")
        
        # Verificar que existe el archivo consolidado
        if not os.path.exists(consolidado_path):
            self.logger.debug("No existe consolidado.json para NIT %s", nit)
            return nit_stats
        
        # Cargar facturas del consolidado
        try:
            with open(consolidado_path, encoding="utf-8") as f:
                facturas = json.load(f)
        except json.JSONDecodeError as exc:
            error_msg = f"Error parseando JSON del NIT {nit}: {exc}"
            self.logger.error(error_msg)
            nit_stats['errores'].append(error_msg)
            return nit_stats
        except Exception as exc:
            error_msg = f"Error leyendo consolidado del NIT {nit}: {exc}"
            self.logger.error(error_msg)
            nit_stats['errores'].append(error_msg)
            return nit_stats
        
        if not facturas:
            self.logger.debug("No hay facturas en consolidado del NIT %s", nit)
            return nit_stats
        
        total_facturas = len(facturas)
        self.logger.info("Procesando NIT %s: %d facturas encontradas", nit, total_facturas)
        
        # Crear sesión para este NIT
        session = self.Session()
        factura_service = FacturaService(session)
        
        try:
            batch = []
            batch_number = 1
            
            for idx, factura in enumerate(facturas, 1):
                nit_stats['procesadas'] += 1
                batch.append((idx, factura))
                
                # Procesar batch cuando alcanza el tamaño configurado o es la última factura
                if len(batch) >= self.batch_size or idx == total_facturas:
                    batch_stats = self._process_batch(
                        session, 
                        factura_service, 
                        batch, 
                        nit, 
                        batch_number,
                        total_facturas
                    )
                    
                    nit_stats['exitosas'] += batch_stats['exitosas']
                    nit_stats['fallidas'] += batch_stats['fallidas']
                    nit_stats['errores'].extend(batch_stats['errores'])
                    
                    # Limpiar batch para siguiente iteración
                    batch = []
                    batch_number += 1
            
            self.logger.info(
                "NIT %s completado: %d exitosas, %d fallidas de %d totales",
                nit, nit_stats['exitosas'], nit_stats['fallidas'], nit_stats['procesadas']
            )
            
        except Exception as exc:
            error_msg = f"Error general procesando NIT {nit}: {exc}"
            self.logger.error(error_msg, exc_info=True)
            nit_stats['errores'].append(error_msg)
            
        finally:
            # Cerrar sesión siempre
            session.close()
        
        return nit_stats

    def _process_batch(
        self, 
        session, 
        factura_service: FacturaService, 
        batch: list, 
        nit: str,
        batch_number: int,
        total_facturas: int
    ) -> dict:
        """
        Procesa un batch de facturas con manejo de transacciones.
        
        Args:
            session: Sesión de SQLAlchemy
            factura_service: Servicio de facturas
            batch: Lista de tuplas (índice, factura)
            nit: NIT siendo procesado
            batch_number: Número del batch actual
            total_facturas: Total de facturas del NIT
            
        Returns:
            dict: Estadísticas del batch procesado
        """
        batch_stats = {
            'exitosas': 0,
            'fallidas': 0,
            'errores': []
        }
        
        batch_size = len(batch)
        start_idx = batch[0][0]
        end_idx = batch[-1][0]
        
        self.logger.info(
            "NIT %s - Batch #%d: Procesando facturas %d-%d de %d (tamaño: %d)",
            nit, batch_number, start_idx, end_idx, total_facturas, batch_size
        )
        
        try:
            # Procesar cada factura del batch
            for idx, factura in batch:
                try:
                    cuenta_correo_id = factura.get('cuenta_correo_id')
                    factura_service.procesar_factura(factura, cuenta_correo_id=cuenta_correo_id)
                    batch_stats['exitosas'] += 1
                    
                    # Log detallado solo en modo debug
                    self.logger.debug(
                        "NIT %s - Factura %d/%d procesada: %s",
                        nit, idx, total_facturas, 
                        factura.get('numero_factura', 'N/A')
                    )
                    
                except Exception as exc:
                    batch_stats['fallidas'] += 1
                    error_msg = (
                        f"NIT {nit} - Error en factura {idx}/{total_facturas} "
                        f"({factura.get('numero_factura', 'N/A')}): {exc}"
                    )
                    self.logger.error(error_msg)
                    batch_stats['errores'].append(error_msg)
                    
                    # Continuar con las demás facturas del batch
                    continue
            
            # Commit del batch completo si hubo al menos una factura exitosa
            if batch_stats['exitosas'] > 0:
                session.commit()
                self.logger.info(
                    "NIT %s - Batch #%d COMMIT exitoso: %d facturas guardadas",
                    nit, batch_number, batch_stats['exitosas']
                )
            else:
                # Si todas fallaron, hacer rollback
                session.rollback()
                self.logger.warning(
                    "NIT %s - Batch #%d: Todas las facturas fallaron, ROLLBACK aplicado",
                    nit, batch_number
                )
                
        except SQLAlchemyError as exc:
            # Error de base de datos - hacer rollback
            session.rollback()
            error_msg = (
                f"NIT {nit} - Error de base de datos en Batch #{batch_number}: {exc}"
            )
            self.logger.error(error_msg, exc_info=True)
            batch_stats['errores'].append(error_msg)
            
            # Marcar todas las facturas del batch como fallidas
            batch_stats['fallidas'] = batch_size
            batch_stats['exitosas'] = 0
            
        except Exception as exc:
            # Error inesperado - hacer rollback
            session.rollback()
            error_msg = (
                f"NIT {nit} - Error inesperado en Batch #{batch_number}: {exc}"
            )
            self.logger.error(error_msg, exc_info=True)
            batch_stats['errores'].append(error_msg)
            
            # Marcar todas las facturas del batch como fallidas
            batch_stats['fallidas'] = batch_size
            batch_stats['exitosas'] = 0
        
        return batch_stats

    def verify_database_connection(self) -> bool:
        """
        Verifica que la conexión a la base de datos está activa.
        
        Returns:
            bool: True si la conexión es exitosa
        """
        from sqlalchemy import text
        
        try:
            session = self.Session()
            session.execute(text("SELECT 1"))
            session.close()
            self.logger.info("Conexión a base de datos verificada correctamente")
            return True
        except Exception as exc:
            self.logger.error("Error verificando conexión a base de datos: %s", exc)
            return False

    def get_ingest_progress(self) -> dict:
        """
        Obtiene el progreso actual de la ingesta consultando la base de datos.
        
        Returns:
            dict: Información del progreso con formato:
                {
                    'total_facturas_db': int,
                    'facturas_por_nit': dict,
                    'ultima_fecha_procesamiento': str
                }
        """
        from sqlalchemy import text
        
        progress = {
            'total_facturas_db': 0,
            'facturas_por_nit': {},
            'ultima_fecha_procesamiento': None
        }
        
        try:
            session = self.Session()
            
            # Total de facturas en DB
            result = session.execute(text("SELECT COUNT(*) FROM facturas"))
            progress['total_facturas_db'] = result.scalar()
            
            # Facturas por proveedor (últimos 10 NITs)
            result = session.execute(text("""
                SELECT p.nit, p.razon_social, COUNT(f.id) as total
                FROM facturas f
                JOIN proveedores p ON f.proveedor_id = p.id
                GROUP BY p.nit, p.razon_social
                ORDER BY total DESC
                LIMIT 10
            """))
            
            for row in result:
                progress['facturas_por_nit'][row[0]] = {
                    'razon_social': row[1],
                    'total': row[2]
                }
            
            # Última fecha de procesamiento
            result = session.execute(text("""
                SELECT MAX(fecha_procesamiento_auto)
                FROM facturas
                WHERE fecha_procesamiento_auto IS NOT NULL
            """))
            progress['ultima_fecha_procesamiento'] = result.scalar()
            
            session.close()
            
        except Exception as exc:
            self.logger.error("Error obteniendo progreso de ingesta: %s", exc)
        
        return progress