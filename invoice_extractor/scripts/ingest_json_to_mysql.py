import sys
import os
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Agregar src al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.deduplication import deduplicate_facturas

# Cargar variables del .env
load_dotenv()

# Obtener URL de conexión desde .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Crear el motor de conexión SQLAlchemy
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Leer facturas desde archivos
facturas_total = []

output_dir = 'output'
for nit_dir in os.listdir(output_dir):
    nit_path = os.path.join(output_dir, nit_dir)
    consolidado_path = os.path.join(nit_path, 'consolidado.json')
    if os.path.isdir(nit_path) and os.path.exists(consolidado_path):
        with open(consolidado_path, encoding='utf-8') as f:
            facturas = json.load(f)
            facturas_total.extend(facturas)

# Deduplicar facturas
facturas_total = deduplicate_facturas(facturas_total)

# Ejecutar inserts usando SQLAlchemy
insert_sql = text("""
    INSERT INTO facturas (
        numero_factura, cufe, fecha_emision, fecha_vencimiento,
        nit_proveedor, razon_social_proveedor,
        nit_cliente, razon_social_cliente,
        subtotal, iva, total_a_pagar,
        concepto_principal, concepto_normalizado, concepto_hash,
        items_resumen, orden_compra_numero, orden_compra_sap, tipo_factura,
        procesamiento_info, notas_adicionales,
        patron_recurrencia, confianza_automatica, factura_referencia_id, motivo_decision,
        version_algoritmo
    ) VALUES (
        :numero_factura, :cufe, :fecha_emision, :fecha_vencimiento,
        :nit_proveedor, :razon_social_proveedor,
        :nit_cliente, :razon_social_cliente,
        :subtotal, :iva, :total_a_pagar,
        :concepto_principal, :concepto_normalizado, :concepto_hash,
        :items_resumen, :orden_compra_numero, :orden_compra_sap, :tipo_factura,
        :procesamiento_info, :notas_adicionales,
        :patron_recurrencia, :confianza_automatica, :factura_referencia_id, :motivo_decision,
        :version_algoritmo
    )
    ON DUPLICATE KEY UPDATE
        total_a_pagar = VALUES(total_a_pagar),
        concepto_principal = VALUES(concepto_principal),
        concepto_normalizado = VALUES(concepto_normalizado),
        concepto_hash = VALUES(concepto_hash),
        items_resumen = VALUES(items_resumen),
        orden_compra_numero = VALUES(orden_compra_numero),
        orden_compra_sap = VALUES(orden_compra_sap),
        tipo_factura = VALUES(tipo_factura),
        procesamiento_info = VALUES(procesamiento_info),
        notas_adicionales = VALUES(notas_adicionales),
        version_algoritmo = VALUES(version_algoritmo)
""")

for factura in facturas_total:
    # Verificar si el proveedor existe
    check_proveedor_sql = text("""
        SELECT nit FROM proveedores WHERE nit = :nit_proveedor
    """)
    result = session.execute(check_proveedor_sql, {'nit_proveedor': factura['nit_proveedor']})
    proveedor_existe = result.scalar() is not None

    # Si el proveedor no existe, insertarlo
    if not proveedor_existe:
        insert_proveedor_sql = text("""
            INSERT INTO proveedores (nit, razon_social)
            VALUES (:nit, :razon_social)
        """)
        session.execute(insert_proveedor_sql, {
            'nit': factura['nit_proveedor'],
            'razon_social': factura['razon_social_proveedor']
        })

    # Preparar datos para insertar
    factura_params = {
        'numero_factura': factura['numero_factura'],
        'cufe': factura['cufe'],
        'fecha_emision': factura['fecha_emision'],
        'fecha_vencimiento': factura['fecha_vencimiento'],
        'nit_proveedor': factura['nit_proveedor'],
        'razon_social_proveedor': factura['razon_social_proveedor'],
        'nit_cliente': factura['nit_cliente'],
        'razon_social_cliente': factura['razon_social_cliente'],
        'subtotal': factura['subtotal'],
        'iva': factura['iva'],
        'total_a_pagar': factura['total_a_pagar'],

        
        #  NUEVOS CAMPOS PARA AUTOMATIZACIÓN 
        'concepto_principal': factura.get('concepto_principal'),
        'concepto_normalizado': factura.get('concepto_normalizado'),
        'concepto_hash': factura.get('concepto_hash'),
        'items_resumen': json.dumps(factura.get('items_resumen')) if factura.get('items_resumen') else None,
        'orden_compra_numero': factura.get('orden_compra', {}).get('numero_oc') if factura.get('orden_compra') else None,
        'orden_compra_sap': factura.get('orden_compra', {}).get('numero_sap') if factura.get('orden_compra') else None,
        'tipo_factura': factura.get('tipo_factura'),
        'procesamiento_info': json.dumps(factura.get('procesamiento_info')) if factura.get('procesamiento_info') else None,
        'notas_adicionales': json.dumps(factura.get('notas_adicionales')) if factura.get('notas_adicionales') else None,
        'patron_recurrencia': factura.get('patron_recurrencia'),
        'confianza_automatica': factura.get('confianza_automatica'),
        'factura_referencia_id': factura.get('factura_referencia_id'),
        'motivo_decision': factura.get('motivo_decision'),

        'version_algoritmo': factura.get('procesamiento_info', {}).get('version_algoritmo') if factura.get('procesamiento_info') else None,
    }
    
    # Insertar la factura
    session.execute(insert_sql, factura_params)

# Confirmar los cambios y cerrar sesión
session.commit()
session.close()
