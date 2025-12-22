# app/services/automation/pattern_detector.py
"""
Detector de patrones de recurrencia en facturas.

Este módulo analiza facturas históricas para detectar patrones temporales
y de contenido que indiquen recurrencia, permitiendo predecir si una
nueva factura sigue un patrón establecido.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import statistics
from dataclasses import dataclass

from app.models.factura import Factura
from .fingerprint_generator import FingerprintGenerator


@dataclass
class PatronTemporal:
    """Representa un patrón temporal detectado."""
    tipo: str  # 'mensual', 'quincenal', 'semanal', 'irregular'
    promedio_dias: float
    desviacion_estandar: float
    consistente: bool
    confianza: float  # 0.0 - 1.0


@dataclass
class PatronMonto:
    """Representa un patrón de montos detectado."""
    monto_promedio: Decimal
    variacion_porcentaje: float
    montos_historicos: List[Decimal]
    estable: bool
    confianza: float


@dataclass
class ResultadoAnalisisPatron:
    """Resultado del análisis de patrones de una factura."""
    patron_temporal: PatronTemporal
    patron_monto: PatronMonto
    facturas_referencia: List[int]
    es_recurrente: bool
    confianza_global: float
    razon_decision: str


class PatternDetector:
    """
    Detector de patrones de recurrencia en facturas.
    """
    
    def __init__(self):
        self.fingerprint_gen = FingerprintGenerator()
        
        # Umbrales para clasificación de patrones
        self.umbrales = {
            'dias_mensual_min': 26,
            'dias_mensual_max': 35,
            'dias_quincenal_min': 13,
            'dias_quincenal_max': 17,
            'dias_semanal_min': 6,
            'dias_semanal_max': 9,
            'desviacion_max_consistente': 3.0,
            'variacion_monto_max_estable': 15.0,  # Porcentaje
            'min_facturas_patron': 2,
            'confianza_minima_recurrencia': 0.7
        }

    def analizar_patron_recurrencia(
        self, 
        factura_nueva: Factura, 
        facturas_historicas: List[Factura]
    ) -> ResultadoAnalisisPatron:
        """
        Analiza si una nueva factura sigue un patrón de recurrencia.
        
        Args:
            factura_nueva: Factura a analizar
            facturas_historicas: Historial de facturas del mismo proveedor/concepto
            
        Returns:
            Resultado del análisis de patrones
        """
        if len(facturas_historicas) < self.umbrales['min_facturas_patron']:
            return self._crear_resultado_sin_patron(
                "Insuficiente historial para detectar patrones"
            )
        
        # Analizar patrón temporal
        patron_temporal = self._analizar_patron_temporal(facturas_historicas, factura_nueva)
        
        # Analizar patrón de montos
        patron_monto = self._analizar_patron_montos(facturas_historicas, factura_nueva)
        
        # Calcular confianza global
        confianza_global = self._calcular_confianza_global(patron_temporal, patron_monto)
        
        # Determinar si es recurrente
        es_recurrente = confianza_global >= self.umbrales['confianza_minima_recurrencia']
        
        # Generar razón de la decisión
        razon_decision = self._generar_razon_decision(
            patron_temporal, patron_monto, confianza_global, es_recurrente
        )
        
        return ResultadoAnalisisPatron(
            patron_temporal=patron_temporal,
            patron_monto=patron_monto,
            facturas_referencia=[f.id for f in facturas_historicas[:5]],
            es_recurrente=es_recurrente,
            confianza_global=confianza_global,
            razon_decision=razon_decision
        )

    def _analizar_patron_temporal(
        self, 
        facturas_historicas: List[Factura], 
        factura_nueva: Factura
    ) -> PatronTemporal:
        """
        Analiza el patrón temporal de las facturas históricas.
        """
        fechas = [f.fecha_emision for f in facturas_historicas] + [factura_nueva.fecha_emision]
        fechas.sort()
        
        if len(fechas) < 2:
            return PatronTemporal("insuficiente", 0.0, 0.0, False, 0.0)
        
        # Calcular diferencias entre fechas consecutivas
        diferencias_dias = []
        for i in range(1, len(fechas)):
            diff = (fechas[i] - fechas[i-1]).days
            diferencias_dias.append(diff)
        
        if not diferencias_dias:
            return PatronTemporal("insuficiente", 0.0, 0.0, False, 0.0)
        
        # Estadísticas básicas
        promedio_dias = statistics.mean(diferencias_dias)
        desviacion = statistics.stdev(diferencias_dias) if len(diferencias_dias) > 1 else 0.0
        
        # Clasificar tipo de patrón
        tipo_patron = self._clasificar_patron_temporal(promedio_dias)
        
        # Determinar si es consistente
        consistente = desviacion <= self.umbrales['desviacion_max_consistente']
        
        # Calcular confianza temporal
        confianza = self._calcular_confianza_temporal(
            promedio_dias, desviacion, len(diferencias_dias), consistente
        )
        
        return PatronTemporal(
            tipo=tipo_patron,
            promedio_dias=promedio_dias,
            desviacion_estandar=desviacion,
            consistente=consistente,
            confianza=confianza
        )

    def _clasificar_patron_temporal(self, promedio_dias: float) -> str:
        """
        Clasifica el tipo de patrón temporal basado en el promedio de días.
        """
        umbrales = self.umbrales
        
        if umbrales['dias_semanal_min'] <= promedio_dias <= umbrales['dias_semanal_max']:
            return 'semanal'
        elif umbrales['dias_quincenal_min'] <= promedio_dias <= umbrales['dias_quincenal_max']:
            return 'quincenal'
        elif umbrales['dias_mensual_min'] <= promedio_dias <= umbrales['dias_mensual_max']:
            return 'mensual'
        elif 60 <= promedio_dias <= 95:
            return 'bimestral'
        elif 85 <= promedio_dias <= 105:
            return 'trimestral'
        else:
            return 'irregular'

    def _calcular_confianza_temporal(
        self, 
        promedio_dias: float, 
        desviacion: float, 
        num_observaciones: int, 
        consistente: bool
    ) -> float:
        """
        Calcula la confianza del patrón temporal.
        """
        confianza_base = 0.5
        
        # Bonificación por consistencia
        if consistente:
            confianza_base += 0.3
        
        # Bonificación por número de observaciones
        bonificacion_observaciones = min(0.2, (num_observaciones - 2) * 0.05)
        confianza_base += bonificacion_observaciones
        
        # Penalización por desviación alta
        if desviacion > 5:
            penalizacion = min(0.3, (desviacion - 5) * 0.02)
            confianza_base -= penalizacion
        
        # Bonificación por patrones conocidos
        if promedio_dias in range(26, 36):  # Mensual
            confianza_base += 0.1
        elif promedio_dias in range(13, 18):  # Quincenal
            confianza_base += 0.1
        
        return max(0.0, min(1.0, confianza_base))

    def _analizar_patron_montos(
        self, 
        facturas_historicas: List[Factura], 
        factura_nueva: Factura
    ) -> PatronMonto:
        """
        Analiza el patrón de montos de las facturas.
        """
        montos = [f.total_a_pagar for f in facturas_historicas if f.total_a_pagar]
        
        if not montos:
            return PatronMonto(Decimal('0'), 100.0, [], False, 0.0)
        
        monto_nuevo = factura_nueva.total_a_pagar or Decimal('0')
        montos_todos = montos + [monto_nuevo]
        
        # Calcular estadísticas
        monto_promedio = sum(montos) / len(montos)
        
        # Calcular variación porcentual
        if monto_promedio > 0:
            variaciones = [
                abs(float(monto - monto_promedio)) / float(monto_promedio) * 100
                for monto in montos_todos
            ]
            variacion_maxima = max(variaciones) if variaciones else 0.0
        else:
            variacion_maxima = 100.0
        
        # Determinar estabilidad
        estable = variacion_maxima <= self.umbrales['variacion_monto_max_estable']
        
        # Calcular confianza de monto
        confianza = self._calcular_confianza_monto(variacion_maxima, len(montos), estable)
        
        return PatronMonto(
            monto_promedio=monto_promedio,
            variacion_porcentaje=variacion_maxima,
            montos_historicos=montos,
            estable=estable,
            confianza=confianza
        )

    def _calcular_confianza_monto(
        self, 
        variacion_maxima: float, 
        num_montos: int, 
        estable: bool
    ) -> float:
        """
        Calcula la confianza del patrón de montos.
        """
        confianza_base = 0.5
        
        # Bonificación por estabilidad
        if estable:
            confianza_base += 0.3
        
        # Bonificación inversamente proporcional a la variación
        if variacion_maxima <= 5:
            confianza_base += 0.2
        elif variacion_maxima <= 10:
            confianza_base += 0.1
        elif variacion_maxima > 25:
            confianza_base -= 0.2
        
        # Bonificación por número de observaciones
        bonificacion_observaciones = min(0.2, (num_montos - 1) * 0.05)
        confianza_base += bonificacion_observaciones
        
        return max(0.0, min(1.0, confianza_base))

    def _calcular_confianza_global(
        self, 
        patron_temporal: PatronTemporal, 
        patron_monto: PatronMonto
    ) -> float:
        """
        Calcula la confianza global combinando patrones temporal y de monto.
        """
        # Pesos para diferentes componentes
        peso_temporal = 0.6
        peso_monto = 0.4
        
        confianza_combinada = (
            patron_temporal.confianza * peso_temporal +
            patron_monto.confianza * peso_monto
        )
        
        # Bonificación si ambos patrones son consistentes
        if patron_temporal.consistente and patron_monto.estable:
            confianza_combinada += 0.1
        
        # Penalización si algún patrón es muy débil
        if patron_temporal.confianza < 0.3 or patron_monto.confianza < 0.3:
            confianza_combinada -= 0.15
        
        return max(0.0, min(1.0, confianza_combinada))

    def _generar_razon_decision(
        self, 
        patron_temporal: PatronTemporal, 
        patron_monto: PatronMonto, 
        confianza_global: float, 
        es_recurrente: bool
    ) -> str:
        """
        Genera una explicación textual de la decisión tomada.
        """
        if not es_recurrente:
            if confianza_global < 0.3:
                return f"Confianza muy baja ({confianza_global:.1%}) - patrón irregular"
            elif not patron_temporal.consistente:
                return f"Patrón temporal inconsistente - desviación: {patron_temporal.desviacion_estandar:.1f} días"
            elif not patron_monto.estable:
                return f"Montos variables - variación: {patron_monto.variacion_porcentaje:.1f}%"
            else:
                return f"Confianza insuficiente ({confianza_global:.1%}) para aprobación automática"
        
        # Es recurrente - explicar por qué
        razones = []
        
        if patron_temporal.consistente:
            razones.append(f"patrón {patron_temporal.tipo} consistente")
        
        if patron_monto.estable:
            razones.append(f"monto estable (±{patron_monto.variacion_porcentaje:.1f}%)")
        
        if confianza_global >= 0.9:
            nivel_confianza = "muy alta"
        elif confianza_global >= 0.8:
            nivel_confianza = "alta"
        else:
            nivel_confianza = "moderada"
        
        razon_base = f"Recurrencia detectada con confianza {nivel_confianza} ({confianza_global:.1%})"
        
        if razones:
            return f"{razon_base}: {', '.join(razones)}"
        else:
            return razon_base

    def _crear_resultado_sin_patron(self, razon: str) -> ResultadoAnalisisPatron:
        """
        Crea un resultado cuando no se puede detectar un patrón.
        """
        return ResultadoAnalisisPatron(
            patron_temporal=PatronTemporal("insuficiente", 0.0, 0.0, False, 0.0),
            patron_monto=PatronMonto(Decimal('0'), 0.0, [], False, 0.0),
            facturas_referencia=[],
            es_recurrente=False,
            confianza_global=0.0,
            razon_decision=razon
        )

    def predecir_proxima_fecha(self, facturas_historicas: List[Factura]) -> Optional[date]:
        """
        Predice cuándo debería llegar la próxima factura basándose en el patrón.
        """
        if len(facturas_historicas) < 2:
            return None

        patron_temporal = self._analizar_patron_temporal(facturas_historicas[:-1], facturas_historicas[-1])

        if not patron_temporal.consistente:
            return None

        # Filtrar facturas con fecha de emisión válida
        fechas_validas = [f.fecha_emision for f in facturas_historicas if f.fecha_emision]

        if not fechas_validas:
            return None

        ultima_fecha = max(fechas_validas)
        dias_a_sumar = int(patron_temporal.promedio_dias)

        return ultima_fecha + timedelta(days=dias_a_sumar)

    def calcular_probabilidad_recurrencia_mensual(self, facturas_historicas: List[Factura]) -> float:
        """
        Calcula la probabilidad de que las facturas sigan un patrón mensual.
        """
        if len(facturas_historicas) < 3:
            return 0.0
        
        patron_temporal = self._analizar_patron_temporal(facturas_historicas[:-1], facturas_historicas[-1])
        
        if patron_temporal.tipo == 'mensual' and patron_temporal.consistente:
            return patron_temporal.confianza
        else:
            return 0.0

    def comparar_con_mes_anterior(
        self,
        factura_nueva: Factura,
        factura_mes_anterior: Optional[Factura],
        tolerancia_porcentaje: float = 5.0
    ) -> Dict[str, Any]:
        """
        Compara una factura nueva con la del mes anterior para aprobación automática.

        Esta es la lógica clave para el sistema de aprobación automática:
        Si la factura del mes actual tiene el MISMO MONTO que la del mes anterior,
        se aprueba automáticamente. Si hay diferencia, pasa a revisión.

        Args:
            factura_nueva: Factura a evaluar
            factura_mes_anterior: Factura del mes anterior (puede ser None)
            tolerancia_porcentaje: % de tolerancia en variación (default: 5%)

        Returns:
            Dict con:
            - tiene_mes_anterior: bool
            - montos_coinciden: bool
            - diferencia_porcentaje: float
            - diferencia_absoluta: Decimal
            - decision_sugerida: 'aprobar_auto' | 'revision_manual'
            - razon: str
            - confianza: float
        """
        # Si no hay factura del mes anterior, requiere revisión manual
        if not factura_mes_anterior:
            return {
                'tiene_mes_anterior': False,
                'montos_coinciden': False,
                'diferencia_porcentaje': 100.0,
                'diferencia_absoluta': factura_nueva.total_a_pagar,
                'decision_sugerida': 'revision_manual',
                'razon': 'No existe factura del mes anterior para comparar',
                'confianza': 0.0,
                'monto_actual': float(factura_nueva.total_a_pagar or 0),
                'monto_anterior': 0.0
            }

        # Obtener montos
        monto_nuevo = factura_nueva.total_a_pagar or Decimal('0')
        monto_anterior = factura_mes_anterior.total_a_pagar or Decimal('0')

        # Validar que los montos sean válidos
        if monto_anterior == 0:
            return {
                'tiene_mes_anterior': True,
                'montos_coinciden': False,
                'diferencia_porcentaje': 100.0,
                'diferencia_absoluta': monto_nuevo,
                'decision_sugerida': 'revision_manual',
                'razon': 'Factura del mes anterior tiene monto 0 o inválido',
                'confianza': 0.0,
                'monto_actual': float(monto_nuevo),
                'monto_anterior': float(monto_anterior)
            }

        # Calcular diferencia
        diferencia_absoluta = abs(monto_nuevo - monto_anterior)
        diferencia_porcentaje = (float(diferencia_absoluta) / float(monto_anterior)) * 100

        # Determinar si los montos coinciden dentro de la tolerancia
        montos_coinciden = diferencia_porcentaje <= tolerancia_porcentaje

        # Calcular confianza basada en la similitud de montos
        if diferencia_porcentaje == 0:
            confianza = 1.0
        elif diferencia_porcentaje <= 1:
            confianza = 0.95
        elif diferencia_porcentaje <= 3:
            confianza = 0.85
        elif diferencia_porcentaje <= 5:
            confianza = 0.75
        elif diferencia_porcentaje <= 10:
            confianza = 0.60
        else:
            confianza = 0.40

        # Decisión y razón
        if montos_coinciden:
            decision = 'aprobar_auto'
            if diferencia_porcentaje == 0:
                razon = f'Monto idéntico al mes anterior (${monto_anterior:,.2f})'
            else:
                razon = (
                    f'Monto similar al mes anterior: ${monto_anterior:,.2f} → ${monto_nuevo:,.2f} '
                    f'({diferencia_porcentaje:.2f}% diferencia, dentro de tolerancia {tolerancia_porcentaje}%)'
                )
        else:
            decision = 'revision_manual'
            razon = (
                f'Monto difiere del mes anterior: ${monto_anterior:,.2f} → ${monto_nuevo:,.2f} '
                f'({diferencia_porcentaje:.2f}% diferencia, supera tolerancia {tolerancia_porcentaje}%)'
            )

        return {
            'tiene_mes_anterior': True,
            'montos_coinciden': montos_coinciden,
            'diferencia_porcentaje': diferencia_porcentaje,
            'diferencia_absoluta': diferencia_absoluta,
            'decision_sugerida': decision,
            'razon': razon,
            'confianza': confianza,
            'monto_actual': float(monto_nuevo),
            'monto_anterior': float(monto_anterior),
            'factura_anterior_id': factura_mes_anterior.id,
            'factura_anterior_numero': factura_mes_anterior.numero_factura,
            'factura_anterior_fecha': factura_mes_anterior.fecha_emision.isoformat() if factura_mes_anterior.fecha_emision else None
        }