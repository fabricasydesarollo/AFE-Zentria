# app/services/analisis_patrones.py
"""
Servicio de análisis de patrones históricos de pago.
Implementa la lógica de clasificación según el PDF del proyecto:
- Tipo A: Valores fijos predecibles (CV < 5%)
- Tipo B: Valores fluctuantes predecibles (CV < 30%)
- Tipo C: Valores excepcionales (CV > 30% o sin historial)
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from decimal import Decimal
import statistics
import hashlib

from app.models.factura import Factura
from app.models.patrones_facturas import PatronesFacturas, TipoPatron
from app.models.proveedor import Proveedor


class AnalizadorPatrones:
    """Analiza patrones históricos de pago para clasificación inteligente"""

    # Umbrales de clasificación según el PDF
    UMBRAL_TIPO_A = 5.0  # CV < 5% = Fijo
    UMBRAL_TIPO_B = 30.0  # CV < 30% = Fluctuante predecible
    MESES_MINIMOS_ANALISIS = 3  # Mínimo de meses para tener patrón confiable
    MESES_ANALISIS = 12  # Analizar últimos 12 meses

    def __init__(self, db: Session):
        self.db = db

    def normalizar_concepto(self, concepto: str) -> str:
        """
        Normaliza un concepto para matching consistente.
        Elimina variaciones menores manteniendo la esencia del servicio.
        """
        if not concepto:
            return ""

        # Convertir a mayúsculas y eliminar espacios extras
        normalizado = concepto.upper().strip()

        # Eliminar palabras comunes que varían
        palabras_ignorar = ["DEL", "DE", "LA", "EL", "LOS", "LAS", "PARA",
                           "MES", "PERIODO", "CORRESPONDIENTE", "A"]

        palabras = normalizado.split()
        palabras_filtradas = [p for p in palabras if p not in palabras_ignorar]

        return " ".join(palabras_filtradas)

    def calcular_hash_concepto(self, concepto_normalizado: str) -> str:
        """Calcula hash MD5 del concepto para búsqueda rápida"""
        return hashlib.md5(concepto_normalizado.encode()).hexdigest()

    def obtener_facturas_historicas(
        self,
        proveedor_id: int,
        concepto_hash: str,
        meses_atras: int = 12,
        excluir_factura_id: Optional[int] = None
    ) -> List[Factura]:
        """
        Obtiene facturas históricas del mismo proveedor y concepto.

        Args:
            proveedor_id: ID del proveedor
            concepto_hash: Hash del concepto normalizado
            meses_atras: Cantidad de meses hacia atrás a analizar
            excluir_factura_id: ID de factura a excluir (la actual)
        """
        fecha_limite = datetime.now() - timedelta(days=meses_atras * 30)

        query = self.db.query(Factura).filter(
            and_(
                Factura.proveedor_id == proveedor_id,
                Factura.concepto_hash == concepto_hash,
                Factura.fecha_emision >= fecha_limite,
                Factura.estado.in_(["aprobada", "aprobada_auto"])  # Solo facturas aprobadas
            )
        )

        if excluir_factura_id:
            query = query.filter(Factura.id != excluir_factura_id)

        return query.order_by(Factura.fecha_emision.desc()).all()

    def calcular_estadisticas(self, montos: List[Decimal]) -> Dict:
        """
        Calcula estadísticas descriptivas de los montos.

        Returns:
            Dict con promedio, min, max, desviación, CV, rangos
        """
        if not montos:
            return {
                "promedio": Decimal(0),
                "minimo": Decimal(0),
                "maximo": Decimal(0),
                "desviacion": Decimal(0),
                "cv": Decimal(0),
                "rango_inferior": Decimal(0),
                "rango_superior": Decimal(0),
            }

        # Convertir a float para cálculos estadísticos
        montos_float = [float(m) for m in montos]

        promedio = statistics.mean(montos_float)
        minimo = min(montos_float)
        maximo = max(montos_float)

        # Desviación estándar (solo si hay más de 1 valor)
        if len(montos_float) > 1:
            desviacion = statistics.stdev(montos_float)
        else:
            desviacion = 0

        # Coeficiente de variación: (desv / promedio) * 100
        cv = (desviacion / promedio * 100) if promedio > 0 else 0

        # Rango esperado: promedio ± 2 * desviación (95% confianza)
        rango_inferior = max(0, promedio - 2 * desviacion)
        rango_superior = promedio + 2 * desviacion

        return {
            "promedio": Decimal(str(round(promedio, 2))),
            "minimo": Decimal(str(round(minimo, 2))),
            "maximo": Decimal(str(round(maximo, 2))),
            "desviacion": Decimal(str(round(desviacion, 2))),
            "cv": Decimal(str(round(cv, 2))),
            "rango_inferior": Decimal(str(round(rango_inferior, 2))),
            "rango_superior": Decimal(str(round(rango_superior, 2))),
        }

    def clasificar_patron(
        self,
        cv: Decimal,
        cantidad_pagos: int,
        meses_con_pagos: int
    ) -> TipoPatron:
        """
        Clasifica el patrón según coeficiente de variación y cantidad de datos.

        Args:
            cv: Coeficiente de variación
            cantidad_pagos: Total de pagos analizados
            meses_con_pagos: Cantidad de meses diferentes con pagos

        Returns:
            TipoPatron (TIPO_A, TIPO_B, o TIPO_C)
        """
        # Si no hay suficiente historial, es Tipo C (excepcional)
        if cantidad_pagos < 2 or meses_con_pagos < self.MESES_MINIMOS_ANALISIS:
            return TipoPatron.TIPO_C

        # Clasificación según CV
        if cv < self.UMBRAL_TIPO_A:
            return TipoPatron.TIPO_A  # Fijo
        elif cv < self.UMBRAL_TIPO_B:
            return TipoPatron.TIPO_B  # Fluctuante predecible
        else:
            return TipoPatron.TIPO_C  # Excepcional

    def analizar_proveedor_concepto(
        self,
        proveedor_id: int,
        concepto_normalizado: str,
        guardar: bool = True
    ) -> Optional[PatronesFacturas]:
        """
        Analiza el historial de facturas para un proveedor y concepto específico.

        Args:
            proveedor_id: ID del proveedor
            concepto_normalizado: Concepto normalizado
            guardar: Si True, guarda o actualiza el registro en BD

        Returns:
            PatronesFacturas con el análisis completo
        """
        concepto_hash = self.calcular_hash_concepto(concepto_normalizado)

        # Obtener facturas históricas
        facturas = self.obtener_facturas_historicas(
            proveedor_id,
            concepto_hash,
            meses_atras=self.MESES_ANALISIS
        )

        if not facturas:
            # Sin historial = Tipo C
            if not guardar:
                return None

            historial = PatronesFacturas(
                proveedor_id=proveedor_id,
                concepto_normalizado=concepto_normalizado,
                concepto_hash=concepto_hash,
                tipo_patron=TipoPatron.TIPO_C,
                pagos_analizados=0,
                meses_con_pagos=0,
                monto_promedio=Decimal(0),
                monto_minimo=Decimal(0),
                monto_maximo=Decimal(0),
                desviacion_estandar=Decimal(0),
                coeficiente_variacion=Decimal(999.99),
                puede_aprobar_auto=0,
                pagos_detalle=[],
            )
            self.db.add(historial)
            self.db.commit()
            return historial

        # Extraer montos y preparar datos
        montos = [f.total for f in facturas if f.total]

        # Contar meses únicos
        periodos_unicos = set(f.periodo_factura for f in facturas if f.periodo_factura)
        meses_con_pagos = len(periodos_unicos)

        # Calcular estadísticas
        stats = self.calcular_estadisticas(montos)

        # Clasificar patrón
        tipo = self.clasificar_patron(
            stats["cv"],
            len(montos),
            meses_con_pagos
        )

        # Determinar si puede aprobar automáticamente
        # Tipo A siempre puede, Tipo B con baja variación puede
        puede_aprobar = 1 if tipo in [TipoPatron.TIPO_A, TipoPatron.TIPO_B] else 0

        # Preparar detalle de pagos (últimos 12)
        pagos_detalle = [
            {
                "periodo": f.periodo_factura,
                "monto": float(f.total),
                "factura_id": f.id,
                "fecha": f.fecha_emision.isoformat() if f.fecha_emision else None,
            }
            for f in facturas[:12]
        ]

        # Último pago
        ultimo = facturas[0] if facturas else None

        # Buscar si ya existe un análisis previo
        historial_existente = self.db.query(PatronesFacturas).filter(
            and_(
                PatronesFacturas.proveedor_id == proveedor_id,
                PatronesFacturas.concepto_hash == concepto_hash
            )
        ).first()

        if historial_existente:
            # Actualizar existente
            historial_existente.tipo_patron = tipo
            historial_existente.pagos_analizados = len(montos)
            historial_existente.meses_con_pagos = meses_con_pagos
            historial_existente.monto_promedio = stats["promedio"]
            historial_existente.monto_minimo = stats["minimo"]
            historial_existente.monto_maximo = stats["maximo"]
            historial_existente.desviacion_estandar = stats["desviacion"]
            historial_existente.coeficiente_variacion = stats["cv"]
            historial_existente.rango_inferior = stats["rango_inferior"]
            historial_existente.rango_superior = stats["rango_superior"]
            historial_existente.puede_aprobar_auto = puede_aprobar
            historial_existente.pagos_detalle = pagos_detalle
            historial_existente.ultimo_pago_fecha = ultimo.fecha_emision if ultimo else None
            historial_existente.ultimo_pago_monto = ultimo.total if ultimo else None
            historial_existente.fecha_analisis = datetime.now()
            historial = historial_existente
        else:
            # Crear nuevo
            historial = PatronesFacturas(
                proveedor_id=proveedor_id,
                concepto_normalizado=concepto_normalizado,
                concepto_hash=concepto_hash,
                tipo_patron=tipo,
                pagos_analizados=len(montos),
                meses_con_pagos=meses_con_pagos,
                monto_promedio=stats["promedio"],
                monto_minimo=stats["minimo"],
                monto_maximo=stats["maximo"],
                desviacion_estandar=stats["desviacion"],
                coeficiente_variacion=stats["cv"],
                rango_inferior=stats["rango_inferior"],
                rango_superior=stats["rango_superior"],
                puede_aprobar_auto=puede_aprobar,
                pagos_detalle=pagos_detalle,
                ultimo_pago_fecha=ultimo.fecha_emision if ultimo else None,
                ultimo_pago_monto=ultimo.total if ultimo else None,
            )
            self.db.add(historial)

        if guardar:
            self.db.commit()
            self.db.refresh(historial)

        return historial

    def evaluar_factura_nueva(
        self,
        factura: Factura
    ) -> Tuple[Optional[PatronesFacturas], Dict]:
        """
        Evalúa una factura nueva comparándola con el historial.

        Args:
            factura: Factura a evaluar

        Returns:
            Tuple (PatronesFacturas, Dict con recomendación)
        """
        if not factura.concepto_normalizado or not factura.proveedor_id:
            return None, {
                "tipo_patron": "TIPO_C",
                "recomendacion": "REQUIERE_ANALISIS",
                "motivo": "Factura sin concepto normalizado o proveedor",
                "confianza": 0.0,
                "contexto": {}
            }

        # Obtener o generar análisis histórico
        historial = self.analizar_proveedor_concepto(
            factura.proveedor_id,
            factura.concepto_normalizado,
            guardar=True
        )

        if not historial or historial.pagos_analizados == 0:
            return historial, {
                "tipo_patron": "TIPO_C",
                "recomendacion": "REQUIERE_ANALISIS",
                "motivo": "Sin historial de pagos previos",
                "confianza": 0.0,
                "contexto": {}
            }

        # Evaluar según tipo de patrón
        monto_factura = factura.total

        if historial.tipo_patron == TipoPatron.TIPO_A:
            # Tipo A: Debe ser muy similar al promedio
            diferencia_pct = abs(float(monto_factura - historial.monto_promedio) / float(historial.monto_promedio) * 100)

            if diferencia_pct < 5:
                return historial, {
                    "tipo_patron": "TIPO_A",
                    "recomendacion": "LISTA_PARA_APROBAR",
                    "motivo": f"Factura fija recurrente. Diferencia: {diferencia_pct:.2f}%",
                    "confianza": 0.95,
                    "contexto": {
                        "monto_esperado": float(historial.monto_promedio),
                        "monto_actual": float(monto_factura),
                        "diferencia_porcentaje": round(diferencia_pct, 2),
                        "pagos_historicos": historial.pagos_analizados,
                    }
                }
            else:
                return historial, {
                    "tipo_patron": "TIPO_A",
                    "recomendacion": "REQUIERE_ANALISIS",
                    "motivo": f"Monto atípico para factura fija. Diferencia: {diferencia_pct:.2f}%",
                    "confianza": 0.3,
                    "contexto": {
                        "monto_esperado": float(historial.monto_promedio),
                        "monto_actual": float(monto_factura),
                        "diferencia_porcentaje": round(diferencia_pct, 2),
                        "pagos_historicos": historial.pagos_analizados,
                    }
                }

        elif historial.tipo_patron == TipoPatron.TIPO_B:
            # Tipo B: Debe estar dentro del rango esperado
            dentro_rango = historial.rango_inferior <= monto_factura <= historial.rango_superior

            if dentro_rango:
                return historial, {
                    "tipo_patron": "TIPO_B",
                    "recomendacion": "LISTA_PARA_APROBAR",
                    "motivo": "Factura dentro del rango histórico esperado",
                    "confianza": 0.85,
                    "contexto": {
                        "rango_inferior": float(historial.rango_inferior),
                        "rango_superior": float(historial.rango_superior),
                        "monto_actual": float(monto_factura),
                        "monto_promedio": float(historial.monto_promedio),
                        "pagos_historicos": historial.pagos_analizados,
                    }
                }
            else:
                return historial, {
                    "tipo_patron": "TIPO_B",
                    "recomendacion": "REQUIERE_ANALISIS",
                    "motivo": "Monto fuera del rango histórico esperado",
                    "confianza": 0.4,
                    "contexto": {
                        "rango_inferior": float(historial.rango_inferior),
                        "rango_superior": float(historial.rango_superior),
                        "monto_actual": float(monto_factura),
                        "monto_promedio": float(historial.monto_promedio),
                        "pagos_historicos": historial.pagos_analizados,
                    }
                }

        else:  # TIPO_C
            return historial, {
                "tipo_patron": "TIPO_C",
                "recomendacion": "REQUIERE_ANALISIS",
                "motivo": "Factura excepcional o sin patrón predecible",
                "confianza": 0.1,
                "contexto": {
                    "cv": float(historial.coeficiente_variacion),
                    "monto_actual": float(monto_factura),
                    "pagos_historicos": historial.pagos_analizados,
                }
            }

    def regenerar_todos_patrones(self, limit: Optional[int] = None):
        """
        Regenera todos los patrones históricos analizando proveedores y conceptos únicos.
        Útil para inicialización o recalibración del sistema.
        """
        # Obtener todas las combinaciones únicas de proveedor + concepto
        query = self.db.query(
            Factura.proveedor_id,
            Factura.concepto_normalizado
        ).filter(
            and_(
                Factura.proveedor_id.isnot(None),
                Factura.concepto_normalizado.isnot(None),
                Factura.estado.in_(["aprobada", "aprobada_auto"])
            )
        ).distinct()

        if limit:
            query = query.limit(limit)

        combinaciones = query.all()

        print(f"Regenerando patrones para {len(combinaciones)} combinaciones proveedor-concepto...")

        for i, (proveedor_id, concepto) in enumerate(combinaciones, 1):
            try:
                self.analizar_proveedor_concepto(
                    proveedor_id,
                    concepto,
                    guardar=True
                )
                if i % 10 == 0:
                    print(f"Procesados {i}/{len(combinaciones)}...")
            except Exception as e:
                print(f"Error procesando proveedor {proveedor_id}: {e}")
                continue

        print("Regeneración completada.")
