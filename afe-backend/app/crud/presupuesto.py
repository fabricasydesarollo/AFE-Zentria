"""
CRUD operations para el sistema de control presupuestal empresarial
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, extract

from app.models.presupuesto import (
    LineaPresupuesto,
    EjecucionPresupuestal,
    EstadoLineaPresupuesto,
    TipoDesviacion,
    NivelAprobacion,
    EstadoEjecucion,
    TipoAlerta,
    TipoVinculacion
)
from app.models.factura import Factura


# ========================================
# CRUD para LineaPresupuesto
# ========================================

def create_linea_presupuesto(
    db: Session,
    codigo: str,
    nombre: str,
    descripcion: Optional[str],
    responsable_id: int,
    año_fiscal: int,
    presupuestos_mensuales: Dict[str, Decimal],  # {"ene": 1000.00, "feb": 1500.00, ...}
    centro_costo: Optional[str] = None,
    categoria: Optional[str] = None,
    subcategoria: Optional[str] = None,
    proveedor_preferido: Optional[str] = None,
    umbral_alerta: int = 80,
    nivel_aprobacion: str = "RESPONSABLE_LINEA",
    creado_por: Optional[str] = None
) -> LineaPresupuesto:
    """
    Crea una nueva línea presupuestal con presupuestos mensuales.
    """
    # Calcular total anual
    total_anual = sum(presupuestos_mensuales.values())

    linea = LineaPresupuesto(
        codigo=codigo,
        nombre=nombre,
        descripcion=descripcion,
        responsable_id=responsable_id,
        año_fiscal=año_fiscal,
        centro_costo=centro_costo,
        categoria=categoria,
        subcategoria=subcategoria,
        proveedor_preferido=proveedor_preferido,

        # Presupuestos mensuales
        presupuesto_ene=presupuestos_mensuales.get("ene", Decimal("0.00")),
        presupuesto_feb=presupuestos_mensuales.get("feb", Decimal("0.00")),
        presupuesto_mar=presupuestos_mensuales.get("mar", Decimal("0.00")),
        presupuesto_abr=presupuestos_mensuales.get("abr", Decimal("0.00")),
        presupuesto_may=presupuestos_mensuales.get("may", Decimal("0.00")),
        presupuesto_jun=presupuestos_mensuales.get("jun", Decimal("0.00")),
        presupuesto_jul=presupuestos_mensuales.get("jul", Decimal("0.00")),
        presupuesto_ago=presupuestos_mensuales.get("ago", Decimal("0.00")),
        presupuesto_sep=presupuestos_mensuales.get("sep", Decimal("0.00")),
        presupuesto_oct=presupuestos_mensuales.get("oct", Decimal("0.00")),
        presupuesto_nov=presupuestos_mensuales.get("nov", Decimal("0.00")),
        presupuesto_dic=presupuestos_mensuales.get("dic", Decimal("0.00")),

        presupuesto_anual=total_anual,
        ejecutado_acumulado=Decimal("0.00"),
        saldo_disponible=total_anual,
        porcentaje_ejecucion=Decimal("0.00"),

        estado=EstadoLineaPresupuesto.BORRADOR,
        umbral_alerta_porcentaje=umbral_alerta,
        nivel_aprobacion_requerido=nivel_aprobacion,

        version=1,
        creado_por=creado_por,
        creado_en=datetime.now()
    )

    db.add(linea)
    db.commit()
    db.refresh(linea)
    return linea


def get_linea_presupuesto(db: Session, linea_id: int) -> Optional[LineaPresupuesto]:
    """Obtiene una línea presupuestal por ID."""
    return db.query(LineaPresupuesto).filter(LineaPresupuesto.id == linea_id).first()


def get_linea_by_codigo(db: Session, codigo: str, año_fiscal: int) -> Optional[LineaPresupuesto]:
    """Obtiene una línea presupuestal por código y año fiscal."""
    return db.query(LineaPresupuesto).filter(
        and_(
            LineaPresupuesto.codigo == codigo,
            LineaPresupuesto.año_fiscal == año_fiscal
        )
    ).first()


def list_lineas_presupuesto(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    año_fiscal: Optional[int] = None,
    responsable_id: Optional[int] = None,
    estado: Optional[str] = None,
    categoria: Optional[str] = None
) -> List[LineaPresupuesto]:
    """Lista líneas presupuestales con filtros opcionales."""
    query = db.query(LineaPresupuesto)

    if año_fiscal:
        query = query.filter(LineaPresupuesto.año_fiscal == año_fiscal)
    if responsable_id:
        query = query.filter(LineaPresupuesto.responsable_id == responsable_id)
    if estado:
        query = query.filter(LineaPresupuesto.estado == estado)
    if categoria:
        query = query.filter(LineaPresupuesto.categoria == categoria)

    return query.order_by(
        desc(LineaPresupuesto.año_fiscal),
        LineaPresupuesto.codigo
    ).offset(skip).limit(limit).all()


def update_linea_presupuesto(
    db: Session,
    linea_id: int,
    actualizado_por: str,
    **campos
) -> Optional[LineaPresupuesto]:
    """
    Actualiza campos de una línea presupuestal.
    Si se actualizan presupuestos mensuales, recalcula totales.
    """
    linea = get_linea_presupuesto(db, linea_id)
    if not linea:
        return None

    # Actualizar campos
    for campo, valor in campos.items():
        if hasattr(linea, campo):
            setattr(linea, campo, valor)

    # Recalcular totales si se modificaron presupuestos mensuales
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    if any(f"presupuesto_{mes}" in campos for mes in meses):
        total_anual = sum([
            getattr(linea, f"presupuesto_{mes}") or Decimal("0.00")
            for mes in meses
        ])
        linea.presupuesto_anual = total_anual
        linea.saldo_disponible = total_anual - (linea.ejecutado_acumulado or Decimal("0.00"))

        if total_anual > 0:
            linea.porcentaje_ejecucion = (linea.ejecutado_acumulado / total_anual * 100)

    linea.actualizado_por = actualizado_por
    linea.actualizado_en = datetime.now()

    db.commit()
    db.refresh(linea)
    return linea


def aprobar_linea_presupuesto(
    db: Session,
    linea_id: int,
    aprobador: str,
    observaciones: Optional[str] = None
) -> Optional[LineaPresupuesto]:
    """Aprueba una línea presupuestal y la activa."""
    linea = get_linea_presupuesto(db, linea_id)
    if not linea:
        return None

    linea.estado = EstadoLineaPresupuesto.APROBADO
    linea.aprobado_por = aprobador
    linea.fecha_aprobacion = datetime.now()
    linea.observaciones_aprobacion = observaciones
    linea.actualizado_por = aprobador
    linea.actualizado_en = datetime.now()

    db.commit()
    db.refresh(linea)
    return linea


def activar_linea_presupuesto(db: Session, linea_id: int) -> Optional[LineaPresupuesto]:
    """Activa una línea presupuestal aprobada para ejecución."""
    linea = get_linea_presupuesto(db, linea_id)
    if not linea or linea.estado != EstadoLineaPresupuesto.APROBADO:
        return None

    linea.estado = EstadoLineaPresupuesto.ACTIVO
    linea.fecha_inicio_vigencia = datetime.now()
    db.commit()
    db.refresh(linea)
    return linea


def recalcular_ejecucion_linea(db: Session, linea_id: int) -> Optional[LineaPresupuesto]:
    """
    Recalcula el ejecutado acumulado de una línea sumando todas sus ejecuciones aprobadas.
    """
    linea = get_linea_presupuesto(db, linea_id)
    if not linea:
        return None

    # Sumar todas las ejecuciones aprobadas (nivel 1 mínimo)
    total_ejecutado = db.query(func.sum(EjecucionPresupuestal.monto_ejecutado)).filter(
        and_(
            EjecucionPresupuestal.linea_presupuesto_id == linea_id,
            EjecucionPresupuestal.aprobado_nivel1 == True
        )
    ).scalar() or Decimal("0.00")

    linea.ejecutado_acumulado = total_ejecutado
    linea.saldo_disponible = linea.presupuesto_anual - total_ejecutado

    if linea.presupuesto_anual > 0:
        linea.porcentaje_ejecucion = (total_ejecutado / linea.presupuesto_anual * 100)

    db.commit()
    db.refresh(linea)
    return linea


# ========================================
# CRUD para EjecucionPresupuestal
# ========================================

def create_ejecucion_presupuestal(
    db: Session,
    linea_presupuesto_id: int,
    factura_id: int,
    monto_ejecutado: Decimal,
    periodo_ejecucion: date,
    descripcion: Optional[str] = None,
    vinculacion_automatica: bool = False,
    confianza_vinculacion: Optional[int] = None,
    criterios_matching: Optional[Dict] = None,
    creado_por: Optional[str] = None
) -> Optional[EjecucionPresupuestal]:
    """
    Crea una nueva ejecución presupuestal vinculando una factura con una línea de presupuesto.
    Calcula automáticamente la desviación.
    """
    # Verificar que la línea existe y está activa
    linea = get_linea_presupuesto(db, linea_presupuesto_id)
    if not linea or linea.estado != EstadoLineaPresupuesto.ACTIVO:
        return None

    # Verificar que la factura existe
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        return None

    # Obtener presupuesto del mes correspondiente
    mes = periodo_ejecucion.month
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    presupuesto_mes = getattr(linea, f"presupuesto_{meses[mes-1]}") or Decimal("0.00")

    # Calcular desviación
    desviacion = monto_ejecutado - presupuesto_mes
    desviacion_porcentaje = (desviacion / presupuesto_mes * 100) if presupuesto_mes > 0 else Decimal("0.00")

    # Determinar tipo de desviación
    if abs(desviacion_porcentaje) <= 5:
        tipo_desviacion = TipoDesviacion.DENTRO_RANGO
    elif desviacion < 0:
        tipo_desviacion = TipoDesviacion.BAJO_PRESUPUESTO
    elif desviacion > 0 and desviacion_porcentaje <= 15:
        tipo_desviacion = TipoDesviacion.SOBRE_PRESUPUESTO_LEVE
    elif desviacion > 0 and desviacion_porcentaje <= 25:
        tipo_desviacion = TipoDesviacion.SOBRE_PRESUPUESTO_MODERADO
    else:
        tipo_desviacion = TipoDesviacion.SOBRE_PRESUPUESTO_CRITICO

    # Determinar si requiere aprobación adicional
    requiere_nivel2 = abs(desviacion_porcentaje) > 15
    requiere_nivel3 = abs(desviacion_porcentaje) > 25

    ejecucion = EjecucionPresupuestal(
        linea_presupuesto_id=linea_presupuesto_id,
        factura_id=factura_id,
        monto_ejecutado=monto_ejecutado,
        periodo_ejecucion=periodo_ejecucion,
        mes_ejecucion=mes,
        año_ejecucion=periodo_ejecucion.year,

        presupuesto_mes_correspondiente=presupuesto_mes,
        desviacion=desviacion,
        desviacion_porcentaje=desviacion_porcentaje,
        tipo_desviacion=tipo_desviacion,

        descripcion=descripcion,
        estado=EstadoEjecucion.PENDIENTE_APROBACION,

        vinculacion_automatica=vinculacion_automatica,
        tipo_vinculacion=TipoVinculacion.AUTOMATICA if vinculacion_automatica else TipoVinculacion.MANUAL,
        confianza_vinculacion=confianza_vinculacion,
        criterios_matching=criterios_matching,

        requiere_aprobacion_nivel2=requiere_nivel2,
        requiere_aprobacion_nivel3=requiere_nivel3,

        creado_por=creado_por,
        creado_en=datetime.now()
    )

    db.add(ejecucion)
    db.commit()
    db.refresh(ejecucion)
    return ejecucion


def get_ejecucion_presupuestal(db: Session, ejecucion_id: int) -> Optional[EjecucionPresupuestal]:
    """Obtiene una ejecución presupuestal por ID."""
    return db.query(EjecucionPresupuestal).filter(EjecucionPresupuestal.id == ejecucion_id).first()


def list_ejecuciones_presupuestales(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    linea_presupuesto_id: Optional[int] = None,
    factura_id: Optional[int] = None,
    año_ejecucion: Optional[int] = None,
    mes_ejecucion: Optional[int] = None,
    estado: Optional[str] = None
) -> List[EjecucionPresupuestal]:
    """Lista ejecuciones presupuestales con filtros opcionales."""
    query = db.query(EjecucionPresupuestal)

    if linea_presupuesto_id:
        query = query.filter(EjecucionPresupuestal.linea_presupuesto_id == linea_presupuesto_id)
    if factura_id:
        query = query.filter(EjecucionPresupuestal.factura_id == factura_id)
    if año_ejecucion:
        query = query.filter(EjecucionPresupuestal.año_ejecucion == año_ejecucion)
    if mes_ejecucion:
        query = query.filter(EjecucionPresupuestal.mes_ejecucion == mes_ejecucion)
    if estado:
        query = query.filter(EjecucionPresupuestal.estado == estado)

    return query.order_by(
        desc(EjecucionPresupuestal.periodo_ejecucion)
    ).offset(skip).limit(limit).all()


def aprobar_ejecucion_nivel1(
    db: Session,
    ejecucion_id: int,
    aprobador: str,
    observaciones: Optional[str] = None
) -> Optional[EjecucionPresupuestal]:
    """Aprueba una ejecución presupuestal en nivel 1 (Usuario de Línea)."""
    ejecucion = get_ejecucion_presupuestal(db, ejecucion_id)
    if not ejecucion:
        return None

    ejecucion.aprobado_nivel1 = True
    ejecucion.aprobador_nivel1 = aprobador
    ejecucion.fecha_aprobacion_nivel1 = datetime.now()
    ejecucion.observaciones_nivel1 = observaciones

    # Si no requiere más aprobaciones, marcar como aprobada
    if not ejecucion.requiere_aprobacion_nivel2:
        ejecucion.estado = EstadoEjecucion.APROBADO
        ejecucion.fecha_aprobacion_final = datetime.now()

        # Recalcular ejecución de la línea
        recalcular_ejecucion_linea(db, ejecucion.linea_presupuesto_id)
    else:
        ejecucion.estado = EstadoEjecucion.APROBADO_NIVEL1

    db.commit()
    db.refresh(ejecucion)
    return ejecucion


def aprobar_ejecucion_nivel2(
    db: Session,
    ejecucion_id: int,
    aprobador: str,
    observaciones: Optional[str] = None
) -> Optional[EjecucionPresupuestal]:
    """Aprueba una ejecución presupuestal en nivel 2 (Jefe de Área)."""
    ejecucion = get_ejecucion_presupuestal(db, ejecucion_id)
    if not ejecucion or not ejecucion.aprobado_nivel1:
        return None

    ejecucion.aprobado_nivel2 = True
    ejecucion.aprobador_nivel2 = aprobador
    ejecucion.fecha_aprobacion_nivel2 = datetime.now()
    ejecucion.observaciones_nivel2 = observaciones

    # Si no requiere aprobación nivel 3, marcar como aprobada
    if not ejecucion.requiere_aprobacion_nivel3:
        ejecucion.estado = EstadoEjecucion.APROBADO
        ejecucion.fecha_aprobacion_final = datetime.now()

        # Recalcular ejecución de la línea
        recalcular_ejecucion_linea(db, ejecucion.linea_presupuesto_id)
    else:
        ejecucion.estado = EstadoEjecucion.APROBADO_NIVEL2

    db.commit()
    db.refresh(ejecucion)
    return ejecucion


def aprobar_ejecucion_nivel3(
    db: Session,
    ejecucion_id: int,
    aprobador: str,
    observaciones: Optional[str] = None
) -> Optional[EjecucionPresupuestal]:
    """Aprueba una ejecución presupuestal en nivel 3 (CFO/Gerencia)."""
    ejecucion = get_ejecucion_presupuestal(db, ejecucion_id)
    if not ejecucion or not ejecucion.aprobado_nivel2:
        return None

    ejecucion.aprobado_nivel3 = True
    ejecucion.aprobador_nivel3 = aprobador
    ejecucion.fecha_aprobacion_nivel3 = datetime.now()
    ejecucion.observaciones_nivel3 = observaciones

    ejecucion.estado = EstadoEjecucion.APROBADO
    ejecucion.fecha_aprobacion_final = datetime.now()

    # Recalcular ejecución de la línea
    recalcular_ejecucion_linea(db, ejecucion.linea_presupuesto_id)

    db.commit()
    db.refresh(ejecucion)
    return ejecucion


def rechazar_ejecucion(
    db: Session,
    ejecucion_id: int,
    rechazado_por: str,
    motivo_rechazo: str
) -> Optional[EjecucionPresupuestal]:
    """Rechaza una ejecución presupuestal."""
    ejecucion = get_ejecucion_presupuestal(db, ejecucion_id)
    if not ejecucion:
        return None

    ejecucion.estado = EstadoEjecucion.RECHAZADO
    ejecucion.motivo_rechazo = motivo_rechazo
    ejecucion.actualizado_por = rechazado_por
    ejecucion.actualizado_en = datetime.now()

    db.commit()
    db.refresh(ejecucion)
    return ejecucion


# ========================================
# Funciones de Análisis y Reportes
# ========================================

def get_dashboard_presupuesto(
    db: Session,
    año_fiscal: int,
    responsable_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Genera un dashboard ejecutivo del presupuesto con métricas clave.
    """
    query = db.query(LineaPresupuesto).filter(LineaPresupuesto.año_fiscal == año_fiscal)

    if responsable_id:
        query = query.filter(LineaPresupuesto.responsable_id == responsable_id)

    lineas = query.all()

    # Calcular métricas agregadas
    total_presupuesto = sum([linea.presupuesto_anual for linea in lineas])
    total_ejecutado = sum([linea.ejecutado_acumulado for linea in lineas])
    total_saldo = total_presupuesto - total_ejecutado
    porcentaje_ejecucion_global = (total_ejecutado / total_presupuesto * 100) if total_presupuesto > 0 else 0

    # Contar líneas por estado
    lineas_por_estado = {}
    for estado in EstadoLineaPresupuesto:
        lineas_por_estado[estado.value] = len([l for l in lineas if l.estado == estado])

    # Identificar líneas en riesgo (sobre 80% de ejecución)
    lineas_en_riesgo = [
        {
            "id": linea.id,
            "codigo": linea.codigo,
            "nombre": linea.nombre,
            "porcentaje_ejecucion": float(linea.porcentaje_ejecucion),
            "saldo_disponible": float(linea.saldo_disponible)
        }
        for linea in lineas
        if linea.porcentaje_ejecucion and linea.porcentaje_ejecucion >= linea.umbral_alerta_porcentaje
    ]

    return {
        "año_fiscal": año_fiscal,
        "total_lineas": len(lineas),
        "presupuesto_total": float(total_presupuesto),
        "ejecutado_total": float(total_ejecutado),
        "saldo_total": float(total_saldo),
        "porcentaje_ejecucion_global": float(porcentaje_ejecucion_global),
        "lineas_por_estado": lineas_por_estado,
        "lineas_en_riesgo": lineas_en_riesgo,
        "total_lineas_en_riesgo": len(lineas_en_riesgo)
    }


def get_ejecucion_mensual(
    db: Session,
    linea_presupuesto_id: int
) -> List[Dict[str, Any]]:
    """
    Retorna la comparación presupuesto vs ejecución mes a mes para una línea.
    """
    linea = get_linea_presupuesto(db, linea_presupuesto_id)
    if not linea:
        return []

    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    resultado = []

    for idx, mes in enumerate(meses, start=1):
        presupuesto_mes = getattr(linea, f"presupuesto_{mes}") or Decimal("0.00")

        # Sumar ejecuciones del mes
        ejecutado_mes = db.query(func.sum(EjecucionPresupuestal.monto_ejecutado)).filter(
            and_(
                EjecucionPresupuestal.linea_presupuesto_id == linea_presupuesto_id,
                EjecucionPresupuestal.mes_ejecucion == idx,
                EjecucionPresupuestal.aprobado_nivel1 == True
            )
        ).scalar() or Decimal("0.00")

        desviacion = ejecutado_mes - presupuesto_mes
        porcentaje = (ejecutado_mes / presupuesto_mes * 100) if presupuesto_mes > 0 else 0

        resultado.append({
            "mes": mes.upper(),
            "mes_numero": idx,
            "presupuesto": float(presupuesto_mes),
            "ejecutado": float(ejecutado_mes),
            "desviacion": float(desviacion),
            "porcentaje_ejecucion": float(porcentaje)
        })

    return resultado
