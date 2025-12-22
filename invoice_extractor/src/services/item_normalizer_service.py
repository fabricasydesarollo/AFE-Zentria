"""
Servicio de Normalización de Items de Facturas.

Este servicio normaliza descripciones de items para permitir comparaciones
consistentes entre facturas de diferentes períodos.

Autor: Sistema AFE
Fecha: 2025-10-09
"""

import hashlib
import re
import unicodedata
from typing import Optional


class ItemNormalizerService:
    """
    Servicio para normalizar descripciones de items/productos de facturas.

    Funcionalidad:
    - Normaliza texto (lowercase, sin acentos, sin caracteres especiales)
    - Genera hash MD5 para matching rápido
    - Extrae categorías automáticamente
    - Detecta palabras clave de recurrencia
    """

    # Palabras clave que indican servicios recurrentes
    PALABRAS_RECURRENTES = {
        'mensual', 'monthly', 'suscripcion', 'subscription',
        'licencia', 'license', 'mantenimiento', 'maintenance',
        'soporte', 'support', 'hosting', 'renta', 'rent',
        'arrendamiento', 'lease', 'canon', 'servicio mensual'
    }

    # Mapeo de categorías por palabras clave
    CATEGORIAS = {
        'software': ['software', 'licencia', 'license', 'saas', 'aplicacion', 'app'],
        'hardware': ['hardware', 'equipo', 'servidor', 'computador', 'laptop', 'pc'],
        'servicio_cloud': ['cloud', 'aws', 'azure', 'gcp', 'hosting', 'nube'],
        'conectividad': ['internet', 'conectividad', 'vpn', 'red', 'network', 'fibra'],
        'telefonia': ['telefonia', 'celular', 'movil', 'llamadas', 'telecom'],
        'energia': ['energia', 'electricidad', 'luz', 'power', 'energia electrica'],
        'consultoria': ['consultoria', 'consulting', 'asesoria', 'advisory'],
        'desarrollo': ['desarrollo', 'programacion', 'development', 'coding'],
        'soporte': ['soporte', 'support', 'mantenimiento', 'maintenance'],
        'capacitacion': ['capacitacion', 'training', 'curso', 'formacion'],
    }

    @staticmethod
    def normalizar_texto(texto: str) -> str:
        """
        Normaliza un texto para comparación consistente.

        Proceso:
        1. Lowercase
        2. Eliminar acentos/diacríticos
        3. Eliminar caracteres especiales
        4. Eliminar espacios múltiples
        5. Trim

        Args:
            texto: Texto original

        Returns:
            Texto normalizado

        Example:
            >>> ItemNormalizerService.normalizar_texto("Servicio de Hosting AWS - Plan Premium")
            'servicio de hosting aws plan premium'
        """
        if not texto:
            return ""

        # Lowercase
        texto = texto.lower()

        # Eliminar acentos (NFD = Normalization Form Canonical Decomposition)
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')

        # Eliminar caracteres especiales, dejar solo letras, números y espacios
        texto = re.sub(r'[^a-z0-9\s]', ' ', texto)

        # Eliminar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto)

        # Trim
        texto = texto.strip()

        return texto

    @staticmethod
    def generar_hash(texto_normalizado: str) -> str:
        """
        Genera un hash MD5 del texto normalizado para matching rápido.

        Args:
            texto_normalizado: Texto ya normalizado

        Returns:
            Hash MD5 (32 caracteres hexadecimales)

        Example:
            >>> ItemNormalizerService.generar_hash("servicio de hosting aws")
            'a1b2c3d4e5f6...'
        """
        if not texto_normalizado:
            return ""

        return hashlib.md5(texto_normalizado.encode('utf-8')).hexdigest()

    @classmethod
    def detectar_categoria(cls, descripcion_normalizada: str) -> Optional[str]:
        """
        Detecta la categoría del item basado en palabras clave.

        Args:
            descripcion_normalizada: Descripción normalizada

        Returns:
            Categoría detectada o None

        Example:
            >>> ItemNormalizerService.detectar_categoria("licencia office 365")
            'software'
        """
        if not descripcion_normalizada:
            return None

        # Buscar categorías por palabras clave
        for categoria, palabras_clave in cls.CATEGORIAS.items():
            for palabra in palabras_clave:
                if palabra in descripcion_normalizada:
                    return categoria

        return None

    @classmethod
    def es_recurrente(cls, descripcion_normalizada: str) -> bool:
        """
        Detecta si un item es de tipo recurrente (mensual, suscripción, etc).

        Args:
            descripcion_normalizada: Descripción normalizada

        Returns:
            True si contiene palabras clave de recurrencia

        Example:
            >>> ItemNormalizerService.es_recurrente("licencia mensual office 365")
            True
        """
        if not descripcion_normalizada:
            return False

        # Buscar palabras clave de recurrencia
        for palabra in cls.PALABRAS_RECURRENTES:
            if palabra in descripcion_normalizada:
                return True

        return False

    @classmethod
    def normalizar_item_completo(cls, descripcion: str) -> dict:
        """
        Normaliza un item completo y extrae toda la metadata.

        Args:
            descripcion: Descripción original del item

        Returns:
            Dict con:
            - descripcion_normalizada
            - item_hash
            - categoria
            - es_recurrente

        Example:
            >>> ItemNormalizerService.normalizar_item_completo("Licencia Mensual Office 365")
            {
                'descripcion_normalizada': 'licencia mensual office 365',
                'item_hash': 'a1b2c3d4...',
                'categoria': 'software',
                'es_recurrente': True
            }
        """
        # Normalizar texto
        desc_norm = cls.normalizar_texto(descripcion)

        # Generar hash
        item_hash = cls.generar_hash(desc_norm)

        # Detectar categoría
        categoria = cls.detectar_categoria(desc_norm)

        # Detectar recurrencia
        recurrente = cls.es_recurrente(desc_norm)

        return {
            'descripcion_normalizada': desc_norm,
            'item_hash': item_hash,
            'categoria': categoria,
            'es_recurrente': 1 if recurrente else 0
        }

    @staticmethod
    def calcular_similitud(desc1: str, desc2: str) -> float:
        """
        Calcula similitud entre dos descripciones (Jaccard similarity).

        Args:
            desc1: Primera descripción normalizada
            desc2: Segunda descripción normalizada

        Returns:
            Similitud de 0.0 a 1.0

        Example:
            >>> ItemNormalizerService.calcular_similitud(
            ...     "servicio hosting aws",
            ...     "servicio de hosting amazon aws"
            ... )
            0.75
        """
        if not desc1 or not desc2:
            return 0.0

        # Convertir a conjuntos de palabras
        palabras1 = set(desc1.split())
        palabras2 = set(desc2.split())

        # Jaccard similarity = |intersección| / |unión|
        interseccion = palabras1.intersection(palabras2)
        union = palabras1.union(palabras2)

        if len(union) == 0:
            return 0.0

        return len(interseccion) / len(union)

    @classmethod
    def son_items_similares(
        cls,
        desc1: str,
        desc2: str,
        umbral_similitud: float = 0.7
    ) -> bool:
        """
        Determina si dos items son similares (mismo servicio/producto).

        Args:
            desc1: Primera descripción
            desc2: Segunda descripción
            umbral_similitud: Mínimo de similitud para considerar match (default 0.7)

        Returns:
            True si similitud >= umbral

        Example:
            >>> ItemNormalizerService.son_items_similares(
            ...     "Hosting AWS Plan Premium",
            ...     "Hosting Amazon AWS Premium Plan"
            ... )
            True
        """
        # Normalizar ambas
        norm1 = cls.normalizar_texto(desc1)
        norm2 = cls.normalizar_texto(desc2)

        # Calcular similitud
        similitud = cls.calcular_similitud(norm1, norm2)

        return similitud >= umbral_similitud
