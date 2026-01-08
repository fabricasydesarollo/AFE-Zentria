# app/services/automation/automation_service.py
"""Servicio principal de automatización de facturas recurrentes."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.factura import Factura, EstadoFactura
from app.models.patrones_facturas import PatronesFacturas, TipoPatron
from app.crud import factura as crud_factura
from app.crud import audit as crud_audit


from .fingerprint_generator import FingerprintGenerator
from .pattern_detector import PatternDetector, ResultadoAnalisisPatron
from .decision_engine import DecisionEngine, ResultadoDecision, TipoDecision


# Configurar logging
logger = logging.getLogger(__name__)


class AutomationService:
    """Servicio principal de automatización de facturas recurrentes."""

    def __init__(self):
        self.fingerprint_gen = FingerprintGenerator()
        self.pattern_detector = PatternDetector()
        self.decision_engine = DecisionEngine()
        
        # Estadísticas del procesamiento
        self.stats = {
            'facturas_procesadas': 0,
            'aprobadas_automaticamente': 0,
            'enviadas_revision': 0,
            'errores': 0,
            'tiempo_inicio': None,
            'tiempo_fin': None
        }

    def procesar_facturas_pendientes(
        self,
        db: Session,
        limite_facturas: int = 50,
        modo_debug: bool = False
    ) -> Dict[str, Any]:
        """Procesa todas las facturas pendientes de automatización."""
        self.stats['tiempo_inicio'] = datetime.utcnow()
        
        try:
            # Obtener facturas pendientes de procesamiento
            facturas_pendientes = crud_factura.get_facturas_pendientes_procesamiento(
                db, limit=limite_facturas
            )
            
            logger.info(f"Iniciando procesamiento de {len(facturas_pendientes)} facturas pendientes")
            
            resultados = []
            
            for factura in facturas_pendientes:
                try:
                    resultado = self.procesar_factura_individual(db, factura, modo_debug)
                    resultados.append(resultado)
                    self.stats['facturas_procesadas'] += 1
                    
                    # Actualizar estadísticas
                    if resultado['decision'] == TipoDecision.APROBACION_AUTOMATICA.value:
                        self.stats['aprobadas_automaticamente'] += 1
                    else:
                        self.stats['enviadas_revision'] += 1
                        
                except Exception as e:
                    logger.error(f"Error procesando factura {factura.id}: {str(e)}")
                    self.stats['errores'] += 1
                    
                    # Registrar error en auditoría
                    self._registrar_error_auditoria(db, factura, str(e))
            
            self.stats['tiempo_fin'] = datetime.utcnow()
            
            return self._generar_resumen_procesamiento(resultados, modo_debug)
            
        except Exception as e:
            logger.error(f"Error general en procesamiento de facturas: {str(e)}")
            self.stats['errores'] += 1
            raise

    def procesar_factura_individual(
        self,
        db: Session,
        factura: Factura,
        modo_debug: bool = False
    ) -> Dict[str, Any]:
        """Procesa una factura individual para determinar si debe ser aprobada automáticamente."""
        logger.info(f"Procesando factura {factura.numero_factura} (ID: {factura.id})")
        
        try:
            # 1. Verificar que la factura tenga los datos necesarios
            if not self._validar_datos_minimos(factura):
                return self._crear_resultado_error(
                    factura, "Datos insuficientes para procesamiento automático"
                )
            
            # 2. Enriquecer datos de la factura si es necesario
            self._enriquecer_datos_factura(db, factura)
            
            # 3. Buscar facturas históricas similares
            facturas_historicas = self._buscar_facturas_historicas(db, factura)

            # 3.5. 🔑 NUEVA LÓGICA: Comparar con mes anterior (prioridad máxima)
            factura_mes_anterior = facturas_historicas[0] if facturas_historicas else None
            comparacion_mes_anterior = self.pattern_detector.comparar_con_mes_anterior(
                factura_nueva=factura,
                factura_mes_anterior=factura_mes_anterior,
                tolerancia_porcentaje=5.0  # 5% de tolerancia configurable
            )

            # 4. Analizar patrones de recurrencia (análisis adicional)
            resultado_patron = self.pattern_detector.analizar_patron_recurrencia(
                factura, facturas_historicas
            )

            # 5. Tomar decisión final (incorporando comparación mes anterior)
            resultado_decision = self.decision_engine.tomar_decision(
                factura, resultado_patron, facturas_historicas,
                comparacion_mes_anterior=comparacion_mes_anterior
            )
            
            # 6. Aplicar la decisión a la base de datos
            self._aplicar_decision(db, factura, resultado_decision, resultado_patron)
            
            # 7. Registrar en auditoría
            self._registrar_auditoria(db, factura, resultado_decision, resultado_patron)
            
            return self._crear_resultado_exitoso(
                factura, resultado_decision, resultado_patron, modo_debug
            )
            
        except Exception as e:
            logger.error(f"Error procesando factura {factura.id}: {str(e)}")
            return self._crear_resultado_error(factura, str(e))

    def _validar_datos_minimos(self, factura: Factura) -> bool:
        """Valida que la factura tenga los datos mínimos necesarios."""
        return all([
            factura.numero_factura,
            factura.fecha_emision,
            factura.total_a_pagar,
            factura.proveedor_id,
            factura.cufe
        ])

    def _enriquecer_datos_factura(self, db: Session, factura: Factura) -> None:
        """Enriquece los datos de la factura si faltan campos de automatización."""
        actualizar = False
        campos_actualizacion = {}
        
        # Generar concepto hash si falta
        if not factura.concepto_hash and factura.concepto_normalizado:
            fingerprints = self.fingerprint_gen.generar_fingerprint_desde_factura(factura)
            campos_actualizacion['concepto_hash'] = fingerprints['principal'][:32]
            actualizar = True
        
        # Clasificar tipo de factura si falta
        if not factura.tipo_factura:
            tipo = self._clasificar_tipo_factura_basico(factura)
            campos_actualizacion['tipo_factura'] = tipo
            actualizar = True
        
        if actualizar:
            crud_factura.update_factura(db, factura, campos_actualizacion)

    def _clasificar_tipo_factura_basico(self, factura: Factura) -> str:
        """Clasificación básica del tipo de factura."""
        if factura.items_resumen:
            return "productos_con_detalle"
        elif factura.orden_compra_numero:
            return "orden_compra_referenciada"
        else:
            return "factura_estandar"

    def _buscar_facturas_historicas(self, db: Session, factura: Factura) -> List[Factura]:
        """Busca facturas históricas similares para análisis de patrones."""
        facturas_historicas = []

        # PRIORIDAD 1: Buscar factura del mes anterior (lógica principal de aprobación)
        factura_mes_anterior = crud_factura.find_factura_mes_anterior(
            db=db,
            proveedor_id=factura.proveedor_id,
            fecha_actual=factura.fecha_emision,
            concepto_hash=factura.concepto_hash,
            concepto_normalizado=factura.concepto_normalizado,
            numero_factura=factura.numero_factura
        )

        # Si encontramos factura del mes anterior, agregarla primero (máxima prioridad)
        if factura_mes_anterior:
            facturas_historicas.append(factura_mes_anterior)

        # Buscar por concepto normalizado si existe
        if factura.concepto_normalizado:
            facturas_por_concepto = crud_factura.find_facturas_by_concepto_proveedor(
                db, factura.proveedor_id, factura.concepto_normalizado, limit=12
            )
            facturas_historicas.extend(facturas_por_concepto)

        # Buscar por hash de concepto si existe
        if factura.concepto_hash:
            facturas_por_hash = crud_factura.find_facturas_by_concepto_hash(
                db, factura.concepto_hash, factura.proveedor_id, limit=8
            )
            # Evitar duplicados
            ids_existentes = {f.id for f in facturas_historicas}
            facturas_historicas.extend([
                f for f in facturas_por_hash if f.id not in ids_existentes
            ])

        # Buscar por orden de compra si existe
        if factura.orden_compra_numero:
            facturas_por_oc = crud_factura.find_facturas_by_orden_compra(
                db, factura.orden_compra_numero, factura.proveedor_id
            )
            ids_existentes = {f.id for f in facturas_historicas}
            facturas_historicas.extend([
                f for f in facturas_por_oc if f.id not in ids_existentes
            ])

        # Filtrar facturas futuras y la misma factura
        facturas_filtradas = [
            f for f in facturas_historicas
            if f.fecha_emision < factura.fecha_emision and f.id != factura.id
        ]

        # Ordenar por fecha descendente y limitar
        facturas_filtradas.sort(key=lambda x: x.fecha_emision, reverse=True)
        return facturas_filtradas[:10]  # Máximo 10 facturas históricas

    def _aplicar_decision(
        self,
        db: Session,
        factura: Factura,
        resultado_decision: ResultadoDecision,
        resultado_patron: ResultadoAnalisisPatron
    ) -> None:
        """Aplica la decisión tomada actualizando la factura en la base de datos."""
        campos_actualizacion = {
            'patron_recurrencia': resultado_patron.patron_temporal.tipo,
            'confianza_automatica': resultado_decision.confianza,
            'factura_referencia_id': resultado_decision.factura_referencia_id,
            'motivo_decision': resultado_decision.motivo,
            'procesamiento_info': resultado_decision.metadata,
            'fecha_procesamiento_auto': datetime.utcnow(),
            'version_algoritmo': '1.0'
        }
        
        # Actualizar estado si la decisión lo requiere
        if resultado_decision.decision == TipoDecision.APROBACION_AUTOMATICA:
            campos_actualizacion['estado'] = EstadoFactura.aprobada_auto.value
            campos_actualizacion['aprobada_automaticamente'] = True
        elif resultado_decision.decision == TipoDecision.REVISION_MANUAL:
            campos_actualizacion['estado'] = EstadoFactura.en_revision.value
        
        crud_factura.update_factura(db, factura, campos_actualizacion)

    def _registrar_auditoria(
        self,
        db: Session,
        factura: Factura,
        resultado_decision: ResultadoDecision,
        resultado_patron: ResultadoAnalisisPatron
    ) -> None:
        """Registra la decisión en el log de auditoría."""
        accion = "aprobacion_automatica" if resultado_decision.decision == TipoDecision.APROBACION_AUTOMATICA else "revision_requerida"
        
        detalles_auditoria = {
            'decision': resultado_decision.decision.value,
            'confianza': float(resultado_decision.confianza),
            'motivo': resultado_decision.motivo,
            'patron_detectado': {
                'tipo_temporal': resultado_patron.patron_temporal.tipo,
                'confianza_patron': float(resultado_patron.confianza_global),
                'es_recurrente': resultado_patron.es_recurrente
            },
            'criterios_evaluados': [
                {
                    'nombre': c.nombre,
                    'cumplido': c.cumplido,
                    'peso': c.peso,
                    'descripcion': c.descripcion
                }
                for c in resultado_decision.criterios
            ]
        }
        
        crud_audit.create_audit(
            db=db,
            entidad="factura",
            entidad_id=factura.id,
            accion=accion,
            usuario="sistema_automatico",
            detalle=detalles_auditoria
        )

    def _registrar_error_auditoria(self, db: Session, factura: Factura, error: str) -> None:
        """Registra errores de procesamiento en auditoría."""
        crud_audit.create_audit(
            db=db,
            entidad="factura",
            entidad_id=factura.id,
            accion="error_procesamiento_automatico",
            usuario="sistema_automatico",
            detalle={'error': error, 'timestamp': datetime.utcnow().isoformat()}
        )

    def _crear_resultado_exitoso(
        self,
        factura: Factura,
        resultado_decision: ResultadoDecision,
        resultado_patron: ResultadoAnalisisPatron,
        modo_debug: bool
    ) -> Dict[str, Any]:
        """Crea el resultado de un procesamiento exitoso."""
        # Determinar estado final
        if resultado_decision.decision == TipoDecision.APROBACION_AUTOMATICA:
            estado_final = EstadoFactura.aprobada_auto.value
            automatizada = True
        else:
            estado_final = EstadoFactura.en_revision.value
            automatizada = False
        
        resultado = {
            'factura_id': factura.id,
            'numero_factura': factura.numero_factura,
            'decision': resultado_decision.decision.value,
            'automatizada': automatizada,  #   Campo agregado
            'confianza': float(resultado_decision.confianza),
            'razon': resultado_decision.motivo,
            'motivo': resultado_decision.motivo,
            'estado_anterior': factura.estado,
            'estado_nuevo': estado_final,
            'estado': estado_final,  #   Campo agregado
            'es_recurrente': resultado_patron.es_recurrente,
            'patron_temporal': resultado_patron.patron_temporal.tipo,
            'requiere_accion_manual': resultado_decision.requiere_accion_manual,
            'fingerprint_generado': bool(factura.concepto_hash),  #   Campo agregado
            'patrones_detectados': len(resultado_patron.facturas_referencia) > 0,  #   Campo agregado
            'procesado_exitosamente': True
        }
        
        if modo_debug:
            resultado['debug_info'] = {
                'criterios_detallados': [
                    {
                        'nombre': c.nombre,
                        'cumplido': c.cumplido,
                        'peso': c.peso,
                        'descripcion': c.descripcion,
                        'valor_obtenido': c.valor_obtenido,
                        'valor_requerido': c.valor_requerido
                    }
                    for c in resultado_decision.criterios
                ],
                'patron_detallado': {
                    'temporal': {
                        'tipo': resultado_patron.patron_temporal.tipo,
                        'promedio_dias': resultado_patron.patron_temporal.promedio_dias,
                        'consistente': resultado_patron.patron_temporal.consistente,
                        'confianza': resultado_patron.patron_temporal.confianza
                    },
                    'monto': {
                        'estable': resultado_patron.patron_monto.estable,
                        'variacion_pct': float(resultado_patron.patron_monto.variacion_porcentaje),
                        'confianza': resultado_patron.patron_monto.confianza
                    }
                },
                'facturas_referencia': resultado_patron.facturas_referencia,
                'metadata': resultado_decision.metadata
            }
        
        return resultado

    def _crear_resultado_error(self, factura: Factura, error: str) -> Dict[str, Any]:
        """Crea el resultado de un procesamiento con error."""
        return {
            'factura_id': factura.id,
            'numero_factura': factura.numero_factura,
            'procesado_exitosamente': False,
            'automatizada': False,  #   Campo agregado
            'confianza': 0.0,  #   Campo agregado
            'razon': f"Error: {error}",  #   Campo agregado
            'estado': factura.estado,  #   Campo agregado
            'error': error,
            'decision': 'error',
            'requiere_accion_manual': True,
            'fingerprint_generado': False,  #   Campo agregado
            'patrones_detectados': False   #   Campo agregado
        }

    def _generar_resumen_procesamiento(
        self,
        resultados: List[Dict[str, Any]],
        modo_debug: bool
    ) -> Dict[str, Any]:
        """Genera el resumen final del procesamiento."""
        tiempo_total = None
        if self.stats['tiempo_inicio'] and self.stats['tiempo_fin']:
            tiempo_total = (self.stats['tiempo_fin'] - self.stats['tiempo_inicio']).total_seconds()
        
        resumen = {
            'facturas_procesadas': self.stats['facturas_procesadas'],  #   Campo de nivel superior
            'aprobadas_automaticamente': self.stats['aprobadas_automaticamente'],  #   Campo de nivel superior
            'enviadas_revision': self.stats['enviadas_revision'],  #   Campo de nivel superior
            'errores': self.stats['errores'],  #   Campo de nivel superior
            'tiempo_inicio': self.stats['tiempo_inicio'],  #   Campo de nivel superior
            'tiempo_fin': self.stats['tiempo_fin'],  #   Campo de nivel superior
            'resumen_general': {
                'facturas_procesadas': self.stats['facturas_procesadas'],
                'aprobadas_automaticamente': self.stats['aprobadas_automaticamente'],
                'enviadas_revision': self.stats['enviadas_revision'],
                'errores': self.stats['errores'],
                'tiempo_procesamiento_segundos': tiempo_total,
                'tasa_automatizacion': (
                    self.stats['aprobadas_automaticamente'] / max(self.stats['facturas_procesadas'], 1) * 100
                )
            },
            'facturas_procesadas_detalle': resultados
        }
        
        if modo_debug:
            resumen['estadisticas_detalladas'] = self._generar_estadisticas_detalladas(resultados)
        
        return resumen

    def _generar_estadisticas_detalladas(self, resultados: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Genera estadísticas detalladas del procesamiento."""
        patrones_detectados = {}
        criterios_fallidos = {}
        
        for resultado in resultados:
            if resultado.get('procesado_exitosamente'):
                # Contar patrones temporales
                patron = resultado.get('patron_temporal', 'unknown')
                patrones_detectados[patron] = patrones_detectados.get(patron, 0) + 1
                
                # Analizar criterios fallidos (si hay debug info)
                if 'debug_info' in resultado:
                    for criterio in resultado['debug_info']['criterios_detallados']:
                        if not criterio['cumplido']:
                            nombre = criterio['nombre']
                            criterios_fallidos[nombre] = criterios_fallidos.get(nombre, 0) + 1
        
        return {
            'patrones_temporales_detectados': patrones_detectados,
            'criterios_mas_fallidos': dict(sorted(criterios_fallidos.items(), key=lambda x: x[1], reverse=True)[:5]),
            'confianza_promedio': sum(r.get('confianza', 0) for r in resultados if r.get('procesado_exitosamente')) / max(len([r for r in resultados if r.get('procesado_exitosamente')]), 1)
        }

    def obtener_configuracion_actual(self) -> Dict[str, Any]:
        """Obtiene la configuración actual del servicio."""
        return {
            'fingerprint_generator': 'active',
            'pattern_detector': self.pattern_detector.umbrales,
            'decision_engine': self.decision_engine.config,
            'version': '1.0'
        }

    def actualizar_configuracion(self, nueva_config: Dict[str, Any]) -> None:
        """Actualiza la configuración del servicio."""
        if 'decision_engine' in nueva_config:
            self.decision_engine.actualizar_configuracion(nueva_config['decision_engine'])
        
        if 'pattern_detector' in nueva_config:
            self.pattern_detector.umbrales.update(nueva_config['pattern_detector'])

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene las estadísticas actuales del servicio."""
        return self.stats.copy()