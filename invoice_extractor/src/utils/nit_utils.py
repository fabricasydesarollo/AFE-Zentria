# src/utils/nit_utils.py
"""
Utilidades para manejo de NITs colombianos.
"""


def calcular_digito_verificador_nit(nit: str) -> str:
    """
    Calcula el dígito verificador de un NIT colombiano.
    
    Args:
        nit (str): NIT sin dígito verificador (solo números)
        
    Returns:
        str: Dígito verificador (0-9 o 'X' para 10)
        
    Example:
        >>> calcular_digito_verificador_nit("800185449")
        "9"
    """
    if not nit or not nit.isdigit():
        return ""
    
    # Tabla de multiplicadores para el algoritmo colombiano
    multiplicadores = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
    
    # Convertir NIT a lista de dígitos (de derecha a izquierda)
    digitos = [int(d) for d in reversed(nit)]
    
    # Calcular suma ponderada
    suma = 0
    for i, digito in enumerate(digitos):
        if i < len(multiplicadores):
            suma += digito * multiplicadores[i]
    
    # Calcular residuo
    residuo = suma % 11
    
    # Determinar dígito verificador
    if residuo < 2:
        return str(residuo)
    else:
        dv = 11 - residuo
        return str(dv) if dv < 10 else "X"


def completar_nit_con_dv(nit: str) -> str:
    """
    Completa un NIT con su dígito verificador si no lo tiene.
    
    Args:
        nit (str): NIT que puede o no tener dígito verificador
        
    Returns:
        str: NIT completo con dígito verificador
        
    Example:
        >>> completar_nit_con_dv("800185449")
        "800185449-9"
        >>> completar_nit_con_dv("800185449-9")
        "800185449-9"
    """
    if not nit:
        return nit
    
    nit = nit.strip()
    
    # Si ya tiene dígito verificador, devolverlo tal como está
    if "-" in nit:
        return nit
    
    # Si no tiene dígito verificador, calcularlo y agregarlo
    if nit.isdigit():
        dv = calcular_digito_verificador_nit(nit)
        if dv:
            return f"{nit}-{dv}"
    
    return nit


def validar_nit_colombiano(nit: str) -> bool:
    """
    Valida si un NIT colombiano es correcto.
    
    Args:
        nit (str): NIT con o sin dígito verificador
        
    Returns:
        bool: True si es válido, False en caso contrario
        
    Example:
        >>> validar_nit_colombiano("800185449-9")
        True
        >>> validar_nit_colombiano("800185449-8")
        False
    """
    if not nit:
        return False
    
    nit = nit.strip()
    
    # Si no tiene dígito verificador, solo validar que sean números
    if "-" not in nit:
        return nit.isdigit() and len(nit) >= 7
    
    # Si tiene dígito verificador, validar que sea correcto
    try:
        numero, dv_actual = nit.split("-")
        if not numero.isdigit():
            return False
        
        dv_calculado = calcular_digito_verificador_nit(numero)
        return dv_actual.upper() == dv_calculado.upper()
    except ValueError:
        return False