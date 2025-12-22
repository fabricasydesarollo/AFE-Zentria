# app/services/automation/decision_engine.py
"""
Motor de decisiones para aprobación automática de facturas.

Este módulo toma las decisiones finales sobre si una factura debe ser:
- Aprobada automáticamente
- Enviada a revisión manual
- Rechazada automáticamente

Basándose en múltiples criterios y niveles de confianza.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from app.models.factura import Factura, EstadoFactura
from .pattern_detector import ResultadoAnalisisPatron


class TipoDecision(Enum):
    """Tipos de decisión que puede tomar el motor."""
    APROBACION_AUTOMATICA = "aprobada_auto"
    REVISION_MANUAL = "en_revision"
    RECHAZO_AUTOMATICO = "rechazada"


@dataclass
class CriterioValidacion:
    """Representa un criterio individual de validación."""
    nombre: str
    cumplido: bool
    peso: float  # 0.0 - 1.0
    descripcion: str
    valor_obtenido: Any = None
    valor_requerido: Any = None


@dataclass
class ResultadoDecision:
    """Resultado final de la decisión del motor."""
    decision: TipoDecision
    confianza: float  # 0.0 - 1.0
    motivo: str
    criterios: List[CriterioValidacion]
    requiere_accion_manual: bool
    factura_referencia_id: Optional[int] = None
    metadata: Dict[str, Any] = None


class DecisionEngine:
    """
    Motor de decisiones para automatización de facturas.
    """
    
    def __init__(self):
        # Configuración de umbrales y pesos
        self.config = {
            # Umbrales de confianza
            'confianza_aprobacion_automatica': 0.85,
            'confianza_revision_manual': 0.40,
            
            # Pesos de criterios (deben sumar 1.0)
            'peso_patron_recurrencia': 0.35,
            'peso_proveedor_confiable': 0.20,
            'peso_monto_razonable': 0.15,
            'peso_fecha_esperada': 0.15,
            'peso_orden_compra': 0.10,
            'peso_historial_aprobaciones': 0.05,
            
            # Umbrales específicos
            'max_dias_diferencia_esperada': 7,
            'max_variacion_monto_porcentaje': 20.0,
            'min_facturas_historial_proveedor': 3,
            'max_monto_aprobacion_automatica': Decimal('50000000'),  # 50M COP
            
            # Lista de proveedores de confianza (NITs)
            'proveedores_confianza_alta': set(),
            'proveedores_bloqueados': set(),
        }
    
    def tomar_decision(
        self,
        factura: Factura,
        resultado_patron: ResultadoAnalisisPatron,
        facturas_historicas: List[Factura],
        metadata_adicional: Optional[Dict[str, Any]] = None,
        comparacion_mes_anterior: Optional[Dict[str, Any]] = None
    ) -> ResultadoDecision:
        """
        Toma la decisión final sobre una factura basándose en múltiples criterios.
        
        Args:
            factura: Factura a evaluar
            resultado_patron: Resultado del análisis de patrones
            facturas_historicas: Historial de facturas del proveedor
            metadata_adicional: Información adicional para la decisión
            
        Returns:
            Resultado de la decisión con explicación detallada
        """
        # 🔑 PRIORIDAD MÁXIMA: Si hay comparación con mes anterior, usarla primero
        if comparacion_mes_anterior and comparacion_mes_anterior.get('tiene_mes_anterior'):
            # Si el monto coincide con el mes anterior, aprobar automáticamente
            if comparacion_mes_anterior.get('decision_sugerida') == 'aprobar_auto':
                return ResultadoDecision(
                    decision=TipoDecision.APROBACION_AUTOMATICA,
                    confianza=comparacion_mes_anterior.get('confianza', 0.95),
                    motivo=comparacion_mes_anterior.get('razon'),
                    criterios=[
                        CriterioValidacion(
                            nombre="comparacion_mes_anterior",
                            cumplido=True,
                            peso=1.0,
                            descripcion="Monto coincide con factura del mes anterior",
                            valor_obtenido=comparacion_mes_anterior.get('diferencia_porcentaje'),
                            valor_requerido=5.0
                        )
                    ],
                    requiere_accion_manual=False,
                    factura_referencia_id=comparacion_mes_anterior.get('factura_anterior_id'),
                    metadata={
                        'metodo_aprobacion': 'comparacion_mes_anterior',
                        'comparacion_detalle': comparacion_mes_anterior
                    }
                )

        # Evaluar todos los criterios (lógica original para casos sin mes anterior)
        criterios = self._evaluar_criterios(
            factura, resultado_patron, facturas_historicas,
            metadata_adicional or {}, comparacion_mes_anterior
        )

        # Calcular puntuación ponderada
        puntuacion_total = self._calcular_puntuacion_ponderada(criterios)

        # Tomar decisión basada en puntuación y criterios críticos
        decision, motivo, requiere_accion = self._determinar_decision_final(
            puntuacion_total, criterios, resultado_patron
        )
        
        # Preparar metadata de la decisión
        metadata_decision = self._preparar_metadata_decision(
            factura, resultado_patron, criterios, puntuacion_total, metadata_adicional or {}
        )
        
        return ResultadoDecision(
            decision=decision,
            confianza=puntuacion_total,
            motivo=motivo,
            criterios=criterios,
            requiere_accion_manual=requiere_accion,
            factura_referencia_id=self._obtener_factura_referencia_id(resultado_patron),
            metadata=metadata_decision
        )

    def _evaluar_criterios(
        self,
        factura: Factura,
        resultado_patron: ResultadoAnalisisPatron,
        facturas_historicas: List[Factura],
        metadata: Dict[str, Any],
        comparacion_mes_anterior: Optional[Dict[str, Any]] = None
    ) -> List[CriterioValidacion]:
        """
        Evalúa todos los criterios de validación.
        """
        criterios = []
        
        # 1. Criterio: Patrón de recurrencia detectado
        criterios.append(self._evaluar_patron_recurrencia(resultado_patron))
        
        # 2. Criterio: Proveedor confiable
        criterios.append(self._evaluar_proveedor_confiable(factura, facturas_historicas))
        
        # 3. Criterio: Monto razonable
        criterios.append(self._evaluar_monto_razonable(factura, resultado_patron))
        
        # 4. Criterio: Fecha esperada
        criterios.append(self._evaluar_fecha_esperada(factura, resultado_patron, facturas_historicas))
        
        # 5. Criterio: Orden de compra válida
        criterios.append(self._evaluar_orden_compra(factura, facturas_historicas))
        
        # 6. Criterio: Historial de aprobaciones
        criterios.append(self._evaluar_historial_aprobaciones(facturas_historicas))
        
        return criterios

    def _evaluar_patron_recurrencia(self, resultado_patron: ResultadoAnalisisPatron) -> CriterioValidacion:
        """Evalúa si se detectó un patrón de recurrencia confiable."""
        confianza_minima = 0.7
        
        return CriterioValidacion(
            nombre="patron_recurrencia",
            cumplido=resultado_patron.es_recurrente and resultado_patron.confianza_global >= confianza_minima,
            peso=self.config['peso_patron_recurrencia'],
            descripcion=f"Patrón de recurrencia detectado con confianza >= {confianza_minima:.1%}",
            valor_obtenido=resultado_patron.confianza_global,
            valor_requerido=confianza_minima
        )

    def _evaluar_proveedor_confiable(self, factura: Factura, facturas_historicas: List[Factura]) -> CriterioValidacion:
        """Evalúa si el proveedor es confiable."""
        nit_proveedor = factura.proveedor.nit if factura.proveedor else ""
        
        # Verificar si está en lista de confianza alta
        en_lista_confianza = nit_proveedor in self.config['proveedores_confianza_alta']
        
        # Verificar si está bloqueado
        bloqueado = nit_proveedor in self.config['proveedores_bloqueados']
        
        # Evaluar historial (suficientes facturas históricas)
        historial_suficiente = len(facturas_historicas) >= self.config['min_facturas_historial_proveedor']
        
        # Calcular tasa de aprobación histórica
        facturas_aprobadas = sum(1 for f in facturas_historicas 
                               if f.estado in [EstadoFactura.aprobada, EstadoFactura.aprobada_auto])
        tasa_aprobacion = facturas_aprobadas / len(facturas_historicas) if facturas_historicas else 0
        
        # Proveedor es confiable si:
        # - No está bloqueado Y
        # - (Está en lista de confianza O tiene historial suficiente con buena tasa de aprobación)
        es_confiable = (
            not bloqueado and 
            (en_lista_confianza or (historial_suficiente and tasa_aprobacion >= 0.8))
        )
        
        descripcion = "Proveedor con historial confiable"
        if bloqueado:
            descripcion = "Proveedor bloqueado"
        elif en_lista_confianza:
            descripcion = "Proveedor en lista de alta confianza"
        
        return CriterioValidacion(
            nombre="proveedor_confiable",
            cumplido=es_confiable,
            peso=self.config['peso_proveedor_confiable'],
            descripcion=descripcion,
            valor_obtenido=tasa_aprobacion,
            valor_requerido=0.8
        )

    def _evaluar_monto_razonable(self, factura: Factura, resultado_patron: ResultadoAnalisisPatron) -> CriterioValidacion:
        """Evalúa si el monto de la factura está dentro de rangos razonables."""
        monto_factura = factura.total_a_pagar or Decimal('0')
        
        # Verificar límite máximo
        dentro_limite_maximo = monto_factura <= self.config['max_monto_aprobacion_automatica']
        
        # Verificar variación con respecto al patrón histórico
        variacion_aceptable = True
        if resultado_patron.patron_monto.montos_historicos:
            monto_promedio = resultado_patron.patron_monto.monto_promedio
            if monto_promedio > 0:
                variacion_porcentual = abs(float(monto_factura - monto_promedio)) / float(monto_promedio) * 100
                variacion_aceptable = variacion_porcentual <= self.config['max_variacion_monto_porcentaje']
        
        monto_razonable = dentro_limite_maximo and variacion_aceptable
        
        return CriterioValidacion(
            nombre="monto_razonable",
            cumplido=monto_razonable,
            peso=self.config['peso_monto_razonable'],
            descripcion=f"Monto dentro de límites (≤{self.config['max_monto_aprobacion_automatica']:,} COP) y variación aceptable",
            valor_obtenido=monto_factura,
            valor_requerido=self.config['max_monto_aprobacion_automatica']
        )

    def _evaluar_fecha_esperada(self, factura: Factura, resultado_patron: ResultadoAnalisisPatron, facturas_historicas: List[Factura]) -> CriterioValidacion:
        """Evalúa si la fecha de la factura está cerca de la fecha esperada."""
        if not resultado_patron.patron_temporal.consistente:
            return CriterioValidacion(
                nombre="fecha_esperada",
                cumplido=False,
                peso=self.config['peso_fecha_esperada'],
                descripcion="No hay patrón temporal consistente para evaluar",
                valor_obtenido=None,
                valor_requerido=None
            )
        
        # Calcular fecha esperada basada en patrón temporal
        # NOTA: facturas_referencia contiene IDs, no objetos Factura
        # Por lo tanto, usamos facturas_historicas directamente
        if not resultado_patron.facturas_referencia or not facturas_historicas:
            fecha_esperada_cumple = False
            dias_diferencia = 999
        else:
            # Filtrar facturas históricas con fecha válida
            fechas_historicas = [f.fecha_emision for f in facturas_historicas if f.fecha_emision]

            if not fechas_historicas:
                fecha_esperada_cumple = False
                dias_diferencia = 999
            else:
                # Usar la última fecha histórica como referencia
                ultima_fecha_historica = max(fechas_historicas)
                dias_patron = resultado_patron.patron_temporal.promedio_dias
                fecha_esperada = ultima_fecha_historica + timedelta(days=int(dias_patron))

                dias_diferencia = abs((factura.fecha_emision - fecha_esperada).days)
                fecha_esperada_cumple = dias_diferencia <= self.config['max_dias_diferencia_esperada']
        
        return CriterioValidacion(
            nombre="fecha_esperada",
            cumplido=fecha_esperada_cumple,
            peso=self.config['peso_fecha_esperada'],
            descripcion=f"Fecha dentro del rango esperado (±{self.config['max_dias_diferencia_esperada']} días)",
            valor_obtenido=dias_diferencia,
            valor_requerido=self.config['max_dias_diferencia_esperada']
        )

    def _evaluar_orden_compra(self, factura: Factura, facturas_historicas: List[Factura]) -> CriterioValidacion:
        """Evalúa la validez de la orden de compra."""
        tiene_oc = bool(factura.orden_compra_numero)
        
        if not tiene_oc:
            # Si no hay OC, evaluar si es consistente con el patrón histórico
            facturas_con_oc = [f for f in facturas_historicas if f.orden_compra_numero]
            patron_oc = len(facturas_con_oc) / len(facturas_historicas) if facturas_historicas else 0
            
            # Si menos del 50% de facturas históricas tienen OC, es aceptable no tenerla
            cumple = patron_oc < 0.5
            descripcion = "No requiere OC según patrón histórico" if cumple else "Falta orden de compra"
        else:
            # Verificar que no sea duplicada
            oc_duplicada = any(f.orden_compra_numero == factura.orden_compra_numero 
                             for f in facturas_historicas)
            cumple = not oc_duplicada
            descripcion = "Orden de compra única" if cumple else "Orden de compra duplicada"
        
        return CriterioValidacion(
            nombre="orden_compra",
            cumplido=cumple,
            peso=self.config['peso_orden_compra'],
            descripcion=descripcion,
            valor_obtenido=factura.orden_compra_numero,
            valor_requerido="única y válida"
        )

    def _evaluar_historial_aprobaciones(self, facturas_historicas: List[Factura]) -> CriterioValidacion:
        """Evalúa el historial de aprobaciones del concepto/proveedor."""
        if not facturas_historicas:
            return CriterioValidacion(
                nombre="historial_aprobaciones",
                cumplido=False,
                peso=self.config['peso_historial_aprobaciones'],
                descripcion="Sin historial previo",
                valor_obtenido=0,
                valor_requerido=3
            )
        
        facturas_aprobadas = sum(1 for f in facturas_historicas 
                               if f.estado in [EstadoFactura.aprobada, EstadoFactura.aprobada_auto])
        tasa_aprobacion = facturas_aprobadas / len(facturas_historicas)
        
        # Criterio: Al menos 80% de tasa de aprobación y mínimo 3 facturas
        cumple = (
            len(facturas_historicas) >= 3 and 
            tasa_aprobacion >= 0.8
        )
        
        return CriterioValidacion(
            nombre="historial_aprobaciones",
            cumplido=cumple,
            peso=self.config['peso_historial_aprobaciones'],
            descripcion=f"Historial positivo (≥80% aprobaciones, ≥3 facturas)",
            valor_obtenido=tasa_aprobacion,
            valor_requerido=0.8
        )

    def _calcular_puntuacion_ponderada(self, criterios: List[CriterioValidacion]) -> float:
        """Calcula la puntuación total ponderada de los criterios."""
        puntuacion = 0.0
        peso_total = 0.0
        
        for criterio in criterios:
            if criterio.cumplido:
                puntuacion += criterio.peso
            peso_total += criterio.peso
        
        # Normalizar a escala 0-1
        return puntuacion / peso_total if peso_total > 0 else 0.0

    def _determinar_decision_final(
        self, 
        puntuacion: float, 
        criterios: List[CriterioValidacion],
        resultado_patron: ResultadoAnalisisPatron
    ) -> tuple[TipoDecision, str, bool]:
        """Determina la decisión final basándose en puntuación y criterios críticos."""
        
        # Verificar criterios bloqueantes
        criterios_bloqueantes = self._verificar_criterios_bloqueantes(criterios)
        if criterios_bloqueantes:
            return (
                TipoDecision.REVISION_MANUAL,
                f"Criterios bloqueantes: {', '.join(criterios_bloqueantes)}",
                True
            )
        
        # Decisión basada en puntuación
        if puntuacion >= self.config['confianza_aprobacion_automatica']:
            return (
                TipoDecision.APROBACION_AUTOMATICA,
                f"Alta confianza ({puntuacion:.1%}) - patrón recurrente confiable",
                False
            )
        elif puntuacion >= self.config['confianza_revision_manual']:
            return (
                TipoDecision.REVISION_MANUAL,
                f"Confianza moderada ({puntuacion:.1%}) - requiere revisión manual",
                True
            )
        else:
            return (
                TipoDecision.REVISION_MANUAL,
                f"Baja confianza ({puntuacion:.1%}) - múltiples criterios no cumplidos",
                True
            )

    def _verificar_criterios_bloqueantes(self, criterios: List[CriterioValidacion]) -> List[str]:
        """Identifica criterios que bloquean la aprobación automática."""
        bloqueantes = []
        
        for criterio in criterios:
            if not criterio.cumplido:
                # Criterios que siempre bloquean aprobación automática
                if criterio.nombre in ['proveedor_confiable'] and criterio.descripcion == "Proveedor bloqueado":
                    bloqueantes.append("proveedor_bloqueado")
                elif criterio.nombre == 'monto_razonable' and criterio.valor_obtenido > self.config['max_monto_aprobacion_automatica']:
                    bloqueantes.append("monto_excesivo")
        
        return bloqueantes

    def _obtener_factura_referencia_id(self, resultado_patron: ResultadoAnalisisPatron) -> Optional[int]:
        """Obtiene el ID de la factura de referencia más relevante."""
        if resultado_patron.facturas_referencia:
            return resultado_patron.facturas_referencia[0]  # La más reciente
        return None

    def _preparar_metadata_decision(
        self, 
        factura: Factura, 
        resultado_patron: ResultadoAnalisisPatron,
        criterios: List[CriterioValidacion],
        puntuacion: float,
        metadata_adicional: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepara la metadata completa de la decisión."""
        return {
            'version_algoritmo': '1.0',
            'timestamp_decision': datetime.utcnow().isoformat(),
            'puntuacion_total': float(puntuacion),
            'criterios_evaluados': len(criterios),
            'criterios_cumplidos': sum(1 for c in criterios if c.cumplido),
            'patron_temporal_tipo': resultado_patron.patron_temporal.tipo,
            'patron_temporal_confianza': float(resultado_patron.patron_temporal.confianza),
            'patron_monto_estable': resultado_patron.patron_monto.estable,
            'facturas_referencia_count': len(resultado_patron.facturas_referencia),
            'configuracion_umbrales': self._serializar_config_para_json(),
            **self._serializar_metadata_adicional(metadata_adicional)
        }

    def _serializar_config_para_json(self) -> Dict[str, Any]:
        """Convierte la configuración a formato JSON serializable."""
        config_serializable = {}
        for key, value in self.config.items():
            if isinstance(value, Decimal):
                config_serializable[key] = float(value)
            elif isinstance(value, set):
                config_serializable[key] = list(value)
            else:
                config_serializable[key] = value
        return config_serializable

    def _serializar_metadata_adicional(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte metadata adicional a formato JSON serializable."""
        metadata_serializable = {}
        for key, value in metadata.items():
            if isinstance(value, Decimal):
                metadata_serializable[key] = float(value)
            elif isinstance(value, set):
                metadata_serializable[key] = list(value)
            elif hasattr(value, 'isoformat'):  # datetime objects
                metadata_serializable[key] = value.isoformat()
            else:
                metadata_serializable[key] = value
        return metadata_serializable

    def actualizar_configuracion(self, nueva_config: Dict[str, Any]) -> None:
        """Actualiza la configuración del motor de decisiones."""
        self.config.update(nueva_config)

    def agregar_proveedor_confiable(self, nit: str) -> None:
        """Agrega un proveedor a la lista de confianza alta."""
        self.config['proveedores_confianza_alta'].add(nit)

    def bloquear_proveedor(self, nit: str) -> None:
        """Bloquea un proveedor de aprobaciones automáticas."""
        self.config['proveedores_bloqueados'].add(nit)