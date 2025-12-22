# app/services/email_config_service.py
"""
Servicio de configuración de extracción de correos con caché en memoria.

Este servicio es usado por el invoice_extractor para obtener la configuración
de cuentas de correo y NITs sin consultar la base de datos en cada extracción.

La caché se refresca automáticamente cada 5 minutos o manualmente cuando se
actualiza la configuración.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from app.crud.email_config import get_cuentas_activas_para_extraccion

logger = logging.getLogger(__name__)


class EmailConfigCache:
    """
    Caché en memoria para configuración de extracción de correos.

    Evita consultas repetidas a la base de datos durante la extracción.
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Inicializa el caché.

        Args:
            ttl_seconds: Tiempo de vida del caché en segundos (default: 300 = 5 minutos)
        """
        self._cache: Optional[List[Dict]] = None
        self._last_refresh: Optional[datetime] = None
        self._ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Verifica si el caché ha expirado"""
        if self._last_refresh is None:
            return True

        age = datetime.utcnow() - self._last_refresh
        return age.total_seconds() > self._ttl_seconds

    def get(self, db: Session, force_refresh: bool = False) -> List[Dict]:
        """
        Obtiene configuración desde el caché o refresca si es necesario.

        Args:
            db: Sesión de base de datos
            force_refresh: Fuerza refrescar el caché ignorando TTL

        Returns:
            Lista de configuraciones por cuenta de correo
        """
        if force_refresh or self.is_expired() or self._cache is None:
            self.refresh(db)

        return self._cache or []

    def refresh(self, db: Session) -> None:
        """
        Refresca el caché desde la base de datos.

        Args:
            db: Sesión de base de datos
        """
        logger.info(" Refrescando caché de configuración de extracción de correos...")

        try:
            cuentas = get_cuentas_activas_para_extraccion(db)

            config_list = []
            total_nits = 0

            for cuenta in cuentas:
                # Filtrar solo NITs activos
                nits_activos = [nit.nit for nit in cuenta.nits if nit.activo]

                if nits_activos:  # Solo incluir cuentas con al menos un NIT activo
                    config_list.append({
                        "id": cuenta.id,
                        "email": cuenta.email,
                        "nombre_descriptivo": cuenta.nombre_descriptivo,
                        "nits": nits_activos,
                        "fetch_limit": cuenta.fetch_limit,
                        "fetch_days": cuenta.fetch_days,
                        "organizacion": cuenta.organizacion,
                    })
                    total_nits += len(nits_activos)

            self._cache = config_list
            self._last_refresh = datetime.utcnow()

            logger.info(
                f"  Caché refrescado: {len(config_list)} cuentas activas, {total_nits} NITs totales"
            )

        except Exception as e:
            logger.error(f" Error al refrescar caché de configuración: {str(e)}")
            # Mantener el caché anterior si existe
            if self._cache is None:
                self._cache = []

    def clear(self) -> None:
        """Limpia el caché forzando un refresh en la próxima consulta"""
        self._cache = None
        self._last_refresh = None
        logger.info("🗑️ Caché de configuración limpiado")

    def get_cuenta_by_email(self, db: Session, email: str) -> Optional[Dict]:
        """
        Obtiene configuración de una cuenta específica por email.

        Args:
            db: Sesión de base de datos
            email: Email de la cuenta a buscar

        Returns:
            Configuración de la cuenta o None si no existe
        """
        config = self.get(db)
        for cuenta in config:
            if cuenta["email"].lower() == email.lower():
                return cuenta
        return None

    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del caché.

        Returns:
            Diccionario con información del caché
        """
        if self._cache is None:
            return {
                "status": "empty",
                "total_cuentas": 0,
                "total_nits": 0,
                "last_refresh": None,
                "ttl_seconds": self._ttl_seconds,
                "expired": True,
            }

        total_nits = sum(len(c["nits"]) for c in self._cache)
        age_seconds = (
            (datetime.utcnow() - self._last_refresh).total_seconds()
            if self._last_refresh
            else None
        )

        return {
            "status": "active",
            "total_cuentas": len(self._cache),
            "total_nits": total_nits,
            "last_refresh": self._last_refresh,
            "age_seconds": age_seconds,
            "ttl_seconds": self._ttl_seconds,
            "expired": self.is_expired(),
        }


# Instancia global del caché (singleton)
_email_config_cache = EmailConfigCache(ttl_seconds=300)  # 5 minutos


def get_email_config_cache() -> EmailConfigCache:
    """
    Obtiene la instancia global del caché de configuración.

    Returns:
        Instancia del caché
    """
    return _email_config_cache


class EmailConfigService:
    """
    Servicio de alto nivel para gestión de configuración de extracción.

    Proporciona métodos convenientes para usar en el invoice_extractor.
    """

    def __init__(self, db: Session, use_cache: bool = True):
        """
        Inicializa el servicio.

        Args:
            db: Sesión de base de datos
            use_cache: Si debe usar el caché (default: True)
        """
        self.db = db
        self.use_cache = use_cache
        self.cache = get_email_config_cache()

    def get_configuracion_para_extractor(self, force_refresh: bool = False) -> List[Dict]:
        """
        Obtiene configuración para el invoice_extractor.

        Args:
            force_refresh: Fuerza refrescar el caché

        Returns:
            Lista de configuraciones por cuenta
        """
        if self.use_cache:
            return self.cache.get(self.db, force_refresh=force_refresh)
        else:
            # Sin caché, consulta directa a la BD
            cuentas = get_cuentas_activas_para_extraccion(self.db)
            config_list = []
            for cuenta in cuentas:
                nits_activos = [nit.nit for nit in cuenta.nits if nit.activo]
                if nits_activos:
                    config_list.append({
                        "id": cuenta.id,
                        "email": cuenta.email,
                        "nits": nits_activos,
                        "fetch_limit": cuenta.fetch_limit,
                        "fetch_days": cuenta.fetch_days,
                    })
            return config_list

    def get_configuracion_json_legacy(self, force_refresh: bool = False) -> Dict:
        """
        Obtiene configuración en formato JSON legacy (compatible con código anterior).

        Formato:
        {
          "users": [
            {
              "email": "...",
              "nits": [...],
              "fetch_limit": 500,
              "fetch_days": 90
            }
          ]
        }

        Args:
            force_refresh: Fuerza refrescar el caché

        Returns:
            Diccionario en formato JSON legacy
        """
        config = self.get_configuracion_para_extractor(force_refresh)

        users = []
        for cuenta in config:
            users.append({
                "email": cuenta["email"],
                "nits": cuenta["nits"],
                "fetch_limit": cuenta["fetch_limit"],
                "fetch_days": cuenta["fetch_days"],
            })

        return {"users": users}

    def invalidate_cache(self) -> None:
        """Invalida el caché forzando un refresh en la próxima consulta"""
        self.cache.clear()

    def get_cache_stats(self) -> Dict:
        """Obtiene estadísticas del caché"""
        return self.cache.get_stats()

    def get_cuenta_by_email(self, email: str) -> Optional[Dict]:
        """
        Busca configuración de una cuenta específica por email.

        Args:
            email: Email de la cuenta

        Returns:
            Configuración de la cuenta o None
        """
        return self.cache.get_cuenta_by_email(self.db, email)


def registrar_extraccion(
    db: Session,
    cuenta_id: int,
    correos_procesados: int,
    facturas_encontradas: int,
    facturas_creadas: int,
    facturas_actualizadas: int,
    facturas_ignoradas: int,
    exito: bool = True,
    mensaje_error: Optional[str] = None,
    tiempo_ejecucion_ms: Optional[int] = None,
    fetch_limit_usado: Optional[int] = None,
    fetch_days_usado: Optional[int] = None,
    nits_usados: Optional[int] = None,
) -> None:
    """
    Registra una ejecución de extracción en el historial.

    Args:
        db: Sesión de base de datos
        cuenta_id: ID de la cuenta
        correos_procesados: Total de correos analizados
        facturas_encontradas: Facturas XML encontradas
        facturas_creadas: Nuevas facturas creadas
        facturas_actualizadas: Facturas actualizadas
        facturas_ignoradas: Facturas duplicadas/ignoradas
        exito: Si la extracción fue exitosa
        mensaje_error: Mensaje de error si aplica
        tiempo_ejecucion_ms: Tiempo de ejecución en milisegundos
        fetch_limit_usado: Límite usado en la extracción
        fetch_days_usado: Días usados en la extracción
        nits_usados: Cantidad de NITs activos
    """
    from app.schemas.email_config import HistorialExtraccionCreate
    from app.crud.email_config import create_historial_extraccion

    historial = HistorialExtraccionCreate(
        cuenta_correo_id=cuenta_id,
        correos_procesados=correos_procesados,
        facturas_encontradas=facturas_encontradas,
        facturas_creadas=facturas_creadas,
        facturas_actualizadas=facturas_actualizadas,
        facturas_ignoradas=facturas_ignoradas,
        exito=exito,
        mensaje_error=mensaje_error,
        tiempo_ejecucion_ms=tiempo_ejecucion_ms,
        fetch_limit_usado=fetch_limit_usado,
        fetch_days_usado=fetch_days_usado,
        nits_usados=nits_usados,
    )

    create_historial_extraccion(db, historial)
    logger.info(
        f"Historial registrado: cuenta_id={cuenta_id}, "
        f"facturas_creadas={facturas_creadas}, exito={exito}"
    )
