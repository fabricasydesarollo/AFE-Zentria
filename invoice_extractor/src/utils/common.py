"""
Utilidades comunes para el proyecto Invoice Extractor.
Funciones reutilizables entre diferentes módulos.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


def expand_env_vars(value: str) -> str:
    """
    Expandir variables de entorno en formato ${VAR_NAME}.
    
    Args:
        value: String que puede contener variables de entorno
        
    Returns:
        String con variables expandidas
    """
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        env_var = value[2:-1]
        return os.getenv(env_var, value)
    return value


def load_json_config(config_file: str) -> Dict[str, Any]:
    """
    Cargar configuración desde archivo JSON con soporte para variables de entorno.
    
    Args:
        config_file: Ruta al archivo de configuración
        
    Returns:
        Diccionario con la configuración cargada
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        json.JSONDecodeError: Si el archivo JSON es inválido
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_file}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Expandir variables de entorno recursivamente
        return _expand_config_vars(config)
        
    except json.JSONDecodeError as e:
        # Re-lanzar la excepción original para conservar información de posición/archivo
        raise


def _expand_config_vars(obj: Any) -> Any:
    """
    Expandir variables de entorno recursivamente en configuración.
    
    Args:
        obj: Objeto a procesar (dict, list, str, etc.)
        
    Returns:
        Objeto con variables expandidas
    """
    if isinstance(obj, dict):
        return {key: _expand_config_vars(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_expand_config_vars(item) for item in obj]
    elif isinstance(obj, str):
        return expand_env_vars(obj)
    else:
        return obj


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    logger_name: str = "InvoiceExtractor"
) -> logging.Logger:
    """
    Configurar logging con formato estándar.
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Archivo de log opcional
        logger_name: Nombre del logger
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Evitar agregar handlers múltiples
    if logger.handlers:
        return logger
    
    # Formato de logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo si se especifica
    if log_file:
        # Crear directorio si se especificó una ruta (evitar dirname=="" para nombres simples)
        dir_name = os.path.dirname(log_file)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def validate_required_fields(config: Dict[str, Any], required_fields: list) -> tuple[bool, list]:
    """
    Validar que los campos requeridos estén presentes en la configuración.
    
    Args:
        config: Diccionario de configuración
        required_fields: Lista de campos requeridos (soporta notación de punto)
        
    Returns:
        Tupla (es_válido, campos_faltantes)
    """
    missing_fields = []
    
    for field in required_fields:
        if '.' in field:
            # Soportar notación de punto (ej: "database.host")
            parts = field.split('.')
            current = config
            
            try:
                for part in parts:
                    current = current[part]
                
                # Verificar que no sea None o string vacío
                if current is None or (isinstance(current, str) and not current.strip()):
                    missing_fields.append(field)
                    
            except (KeyError, TypeError):
                missing_fields.append(field)
        else:
            # Campo simple
            if field not in config or config[field] is None or config[field] == "":
                missing_fields.append(field)
    
    return len(missing_fields) == 0, missing_fields


def ensure_directory(path: str) -> str:
    """
    Asegurar que existe un directorio, creándolo si es necesario.
    
    Args:
        path: Ruta del directorio
        
    Returns:
        Ruta del directorio (normalizada)
    """
    directory = Path(path).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory)


def get_project_root() -> Path:
    """
    Obtener la ruta raíz del proyecto.
    
    Returns:
        Path object de la raíz del proyecto
    """
    # Buscar hacia arriba hasta encontrar requirements.txt o settings.json
    # Empezar desde el directorio que contiene este archivo
    current = Path(__file__).resolve().parent

    while current != current.parent:
        if (current / "requirements.txt").exists() or (current / "settings.json").exists():
            return current
        current = current.parent
    
    # Fallback: directorio del archivo actual
    return Path(__file__).resolve().parent.parent


def format_file_size(size_bytes: int) -> str:
    """
    Formatear tamaño de archivo en formato legible.
    
    Args:
        size_bytes: Tamaño en bytes
        
    Returns:
        String formateado (ej: "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


def safe_filename(filename: str) -> str:
    """
    Crear un nombre de archivo seguro removiendo caracteres problemáticos.
    
    Args:
        filename: Nombre de archivo original
        
    Returns:
        Nombre de archivo seguro
    """
    # Caracteres problemáticos en Windows/Linux
    invalid_chars = '<>:"/\\|?*'
    
    safe_name = filename
    for char in invalid_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Remover espacios múltiples y al inicio/final
    safe_name = ' '.join(safe_name.split())
    
    # Limitar longitud
    if len(safe_name) > 200:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:200-len(ext)] + ext
    
    return safe_name