"""
Event Listeners para el modelo Factura.

Sincronización automática de campos calculados/derivados.

ARQUITECTURA:
- Event listeners de SQLAlchemy (ejecutados en Python)
- Se disparan ANTES de hacer commit a la BD
- Mantienen la sincronización de campos relacionados

VENTAJAS:
1. Sincronización automática en tiempo real
2. Código centralizado y fácil de mantener
3. Se ejecuta en TODOS los flujos (API, scripts, migraciones)
4. Fácil de testear
5. No requiere código SQL duplicado

Fecha: 2025-12-15
"""

from sqlalchemy import event
from sqlalchemy.orm import Session
from app.models.factura import Factura, EstadoFactura
from app.models.usuario import Usuario
from app.utils.logger import logger


@event.listens_for(Factura, 'before_update')
def sincronizar_accion_por_on_update(mapper, connection, target: Factura):
    """
    Sincroniza automáticamente el campo accion_por cuando:
    1. Cambia el responsable_id
    2. Cambia el estado de la factura

    LÓGICA DE SINCRONIZACIÓN:
    - Si estado = 'aprobada_auto' → accion_por = 'Sistema Automático'
    - Si estado = 'aprobada' o 'rechazada' → accion_por = nombre del responsable
    - Si estado = 'en_revision' → accion_por = NULL (factura sin procesar)

    Este listener se ejecuta ANTES de hacer UPDATE en la BD.
    """

    # Obtener el estado anterior del objeto
    state = target._sa_instance_state
    history = state.get_history('estado', True)
    responsable_history = state.get_history('responsable_id', True)

    # Flags de cambios
    estado_changed = history and history.has_changes()
    responsable_changed = responsable_history and responsable_history.has_changes()

    # Si no cambiaron los campos relevantes, no hacer nada
    if not estado_changed and not responsable_changed:
        return

    # SINCRONIZACIÓN AUTOMÁTICA
    estado_actual = target.estado

    # Caso 1: Aprobación automática
    if estado_actual == EstadoFactura.aprobada_auto:
        if target.accion_por != 'Sistema Automático':
            logger.info(f"[SYNC] Factura {target.numero_factura}: accion_por → 'Sistema Automático'")
            target.accion_por = 'Sistema Automático'

    # Caso 2: Aprobación manual
    elif estado_actual == EstadoFactura.aprobada:
        if target.responsable_id:
            # Obtener nombre del responsable
            session = Session.object_session(target)
            if session:
                responsable = session.query(Usuario).filter(Usuario.id == target.responsable_id).first()
                if responsable:
                    nuevo_accion_por = responsable.nombre
                    if target.accion_por != nuevo_accion_por:
                        logger.info(f"[SYNC] Factura {target.numero_factura}: accion_por → '{nuevo_accion_por}'")
                        target.accion_por = nuevo_accion_por

    # Caso 3: Rechazo
    elif estado_actual == EstadoFactura.rechazada:
        if target.responsable_id:
            session = Session.object_session(target)
            if session:
                responsable = session.query(Usuario).filter(Usuario.id == target.responsable_id).first()
                if responsable:
                    nuevo_accion_por = responsable.nombre
                    if target.accion_por != nuevo_accion_por:
                        logger.info(f"[SYNC] Factura {target.numero_factura}: accion_por → '{nuevo_accion_por}' (rechazada)")
                        target.accion_por = nuevo_accion_por

    # Caso 4: En revisión (limpiar accion_por)
    elif estado_actual == EstadoFactura.en_revision:
        if target.accion_por is not None:
            logger.info(f"[SYNC] Factura {target.numero_factura}: accion_por → NULL (en revisión)")
            target.accion_por = None


@event.listens_for(Factura, 'before_insert')
def sincronizar_accion_por_on_insert(mapper, connection, target: Factura):
    """
    Sincroniza accion_por al CREAR una factura nueva.

    Útil cuando se crean facturas directamente con estado 'aprobada_auto'.
    """
    if target.estado == EstadoFactura.aprobada_auto:
        if target.accion_por != 'Sistema Automático':
            logger.info(f"[SYNC-INSERT] Factura {target.numero_factura}: accion_por → 'Sistema Automático'")
            target.accion_por = 'Sistema Automático'


# OPCIONAL: Listener para cambios de responsable_id solamente
@event.listens_for(Factura.responsable_id, 'set')
def on_responsable_id_changed(target: Factura, value, oldvalue, initiator):
    """
    Event listener que se dispara cuando cambia responsable_id.

    CASOS DE USO:
    1. Se reasigna una factura a otro usuario
    2. Se asigna un responsable a una factura sin asignar

    SINCRONIZACIÓN:
    - Si la factura ya tiene un accion_por, actualizarlo con el nuevo responsable
    - Solo si el estado es 'aprobada' o 'rechazada'
    """

    # Solo sincronizar si la factura ya tiene acción tomada
    if target.estado in [EstadoFactura.aprobada, EstadoFactura.rechazada]:
        if value and value != oldvalue:  # Cambió el responsable
            session = Session.object_session(target)
            if session:
                nuevo_responsable = session.query(Usuario).filter(Usuario.id == value).first()
                if nuevo_responsable:
                    logger.info(
                        f"[SYNC-RESPONSABLE] Factura {target.numero_factura}: "
                        f"responsable cambió de {oldvalue} → {value}, "
                        f"actualizando accion_por → '{nuevo_responsable.nombre}'"
                    )
                    target.accion_por = nuevo_responsable.nombre


# Registrar los listeners cuando se importe este módulo
logger.info("[EVENT-LISTENERS] Listeners de sincronización de accion_por registrados correctamente")
