# app/services/automation/fingerprint_generator.py
"""
Generador de fingerprints para facturas.

Este módulo se encarga de crear identificadores únicos (huellas digitales)
para facturas basándose en su concepto, proveedor y monto, permitiendo
identificar patrones de recurrencia de forma eficiente.
"""

import hashlib
import re
from decimal import Decimal
from typing import Dict, List, Optional, Any
from app.models.factura import Factura


class FingerprintGenerator:
    """
    Clase para generar fingerprints únicos de facturas para matching de recurrencia.
    """
    
    def __init__(self):
        # Palabras no discriminativas que se remueven durante normalización
        self.stop_words = {
            'factura', 'numero', 'del', 'de', 'la', 'el', 'por', 'para', 
            'con', 'en', 'y', 'o', 'un', 'una', 'los', 'las', 'al', 'se'
        }
        
        # Categorías de productos médicos comunes
        self.categorias_medicas = {
            'suturas': ['sutura', 'vicryl', 'monocryl', 'prolene', 'seda'],
            'hemostaticos': ['spongostan', 'esponja', 'hemostatico', 'gelfoam'],
            'instrumental': ['instrumental', 'pinza', 'tijera', 'clamp'],
            'implantes': ['implante', 'protesis', 'tornillo', 'placa'],
            'consumibles': ['guante', 'mascarilla', 'jeringa', 'cateter'],
            'medicamentos': ['antibiotico', 'analgesico', 'suero', 'medicamento']
        }

    def generar_fingerprint_completo(self, factura_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Genera múltiples tipos de fingerprints para una factura.
        
        Args:
            factura_data: Diccionario con datos de la factura
            
        Returns:
            Dict con diferentes tipos de fingerprints
        """
        # Fingerprint principal (más estricto)
        fingerprint_principal = self.generar_fingerprint_principal(factura_data)
        
        # Fingerprint de concepto (solo concepto + proveedor)
        fingerprint_concepto = self.generar_fingerprint_concepto(factura_data)
        
        # Fingerprint de monto (concepto + rango de monto)
        fingerprint_monto = self.generar_fingerprint_con_tolerancia_monto(factura_data)
        
        # Fingerprint de orden de compra (si existe)
        fingerprint_oc = self.generar_fingerprint_orden_compra(factura_data)
        
        return {
            'principal': fingerprint_principal,
            'concepto': fingerprint_concepto,
            'monto_tolerante': fingerprint_monto,
            'orden_compra': fingerprint_oc
        }

    def generar_fingerprint_principal(self, factura_data: Dict[str, Any]) -> str:
        """
        Genera el fingerprint principal (más estricto) de una factura.
        
        Combina: NIT + Concepto Normalizado + Monto Redondeado
        """
        nit = factura_data.get('nit_proveedor', '')
        concepto = self.normalizar_concepto(factura_data.get('concepto_principal', ''))
        monto = self._redondear_monto(factura_data.get('total_a_pagar', 0))
        
        fingerprint_data = f"{nit}:{concepto}:{monto}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()

    def generar_fingerprint_concepto(self, factura_data) -> str:
        """
        Genera fingerprint basado solo en proveedor y concepto.
        Útil para detectar servicios recurrentes independientemente del monto.
        Acepta tanto diccionario de factura como string directo de concepto.
        """
        if isinstance(factura_data, str):
            # Si es solo el concepto como string
            concepto = self.normalizar_concepto(factura_data)
            fingerprint_data = f"concepto:{concepto}"
        else:
            # Si es diccionario completo de factura
            nit = factura_data.get('nit_proveedor', '')
            concepto = self.normalizar_concepto(factura_data.get('concepto_principal', ''))
            fingerprint_data = f"{nit}:{concepto}"
        
        return hashlib.md5(fingerprint_data.encode()).hexdigest()

    def generar_fingerprint_con_tolerancia_monto(self, factura_data: Dict[str, Any]) -> str:
        """
        Genera fingerprint con tolerancia en el monto (±10%).
        Útil para servicios que varían ligeramente en precio.
        """
        nit = factura_data.get('nit_proveedor', '')
        concepto = self.normalizar_concepto(factura_data.get('concepto_principal', ''))
        monto_base = self._generar_rango_monto(factura_data.get('total_a_pagar', 0))
        
        fingerprint_data = f"{nit}:{concepto}:{monto_base}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()

    def generar_fingerprint_orden_compra(self, factura_data: Dict[str, Any]) -> Optional[str]:
        """
        Genera fingerprint basado en orden de compra si está disponible.
        """
        orden_compra = factura_data.get('orden_compra_numero')
        if not orden_compra:
            return None
            
        nit = factura_data.get('nit_proveedor', '')
        fingerprint_data = f"{nit}:OC:{orden_compra}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()

    def normalizar_concepto(self, concepto: str) -> str:
        """
        Normaliza el concepto de la factura para facilitar el matching.
        """
        if not concepto:
            return "concepto_vacio"
        
        # Convertir a minúsculas y remover caracteres especiales
        concepto_limpio = re.sub(r'[^\w\s]', '', concepto.lower())
        
        # Remover fechas y números específicos
        concepto_limpio = re.sub(r'\b\d{1,2}/\d{4}\b', '', concepto_limpio)  # mm/yyyy
        concepto_limpio = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', concepto_limpio)  # yyyy-mm-dd
        concepto_limpio = re.sub(r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{4}\b', '', concepto_limpio)
        
        # Extraer palabras significativas
        palabras = [w for w in concepto_limpio.split() if w not in self.stop_words and len(w) > 2]
        
        # Identificar categorías médicas
        categorias_encontradas = self._identificar_categorias_medicas(concepto_limpio)
        
        # Si hay categorías específicas, priorizarlas
        if categorias_encontradas:
            palabras_clave = categorias_encontradas + [w for w in palabras[:3] if w not in categorias_encontradas]
        else:
            # Usar primeras palabras significativas
            palabras_clave = palabras[:4]  # Máximo 4 palabras clave
        
        # Si no hay palabras clave, generar desde descripción
        if not palabras_clave:
            palabras_clave = self._extraer_palabras_clave_fallback(concepto)
        
        return '_'.join(palabras_clave[:4])  # Máximo 4 términos

    def _identificar_categorias_medicas(self, texto: str) -> List[str]:
        """
        Identifica categorías de productos médicos en el texto.
        """
        categorias_encontradas = []
        
        for categoria, palabras_categoria in self.categorias_medicas.items():
            for palabra in palabras_categoria:
                if palabra in texto:
                    categorias_encontradas.append(categoria)
                    break  # Solo agregar la categoría una vez
        
        return categorias_encontradas

    def _extraer_palabras_clave_fallback(self, concepto: str) -> List[str]:
        """
        Extrae palabras clave como fallback cuando no se encuentran patrones específicos.
        """
        # Buscar palabras en mayúsculas (códigos de producto)
        palabras_mayus = re.findall(r'\b[A-Z]{3,}\b', concepto)
        
        if palabras_mayus:
            return [w.lower() for w in palabras_mayus[:2]]
        
        # Como último recurso, usar primeras palabras del concepto
        palabras_basicas = re.findall(r'\b\w{4,}\b', concepto.lower())
        return palabras_basicas[:2] if palabras_basicas else ['producto_generico']

    def _redondear_monto(self, monto: Any, precision: int = -3) -> int:
        """
        Redondea el monto para permitir pequeñas variaciones.
        
        Args:
            monto: Monto a redondear
            precision: Precisión del redondeo (-3 = miles, -2 = centenas)
        """
        try:
            monto_float = float(monto)
            return int(round(monto_float, precision))
        except (ValueError, TypeError):
            return 0

    def _generar_rango_monto(self, monto: Any, tolerancia_pct: float = 10.0) -> str:
        """
        Genera un rango de monto para permitir tolerancia en el matching.
        """
        try:
            monto_float = float(monto)
            tolerancia = monto_float * (tolerancia_pct / 100)
            rango_min = int((monto_float - tolerancia) // 10000) * 10000  # Redondear a decenas de miles
            rango_max = int((monto_float + tolerancia) // 10000) * 10000
            return f"{rango_min}-{rango_max}"
        except (ValueError, TypeError):
            return "0-0"

    def generar_fingerprint_desde_factura(self, factura: Factura) -> Dict[str, str]:
        """
        Genera fingerprints a partir de un objeto Factura de SQLAlchemy.
        """
        factura_data = {
            'nit_proveedor': factura.proveedor.nit if factura.proveedor else '',
            'concepto_principal': factura.concepto_principal or '',
            'total_a_pagar': factura.total_a_pagar,
            'orden_compra_numero': factura.orden_compra_numero
        }
        
        return self.generar_fingerprint_completo(factura_data)

    def comparar_fingerprints(self, fp1: Dict[str, str], fp2: Dict[str, str]) -> Dict[str, bool]:
        """
        Compara dos conjuntos de fingerprints y retorna las coincidencias.
        """
        return {
            'coincidencia_exacta': fp1['principal'] == fp2['principal'],
            'coincidencia_concepto': fp1['concepto'] == fp2['concepto'],
            'coincidencia_monto_tolerante': fp1['monto_tolerante'] == fp2['monto_tolerante'],
            'coincidencia_orden_compra': (
                fp1.get('orden_compra') and fp2.get('orden_compra') and 
                fp1['orden_compra'] == fp2['orden_compra']
            )
        }