# app/crud/email_config.py
"""
Operaciones CRUD para configuración de extracción de correos.

Funciones para gestionar cuentas de correo, NITs y historial de extracciones.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, Integer
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from app.models.email_config import CuentaCorreo, NitConfiguracion, HistorialExtraccion
from app.schemas.email_config import (
    CuentaCorreoCreate,
    CuentaCorreoUpdate,
    NitConfiguracionCreate,
    NitConfiguracionUpdate,
    HistorialExtraccionCreate,
)
from app.utils.nit_validator import nit_validator


# ==================== CRUD Cuenta Correo ====================

def get_cuenta_correo(db: Session, cuenta_id: int) -> Optional[CuentaCorreo]:
    """Obtiene una cuenta de correo por ID con sus NITs"""
    return db.query(CuentaCorreo).options(joinedload(CuentaCorreo.nits)).filter(CuentaCorreo.id == cuenta_id).first()


def get_cuenta_correo_by_email(db: Session, email: str) -> Optional[CuentaCorreo]:
    """Obtiene una cuenta de correo por email"""
    return db.query(CuentaCorreo).options(joinedload(CuentaCorreo.nits)).filter(CuentaCorreo.email == email).first()


def get_cuentas_correo(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    solo_activas: bool = False,
    organizacion: Optional[str] = None
) -> List[CuentaCorreo]:
    """Obtiene lista de cuentas de correo con filtros"""
    query = db.query(CuentaCorreo).options(joinedload(CuentaCorreo.nits))

    if solo_activas:
        query = query.filter(CuentaCorreo.activa == True)

    if organizacion:
        query = query.filter(CuentaCorreo.organizacion == organizacion)

    return query.order_by(CuentaCorreo.email).offset(skip).limit(limit).all()


def get_cuentas_activas_para_extraccion(db: Session) -> List[CuentaCorreo]:
    """
    Obtiene todas las cuentas activas con sus NITs activos para el proceso de extracción.

    Usado por el invoice_extractor para obtener la configuración.
    """
    return (
        db.query(CuentaCorreo)
        .options(joinedload(CuentaCorreo.nits))
        .filter(CuentaCorreo.activa == True)
        .order_by(CuentaCorreo.email)
        .all()
    )


def create_cuenta_correo(db: Session, cuenta: CuentaCorreoCreate) -> CuentaCorreo:
    """Crea una nueva cuenta de correo"""
    db_cuenta = CuentaCorreo(
        email=cuenta.email,
        nombre_descriptivo=cuenta.nombre_descriptivo,
        max_correos_por_ejecucion=cuenta.max_correos_por_ejecucion,
        ventana_inicial_dias=cuenta.ventana_inicial_dias,
        activa=cuenta.activa,
        organizacion=cuenta.organizacion,
        grupo_id=cuenta.grupo_id,  # MULTI-TENANT: Asignar grupo al crear
        creada_por=cuenta.creada_por,
    )
    db.add(db_cuenta)
    db.flush()  # Para obtener el ID sin hacer commit

    # Agregar NITs si se proporcionaron
    if cuenta.nits:
        for nit in cuenta.nits:
            db_nit = NitConfiguracion(
                cuenta_correo_id=db_cuenta.id,
                nit=nit,
                activo=True,
                creado_por=cuenta.creada_por,
            )
            db.add(db_nit)

    db.commit()
    db.refresh(db_cuenta)
    return db_cuenta


def update_cuenta_correo(db: Session, cuenta_id: int, update_data: CuentaCorreoUpdate) -> Optional[CuentaCorreo]:
    """Actualiza una cuenta de correo"""
    db_cuenta = db.query(CuentaCorreo).filter(CuentaCorreo.id == cuenta_id).first()
    if not db_cuenta:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)

    # Si se está actualizando el email, verificar que no esté en uso
    if 'email' in update_dict and update_dict['email'] != db_cuenta.email:
        existing = db.query(CuentaCorreo).filter(
            CuentaCorreo.email == update_dict['email'],
            CuentaCorreo.id != cuenta_id
        ).first()
        if existing:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail=f"El email {update_dict['email']} ya está en uso por otra cuenta"
            )

    for key, value in update_dict.items():
        setattr(db_cuenta, key, value)

    db.commit()
    db.refresh(db_cuenta)
    return db_cuenta


def delete_cuenta_correo(db: Session, cuenta_id: int) -> bool:
    """Elimina una cuenta de correo (y sus NITs en cascada)"""
    db_cuenta = db.query(CuentaCorreo).filter(CuentaCorreo.id == cuenta_id).first()
    if not db_cuenta:
        return False

    db.delete(db_cuenta)
    db.commit()
    return True


def toggle_cuenta_activa(db: Session, cuenta_id: int, activa: bool, usuario: str) -> Optional[CuentaCorreo]:
    """Activa o desactiva una cuenta de correo"""
    db_cuenta = db.query(CuentaCorreo).filter(CuentaCorreo.id == cuenta_id).first()
    if not db_cuenta:
        return None

    db_cuenta.activa = activa
    db_cuenta.actualizada_por = usuario
    db.commit()
    db.refresh(db_cuenta)
    return db_cuenta


def update_ultima_ejecucion(
    db: Session,
    cuenta_id: int,
    fecha_ejecucion: datetime,
    fecha_ultimo_correo: Optional[datetime] = None
) -> Optional[CuentaCorreo]:
    """
    Actualiza los campos de tracking de extracción incremental.

    Llamar después de una extracción exitosa para actualizar:
    - ultima_ejecucion_exitosa
    - fecha_ultimo_correo_procesado (si se proporciona)
    """
    db_cuenta = db.query(CuentaCorreo).filter(CuentaCorreo.id == cuenta_id).first()
    if not db_cuenta:
        return None

    db_cuenta.ultima_ejecucion_exitosa = fecha_ejecucion
    if fecha_ultimo_correo:
        db_cuenta.fecha_ultimo_correo_procesado = fecha_ultimo_correo

    db.commit()
    db.refresh(db_cuenta)
    return db_cuenta


# ==================== CRUD NIT Configuración ====================

def get_nit_configuracion(db: Session, nit_id: int) -> Optional[NitConfiguracion]:
    """Obtiene un NIT por ID"""
    return db.query(NitConfiguracion).filter(NitConfiguracion.id == nit_id).first()


def get_nits_by_cuenta(
    db: Session,
    cuenta_id: int,
    solo_activos: bool = False
) -> List[NitConfiguracion]:
    """Obtiene todos los NITs de una cuenta"""
    query = db.query(NitConfiguracion).filter(NitConfiguracion.cuenta_correo_id == cuenta_id)

    if solo_activos:
        query = query.filter(NitConfiguracion.activo == True)

    return query.order_by(NitConfiguracion.nit).all()


def get_nit_by_cuenta_and_nit(db: Session, cuenta_id: int, nit: str) -> Optional[NitConfiguracion]:
    """Busca un NIT específico en una cuenta (para verificar duplicados)"""
    return (
        db.query(NitConfiguracion)
        .filter(
            and_(
                NitConfiguracion.cuenta_correo_id == cuenta_id,
                NitConfiguracion.nit == nit
            )
        )
        .first()
    )


def create_nit_configuracion(db: Session, nit: NitConfiguracionCreate) -> NitConfiguracion:
    """Crea un nuevo NIT"""
    db_nit = NitConfiguracion(
        cuenta_correo_id=nit.cuenta_correo_id,
        nit=nit.nit,
        nombre_proveedor=nit.nombre_proveedor,
        activo=nit.activo,
        notas=nit.notas,
        creado_por=nit.creado_por,
    )
    db.add(db_nit)
    db.commit()
    db.refresh(db_nit)
    return db_nit


def bulk_create_nits(
    db: Session,
    cuenta_id: int,
    nits: List[str],
    creado_por: str
) -> Tuple[int, int, List[dict]]:
    """
    Crea múltiples NITs en una cuenta con NORMALIZACIÓN AUTOMÁTICA.

    NORMALIZACIÓN:
    - Acepta NITs en cualquier formato: "800185449", "800.185.449", "800185449-9", etc.
    - Calcula automáticamente el dígito verificador DIAN (módulo 11)
    - Almacena todos los NITs en formato normalizado: "XXXXXXXXX-D"
    - Valida que cada NIT sea correcto

    Returns:
        Tuple[agregados, duplicados, fallidos, detalles]
    """
    agregados = 0
    duplicados = 0
    fallidos = 0
    detalles = []

    for nit_raw in nits:
        try:
            # PASO 1: Normalizar el NIT con cálculo automático del DV
            nit_normalizado = nit_validator.normalizar_nit(nit_raw)

            # PASO 2: Verificar si ya existe en esta cuenta
            existing = get_nit_by_cuenta_and_nit(db, cuenta_id, nit_normalizado)
            if existing:
                duplicados += 1
                detalles.append({
                    "nit_original": nit_raw.strip(),
                    "nit_normalizado": nit_normalizado,
                    "status": "duplicado",
                    "id": existing.id
                })
            else:
                # PASO 3: Crear el NIT en BD con formato normalizado
                db_nit = NitConfiguracion(
                    cuenta_correo_id=cuenta_id,
                    nit=nit_normalizado,  # Almacena formato "XXXXXXXXX-D"
                    activo=True,
                    creado_por=creado_por,
                )
                db.add(db_nit)
                db.flush()
                agregados += 1
                detalles.append({
                    "nit_original": nit_raw.strip(),
                    "nit_normalizado": nit_normalizado,
                    "status": "agregado",
                    "id": db_nit.id
                })
        except ValueError as ve:
            # NIT inválido
            fallidos += 1
            detalles.append({
                "nit_original": nit_raw.strip(),
                "status": "error",
                "mensaje": str(ve)
            })
        except Exception as e:
            # Otros errores
            fallidos += 1
            detalles.append({
                "nit_original": nit_raw.strip(),
                "status": "error",
                "mensaje": f"Error inesperado: {str(e)}"
            })

    db.commit()
    return agregados, duplicados, detalles


def update_nit_configuracion(db: Session, nit_id: int, update_data: NitConfiguracionUpdate) -> Optional[NitConfiguracion]:
    """Actualiza un NIT"""
    db_nit = db.query(NitConfiguracion).filter(NitConfiguracion.id == nit_id).first()
    if not db_nit:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_nit, key, value)

    db.commit()
    db.refresh(db_nit)
    return db_nit


def delete_nit_configuracion(db: Session, nit_id: int) -> bool:
    """Elimina un NIT"""
    db_nit = db.query(NitConfiguracion).filter(NitConfiguracion.id == nit_id).first()
    if not db_nit:
        return False

    db.delete(db_nit)
    db.commit()
    return True


def toggle_nit_activo(db: Session, nit_id: int, activo: bool, usuario: str) -> Optional[NitConfiguracion]:
    """Activa o desactiva un NIT"""
    db_nit = db.query(NitConfiguracion).filter(NitConfiguracion.id == nit_id).first()
    if not db_nit:
        return None

    db_nit.activo = activo
    db_nit.actualizado_por = usuario
    db.commit()
    db.refresh(db_nit)
    return db_nit


# ==================== CRUD Historial Extracción ====================

def create_historial_extraccion(db: Session, historial: HistorialExtraccionCreate) -> HistorialExtraccion:
    """Registra una ejecución de extracción"""
    db_historial = HistorialExtraccion(**historial.model_dump())
    db.add(db_historial)
    db.commit()
    db.refresh(db_historial)
    return db_historial


def get_historial_by_cuenta(
    db: Session,
    cuenta_id: int,
    limit: int = 50
) -> List[HistorialExtraccion]:
    """Obtiene historial de extracciones de una cuenta"""
    return (
        db.query(HistorialExtraccion)
        .filter(HistorialExtraccion.cuenta_correo_id == cuenta_id)
        .order_by(HistorialExtraccion.fecha_ejecucion.desc())
        .limit(limit)
        .all()
    )


def get_ultima_extraccion(db: Session, cuenta_id: int) -> Optional[HistorialExtraccion]:
    """Obtiene la última extracción de una cuenta"""
    return (
        db.query(HistorialExtraccion)
        .filter(HistorialExtraccion.cuenta_correo_id == cuenta_id)
        .order_by(HistorialExtraccion.fecha_ejecucion.desc())
        .first()
    )


def get_estadisticas_extraccion(db: Session, cuenta_id: int, dias: int = 30) -> dict:
    """
    Obtiene estadísticas de extracción de una cuenta en los últimos N días.
    """
    fecha_desde = datetime.utcnow() - timedelta(days=dias)

    stats = (
        db.query(
            func.count(HistorialExtraccion.id).label('total_ejecuciones'),
            func.sum(HistorialExtraccion.facturas_encontradas).label('total_facturas_encontradas'),
            func.sum(HistorialExtraccion.facturas_creadas).label('total_facturas_creadas'),
            func.sum(HistorialExtraccion.facturas_actualizadas).label('total_facturas_actualizadas'),
            func.avg(HistorialExtraccion.tiempo_ejecucion_ms).label('promedio_tiempo_ms'),
            func.sum(func.cast(HistorialExtraccion.exito, Integer)).label('ejecuciones_exitosas'),
        )
        .filter(
            and_(
                HistorialExtraccion.cuenta_correo_id == cuenta_id,
                HistorialExtraccion.fecha_ejecucion >= fecha_desde
            )
        )
        .first()
    )

    total = stats.total_ejecuciones or 0
    exitosas = stats.ejecuciones_exitosas or 0

    return {
        "total_ejecuciones": total,
        "total_facturas_encontradas": stats.total_facturas_encontradas or 0,
        "total_facturas_creadas": stats.total_facturas_creadas or 0,
        "total_facturas_actualizadas": stats.total_facturas_actualizadas or 0,
        "promedio_tiempo_ms": round(stats.promedio_tiempo_ms, 2) if stats.promedio_tiempo_ms else 0,
        "tasa_exito": round((exitosas / total * 100), 2) if total > 0 else 0,
        "dias_analizados": dias,
    }


def get_resumen_todas_cuentas(db: Session) -> List[dict]:
    """
    Obtiene resumen de todas las cuentas con conteos de NITs.
    """
    from app.models.grupo import Grupo

    cuentas = (
        db.query(
            CuentaCorreo.id,
            CuentaCorreo.email,
            CuentaCorreo.nombre_descriptivo,
            CuentaCorreo.activa,
            CuentaCorreo.organizacion,
            CuentaCorreo.grupo_id,
            Grupo.codigo_corto.label('grupo_codigo'),
            Grupo.nombre.label('grupo_nombre'),
            CuentaCorreo.creada_en,
            func.count(NitConfiguracion.id).label('total_nits'),
            func.sum(func.cast(NitConfiguracion.activo, Integer)).label('total_nits_activos'),
        )
        .outerjoin(NitConfiguracion)
        .outerjoin(Grupo, CuentaCorreo.grupo_id == Grupo.id)
        .group_by(CuentaCorreo.id, Grupo.id)
        .order_by(CuentaCorreo.email)
        .all()
    )

    return [
        {
            "id": c.id,
            "email": c.email,
            "nombre_descriptivo": c.nombre_descriptivo,
            "activa": c.activa,
            "organizacion": c.organizacion,
            "grupo_id": c.grupo_id,
            "grupo_codigo": c.grupo_codigo,
            "grupo_nombre": c.grupo_nombre,
            "total_nits": c.total_nits or 0,
            "total_nits_activos": c.total_nits_activos or 0,
            "creada_en": c.creada_en,
        }
        for c in cuentas
    ]


def get_resumen_cuentas_por_grupos(db: Session, grupos_ids: List[int]) -> List[dict]:
    """
    Obtiene resumen de cuentas filtradas por grupos (multi-tenant).

    Args:
        db: Sesión de base de datos
        grupos_ids: Lista de IDs de grupos a filtrar

    Returns:
        Lista de cuentas con sus conteos de NITs
    """
    from app.models.grupo import Grupo

    if not grupos_ids:
        return []

    cuentas = (
        db.query(
            CuentaCorreo.id,
            CuentaCorreo.email,
            CuentaCorreo.nombre_descriptivo,
            CuentaCorreo.activa,
            CuentaCorreo.organizacion,
            CuentaCorreo.grupo_id,
            Grupo.codigo_corto.label('grupo_codigo'),
            Grupo.nombre.label('grupo_nombre'),
            CuentaCorreo.creada_en,
            func.count(NitConfiguracion.id).label('total_nits'),
            func.sum(func.cast(NitConfiguracion.activo, Integer)).label('total_nits_activos'),
        )
        .outerjoin(NitConfiguracion)
        .outerjoin(Grupo, CuentaCorreo.grupo_id == Grupo.id)
        .filter(CuentaCorreo.grupo_id.in_(grupos_ids))
        .group_by(CuentaCorreo.id, Grupo.id)
        .order_by(CuentaCorreo.email)
        .all()
    )

    return [
        {
            "id": c.id,
            "email": c.email,
            "nombre_descriptivo": c.nombre_descriptivo,
            "activa": c.activa,
            "organizacion": c.organizacion,
            "grupo_id": c.grupo_id,
            "grupo_codigo": c.grupo_codigo,
            "grupo_nombre": c.grupo_nombre,
            "total_nits": c.total_nits or 0,
            "total_nits_activos": c.total_nits_activos or 0,
            "creada_en": c.creada_en,
        }
        for c in cuentas
    ]
