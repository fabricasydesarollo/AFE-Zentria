"""
EJEMPLOS DE USO DEL SISTEMA DE PROCESAMIENTO DE FACTURAS
=========================================================

Este archivo contiene ejemplos de cómo usar tanto la nueva API refactorizada
como la API legacy para mantener compatibilidad con código existente.
"""

import sys
from pathlib import Path

# Agregar el directorio padre al path para poder importar src
sys.path.append(str(Path(__file__).parent.parent))

from src.facade.invoice_parser_facade import InvoiceParserFacade
# FacturaParser ahora es un alias de InvoiceParserFacade
from src.facade.invoice_parser_facade import InvoiceParserFacade as FacturaParser


def procesar_factura_nueva_api(xml_path: Path):
    """
    EJEMPLO DE USO - CÓDIGO NUEVO (RECOMENDADO)
    ============================================
    
    Ejemplo usando la nueva API refactorizada (RECOMENDADO).
    """
    # Crear la facade
    facade = InvoiceParserFacade(xml_path)
    
    # Cargar y validar XML
    if not facade.load():
        print(f"Error cargando {xml_path}")
        return None
    
    # Extraer todos los datos
    datos = facade.extract()
    
    if datos:
        print(f"✅ Factura procesada: {datos['numero_factura']}")
        print(f"   Total a pagar: ${datos['total_a_pagar']:,.2f}")
        print(f"   Concepto: {datos['concepto_principal']}")
        print(f"   Tipo: {datos['tipo_factura']}")
        return datos
    else:
        print(f"❌ Error extrayendo datos de {xml_path}")
        return None


def procesar_factura_legacy(xml_path: Path):
    """
    EJEMPLO DE USO - CÓDIGO LEGACY (COMPATIBILIDAD)
    ================================================
    
    Ejemplo usando la API antigua (para compatibilidad con código existente).
    
    NOTA: Esta forma es DEPRECADA pero funciona para no romper código existente.
    """
    # Usar FacturaParser como antes
    parser = FacturaParser(xml_path)
    
    if not parser.load():
        print(f"Error cargando {xml_path}")
        return None
    
    datos = parser.extract()
    
    if datos:
        print(f"✅ Factura procesada: {datos['numero_factura']}")
        print(f"   Total a pagar: ${datos['total_a_pagar']:,.2f}")
        return datos
    else:
        print("❌ Error extrayendo datos")
        return None


def procesar_con_componentes_personalizados(xml_path: Path):
    """
    EJEMPLO DE USO AVANZADO - INYECCIÓN DE DEPENDENCIAS
    ====================================================
    
    Ejemplo con componentes personalizados (para casos especiales).
    """

    from src.core.xml_parser import XMLParser
    from src.extraction.monetary_extractor import MonetaryExtractor

    # Crear componentes personalizados si es necesario
    xml_parser = XMLParser()
    monetary_extractor = MonetaryExtractor()

    # Inyectar en la facade (no hay TotalCalculator/AdjustmentDetector)
    facade = InvoiceParserFacade(
        xml_path,
        xml_parser=xml_parser,
        monetary_extractor=monetary_extractor
    )
    
    if facade.load():
        return facade.extract()
    return None


def analizar_factura_detalladamente(xml_path: Path):
    """
    EJEMPLO DE USO - ANÁLISIS DETALLADO
    ====================================
    
    Ejemplo obteniendo información detallada del procesamiento.
    """
    facade = InvoiceParserFacade(xml_path)
    
    if not facade.load():
        return None
    
    # Obtener resumen de procesamiento
    summary = facade.get_processing_summary()
    
    print("📊 RESUMEN DE PROCESAMIENTO")
    print(f"   XML: {summary['xml_path']}")
    print(f"   Total items: {summary['total_items']}")
    print(f"   Campos monetarios: {summary['monetary_fields']}")
    print("   Ajustes detectados: (funcionalidad removida)")
    
    # Extraer datos normales
    datos = facade.extract()
    
    return datos


def demo_todas_las_opciones():
    """
    Función de demostración que muestra todos los ejemplos de uso.
    """
    print("🧪 DEMOSTRACIÓN DE EJEMPLOS DE USO")
    print("=" * 50)
    
    # Ruta de ejemplo (cambiar por una ruta real para testing)
    xml_path = Path("ejemplo_factura.xml")
    
    if not xml_path.exists():
        print(f"⚠️  Archivo {xml_path} no encontrado para la demostración")
        print("   Para probar estos ejemplos, proporciona una ruta XML válida")
        return
    
    print("\n1️⃣ PROBANDO API NUEVA (RECOMENDADA):")
    print("-" * 40)
    resultado1 = procesar_factura_nueva_api(xml_path)
    
    print("\n2️⃣ PROBANDO API LEGACY (COMPATIBILIDAD):")
    print("-" * 45)
    resultado2 = procesar_factura_legacy(xml_path)
    
    print("\n3️⃣ PROBANDO COMPONENTES PERSONALIZADOS:")
    print("-" * 45)
    resultado3 = procesar_con_componentes_personalizados(xml_path)
    
    print("\n4️⃣ PROBANDO ANÁLISIS DETALLADO:")
    print("-" * 35)
    resultado4 = analizar_factura_detalladamente(xml_path)
    
    print("\n✅ DEMOSTRACIÓN COMPLETADA")
    return {
        'nueva_api': resultado1,
        'legacy_api': resultado2,
        'personalizado': resultado3,
        'detallado': resultado4
    }


if __name__ == "__main__":
    # Ejecutar este archivo directamente para ver la demostración.
    # Uso: python tests/test_invoice_usage_examples.py
    demo_todas_las_opciones()