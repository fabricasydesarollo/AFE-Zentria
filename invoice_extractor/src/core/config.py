from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import json
import os

import requests

from pydantic import BaseModel, field_validator, Field
from pydantic_settings import BaseSettings
from src.utils.logger import get_logger

logger = get_logger("Config")


class UserConfig(BaseModel):
    """Configuración por usuario con soporte de extracción incremental"""
    cuenta_id: Optional[int] = None  # ID para registrar historial
    email: str
    nits: List[str] = []

    # Nuevos campos de extracción incremental
    max_correos_por_ejecucion: int = 10000
    ventana_inicial_dias: int = 30
    ultima_ejecucion_exitosa: Optional[datetime] = None
    fecha_ultimo_correo_procesado: Optional[datetime] = None

    # Campos legacy (para compatibilidad hacia atrás)
    fetch_limit: Optional[int] = None
    fetch_days: Optional[int] = None

    def __init__(self, **data):
        """Inicialización con compatibilidad hacia atrás"""
        # Mapear campos legacy a nuevos campos si existen
        if 'fetch_limit' in data and 'max_correos_por_ejecucion' not in data:
            data['max_correos_por_ejecucion'] = data['fetch_limit']
        if 'fetch_days' in data and 'ventana_inicial_dias' not in data:
            data['ventana_inicial_dias'] = data['fetch_days']

        super().__init__(**data)

    def get_fetch_limit(self) -> int:
        """Obtiene el límite de correos a usar en esta ejecución"""
        return self.max_correos_por_ejecucion

    def get_fecha_inicio(self) -> Optional[datetime]:
        """
        Calcula la fecha desde la cual extraer correos.

        - Si es primera ejecución: usa ventana_inicial_dias
        - Si es ejecución incremental: usa ultima_ejecucion_exitosa o fecha_ultimo_correo_procesado
        """
        if self.ultima_ejecucion_exitosa:
            # Extracción incremental: desde última ejecución exitosa
            return self.ultima_ejecucion_exitosa
        elif self.fecha_ultimo_correo_procesado:
            # Alternativa: usar fecha del último correo procesado
            return self.fecha_ultimo_correo_procesado
        else:
            # Primera ejecución: usar ventana_inicial_dias
            return None  # El caller debe calcular datetime.now() - timedelta(days=ventana_inicial_dias)

    def es_primera_ejecucion(self) -> bool:
        """Determina si esta es la primera ejecución de esta cuenta"""
        return self.ultima_ejecucion_exitosa is None and self.fecha_ultimo_correo_procesado is None


class Settings(BaseSettings):
    """Configuración global de la aplicación"""
    TENANT_ID_CORREOS: str
    CLIENT_ID_CORREOS: str
    CLIENT_SECRET_CORREOS: str
    LOG_LEVEL: str = "INFO"
    users: List[UserConfig] = []

    # Solo DATABASE_URL
    database_url: str = Field(..., alias="DATABASE_URL")

    @field_validator("users", mode="before")
    @classmethod
    def ensure_users_list(cls, v):
        if v is None:
            return []
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignorar campos extra como API_BASE_URL


def fetch_config_from_api(api_url: str, timeout: int = 10) -> List[dict]:
    """
    Obtiene configuración desde el backend API.

    Args:
        api_url: URL del endpoint de configuración
        timeout: Timeout en segundos

    Returns:
        Lista de configuraciones de usuarios

    Raises:
        requests.RequestException: Si falla la petición
    """
    try:
        response = requests.get(api_url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("users", [])
    except requests.RequestException as e:
        logger.error(f"Error obteniendo configuración desde API: {e}")
        raise


def load_config(settings_path: Optional[Path] = None, use_api: bool = True) -> Settings:
    """
    Carga configuración desde API (preferido) o settings.json (fallback).

    Args:
        settings_path: Ruta opcional al archivo settings.json (fallback)
        use_api: Si True, intenta obtener config desde API primero

    Returns:
        Objeto Settings con configuración completa
    """
    users_data = []

    # Intentar obtener configuración desde API
    if use_api:
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        api_endpoint = f"{api_base_url}/api/v1/email-config/configuracion-extractor-public"

        try:
            logger.info(f"Obteniendo configuración desde API: {api_endpoint}")
            users_data = fetch_config_from_api(api_endpoint)
            logger.info(f"Configuración obtenida desde API: {len(users_data)} cuentas")
        except Exception as e:
            logger.warning(f"No se pudo obtener configuración desde API: {e}")
            logger.info("Intentando fallback a settings.json...")
            use_api = False

    # Fallback a settings.json si API falla o use_api=False
    if not use_api or not users_data:
        base = Path(__file__).resolve().parent.parent.parent
        root_settings = base / "settings.json"
        src_settings = base / "src" / "settings.json"

        if settings_path is None:
            if root_settings.exists():
                settings_path = root_settings
            elif src_settings.exists():
                settings_path = src_settings
            else:
                settings_path = root_settings  # fallback para logs

        if settings_path.exists():
            logger.info(f"Cargando configuración desde: {settings_path}")
            with open(settings_path, "r", encoding="utf-8") as fh:
                file_settings = json.load(fh)
                users_data = file_settings.get("users", [])
            logger.info(f"Configuración obtenida desde archivo: {len(users_data)} cuentas")
        else:
            logger.warning(f"Advertencia: No se encontró {settings_path}")

    env_settings = Settings()
    config_dict = env_settings.model_dump()
    config_dict["users"] = users_data

    if "database_url" in config_dict:
        config_dict["DATABASE_URL"] = config_dict.pop("database_url")

    return Settings.model_validate(config_dict)