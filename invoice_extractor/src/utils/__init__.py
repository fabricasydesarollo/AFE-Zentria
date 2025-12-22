# Utilidades específicas del dominio
from .logger import get_logger, logger
from .nit_utils import (
    calcular_digito_verificador_nit,
    completar_nit_con_dv,
    validar_nit_colombiano
)
from .deduplication import (
    make_factura_key,
    deduplicate_facturas,
    load_index_from_file
)

# Utilidades genéricas (migradas desde utils/common.py)
from .common import (
    expand_env_vars,
    load_json_config,
    setup_logging,
    validate_required_fields,
    ensure_directory,
    get_project_root,
    format_file_size,
    safe_filename
)

__version__ = "1.0.0"

__all__ = [
    # Logger
    "get_logger",
    "logger",
    
    # NIT utilities
    "calcular_digito_verificador_nit",
    "completar_nit_con_dv",
    "validar_nit_colombiano",
    
    # Deduplication
    "make_factura_key",
    "deduplicate_facturas",
    "load_index_from_file",
    
    # Common utilities
    "expand_env_vars",
    "load_json_config",
    "setup_logging",
    "validate_required_fields",
    "ensure_directory",
    "get_project_root",
    "format_file_size",
    "safe_filename",
]