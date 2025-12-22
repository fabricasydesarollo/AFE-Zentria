"""deprecate_auto_creation

Revision ID: 2025_12_15_deprecate
Revises: 20251214_cuarentena
Create Date: 2025-12-15

🔒 SEGURIDAD 2025-12-15: Depreca auto-creación de proveedores

MOTIVACIÓN:
La auto-creación de proveedores desde facturas electrónicas representa un riesgo
de seguridad, ya que permite que entidades no autorizadas se registren en el
sistema sin validación previa.

CAMBIOS IMPLEMENTADOS:
1. invoice_extractor: Ya NO crea proveedores automáticamente
   - Si el NIT no existe → factura va a cuarentena (proveedor_id=NULL)
   - Admin debe crear proveedor manualmente desde /proveedores

2. Backend: Eliminado ProviderManagementService (código legacy)
   - Solo creación manual desde UI/API
   - Validación y normalización obligatoria

3. Modelo Proveedor: Campos deprecated pero mantenidos
   - es_auto_creado: [DEPRECATED] Siempre False para nuevos proveedores
   - creado_automaticamente_en: [DEPRECATED] Siempre NULL
   - Se mantienen por auditoría histórica

FLUJO NUEVO:
1. Llega factura con NIT no registrado
2. proveedor_id = NULL
3. grupo_id = NULL
4. estado = "en_cuarentena"
5. Admin valida y crea proveedor desde /proveedores
6. Admin configura NIT en /email-config
7. Facturas futuras fluyen normalmente

NO HAY CAMBIOS EN BD:
Esta migración es solo documental. Los campos se mantienen en la estructura
de la tabla para preservar la integridad de los datos históricos.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_12_15_deprecate'
down_revision = '20251214_cuarentena'
branch_labels = None
depends_on = None


def upgrade():
    """
    No hay cambios estructurales en la BD.

    Los campos es_auto_creado y creado_automaticamente_en se mantienen
    por razones de auditoría histórica pero ya no se usan en el código.
    """
    # Actualizar comentarios de las columnas para marcar como DEPRECATED
    op.execute("""
        ALTER TABLE proveedores
        MODIFY COLUMN es_auto_creado BOOLEAN NOT NULL DEFAULT 0
        COMMENT '[DEPRECATED 2025-12-15] Flag auto-creación (ya no se usa, siempre False)'
    """)

    op.execute("""
        ALTER TABLE proveedores
        MODIFY COLUMN creado_automaticamente_en DATETIME NULL
        COMMENT '[DEPRECATED 2025-12-15] Timestamp auto-creación (ya no se usa, siempre NULL)'
    """)


def downgrade():
    """
    Revertir comentarios de columnas a su estado original.
    """
    op.execute("""
        ALTER TABLE proveedores
        MODIFY COLUMN es_auto_creado BOOLEAN NOT NULL DEFAULT 0
        COMMENT 'Flag indicador: True si fue auto-creado desde factura, False si manual'
    """)

    op.execute("""
        ALTER TABLE proveedores
        MODIFY COLUMN creado_automaticamente_en DATETIME NULL
        COMMENT 'Timestamp exacto de auto-creación desde factura (NULL si manual)'
    """)
