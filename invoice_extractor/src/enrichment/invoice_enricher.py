"""
Enriquecimiento de facturas con metadatos y clasificaciones.
"""
from typing import Optional, List, Dict, Any
import hashlib
import re

from src.utils.logger import logger


class InvoiceEnricher:
    """Genera metadatos y clasificaciones para facturas"""
    
    def generate_concepto_principal(
        self,
        items_resumen: Optional[List[Dict[str, Any]]]
    ) -> Optional[str]:
        """
        Genera el concepto principal basado en los items de la factura.
        
        Args:
            items_resumen: Lista de items de la factura
            
        Returns:
            Concepto principal generado o None
        """
        if not items_resumen:
            return None
        
        try:
            # Obtener descripciones de los items más importantes
            descripciones = []
            for item in items_resumen[:3]:  # Solo top 3
                desc = item.get("descripcion", "")
                if desc:
                    descripciones.append(desc)
            
            if not descripciones:
                return None
            
            # Analizar palabras clave
            texto_completo = " ".join(descripciones).upper()
            
            # Patrones médicos
            if any(word in texto_completo for word in [
                "VICRYL", "SUTURA", "QUIRURGICO", "SPONGOSTAN", "MEDICAL", "INVIMA"
            ]):
                return "Suturas y material quirúrgico"
            
            # Patrones de medicamentos
            elif any(word in texto_completo for word in [
                "MEDICAMENT", "FARMAC", "DROGA", "MEDICINA"
            ]):
                return "Medicamentos y productos farmacéuticos"
            
            # Patrones de insumos médicos
            elif any(word in texto_completo for word in [
                "INSUMO", "MATERIAL", "DISPOSABLE", "CONSUMIBLE"
            ]):
                return "Insumos médicos y consumibles"
            
            # Patrones de equipos
            elif any(word in texto_completo for word in [
                "EQUIPO", "MAQUINA", "DISPOSITIVO", "APARATO"
            ]):
                return "Equipos y dispositivos médicos"
            
            # Concepto genérico basado en el primer item
            else:
                primera_desc = descripciones[0]
                palabras = primera_desc.split()[:4]
                concepto = " ".join(palabras).title()
                return concepto if len(concepto) <= 100 else concepto[:100]
            
        except Exception as exc:
            logger.warning(f"Error generating main concept: {exc}")
            return "Productos y servicios diversos"
    
    def normalize_concepto(self, concepto_principal: Optional[str]) -> Optional[str]:
        """
        Normaliza el concepto para facilitar matching automático.
        
        Args:
            concepto_principal: Concepto principal a normalizar
            
        Returns:
            Concepto normalizado o None
        """
        if not concepto_principal:
            return None
        
        try:
            # Convertir a minúsculas
            normalizado = concepto_principal.lower()
            
            # Mapeo de acentos
            acentos = {
                'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
                'ñ': 'n', 'ü': 'u'
            }
            
            for acento, letra in acentos.items():
                normalizado = normalizado.replace(acento, letra)
            
            # Remover caracteres especiales
            normalizado = re.sub(r'[^\w\s]', '', normalizado)
            
            # Reemplazar espacios múltiples por guiones bajos
            normalizado = re.sub(r'\s+', '_', normalizado.strip())
            
            # Limitar longitud
            return normalizado[:200] if normalizado else None
            
        except Exception as exc:
            logger.warning(f"Error normalizing concept: {exc}")
            return None
    
    def generate_concepto_hash(self, concepto_normalizado: Optional[str]) -> Optional[str]:
        """
        Genera hash MD5 del concepto normalizado.
        
        Args:
            concepto_normalizado: Concepto normalizado
            
        Returns:
            Hash MD5 del concepto o None
        """
        if not concepto_normalizado:
            return None
        
        try:
            return hashlib.md5(concepto_normalizado.encode('utf-8')).hexdigest()
        except Exception as exc:
            logger.warning(f"Error generating concept hash: {exc}")
            return None
    
    def classify_invoice_type(
        self,
        items_resumen: Optional[List[Dict[str, Any]]],
        proveedor: Optional[str]
    ) -> Optional[str]:
        """
        Clasifica automáticamente el tipo de factura.
        
        Args:
            items_resumen: Lista de items de la factura
            proveedor: Razón social del proveedor
            
        Returns:
            Tipo de factura clasificado o None
        """
        if not items_resumen and not proveedor:
            return None
        
        try:
            # Análisis basado en items
            if items_resumen:
                texto_items = " ".join([
                    item.get("descripcion", "") for item in items_resumen
                ]).upper()
                
                # Productos médicos específicos
                if any(word in texto_items for word in [
                    "VICRYL", "SUTURA", "SPONGOSTAN", "INVIMA", "QUIRURGICO"
                ]):
                    return "productos_medicos_estandar"
                
                elif "MEDICAMENT" in texto_items:
                    return "medicamentos_farmaceuticos"
                
                elif "EQUIPO" in texto_items or "DISPOSITIVO" in texto_items:
                    return "equipos_medicos"
                
                elif "INSUMO" in texto_items or "CONSUMIBLE" in texto_items:
                    return "insumos_medicos_consumibles"
            
            # Análisis basado en proveedor
            if proveedor:
                proveedor_upper = proveedor.upper()
                
                if any(word in proveedor_upper for word in [
                    "MEDICAL", "HEALTH", "SALUD", "CLINIC"
                ]):
                    return "productos_medicos_estandar"
                
                elif "FARMAC" in proveedor_upper or "DRUG" in proveedor_upper:
                    return "medicamentos_farmaceuticos"
            
            return "productos_servicios_generales"
            
        except Exception as exc:
            logger.warning(f"Error classifying invoice type: {exc}")
            return "no_clasificado"