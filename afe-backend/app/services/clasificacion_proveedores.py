"""
Servicio de clasificación automática de proveedores.

Clasifica y reclasifica proveedores basándose en patrones
de facturación y antigüedad.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean, stdev

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.factura import Factura, EstadoFactura
from app.models.proveedor import Proveedor
from app.models.workflow_aprobacion import (
    AsignacionNitResponsable,
    TipoServicioProveedor,
    NivelConfianzaProveedor
)


class ClasificacionProveedoresService:
    """Servicio de clasificación automática de proveedores."""

    def __init__(self, db: Session):
        self.db = db

        # Umbrales de clasificación (configurables desde BD en futuro)
        self.CONFIG = {
            'cv_fijo': 15.0,
            'cv_variable': 80.0,
            'meses_minimos_historial': 3,
            'facturas_minimas': 3,
            'dias_critico': 730,     # 24 meses
            'dias_alto': 365,        # 12 meses
            'dias_medio': 180,       # 6 meses
            'dias_bajo': 90,         # 3 meses
            'monto_requiere_oc': 10_000_000  # $10M COP
        }

        # Umbrales de auto-aprobación por tipo de servicio
        self.UMBRALES_APROBACION = {
            TipoServicioProveedor.SERVICIO_FIJO_MENSUAL: {
                'umbral_base': 0.95,
                'tolerancia_variacion': 0.05,
                'requiere_orden_compra': False
            },
            TipoServicioProveedor.SERVICIO_VARIABLE_PREDECIBLE: {
                'umbral_base': 0.88,
                'tolerancia_variacion': 0.15,
                'requiere_orden_compra': False
            },
            TipoServicioProveedor.SERVICIO_POR_CONSUMO: {
                'umbral_base': 0.85,
                'tolerancia_variacion': 0.25,
                'requiere_orden_compra': True
            },
            TipoServicioProveedor.SERVICIO_EVENTUAL: {
                'umbral_base': 1.00,  # Nunca auto-aprobar
                'tolerancia_variacion': 0.0,
                'requiere_orden_compra': True
            }
        }

        # Ajustes de umbral por nivel de confianza del proveedor
        self.AJUSTES_NIVEL_CONFIANZA = {
            NivelConfianzaProveedor.NIVEL_1_CRITICO: -0.07,  # Más estricto (ej: 95% → 88%)
            NivelConfianzaProveedor.NIVEL_2_ALTO: -0.03,     # Poco más estricto (ej: 95% → 92%)
            NivelConfianzaProveedor.NIVEL_3_MEDIO: 0.00,     # Sin cambio (ej: 95% → 95%)
            NivelConfianzaProveedor.NIVEL_4_BAJO: +0.05,     # Más permisivo (ej: 88% → 93%)
            NivelConfianzaProveedor.NIVEL_5_NUEVO: +0.15,    # Súper permisivo = 100% (nunca auto-aprobar)
        }

    def clasificar_proveedor_automatico(
        self,
        nit: str,
        forzar_reclasificacion: bool = False
    ) -> Dict[str, Any]:
        """Clasifica un proveedor automáticamente basándose en historial de facturas."""
        # Obtener o crear asignación
        asignacion = self.db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.nit == nit
        ).first()

        if not asignacion:
            return {
                'clasificado': False,
                'razon': 'NIT sin asignación. Crear AsignacionNitResponsable primero.'
            }

        # Si ya está clasificado y no es forzado, retornar clasificación actual
        if not forzar_reclasificacion and asignacion.tipo_servicio_proveedor:
            return {
                'clasificado': True,
                'ya_clasificado': True,
                'tipo_servicio': asignacion.tipo_servicio_proveedor,
                'nivel_confianza': asignacion.nivel_confianza_proveedor,
                'cv': float(asignacion.coeficiente_variacion_historico or 0)
            }

        # Obtener proveedor
        proveedor = self.db.query(Proveedor).filter(
            Proveedor.nit == nit
        ).first()

        if not proveedor:
            # Proveedor nuevo sin facturas → Clasificación por defecto
            return self._clasificar_proveedor_sin_historial(asignacion)

        # Analizar facturas históricas
        facturas = self._obtener_facturas_para_analisis(proveedor.id)

        if len(facturas) < self.CONFIG['facturas_minimas']:
            # Proveedor con pocas facturas → Clasificación conservadora
            return self._clasificar_proveedor_sin_historial(asignacion)

        # Calcular estadísticas
        estadisticas = self._calcular_estadisticas(facturas)

        # Determinar clasificación
        tipo_servicio = self._determinar_tipo_servicio(estadisticas['cv'])
        nivel_confianza = self._determinar_nivel_confianza(
            estadisticas['antiguedad_dias'],
            tipo_servicio,
            estadisticas['cv']
        )
        requiere_oc = self._requiere_orden_compra(
            tipo_servicio,
            estadisticas['monto_promedio']
        )

        # Actualizar asignación
        asignacion.tipo_servicio_proveedor = tipo_servicio.value
        asignacion.nivel_confianza_proveedor = nivel_confianza.value
        asignacion.coeficiente_variacion_historico = Decimal(str(round(estadisticas['cv'], 2)))
        asignacion.fecha_inicio_relacion = estadisticas['fecha_primera_factura']
        asignacion.requiere_orden_compra_obligatoria = requiere_oc

        # Metadata de clasificación
        asignacion.metadata_riesgos = {
            'fecha_clasificacion': datetime.now().isoformat(),
            'facturas_analizadas': len(facturas),
            'cv_calculado': round(estadisticas['cv'], 2),
            'antiguedad_dias': estadisticas['antiguedad_dias'],
            'monto_promedio': float(estadisticas['monto_promedio']),
            'meses_con_facturas': estadisticas['meses_con_facturas'],
            'clasificacion_automatica': True,
            'version_algoritmo': '1.0'
        }

        self.db.commit()

        return {
            'clasificado': True,
            'ya_clasificado': False,
            'tipo_servicio': tipo_servicio,
            'nivel_confianza': nivel_confianza,
            'cv': estadisticas['cv'],
            'requiere_oc': requiere_oc,
            'facturas_analizadas': len(facturas)
        }

    def clasificar_nuevo_proveedor_on_the_fly(
        self,
        asignacion: AsignacionNitResponsable
    ) -> None:
        """
        Clasifica un proveedor completamente nuevo en tiempo real.

        Se llama cuando:
        1. Se crea una nueva AsignacionNitResponsable
        2. Llega primera factura de proveedor sin clasificación

        Asigna valores por defecto seguros:
        - Tipo: SERVICIO_EVENTUAL (más restrictivo)
        - Nivel: NIVEL_5_NUEVO (requiere 100% confianza = nunca auto-aprobar)
        - Requiere OC: True

        Args:
            asignacion: Asignación recién creada
        """
        asignacion.tipo_servicio_proveedor = TipoServicioProveedor.SERVICIO_EVENTUAL.value
        asignacion.nivel_confianza_proveedor = NivelConfianzaProveedor.NIVEL_5_NUEVO.value
        asignacion.coeficiente_variacion_historico = None
        asignacion.fecha_inicio_relacion = datetime.now().date()
        asignacion.requiere_orden_compra_obligatoria = True

        asignacion.metadata_riesgos = {
            'fecha_clasificacion': datetime.now().isoformat(),
            'clasificacion_inicial': True,
            'sin_historial': True,
            'razon': 'Proveedor nuevo sin facturas históricas',
            'nota': 'Se reclasificará automáticamente después de 3 meses con 3+ facturas'
        }

        self.db.commit()

    def reclasificar_todos_periodicamente(
        self,
        solo_cambios: bool = True
    ) -> Dict[str, Any]:
        """
        Reclasifica todos los proveedores (tarea mensual programada).

        Args:
            solo_cambios: Si True, solo actualiza si hubo cambio en clasificación

        Returns:
            Resumen de reclasificación
        """
        asignaciones = self.db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == True
        ).all()

        resultados = {
            'total_procesados': 0,
            'actualizados': 0,
            'sin_cambios': 0,
            'errores': 0,
            'cambios': []
        }

        for asignacion in asignaciones:
            try:
                # Guardar clasificación anterior
                tipo_anterior = asignacion.tipo_servicio_proveedor
                nivel_anterior = asignacion.nivel_confianza_proveedor

                # Reclasificar
                resultado = self.clasificar_proveedor_automatico(
                    asignacion.nit,
                    forzar_reclasificacion=True
                )

                if resultado['clasificado']:
                    resultados['total_procesados'] += 1

                    # Verificar si hubo cambio
                    if (resultado['tipo_servicio'] != tipo_anterior or
                        resultado['nivel_confianza'] != nivel_anterior):

                        resultados['actualizados'] += 1

                        # Manejar tanto enums como strings de BD
                        tipo_ant_val = tipo_anterior.value if hasattr(tipo_anterior, 'value') else tipo_anterior
                        nivel_ant_val = nivel_anterior.value if hasattr(nivel_anterior, 'value') else nivel_anterior

                        resultados['cambios'].append({
                            'nit': asignacion.nit,
                            'nombre': asignacion.proveedor.razon_social if asignacion.proveedor else None,
                            'tipo_anterior': tipo_ant_val,
                            'tipo_nuevo': resultado['tipo_servicio'].value,
                            'nivel_anterior': nivel_ant_val,
                            'nivel_nuevo': resultado['nivel_confianza'].value
                        })
                    else:
                        resultados['sin_cambios'] += 1

            except Exception as e:
                resultados['errores'] += 1
                print(f"Error reclasificando {asignacion.nit}: {e}")

        return resultados

    def detectar_cambios_patron_proveedor(
        self,
        nit: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta si un proveedor ha cambiado su patrón de facturación.

        Casos detectados:
        - CV aumentó significativamente (>20 puntos)
        - CV disminuyó significativamente (patrón se estabilizó)
        - Frecuencia de facturación cambió
        - Monto promedio cambió >30%

        Returns:
            Dict con alerta si hay cambio, None si todo normal
        """
        asignacion = self.db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.nit == nit
        ).first()

        if not asignacion or not asignacion.coeficiente_variacion_historico:
            return None

        # Recalcular estadísticas actuales
        proveedor = self.db.query(Proveedor).filter(
            Proveedor.nit == nit
        ).first()

        if not proveedor:
            return None

        facturas_recientes = self._obtener_facturas_para_analisis(
            proveedor.id,
            dias=90  # Últimos 3 meses
        )

        if len(facturas_recientes) < 3:
            return None

        estadisticas_recientes = self._calcular_estadisticas(facturas_recientes)
        cv_actual = float(asignacion.coeficiente_variacion_historico)
        cv_reciente = estadisticas_recientes['cv']

        diferencia_cv = abs(cv_reciente - cv_actual)

        if diferencia_cv > 20:
            return {
                'alerta': True,
                'tipo': 'cambio_patron_cv',
                'cv_historico': cv_actual,
                'cv_reciente': cv_reciente,
                'diferencia': diferencia_cv,
                'mensaje': f'CV cambió de {cv_actual:.1f}% a {cv_reciente:.1f}%',
                'requiere_reclasificacion': True
            }

        return None

    def obtener_umbral_aprobacion(
        self,
        tipo_servicio: Optional[str],
        nivel_confianza: Optional[str]
    ) -> float:
        """
        Calcula el umbral de confianza requerido para auto-aprobación.

        Combina:
        1. Umbral base del tipo de servicio
        2. Ajuste por nivel de confianza del proveedor

        Args:
            tipo_servicio: Tipo de servicio del proveedor (puede ser string de BD)
            nivel_confianza: Nivel de confianza del proveedor (puede ser string de BD)

        Returns:
            Umbral de confianza requerido (0.0-1.0, convertir a % multiplicando por 100)

        Ejemplos:
            - Servicio Fijo + Nivel 3 Medio = 0.95 + 0.00 = 0.95 (95%)
            - Variable Predecible + Nivel 4 Bajo = 0.88 + 0.05 = 0.93 (93%)
            - Por Consumo + Nivel 3 Medio = 0.85 + 0.00 = 0.85 (85%)
            - Eventual + cualquier nivel = 1.00 (100%, nunca auto-aprobar)
            - Nivel 5 Nuevo + cualquier tipo = 1.00 (100%, nunca auto-aprobar)
        """
        # Valores por defecto seguros
        if not tipo_servicio or not nivel_confianza:
            return 1.00  # Si no hay clasificación, requerir 100% = nunca auto-aprobar

        # Convertir strings de BD a enums si es necesario
        try:
            if isinstance(tipo_servicio, str):
                tipo_servicio = TipoServicioProveedor(tipo_servicio)
            if isinstance(nivel_confianza, str):
                nivel_confianza = NivelConfianzaProveedor(nivel_confianza)
        except ValueError:
            return 1.00  # Si valor inválido, requerir 100%

        # Proveedores nuevos NUNCA se auto-aprueban
        if nivel_confianza == NivelConfianzaProveedor.NIVEL_5_NUEVO:
            return 1.00

        # Servicios eventuales NUNCA se auto-aprueban
        if tipo_servicio == TipoServicioProveedor.SERVICIO_EVENTUAL:
            return 1.00

        # Obtener umbral base del tipo de servicio
        config_tipo = self.UMBRALES_APROBACION.get(tipo_servicio)
        if not config_tipo:
            return 1.00  # Tipo desconocido, requerir 100%

        umbral_base = config_tipo['umbral_base']

        # Aplicar ajuste por nivel de confianza
        ajuste = self.AJUSTES_NIVEL_CONFIANZA.get(nivel_confianza, 0.0)
        umbral_final = umbral_base + ajuste

        # Asegurar que umbral está en rango válido [0.0, 1.0]
        umbral_final = max(0.0, min(1.0, umbral_final))

        return umbral_final

    # ========================================================================
    # MÉTODOS PRIVADOS (Lógica interna)
    # ========================================================================

    def _clasificar_proveedor_sin_historial(
        self,
        asignacion: AsignacionNitResponsable
    ) -> Dict[str, Any]:
        """Clasifica proveedor sin historial suficiente."""
        self.clasificar_nuevo_proveedor_on_the_fly(asignacion)

        return {
            'clasificado': True,
            'tipo_servicio': TipoServicioProveedor.SERVICIO_EVENTUAL,
            'nivel_confianza': NivelConfianzaProveedor.NIVEL_5_NUEVO,
            'cv': None,
            'requiere_oc': True,
            'razon': 'Sin historial suficiente'
        }

    def _obtener_facturas_para_analisis(
        self,
        proveedor_id: int,
        dias: int = 365
    ) -> list:
        """Obtiene facturas para análisis estadístico."""
        fecha_limite = datetime.now() - timedelta(days=dias)

        return self.db.query(Factura).filter(
            Factura.proveedor_id == proveedor_id,
            Factura.fecha_emision >= fecha_limite,
            Factura.estado.in_([
                EstadoFactura.aprobada,
                EstadoFactura.aprobada_auto,
                EstadoFactura.validada_contabilidad,  # Facturas validadas (último estado del flujo)
                EstadoFactura.en_revision  # Incluir para cálculo estadístico de CV
            ])
        ).all()

    def _calcular_estadisticas(self, facturas: list) -> Dict[str, Any]:
        """Calcula estadísticas de facturas."""
        montos = [float(f.total_a_pagar) for f in facturas if f.total_a_pagar]

        if not montos:
            return {
                'cv': 999.0,
                'monto_promedio': 0,
                'antiguedad_dias': 0,
                'meses_con_facturas': 0,
                'fecha_primera_factura': None
            }

        monto_promedio = mean(montos)
        desviacion = stdev(montos) if len(montos) > 1 else 0
        cv = (desviacion / monto_promedio * 100) if monto_promedio > 0 else 0

        from datetime import date as date_type

        fechas = [f.fecha_emision for f in facturas if f.fecha_emision]
        fecha_primera = min(fechas) if fechas else datetime.now()

        # Convertir date a datetime si es necesario (date no tiene hora, datetime sí)
        if isinstance(fecha_primera, date_type) and not isinstance(fecha_primera, datetime):
            fecha_primera = datetime.combine(fecha_primera, datetime.min.time())

        antiguedad_dias = (datetime.now() - fecha_primera).days

        meses_unicos = set()
        for f in facturas:
            if f.fecha_emision:
                meses_unicos.add(f"{f.fecha_emision.year}-{f.fecha_emision.month:02d}")

        # Convertir fecha_primera a date para retorno
        if isinstance(fecha_primera, datetime):
            fecha_primera_date = fecha_primera.date()
        else:
            fecha_primera_date = fecha_primera

        return {
            'cv': cv,
            'monto_promedio': monto_promedio,
            'antiguedad_dias': antiguedad_dias,
            'meses_con_facturas': len(meses_unicos),
            'fecha_primera_factura': fecha_primera_date
        }

    def _determinar_tipo_servicio(self, cv: float) -> TipoServicioProveedor:
        """Determina tipo de servicio según CV."""
        if cv < self.CONFIG['cv_fijo']:
            return TipoServicioProveedor.SERVICIO_FIJO_MENSUAL
        elif cv < self.CONFIG['cv_variable']:
            return TipoServicioProveedor.SERVICIO_VARIABLE_PREDECIBLE
        else:
            return TipoServicioProveedor.SERVICIO_POR_CONSUMO

    def _determinar_nivel_confianza(
        self,
        antiguedad_dias: int,
        tipo_servicio: TipoServicioProveedor,
        cv: float
    ) -> NivelConfianzaProveedor:
        """Determina nivel de confianza según antigüedad y tipo."""
        if antiguedad_dias < self.CONFIG['dias_bajo']:
            return NivelConfianzaProveedor.NIVEL_5_NUEVO
        elif antiguedad_dias < self.CONFIG['dias_medio']:
            return NivelConfianzaProveedor.NIVEL_4_BAJO
        elif antiguedad_dias < self.CONFIG['dias_alto']:
            return NivelConfianzaProveedor.NIVEL_3_MEDIO
        elif antiguedad_dias < self.CONFIG['dias_critico']:
            if tipo_servicio == TipoServicioProveedor.SERVICIO_FIJO_MENSUAL and cv < 10:
                return NivelConfianzaProveedor.NIVEL_2_ALTO
            return NivelConfianzaProveedor.NIVEL_3_MEDIO
        else:
            if tipo_servicio == TipoServicioProveedor.SERVICIO_FIJO_MENSUAL and cv < 5:
                return NivelConfianzaProveedor.NIVEL_1_CRITICO
            return NivelConfianzaProveedor.NIVEL_2_ALTO

    def _requiere_orden_compra(
        self,
        tipo_servicio: TipoServicioProveedor,
        monto_promedio: float
    ) -> bool:
        """Determina si requiere orden de compra obligatoria."""
        if tipo_servicio in [
            TipoServicioProveedor.SERVICIO_EVENTUAL,
            TipoServicioProveedor.SERVICIO_POR_CONSUMO
        ]:
            return True

        if monto_promedio > self.CONFIG['monto_requiere_oc']:
            return True

        return False
