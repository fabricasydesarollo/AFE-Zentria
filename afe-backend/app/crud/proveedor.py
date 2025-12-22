# app/crud/proveedor.py
"""
CRUD de Proveedores - Simplificado

Módulo de acceso a datos para proveedores.

🔒 SEGURIDAD 2025-12-15:
- Eliminada auto-creación de proveedores por seguridad
- Solo creación manual desde UI/API
- Validación y normalización de NITs obligatoria


Fecha: 2025-12-15
"""

import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.proveedor import Proveedor
from app.schemas.proveedor import ProveedorBase
from app.utils.nit_validator import NitValidator

logger = logging.getLogger(__name__)


# ================================================================================
# FUNCIONES DE NORMALIZACIÓN (Inline - No requieren módulo separado)
# ================================================================================

def normalizar_email(email: Optional[str]) -> Optional[str]:
    """Normaliza email a lowercase sin espacios."""
    if not email:
        return None
    email = email.strip().lower()
    if '@' not in email or '.' not in email.split('@')[1]:
        return None
    return email


def normalizar_razon_social(razon_social: Optional[str]) -> Optional[str]:
    """Normaliza razón social (elimina espacios extras, capitaliza)."""
    if not razon_social:
        return None
    razon_social = ' '.join(razon_social.split())
    if not razon_social:
        return None
    return razon_social.upper()


# ================================================================================
# OPERACIONES BÁSICAS DE LECTURA
# ================================================================================

def get_proveedor(db: Session, proveedor_id: int) -> Optional[Proveedor]:
    """
    Obtiene un proveedor por ID.

    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor

    Returns:
        Proveedor o None
    """
    return db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()


def list_proveedores(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> List[Proveedor]:
    """
    Lista proveedores con paginación.

    Args:
        db: Sesión de base de datos
        skip: Offset para paginación
        limit: Límite de resultados

    Returns:
        Lista de proveedores
    """
    return db.query(Proveedor).offset(skip).limit(limit).all()


def get_proveedor_by_nit(db: Session, nit: str) -> Optional[Proveedor]:
    """
    Obtiene un proveedor por NIT (normaliza automáticamente).

    Args:
        db: Sesión de base de datos
        nit: NIT en cualquier formato

    Returns:
        Proveedor o None
    """
    try:
        # Normalizar NIT antes de buscar
        es_valido, nit_normalizado = NitValidator.validar_nit(nit)

        if not es_valido:
            logger.warning(f"NIT inválido en búsqueda: {nit}")
            return None

        return db.query(Proveedor).filter(Proveedor.nit == nit_normalizado).first()

    except Exception as e:
        logger.error(f"Error buscando proveedor por NIT: {str(e)}")
        return None


# ================================================================================
# CREACIÓN DE PROVEEDORES (Solo Manual)
# ================================================================================

def create_proveedor(db: Session, data: ProveedorBase) -> Proveedor:
    """
    Crea un proveedor MANUALMENTE (desde API/UI).

    🔒 SEGURIDAD: Solo se permite creación manual por usuarios administradores.
    Los datos se normalizan y validan antes de guardar.

    Args:
        db: Sesión de base de datos
        data: Schema ProveedorBase con datos del proveedor

    Returns:
        Proveedor creado

    Raises:
        ValueError: Si NIT es inválido o ya existe
        IntegrityError: Si hay conflicto de unicidad en BD
    """
    logger.info(
        f"Creando proveedor MANUAL: NIT={data.nit}, Razón Social={data.razon_social}"
    )

    # VALIDAR Y NORMALIZAR NIT
    es_valido, nit_normalizado = NitValidator.validar_nit(data.nit)
    if not es_valido:
        raise ValueError(f"NIT inválido: {data.nit}. {nit_normalizado}")

    # Verificar si ya existe
    proveedor_existente = db.query(Proveedor).filter(
        Proveedor.nit == nit_normalizado
    ).first()

    if proveedor_existente:
        raise ValueError(
            f"Ya existe un proveedor con NIT {nit_normalizado} "
            f"(ID: {proveedor_existente.id})"
        )

    # NORMALIZAR DATOS
    razon_social_norm = normalizar_razon_social(data.razon_social)
    email_norm = normalizar_email(data.contacto_email) if data.contacto_email else None

    # CREAR PROVEEDOR
    proveedor = Proveedor(
        nit=nit_normalizado,
        razon_social=razon_social_norm,
        contacto_email=email_norm,
        telefono=data.telefono,
        direccion=data.direccion,
        area=data.area,
        activo=True,
        # 🔒 IMPORTANTE: Siempre es creación manual
        es_auto_creado=False,
        creado_automaticamente_en=None
    )

    try:
        db.add(proveedor)
        db.commit()
        db.refresh(proveedor)

        logger.info(
            f"✅ Proveedor MANUAL creado: ID={proveedor.id}, NIT={proveedor.nit}"
        )

        return proveedor

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error de integridad al crear proveedor: {str(e)}")
        raise ValueError(f"Error de integridad: posible NIT duplicado")


# ================================================================================
# ACTUALIZACIÓN
# ================================================================================

def update_proveedor(
    db: Session,
    proveedor_id: int,
    data: ProveedorBase
) -> Optional[Proveedor]:
    """
    Actualiza un proveedor existente.

    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor a actualizar
        data: Schema ProveedorBase con nuevos datos

    Returns:
        Proveedor actualizado o None si no existe

    Raises:
        ValueError: Si NIT es inválido
    """
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()

    if not proveedor:
        return None

    logger.info(f"Actualizando proveedor ID={proveedor_id}, NIT={proveedor.nit}")

    # Normalizar datos antes de actualizar
    data_dict = data.dict(exclude_unset=True)

    # VALIDAR Y NORMALIZAR NIT (si viene en el update)
    if 'nit' in data_dict and data_dict['nit']:
        es_valido, nit_normalizado = NitValidator.validar_nit(data_dict['nit'])
        if not es_valido:
            raise ValueError(f"NIT inválido: {data_dict['nit']}")
        data_dict['nit'] = nit_normalizado

    # NORMALIZAR EMAIL
    if 'contacto_email' in data_dict and data_dict['contacto_email']:
        data_dict['contacto_email'] = normalizar_email(data_dict['contacto_email'])

    # NORMALIZAR RAZÓN SOCIAL
    if 'razon_social' in data_dict and data_dict['razon_social']:
        data_dict['razon_social'] = normalizar_razon_social(data_dict['razon_social'])

    # Aplicar cambios
    for key, value in data_dict.items():
        setattr(proveedor, key, value)

    db.commit()
    db.refresh(proveedor)

    logger.info(f"✅ Proveedor actualizado: ID={proveedor_id}")

    return proveedor


# ================================================================================
# ELIMINACIÓN
# ================================================================================

def delete_proveedor(db: Session, proveedor_id: int) -> bool:
    """
    Elimina un proveedor.

    NOTA: Considera usar soft-delete en producción para auditoría.

    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor a eliminar

    Returns:
        True si se eliminó, False si no existe
    """
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()

    if not proveedor:
        return False

    logger.warning(f"Eliminando proveedor: ID={proveedor_id}, NIT={proveedor.nit}")

    db.delete(proveedor)
    db.commit()

    logger.info(f"✅ Proveedor eliminado: ID={proveedor_id}")

    return True


# ================================================================================
# UTILIDADES PARA AUDITORÍA Y REPORTING
# ================================================================================

def count_proveedores(db: Session) -> int:
    """Cuenta el total de proveedores activos."""
    return db.query(Proveedor).filter(Proveedor.activo == True).count()


def count_proveedores_total(db: Session) -> int:
    """Cuenta el total de proveedores (activos e inactivos)."""
    return db.query(Proveedor).count()
