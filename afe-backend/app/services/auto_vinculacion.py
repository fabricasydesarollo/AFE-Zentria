"""
Servicio de vinculación automática de facturas con líneas presupuestales.

Este servicio implementa lógica inteligente para vincular automáticamente
facturas con las líneas de presupuesto correspondientes basándose en:
- Proveedor
- Monto
- Fecha/Período
- Descripción/Concepto
- Categoría

Nivel: Enterprise Fortune 500
"""
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.factura import Factura
from app.models.presupuesto import LineaPresupuesto, EjecucionPresupuestal, EstadoLineaPresupuesto
from app.crud import presupuesto as crud_presupuesto


class AutoVinculador:
    """
    Servicio de vinculación automática inteligente.
    """

    def __init__(self, db: Session):
        self.db = db

    def vincular_factura(
        self,
        factura_id: int,
        año_fiscal: Optional[int] = None,
        umbral_confianza: int = 70
    ) -> Optional[Dict[str, Any]]:
        """
        Intenta vincular automáticamente una factura con una línea presupuestal.

        Args:
            factura_id: ID de la factura a vincular
            año_fiscal: Año fiscal a buscar (si None, usa el año de la factura)
            umbral_confianza: Mínimo % de confianza para vincular automáticamente (70-100)

        Returns:
            Dict con información de la vinculación o None si no se encontró match
        """
        # Obtener factura
        factura = self.db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            return None

        # Verificar si ya está vinculada
        vinculacion_existente = self.db.query(EjecucionPresupuestal).filter(
            EjecucionPresupuestal.factura_id == factura_id
        ).first()
        if vinculacion_existente:
            return {
                "vinculado": False,
                "motivo": "La factura ya está vinculada",
                "ejecucion_id": vinculacion_existente.id
            }

        # Determinar año fiscal
        if not año_fiscal and factura.fecha_emision:
            año_fiscal = factura.fecha_emision.year
        elif not año_fiscal:
            return None

        # Buscar líneas presupuestales activas del año
        lineas = self.db.query(LineaPresupuesto).filter(
            and_(
                LineaPresupuesto.año_fiscal == año_fiscal,
                LineaPresupuesto.estado == EstadoLineaPresupuesto.ACTIVO
            )
        ).all()

        if not lineas:
            return {
                "vinculado": False,
                "motivo": f"No hay líneas presupuestales activas para el año {año_fiscal}"
            }

        # Calcular score de compatibilidad para cada línea
        mejores_matches = []
        for linea in lineas:
            score, criterios = self._calcular_score_compatibilidad(factura, linea)
            if score >= umbral_confianza:
                mejores_matches.append({
                    "linea": linea,
                    "score": score,
                    "criterios": criterios
                })

        if not mejores_matches:
            return {
                "vinculado": False,
                "motivo": f"No se encontró ninguna línea con confianza >= {umbral_confianza}%",
                "mejores_candidatos": self._obtener_top_candidatos(factura, lineas, limit=3)
            }

        # Ordenar por score descendente
        mejores_matches.sort(key=lambda x: x["score"], reverse=True)
        mejor_match = mejores_matches[0]

        # Crear ejecución presupuestal automáticamente
        ejecucion = crud_presupuesto.create_ejecucion_presupuestal(
            db=self.db,
            linea_presupuesto_id=mejor_match["linea"].id,
            factura_id=factura.id,
            monto_ejecutado=factura.total or Decimal("0.00"),
            periodo_ejecucion=factura.fecha_emision or datetime.now().date(),
            descripcion=f"Vinculación automática - Score: {mejor_match['score']}%",
            vinculacion_automatica=True,
            confianza_vinculacion=mejor_match["score"],
            criterios_matching=mejor_match["criterios"],
            creado_por="SISTEMA_AUTO_VINCULACION"
        )

        return {
            "vinculado": True,
            "ejecucion_id": ejecucion.id,
            "linea_presupuesto_id": mejor_match["linea"].id,
            "linea_codigo": mejor_match["linea"].codigo,
            "linea_nombre": mejor_match["linea"].nombre,
            "confianza": mejor_match["score"],
            "criterios_match": mejor_match["criterios"],
            "requiere_aprobacion_nivel2": ejecucion.requiere_aprobacion_nivel2,
            "requiere_aprobacion_nivel3": ejecucion.requiere_aprobacion_nivel3
        }

    def _calcular_score_compatibilidad(
        self,
        factura: Factura,
        linea: LineaPresupuesto
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calcula un score de compatibilidad (0-100) entre una factura y una línea presupuestal.

        Criterios y pesos:
        - Proveedor coincide: 35 puntos
        - Monto dentro del rango presupuestal: 25 puntos
        - Categoría coincide: 20 puntos
        - Período correcto: 10 puntos
        - Nombre/descripción similar: 10 puntos
        """
        score = 0
        criterios = {}

        # 1. Coincidencia de proveedor (35 puntos)
        if linea.proveedor_preferido and factura.proveedor:
            if self._comparar_proveedores(factura.proveedor, linea.proveedor_preferido):
                score += 35
                criterios["proveedor"] = {
                    "match": True,
                    "puntos": 35,
                    "factura_proveedor": factura.proveedor,
                    "linea_proveedor": linea.proveedor_preferido
                }
            else:
                criterios["proveedor"] = {
                    "match": False,
                    "puntos": 0
                }
        else:
            # Si no hay proveedor preferido, dar puntos parciales
            score += 15
            criterios["proveedor"] = {
                "match": "parcial",
                "puntos": 15,
                "nota": "No hay proveedor preferido definido"
            }

        # 2. Monto dentro del rango presupuestal (25 puntos)
        if factura.total and factura.mes_factura:
            mes_idx = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
            mes_nombre = mes_idx[factura.mes_factura - 1]
            presupuesto_mes = getattr(linea, f"presupuesto_{mes_nombre}") or Decimal("0.00")

            if presupuesto_mes > 0:
                # Calcular desviación porcentual
                desviacion_pct = abs((factura.total - presupuesto_mes) / presupuesto_mes * 100)

                if desviacion_pct <= 10:  # Dentro del 10%
                    score += 25
                    criterios["monto"] = {"match": "excelente", "puntos": 25, "desviacion_pct": float(desviacion_pct)}
                elif desviacion_pct <= 25:  # Dentro del 25%
                    score += 18
                    criterios["monto"] = {"match": "bueno", "puntos": 18, "desviacion_pct": float(desviacion_pct)}
                elif desviacion_pct <= 50:  # Dentro del 50%
                    score += 10
                    criterios["monto"] = {"match": "aceptable", "puntos": 10, "desviacion_pct": float(desviacion_pct)}
                else:
                    criterios["monto"] = {"match": False, "puntos": 0, "desviacion_pct": float(desviacion_pct)}
            else:
                criterios["monto"] = {"match": "no_evaluable", "puntos": 0, "nota": "Presupuesto mes = 0"}
        else:
            criterios["monto"] = {"match": "no_evaluable", "puntos": 0}

        # 3. Categoría coincide (20 puntos)
        if linea.categoria and factura.concepto:
            if self._comparar_textos(factura.concepto, linea.categoria):
                score += 20
                criterios["categoria"] = {"match": True, "puntos": 20}
            elif linea.nombre and self._comparar_textos(factura.concepto, linea.nombre):
                score += 15
                criterios["categoria"] = {"match": "parcial", "puntos": 15}
            else:
                criterios["categoria"] = {"match": False, "puntos": 0}
        else:
            score += 10  # Puntos base si no hay categoría
            criterios["categoria"] = {"match": "no_definido", "puntos": 10}

        # 4. Período correcto (10 puntos)
        if factura.año_factura == linea.año_fiscal:
            score += 10
            criterios["periodo"] = {"match": True, "puntos": 10}
        else:
            criterios["periodo"] = {"match": False, "puntos": 0}

        # 5. Descripción similar (10 puntos)
        if linea.descripcion and factura.concepto:
            if self._comparar_textos(factura.concepto, linea.descripcion):
                score += 10
                criterios["descripcion"] = {"match": True, "puntos": 10}
            else:
                criterios["descripcion"] = {"match": False, "puntos": 0}
        else:
            score += 5  # Puntos base
            criterios["descripcion"] = {"match": "no_evaluable", "puntos": 5}

        return score, criterios

    def _comparar_proveedores(self, proveedor1: str, proveedor2: str) -> bool:
        """Compara dos nombres de proveedor con normalización."""
        p1 = proveedor1.lower().strip()
        p2 = proveedor2.lower().strip()

        # Coincidencia exacta
        if p1 == p2:
            return True

        # Coincidencia parcial (uno contiene al otro)
        if p1 in p2 or p2 in p1:
            return True

        # Coincidencia de palabras clave (al menos 2 palabras en común)
        palabras1 = set(p1.split())
        palabras2 = set(p2.split())
        palabras_comunes = palabras1.intersection(palabras2)

        return len(palabras_comunes) >= 2

    def _comparar_textos(self, texto1: str, texto2: str) -> bool:
        """Compara dos textos con normalización."""
        t1 = texto1.lower().strip()
        t2 = texto2.lower().strip()

        # Coincidencia exacta
        if t1 == t2:
            return True

        # Coincidencia parcial
        if t1 in t2 or t2 in t1:
            return True

        # Coincidencia de palabras (al menos 1 palabra en común de 4+ caracteres)
        palabras1 = set([p for p in t1.split() if len(p) >= 4])
        palabras2 = set([p for p in t2.split() if len(p) >= 4])
        palabras_comunes = palabras1.intersection(palabras2)

        return len(palabras_comunes) >= 1

    def _obtener_top_candidatos(
        self,
        factura: Factura,
        lineas: List[LineaPresupuesto],
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Obtiene los mejores candidatos aunque no superen el umbral."""
        candidatos = []
        for linea in lineas:
            score, criterios = self._calcular_score_compatibilidad(factura, linea)
            candidatos.append({
                "linea_id": linea.id,
                "codigo": linea.codigo,
                "nombre": linea.nombre,
                "score": score,
                "criterios": criterios
            })

        # Ordenar por score descendente
        candidatos.sort(key=lambda x: x["score"], reverse=True)
        return candidatos[:limit]

    def vincular_facturas_pendientes(
        self,
        año_fiscal: int,
        umbral_confianza: int = 80,
        limite: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Vincula automáticamente todas las facturas pendientes de un año fiscal.

        Args:
            año_fiscal: Año fiscal a procesar
            umbral_confianza: Umbral mínimo de confianza (recomendado: 80%)
            limite: Límite de facturas a procesar (None = todas)

        Returns:
            Reporte con estadísticas de vinculación
        """
        # Obtener facturas del año que NO están vinculadas
        query = self.db.query(Factura).filter(
            and_(
                Factura.año_factura == año_fiscal,
                ~Factura.id.in_(
                    self.db.query(EjecucionPresupuestal.factura_id)
                )
            )
        ).order_by(Factura.fecha_emision.desc())

        if limite:
            query = query.limit(limite)

        facturas_pendientes = query.all()

        # Procesar cada factura
        resultados = {
            "total_procesadas": 0,
            "total_vinculadas": 0,
            "total_sin_vincular": 0,
            "vinculaciones": [],
            "no_vinculadas": [],
            "errores": []
        }

        for factura in facturas_pendientes:
            resultados["total_procesadas"] += 1

            try:
                resultado = self.vincular_factura(
                    factura_id=factura.id,
                    año_fiscal=año_fiscal,
                    umbral_confianza=umbral_confianza
                )

                if resultado and resultado.get("vinculado"):
                    resultados["total_vinculadas"] += 1
                    resultados["vinculaciones"].append({
                        "factura_id": factura.id,
                        "numero_factura": factura.numero_factura,
                        "ejecucion_id": resultado["ejecucion_id"],
                        "linea_id": resultado["linea_presupuesto_id"],
                        "confianza": resultado["confianza"]
                    })
                else:
                    resultados["total_sin_vincular"] += 1
                    resultados["no_vinculadas"].append({
                        "factura_id": factura.id,
                        "numero_factura": factura.numero_factura,
                        "motivo": resultado.get("motivo") if resultado else "Sin resultado",
                        "candidatos": resultado.get("mejores_candidatos", []) if resultado else []
                    })

            except Exception as e:
                resultados["errores"].append({
                    "factura_id": factura.id,
                    "numero_factura": factura.numero_factura,
                    "error": str(e)
                })

        return resultados

    def sugerir_vinculacion(
        self,
        factura_id: int,
        año_fiscal: Optional[int] = None,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Sugiere las N mejores líneas presupuestales para una factura sin vincular automáticamente.

        Args:
            factura_id: ID de la factura
            año_fiscal: Año fiscal (opcional)
            top_n: Cantidad de sugerencias a retornar

        Returns:
            Lista de sugerencias ordenadas por score
        """
        factura = self.db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            return []

        if not año_fiscal and factura.fecha_emision:
            año_fiscal = factura.fecha_emision.year
        elif not año_fiscal:
            return []

        # Buscar líneas activas
        lineas = self.db.query(LineaPresupuesto).filter(
            and_(
                LineaPresupuesto.año_fiscal == año_fiscal,
                LineaPresupuesto.estado == EstadoLineaPresupuesto.ACTIVO
            )
        ).all()

        return self._obtener_top_candidatos(factura, lineas, limit=top_n)
