"""
Validador y normalizador de NITs colombianos (DIAN).

Implementa el algoritmo oficial DIAN (Orden Administrativa N°4 del 27/10/1989)
para calcular y validar dígitos verificadores de NITs.

Garantiza que todos los NITs en el sistema se almacenan en formato normalizado:
  "XXXXXXXXX-D" donde D es el dígito verificador
"""

import re
from typing import Tuple


class NitValidator:
    """
    Validador y calculador del dígito verificador DIAN para NITs colombianos.

    Algoritmo: Módulo 11 (Orden Administrativa DIAN N°4 del 27/10/1989)
    """

    # Serie multiplicadora oficial DIAN
    MULTIPLIERS = [41, 37, 29, 23, 19, 17, 13, 7, 3]

    @staticmethod
    def calcular_digito_verificador(nit_sin_dv: str) -> str:
        """
        Calcula el dígito verificador (DV) de un NIT usando el algoritmo DIAN.

        Algoritmo:
        1. Multiplica cada dígito del NIT por la serie: 41, 37, 29, 23, 19, 17, 13, 7, 3
        2. Suma todos los productos
        3. Aplica módulo 11 al resultado
        4. DV = 11 - resultado (con excepciones para 0 y 1)

        Args:
            nit_sin_dv: String numérico de máximo 9 dígitos, ej: "800185449"

        Returns:
            String con el dígito verificador calculado (0-9)

        Raises:
            ValueError: Si el NIT no es válido (no numérico, más de 9 dígitos, etc.)

        Example:
            >>> NitValidator.calcular_digito_verificador("800185449")
            "9"
            >>> NitValidator.calcular_digito_verificador("900399741")
            "7"
        """
        # Limpiar y validar
        nit_clean = nit_sin_dv.strip().replace(".", "").replace("-", "")

        # Validar que sea numérico
        if not nit_clean.isdigit():
            raise ValueError(f"NIT debe contener solo dígitos. Recibido: '{nit_sin_dv}'")

        # Validar longitud (máximo 9 dígitos)
        if len(nit_clean) > 9:
            raise ValueError(f"NIT no puede tener más de 9 dígitos. Recibido: '{nit_sin_dv}' ({len(nit_clean)} dígitos)")

        if len(nit_clean) == 0:
            raise ValueError("NIT no puede estar vacío")

        # Rellenar con ceros a la izquierda hasta 9 dígitos
        nit_padded = nit_clean.zfill(9)

        # Paso 1: Multiplicar cada dígito por la serie DIAN
        suma = 0
        for i, digito in enumerate(nit_padded):
            producto = int(digito) * NitValidator.MULTIPLIERS[i]
            suma += producto

        # Paso 2: Aplicar módulo 11
        residuo = suma % 11

        # Paso 3: Calcular dígito verificador
        # Casos especiales para residuos 0 y 1
        if residuo == 0:
            dv = 0
        elif residuo == 1:
            dv = 1
        else:
            dv = 11 - residuo

        return str(dv)

    @staticmethod
    def normalizar_nit(nit: str) -> str:
        """
        Normaliza un NIT a formato estándar: "XXXXXXXXX-D"

        Acepta NITs en varios formatos:
        - "800185449" → "800185449-9" (calcula DV)
        - "800185449-9" → "800185449-9" (ya normalizado)
        - "800.185.449" → "800185449-9" (limpia formato)
        - "800.185.449-9" → "800185449-9" (limpia y normaliza)

        Args:
            nit: String con el NIT en cualquier formato

        Returns:
            String normalizado formato "XXXXXXXXX-D"

        Raises:
            ValueError: Si el NIT no es válido

        Example:
            >>> NitValidator.normalizar_nit("800185449")
            "800185449-9"
            >>> NitValidator.normalizar_nit("800.185.449-9")
            "800185449-9"
        """
        # Limpiar espacios y caracteres especiales
        nit_clean = nit.strip().replace(".", "").replace(" ", "")

        # Separar NIT y DV si ya existen
        if "-" in nit_clean:
            partes = nit_clean.split("-")
            if len(partes) != 2:
                raise ValueError(f"Formato inválido de NIT. Recibido: '{nit}'")
            nit_numero = partes[0]
            dv_proporcionado = partes[1]
        else:
            nit_numero = nit_clean
            dv_proporcionado = None

        # Validar que la parte numérica sea válida
        if not nit_numero.isdigit():
            raise ValueError(f"Parte numérica del NIT debe ser dígitos. Recibido: '{nit}'")

        if len(nit_numero) > 9:
            raise ValueError(f"NIT no puede tener más de 9 dígitos. Recibido: '{nit}'")

        if len(nit_numero) == 0:
            raise ValueError("NIT no puede estar vacío")

        # Calcular DV correcto
        dv_calculado = NitValidator.calcular_digito_verificador(nit_numero)

        # Si se proporcionó DV, validar que sea correcto
        if dv_proporcionado is not None:
            if dv_proporcionado != dv_calculado:
                raise ValueError(
                    f"Dígito verificador incorrecto para NIT {nit_numero}. "
                    f"Proporcionado: {dv_proporcionado}, "
                    f"Correcto: {dv_calculado}"
                )

        # NO rellenar con ceros - mantener el NIT tal como viene
        # El zfill(9) solo se usa para calcular el DV, no para almacenar
        return f"{nit_numero}-{dv_calculado}"

    @staticmethod
    def validar_nit(nit: str) -> Tuple[bool, str]:
        """
        Valida un NIT y retorna (es_válido, nit_normalizado_o_error)

        Args:
            nit: String con el NIT a validar

        Returns:
            Tuple[bool, str]:
            - (True, "XXXXXXXXX-D") si es válido
            - (False, "mensaje de error") si es inválido

        Example:
            >>> es_valido, resultado = NitValidator.validar_nit("800185449")
            >>> if es_valido:
            ...     print(f"NIT válido: {resultado}")
        """
        try:
            nit_normalizado = NitValidator.normalizar_nit(nit)
            return True, nit_normalizado
        except ValueError as e:
            return False, str(e)

    @staticmethod
    def es_nit_normalizado(nit: str) -> bool:
        """
        Verifica si un NIT está en formato normalizado: "XXXXX-D" a "XXXXXXXXX-D"

        Args:
            nit: String con el NIT a verificar

        Returns:
            True si está en formato "NIT-DV" con DV correcto, False en otro caso

        Example:
            >>> NitValidator.es_nit_normalizado("800185449-9")
            True
            >>> NitValidator.es_nit_normalizado("17343874-5")
            True (si el DV es correcto)
            >>> NitValidator.es_nit_normalizado("800185449")
            False
        """
        # Patrón: 1-9 dígitos, guión, 1 dígito
        patron = r'^\d{1,9}-\d$'
        if not re.match(patron, nit.strip()):
            return False

        # Validar que el DV sea correcto
        partes = nit.strip().split("-")
        nit_numero = partes[0]
        dv_proporcionado = partes[1]
        dv_calculado = NitValidator.calcular_digito_verificador(nit_numero)

        return dv_proporcionado == dv_calculado


# Instancia compartida para usar en toda la aplicación
nit_validator = NitValidator()
