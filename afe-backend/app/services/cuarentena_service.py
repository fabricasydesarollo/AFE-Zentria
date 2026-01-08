"""
Servicio de gestión de facturas en cuarentena.

Gestiona facturas que no pudieron procesarse automáticamente,
clasificadas por tipo de problema.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime
from collections import defaultdict

from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura
from app.models.grupo import Grupo, ResponsableGrupo
from app.models.proveedor import Proveedor

logger = logging.getLogger(__name__)


class CuarentenaService:
    """Servicio para gestión de facturas en cuarentena."""

    def __init__(self, db: Session):
        self.db = db

    def obtener_resumen_cuarentena(self) -> Dict[str, Any]:
        """Obtiene resumen de facturas en cuarentena clasificado por tipo de error."""
        facturas_cuarentena = self.db.query(Factura).filter(
            Factura.estado == EstadoFactura.en_cuarentena
        ).all()

        if not facturas_cuarentena:
            return {
                "total": 0,
                "problemas": [],
                "impacto_financiero": 0,
                "acciones_recomendadas": [],
                "mensaje": "No hay facturas en cuarentena"
            }

        problemas_clasificados = self._clasificar_problemas(facturas_cuarentena)
        impacto_total = sum(float(f.total_a_pagar or 0) for f in facturas_cuarentena)
        acciones = self._generar_acciones_recomendadas(problemas_clasificados)

        return {
            "total": len(facturas_cuarentena),
            "problemas": problemas_clasificados,
            "impacto_financiero": round(impacto_total, 2),
            "acciones_recomendadas": acciones,
            "mensaje": f"{len(facturas_cuarentena)} facturas requieren configuración"
        }

    def _clasificar_problemas(self, facturas: List[Factura]) -> List[Dict[str, Any]]:
        """Clasifica facturas por tipo de problema usando metadata de workflows."""
        grupos_error = defaultdict(list)

        for factura in facturas:
            workflow = self.db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            if workflow and workflow.metadata_workflow:
                tipo_error = workflow.metadata_workflow.get('tipo_error', 'SIN_CLASIFICAR')
                categoria = workflow.metadata_workflow.get('categoria', 'DESCONOCIDA')
                severidad = workflow.metadata_workflow.get('severidad', 'MEDIA')
                accion_dirigida = workflow.metadata_workflow.get('accion_dirigida', {})

                grupos_error[tipo_error].append({
                    'factura': factura,
                    'workflow': workflow,
                    'categoria': categoria,
                    'severidad': severidad,
                    'accion_dirigida': accion_dirigida
                })
            else:
                grupos_error['SIN_CLASIFICAR'].append({
                    'factura': factura,
                    'workflow': workflow,
                    'categoria': 'DESCONOCIDA',
                    'severidad': 'MEDIA',
                    'accion_dirigida': {}
                })

        problemas = []
        for tipo_error, items in grupos_error.items():
            total_facturas = len(items)
            impacto_financiero = sum(float(item['factura'].total_a_pagar or 0) for item in items)
            primer_item = items[0]
            categoria = primer_item['categoria']
            severidad = primer_item['severidad']
            accion_dirigida = primer_item['accion_dirigida']

            if tipo_error == 'GRUPO_SIN_RESPONSABLES':
                subproblemas = self._agrupar_por_grupo(items)
            else:
                subproblemas = []

            problemas.append({
                'tipo_error': tipo_error,
                'categoria': categoria,
                'severidad': severidad,
                'total_facturas': total_facturas,
                'impacto_financiero': round(impacto_financiero, 2),
                'accion_dirigida': accion_dirigida,
                'subproblemas': subproblemas,
                'facturas_ids': [item['factura'].id for item in items]
            })

        prioridad_severidad = {'CRITICA': 0, 'ALTA': 1, 'MEDIA': 2, 'BAJA': 3}
        problemas.sort(
            key=lambda x: (
                prioridad_severidad.get(x['severidad'], 4),
                -x['total_facturas']
            )
        )

        return problemas

    def _agrupar_por_grupo(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Agrupa facturas por grupo_id para corrección masiva."""
        grupos = defaultdict(list)

        for item in items:
            grupo_id = item['factura'].grupo_id
            if grupo_id:
                grupos[grupo_id].append(item)

        subproblemas = []
        for grupo_id, grupo_items in grupos.items():
            grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
            nombre_grupo = grupo.nombre if grupo else f"Grupo ID {grupo_id}"
            codigo_grupo = grupo.codigo if grupo else "N/A"

            total_facturas = len(grupo_items)
            impacto = sum(float(item['factura'].total_a_pagar or 0) for item in grupo_items)

            subproblemas.append({
                'grupo_id': grupo_id,
                'nombre_grupo': nombre_grupo,
                'codigo_grupo': codigo_grupo,
                'total_facturas': total_facturas,
                'impacto_financiero': round(impacto, 2),
                'accion_dirigida': {
                    'tipo': 'ASIGNAR_RESPONSABLES_GRUPO',
                    'url': f'/admin/grupos/{grupo_id}/responsables',
                    'descripcion': f'Asignar responsables al grupo {nombre_grupo}',
                    'parametros': {
                        'grupo_id': grupo_id,
                        'nombre_grupo': nombre_grupo,
                        'codigo_grupo': codigo_grupo
                    }
                },
                'facturas_ids': [item['factura'].id for item in grupo_items]
            })

        subproblemas.sort(key=lambda x: -x['impacto_financiero'])

        return subproblemas

    def _generar_acciones_recomendadas(
        self,
        problemas: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Genera lista priorizada de acciones recomendadas con deep-links."""
        acciones = []

        for problema in problemas:
            tipo_error = problema['tipo_error']

            if tipo_error == 'GRUPO_SIN_RESPONSABLES':
                for subproblema in problema.get('subproblemas', []):
                    acciones.append({
                        'prioridad': 1,
                        'titulo': f"Asignar responsables: {subproblema['nombre_grupo']}",
                        'descripcion': (
                            f"{subproblema['total_facturas']} facturas bloqueadas "
                            f"(${subproblema['impacto_financiero']:,.2f})"
                        ),
                        'tipo_accion': 'ASIGNAR_RESPONSABLES',
                        'url': subproblema['accion_dirigida']['url'],
                        'parametros': subproblema['accion_dirigida']['parametros'],
                        'impacto': {
                            'facturas_liberadas': subproblema['total_facturas'],
                            'monto_total': subproblema['impacto_financiero']
                        },
                        'tiempo_estimado': '5-10 minutos'
                    })

            elif tipo_error == 'GRUPO_NO_ASIGNADO':
                acciones.append({
                    'prioridad': 1,
                    'titulo': f"Configurar asignación de grupos",
                    'descripcion': (
                        f"{problema['total_facturas']} facturas sin grupo asignado "
                        f"(${problema['impacto_financiero']:,.2f})"
                    ),
                    'tipo_accion': 'CONFIGURAR_GRUPOS',
                    'url': '/admin/proveedores/asignacion-grupos',
                    'parametros': {},
                    'impacto': {
                        'facturas_liberadas': problema['total_facturas'],
                        'monto_total': problema['impacto_financiero']
                    },
                    'tiempo_estimado': '15-30 minutos'
                })

            else:
                acciones.append({
                    'prioridad': 2,
                    'titulo': f"Revisar facturas sin clasificar",
                    'descripcion': (
                        f"{problema['total_facturas']} facturas requieren revisión manual"
                    ),
                    'tipo_accion': 'REVISION_MANUAL',
                    'url': '/admin/cuarentena/sin-clasificar',
                    'parametros': {},
                    'impacto': {
                        'facturas_liberadas': problema['total_facturas'],
                        'monto_total': problema['impacto_financiero']
                    },
                    'tiempo_estimado': 'Variable'
                })

        acciones.sort(key=lambda x: (x['prioridad'], -x['impacto']['monto_total']))

        return acciones

    def obtener_facturas_cuarentena(
        self,
        tipo_error: Optional[str] = None,
        grupo_id: Optional[int] = None,
        limite: int = 100
    ) -> List[Factura]:
        """Obtiene facturas en cuarentena con filtros opcionales."""
        query = self.db.query(Factura).filter(
            Factura.estado == EstadoFactura.en_cuarentena
        )

        if grupo_id:
            query = query.filter(Factura.grupo_id == grupo_id)

        if tipo_error:
            query = query.join(
                WorkflowAprobacionFactura,
                Factura.id == WorkflowAprobacionFactura.factura_id
            ).filter(
                WorkflowAprobacionFactura.metadata_workflow['tipo_error'].astext == tipo_error
            )

        return query.limit(limite).all()

    def liberar_facturas_grupo(self, grupo_id: int) -> Dict[str, Any]:
        """
        Libera facturas de un grupo en cuarentena.

        Crea workflows para visibilidad en dashboard sin enviar notificaciones
        (son facturas históricas de ciclos anteriores).
        """
        responsables_grupo = self.db.query(ResponsableGrupo).filter(
            and_(
                ResponsableGrupo.grupo_id == grupo_id,
                ResponsableGrupo.activo == True
            )
        ).all()

        if not responsables_grupo:
            return {
                'exito': False,
                'error': f'Grupo {grupo_id} aún no tiene responsables asignados'
            }

        facturas_grupo = self.db.query(Factura).filter(
            and_(
                Factura.grupo_id == grupo_id,
                Factura.estado == EstadoFactura.en_cuarentena
            )
        ).all()

        if not facturas_grupo:
            return {
                'exito': True,
                'facturas_liberadas': 0,
                'workflows_creados': 0,
                'mensaje': f'No hay facturas en cuarentena para grupo {grupo_id}'
            }

        facturas_liberadas = []
        workflows_creados = []

        for factura in facturas_grupo:
            factura.estado = EstadoFactura.en_revision

            workflow_anterior = self.db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            if workflow_anterior and workflow_anterior.metadata_workflow:
                workflow_anterior.metadata_workflow['liberada_de_cuarentena'] = True
                workflow_anterior.metadata_workflow['fecha_liberacion'] = datetime.now().isoformat()
                workflow_anterior.metadata_workflow['liberada_por'] = 'SISTEMA_AUTO'
                workflow_anterior.metadata_workflow['sin_notificacion'] = True
                workflow_anterior.metadata_workflow['razon_sin_notificacion'] = 'Factura histórica - ciclo mensual anterior'

            for responsable in responsables_grupo:
                workflow_nuevo = WorkflowAprobacionFactura(
                    factura_id=factura.id,
                    estado=EstadoFacturaWorkflow.RECIBIDA,
                    nit_proveedor=factura.proveedor.nit if factura.proveedor else None,
                    responsable_id=responsable.responsable_id,
                    area_responsable=responsable.responsable.area if hasattr(responsable.responsable, 'area') else None,
                    fecha_asignacion=datetime.now(),
                    creado_en=datetime.now(),
                    creado_por="SISTEMA_AUTO_LIBERACION_CUARENTENA",
                    metadata_workflow={
                        "liberada_de_cuarentena": True,
                        "fecha_liberacion": datetime.now().isoformat(),
                        "grupo_id": grupo_id,
                        "asignacion_automatica": True,
                        "sin_notificacion_email": True,
                        "razon": "Factura histórica - visible en dashboard sin notificación",
                        "ciclo": "ANTERIOR"
                    }
                )

                self.db.add(workflow_nuevo)
                workflows_creados.append(workflow_nuevo)

            factura.responsable_id = responsables_grupo[0].responsable_id
            facturas_liberadas.append(factura.id)

        self.db.commit()

        logger.info(
            f"Liberación completa SIN notificaciones: {len(facturas_liberadas)} facturas históricas, "
            f"{len(workflows_creados)} workflows creados",
            extra={
                'grupo_id': grupo_id,
                'facturas_liberadas': facturas_liberadas,
                'workflows_creados': len(workflows_creados),
                'responsables_asignados': [r.responsable_id for r in responsables_grupo],
                'notificaciones_enviadas': 0,
                'razon': 'Facturas históricas - ciclo mensual anterior'
            }
        )

        return {
            'exito': True,
            'facturas_liberadas': len(facturas_liberadas),
            'facturas_ids': facturas_liberadas,
            'workflows_creados': len(workflows_creados),
            'responsables_asignados': [r.responsable_id for r in responsables_grupo],
            'notificaciones_enviadas': 0,
            'mensaje': (
                f'{len(facturas_liberadas)} facturas históricas liberadas y visibles en dashboard. '
                f'{len(workflows_creados)} workflows creados. '
                f'Sin notificaciones (facturas de ciclo anterior). '
                f'Facturas nuevas SÍ generarán notificaciones.'
            )
        }
