# src/core/__init__.py

"""
Módulo core - Componentes fundamentales del sistema.
"""
from src.core.xml_utils import (
    safe_parse_xml,
    get_text,
    get_nodes,
    safe_decimal,
    safe_float,
    UBL_NAMESPACES
)
from src.core.xml_parser import XMLParser
from src.core.config import Settings, UserConfig, load_config

__all__ = [
    # XML utilities
    'safe_parse_xml',
    'get_text',
    'get_nodes',
    'safe_decimal',
    'safe_float',
    'UBL_NAMESPACES',
    
    # XML parser
    'XMLParser',
    
    # Config
    'Settings',
    'UserConfig',
    'load_config',
]
