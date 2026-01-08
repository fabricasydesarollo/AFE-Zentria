"""
Servicio de automatización del flujo de facturas.

Orquesta el flujo de automatización mensual: análisis de patrones,
comparación con histórico, aprobación automática y notificaciones.
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.factura import Factura, EstadoFactura
from app.models.patrones_facturas import PatronesFacturas, TipoPatron
from app.models.proveedor import Proveedor
from app.services.analisis_patrones_service import AnalizadorPatronesService
from app.services.notificaciones import NotificacionService
from app.utils.date_helpers import DateHelper


logger = logging.getLogger(__name__)


class FlujoAutomatizacionFacturas:
    """Orquestador principal del flujo de automatización mensual de facturas."""

    def __init__(self, db: Session):
        self.db = db
        self.analizador_patrones = AnalizadorPatronesService(db)
        self.notification_service = NotificacionService(db)

        self.stats = {
            'facturas_marcadas_pagadas': 0,
            'facturas_pendientes_analizadas': 0,
            'facturas_aprobadas_auto': 0,
            'facturas_requieren_revision': 0,
            'notificaciones_enviadas': 0,
            'errores': 0
        }

    def ejecutar_flujo_automatizacion_completo(
        self,
        periodo_analisis: Optional[str] = None,
        solo_proveedores: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Ejecuta el flujo completo de automatización mensual."""
        logger.info("=" * 80)
        logger.info("INICIANDO FLUJO COMPLETO DE AUTOMATIZACION DE FACTURAS")
        logger.info("=" * 80)

        resultado_final = {
            'exito': True,
            'timestamp': datetime.utcnow().isoformat(),
            'pasos_completados': []
        }

        # PASO 1: Analizar patrones históricos
        logger.info("\nPASO 1: Analisis de patrones historicos")
        resultado_patrones = self.analizador_patrones.analizar_patrones_desde_bd(
            ventana_meses=12,
            solo_proveedores=solo_proveedores,
            forzar_recalculo=False
        )
        resultado_final['pasos_completados'].append({
            'paso': 'analisis_patrones',
            'resultado': resultado_patrones
        })

        # PASO 2: Comparar facturas pendientes con mes anterior
        logger.info("\nPASO 2: Comparacion y aprobacion automatica")
        resultado_comparacion = self.comparar_y_aprobar_facturas_pendientes(
            periodo_analisis=periodo_analisis,
            solo_proveedores=solo_proveedores
        )
        resultado_final['pasos_completados'].append({
            'paso': 'comparacion_aprobacion',
            'resultado': resultado_comparacion
        })

        # PASO 3: Enviar notificaciones
        logger.info("\nPASO 3: Envio de notificaciones")
        resultado_notificaciones = self.enviar_notificaciones_responsables(
            resultado_comparacion
        )
        resultado_final['pasos_completados'].append({
            'paso': 'notificaciones',
            'resultado': resultado_notificaciones
        })

        resultado_final['resumen'] = self._generar_resumen_final()

        logger.info("\n" + "=" * 80)
        logger.info("FLUJO COMPLETO DE AUTOMATIZACION FINALIZADO")
        logger.info("=" * 80)
        logger.info(f"   Facturas marcadas como pagadas: {self.stats['facturas_marcadas_pagadas']}")
        logger.info(f"   Facturas aprobadas automaticamente: {self.stats['facturas_aprobadas_auto']}")
        logger.info(f"   Facturas que requieren revision: {self.stats['facturas_requieren_revision']}")
        logger.info(f"   Notificaciones enviadas: {self.stats['notificaciones_enviadas']}")
        logger.info(f"   Errores: {self.stats['errores']}")
        logger.info("=" * 80)

        return resultado_final

    def comparar_y_aprobar_facturas_pendientes(
        self,
        periodo_analisis: Optional[str] = None,
        solo_proveedores: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Compara facturas pendientes con mes anterior y decide aprobación."""
        logger.info(" Comparando facturas pendientes con patrones históricos...")

        if not periodo_analisis:
            periodo_analisis = datetime.now().strftime('%Y-%m')

        facturas_pendientes = self._obtener_facturas_pendientes(
            periodo_analisis,
            solo_proveedores
        )

        logger.info(f"     {len(facturas_pendientes)} facturas pendientes a analizar")

        facturas_aprobadas = []
        facturas_revision = []

        for factura in facturas_pendientes:
            try:
                decision = self._decidir_aprobacion_factura(factura)

                if decision['aprobar_automaticamente']:
                    self._aprobar_factura_automaticamente(factura, decision)
                    facturas_aprobadas.append(decision)
                    self.stats['facturas_aprobadas_auto'] += 1
                else:
                    self._marcar_para_revision(factura, decision)
                    facturas_revision.append(decision)
                    self.stats['facturas_requieren_revision'] += 1

                self.stats['facturas_pendientes_analizadas'] += 1

            except Exception as e:
                logger.error(f"    Error procesando factura {factura.id}: {str(e)}")
                self.stats['errores'] += 1

        self.db.commit()

        return {
            'exito': True,
            'periodo': periodo_analisis,
            'facturas_analizadas': len(facturas_pendientes),
            'aprobadas_automaticamente': facturas_aprobadas,
            'requieren_revision': facturas_revision,
            'total_aprobadas': len(facturas_aprobadas),
            'total_revision': len(facturas_revision)
        }

    def _obtener_facturas_pendientes(
        self,
        periodo: str,
        solo_proveedores: Optional[List[int]]
    ) -> List[Factura]:
        """Obtiene facturas pendientes del período especificado."""
        query = self.db.query(Factura).filter(
            Factura.estado == EstadoFactura.en_revision,
            DateHelper.create_periodo_filter(Factura.fecha_emision, periodo),
            Factura.proveedor_id.isnot(None)
        )

        if solo_proveedores:
            query = query.filter(Factura.proveedor_id.in_(solo_proveedores))

        return query.all()

    def _decidir_aprobacion_factura(self, factura: Factura) -> Dict[str, Any]:
        """Decide si una factura debe aprobarse automáticamente basándose en patrones históricos."""
        concepto_normalizado = factura.concepto_normalizado or "servicio_general"
        concepto_hash = hashlib.md5(concepto_normalizado.encode('utf-8')).hexdigest()

        patron = self.db.query(PatronesFacturas).filter(
            PatronesFacturas.proveedor_id == factura.proveedor_id,
            PatronesFacturas.concepto_hash == concepto_hash
        ).first()

        decision = {
            'factura_id': factura.id,
            'numero_factura': factura.numero_factura,
            'proveedor': factura.proveedor.razon_social if factura.proveedor else "Desconocido",
            'monto_actual': float(factura.total_a_pagar or 0),
            'concepto': concepto_normalizado,
            'aprobar_automaticamente': False,
            'motivo': '',
            'confianza': 0.0,
            'patron_id': None,
            'monto_esperado': None,
            'desviacion_porcentual': None
        }

        if not patron:
            decision['motivo'] = "Sin historial previo - Requiere revisión manual"
            return decision

        decision['patron_id'] = patron.id
        decision['monto_esperado'] = float(patron.monto_promedio)

        if patron.puede_aprobar_auto != 1:
            decision['motivo'] = f"Patrón {patron.tipo_patron.value} no cumple criterios de auto-aprobación"
            return decision

        # Calcular desviación del monto actual vs esperado
        monto_actual = factura.total_a_pagar or Decimal('0')
        desviacion_porcentual = abs(
            (monto_actual - patron.monto_promedio) / patron.monto_promedio * 100
        ) if patron.monto_promedio > 0 else Decimal('100')

        decision['desviacion_porcentual'] = float(desviacion_porcentual)

        if desviacion_porcentual <= patron.umbral_alerta:
            decision['aprobar_automaticamente'] = True

            if patron.tipo_patron == TipoPatron.TIPO_A:
                confianza = 0.95 if desviacion_porcentual < 5 else 0.85
            elif patron.tipo_patron == TipoPatron.TIPO_B:
                confianza = 0.85 if desviacion_porcentual < 15 else 0.70
            else:
                confianza = 0.60

            decision['confianza'] = confianza
            decision['motivo'] = f"Patrón {patron.tipo_patron.value}: Monto dentro del rango esperado (±{patron.umbral_alerta}%)"

        else:
            decision['aprobar_automaticamente'] = False
            decision['motivo'] = f"Desviación {desviacion_porcentual:.1f}% excede umbral {patron.umbral_alerta}%"

        return decision

    def _aprobar_factura_automaticamente(
        self,
        factura: Factura,
        decision: Dict[str, Any]
    ) -> None:
        """Aprueba una factura automáticamente y registra información."""
        factura.estado = EstadoFactura.aprobada_auto
        factura.aprobada_automaticamente = True
        factura.confianza_automatica = Decimal(str(decision['confianza']))
        factura.motivo_decision = decision['motivo']
        factura.factura_referencia_id = decision['patron_id']
        factura.fecha_procesamiento_auto = datetime.utcnow()
        factura.actualizado_en = datetime.utcnow()
        factura.accion_por = 'Sistema Automático'

        logger.info(f"     APROBADA AUTO: {factura.numero_factura} - {decision['motivo']}")

    def _marcar_para_revision(
        self,
        factura: Factura,
        decision: Dict[str, Any]
    ) -> None:
        """Marca una factura para revisión manual."""
        factura.estado = EstadoFactura.en_revision
        factura.aprobada_automaticamente = False
        factura.motivo_decision = decision['motivo']
        factura.factura_referencia_id = decision['patron_id']
        factura.fecha_procesamiento_auto = datetime.utcnow()
        factura.actualizado_en = datetime.utcnow()

        logger.info(f"     REVISIÓN: {factura.numero_factura} - {decision['motivo']}")

    def enviar_notificaciones_responsables(
        self,
        resultado_comparacion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Envía notificaciones a los usuarios sobre facturas procesadas."""
        logger.info("Enviando notificaciones a usuarios...")

        facturas_por_responsable = self._agrupar_facturas_por_responsable(
            resultado_comparacion
        )

        notificaciones_enviadas = []

        for responsable_id, datos in facturas_por_responsable.items():
            try:
                mensaje = self._preparar_mensaje_notificacion(datos)

                notificaciones_enviadas.append({
                    'responsable_id': responsable_id,
                    'email': datos['email'],
                    'facturas_aprobadas': len(datos['aprobadas']),
                    'facturas_revision': len(datos['revision']),
                    'mensaje': mensaje
                })

                self.stats['notificaciones_enviadas'] += 1

                logger.info(f"     Notificación enviada a: {datos['email']}")

            except Exception as e:
                logger.error(f"    Error enviando notificación: {str(e)}")
                self.stats['errores'] += 1

        return {
            'exito': True,
            'notificaciones_enviadas': notificaciones_enviadas,
            'total': len(notificaciones_enviadas)
        }

    def _agrupar_facturas_por_responsable(
        self,
        resultado_comparacion: Dict[str, Any]
    ) -> Dict[int, Dict[str, Any]]:
        """Agrupa facturas por responsable para notificaciones."""
        facturas_por_responsable = {}

        for factura_data in resultado_comparacion.get('aprobadas_automaticamente', []):
            factura = self.db.query(Factura).get(factura_data['factura_id'])
            if factura and factura.responsable_id:
                if factura.responsable_id not in facturas_por_responsable:
                    facturas_por_responsable[factura.responsable_id] = {
                        'email': factura.usuario.email if factura.usuario else None,
                        'nombre': factura.usuario.nombre if factura.usuario else None,
                        'aprobadas': [],
                        'revision': []
                    }
                facturas_por_responsable[factura.responsable_id]['aprobadas'].append(factura_data)

        for factura_data in resultado_comparacion.get('requieren_revision', []):
            factura = self.db.query(Factura).get(factura_data['factura_id'])
            if factura and factura.responsable_id:
                if factura.responsable_id not in facturas_por_responsable:
                    facturas_por_responsable[factura.responsable_id] = {
                        'email': factura.usuario.email if factura.usuario else None,
                        'nombre': factura.usuario.nombre if factura.usuario else None,
                        'aprobadas': [],
                        'revision': []
                    }
                facturas_por_responsable[factura.responsable_id]['revision'].append(factura_data)

        return facturas_por_responsable

    def _preparar_mensaje_notificacion(self, datos: Dict[str, Any]) -> str:
        """Prepara el mensaje de notificación para el usuario."""
        mensaje = f"""
Hola {datos['nombre']},

Te informamos sobre el procesamiento automático de facturas:

  FACTURAS APROBADAS AUTOMÁTICAMENTE: {len(datos['aprobadas'])}
"""

        for factura in datos['aprobadas']:
            mensaje += f"  - {factura['numero_factura']} | {factura['proveedor']} | ${factura['monto_actual']:,.2f}\n"
            mensaje += f"    Motivo: {factura['motivo']}\n"

        mensaje += f"""
 FACTURAS QUE REQUIEREN REVISIÓN: {len(datos['revision'])}
"""

        for factura in datos['revision']:
            mensaje += f"  - {factura['numero_factura']} | {factura['proveedor']} | ${factura['monto_actual']:,.2f}\n"
            mensaje += f"    Motivo: {factura['motivo']}\n"

        mensaje += """
Por favor, revisa las facturas pendientes en el sistema.

Saludos,
Sistema de Automatización de Facturas AFE
"""

        return mensaje

    def _generar_resumen_final(self) -> Dict[str, Any]:
        """Genera resumen final del flujo."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'estadisticas': self.stats.copy(),
            'tasa_automatizacion': (
                (self.stats['facturas_aprobadas_auto'] /
                 self.stats['facturas_pendientes_analizadas'] * 100)
                if self.stats['facturas_pendientes_analizadas'] > 0 else 0
            )
        }
