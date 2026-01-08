# app/services/invoice_service.py
"""
Servicio de procesamiento y persistencia de facturas.

Gestiona validación, deduplicación, auto-creación de proveedores,
y activación de workflows de aprobación.
"""

from sqlalchemy.orm import Session
from app.crud.factura import create_factura, find_by_cufe, find_by_numero_proveedor, update_factura
from app.crud.audit import create_audit
from app.crud.proveedor import get_proveedor_by_nit, create_proveedor
from app.schemas.factura import FacturaCreate
from app.schemas.proveedor import ProveedorBase
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def process_and_persist_invoice(
    db: Session,
    payload: FacturaCreate,
    created_by: str,
    auto_create_provider: bool = True
) -> Tuple[dict, str]:
    """
    Procesa y persiste una factura en BD.

    Realiza validación, deduplicación, auto-creación de proveedor si es necesario,
    y activa el workflow de aprobación.

    Args:
        db: Sesión de BD
        payload: Datos de la factura
        created_by: Usuario/sistema que crea
        auto_create_provider: Si True, auto-crea proveedor si no existe

    Returns:
        Tuple[dict, str]: (resultado, acción)
    """
    data = payload.dict()

    # Validación de campos obligatorios

    if data.get("total") is None:
        raise ValueError("El campo 'total' es obligatorio y debe venir en la factura.")
    if data.get("total_a_pagar") is None:
        raise ValueError("El campo 'total_a_pagar' es obligatorio y debe venir en la factura.")

    # Auto-creación/búsqueda de proveedor
    if auto_create_provider and not data.get("proveedor_id"):
        try:
            nit_proveedor = data.get("nit")

            if nit_proveedor:
                logger.info(
                    f"Buscando proveedor por NIT",
                    extra={
                        "nit": nit_proveedor,
                        "numero_factura": data.get("numero_factura"),
                        "cufe": data.get("cufe")
                    }
                )

                # Buscar proveedor existente por NIT
                proveedor = get_proveedor_by_nit(db=db, nit=nit_proveedor)
                fue_creado = False

                if not proveedor and auto_create_provider:
                    try:
                        proveedor_data = ProveedorBase(
                            nit=nit_proveedor,
                            razon_social=data.get("nombre_proveedor") or "Sin especificar",
                            email=data.get("email_proveedor"),
                            telefono=data.get("telefono_proveedor"),
                            direccion=data.get("direccion_proveedor"),
                            area=data.get("area_proveedor")
                        )
                        proveedor = create_proveedor(db=db, data=proveedor_data)
                        fue_creado = True
                        logger.info(
                            f"Proveedor AUTO-CREADO exitosamente",
                            extra={
                                "proveedor_id": proveedor.id,
                                "nit": nit_proveedor,
                                "razon_social": proveedor.razon_social
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Error creando proveedor",
                            extra={
                                "nit": nit_proveedor,
                                "error": str(e),
                                "numero_factura": data.get("numero_factura")
                            },
                            exc_info=True
                        )

                if proveedor:
                    data["proveedor_id"] = proveedor.id
                    if not fue_creado:
                        logger.debug(
                            f"Proveedor encontrado existente",
                            extra={
                                "proveedor_id": proveedor.id,
                                "nit": nit_proveedor,
                                "razon_social": proveedor.razon_social
                            }
                        )

        except Exception as e:
            logger.warning(
                f"No se pudo auto-crear/buscar proveedor (continuar sin proveedor)",
                extra={
                    "nit": data.get("nit"),
                    "error": str(e),
                    "numero_factura": data.get("numero_factura")
                }
            )

        except Exception as e:
            logger.error(
                f"Error inesperado auto-creando proveedor",
                extra={
                    "nit": data.get("nit"),
                    "error": str(e),
                    "numero_factura": data.get("numero_factura")
                },
                exc_info=True
            )

    # Deduplicación por CUFE
    existing = find_by_cufe(db, data["cufe"])
    if existing:
        changed_fields = {}
        for key in ["subtotal", "iva", "total", "total_a_pagar", "observaciones"]:
            if getattr(existing, key) != data.get(key):
                changed_fields[key] = data.get(key)
        if changed_fields:
            inv = update_factura(db, existing, changed_fields)
            create_audit(
                db, "factura", inv.id, "update", created_by,
                {"reason": "update on existing cufe", "changes": changed_fields}
            )
            return {"id": inv.id, "action": "updated"}, "updated"
        return {"id": existing.id, "action": "ignored"}, "ignored"

    # Deduplicación por número + proveedor
    if data.get("proveedor_id") is not None:
        existing2 = find_by_numero_proveedor(db, data["numero_factura"], data["proveedor_id"])
        if existing2:
            if existing2.cufe != data["cufe"]:
                create_audit(
                    db,
                    "factura",
                    existing2.id,
                    "conflict",
                    created_by,
                    {
                        "msg": "numero/proveedor exists with different cufe",
                        "existing_cufe": existing2.cufe,
                        "incoming_cufe": data["cufe"],
                    },
                )
                return {"id": existing2.id, "action": "conflict"}, "conflict"
            return {"id": existing2.id, "action": "ignored"}, "ignored"

    # Asignar grupo_id automáticamente desde asignación de NITs
    if data.get("grupo_id") is None and data.get("proveedor_id") is not None:
        try:
            from app.models.proveedor import Proveedor
            from app.crud.asignacion_nit import get_grupo_id_por_nit

            proveedor = db.query(Proveedor).filter(Proveedor.id == data.get("proveedor_id")).first()

            if proveedor and proveedor.nit:
                grupo_id = get_grupo_id_por_nit(db, proveedor.nit)

                if grupo_id:
                    data["grupo_id"] = grupo_id
                    logger.info(
                        f"Grupo ID asignado automáticamente desde asignacion_nit_responsable",
                        extra={
                            "proveedor_id": data.get("proveedor_id"),
                            "nit": proveedor.nit,
                            "grupo_id": data["grupo_id"],
                            "numero_factura": data.get("numero_factura")
                        }
                    )
                else:
                    logger.debug(
                        f"NIT no tiene grupo asignado en asignacion_nit_responsable",
                        extra={
                            "nit": proveedor.nit,
                            "proveedor_id": data.get("proveedor_id"),
                            "numero_factura": data.get("numero_factura")
                        }
                    )
            else:
                logger.debug(
                    f"Proveedor sin NIT, no se puede asignar grupo",
                    extra={
                        "proveedor_id": data.get("proveedor_id"),
                        "numero_factura": data.get("numero_factura")
                    }
                )

        except Exception as e:
            logger.warning(
                f"Error al intentar asignar grupo_id automáticamente",
                extra={
                    "proveedor_id": data.get("proveedor_id"),
                    "error": str(e),
                    "numero_factura": data.get("numero_factura")
                }
            )

    # Crear nueva factura (remover 'total' que es propiedad calculada)
    data_para_crear = {k: v for k, v in data.items() if k != 'total'}
    
    inv = create_factura(db, data_para_crear)
    create_audit(
        db,
        "factura",
        inv.id,
        "create",
        created_by,
        {
            "msg": "Nueva factura creada desde Microsoft Graph",
            "proveedor_id": data.get("proveedor_id"),
            "proveedor_auto_creado": data.get("proveedor_id") is not None,
            "grupo_id": data.get("grupo_id"),
            "grupo_asignado_automaticamente": data.get("grupo_id") is not None
        }
    )

    # Activar workflow automático
    try:
        from app.services.workflow_automatico import WorkflowAutomaticoService
        workflow_service = WorkflowAutomaticoService(db)

        logger.info(f"Iniciando workflow automático para factura {inv.id}")
        workflow_resultado = workflow_service.procesar_factura_nueva(inv.id)
        logger.info(f"Resultado del workflow: {workflow_resultado}")

        if workflow_resultado.get("exito"):
            logger.info(
                f"Workflow creado exitosamente para factura {inv.id}",
                extra={
                    "factura_id": inv.id,
                    "responsable_id": workflow_resultado.get('responsable_id'),
                    "nit": workflow_resultado.get('nit'),
                    "tipo_aprobacion": workflow_resultado.get('tipo_aprobacion', 'N/A'),
                    "proveedor_id": data.get("proveedor_id")
                }
            )
        else:
            logger.warning(
                f"Workflow NO se creó para factura {inv.id}. Resultado: {workflow_resultado}",
                extra={
                    "factura_id": inv.id,
                    "error": workflow_resultado.get('error'),
                    "nit": workflow_resultado.get('nit'),
                    "mensaje": workflow_resultado.get('mensaje'),
                    "requiere_configuracion": workflow_resultado.get('requiere_configuracion', False),
                    "proveedor_id": data.get("proveedor_id")
                }
            )

            create_audit(
                db,
                "workflow",
                inv.id,
                "warning",
                "SISTEMA",
                {
                    "msg": "Workflow no se creó - requiere configuración",
                    "resultado_completo": workflow_resultado,
                    "nit": workflow_resultado.get('nit'),
                    "requiere_configuracion": workflow_resultado.get('requiere_configuracion', False)
                }
            )

    except Exception as e:
        logger.error(
            f"ERROR CRÍTICO al crear workflow para factura {inv.id}: {str(e)}",
            extra={
                "factura_id": inv.id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "proveedor_id": data.get("proveedor_id")
            },
            exc_info=True
        )

        create_audit(
            db,
            "workflow",
            inv.id,
            "error",
            "SISTEMA",
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "msg": "Error crítico al crear workflow automático",
                "severity": "CRITICAL"
            }
        )

    return {"id": inv.id, "action": "created"}, "created"


