"""create_grupos_table_multitenant

Revision ID: 9611a5a6b002
Revises: 445be0be5974
Create Date: 2025-12-02 14:27:47.417061

Crea la tabla grupos para arquitectura multi-tenant con jerarquía.
Incluye datos iniciales: AVIDANTI (padre) y CAM, CAI, CASM (hijos).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9611a5a6b002'
down_revision: Union[str, Sequence[str], None] = '445be0be5974'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea tabla grupos con estructura jerárquica y datos iniciales.
    """
    # Crear tabla grupos
    op.create_table(
        'grupos',
        
        # ==================== PRIMARY KEY ====================
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        
        # ==================== IDENTIFICACIÓN ====================
        sa.Column('nombre', sa.String(150), nullable=False, comment='Nombre del grupo/sede'),
        sa.Column('codigo_corto', sa.String(20), nullable=False, unique=True, comment='Código único (CAM, CAI, etc.)'),
        sa.Column('descripcion', sa.Text(), nullable=True, comment='Descripción detallada'),
        
        # ==================== JERARQUÍA ====================
        sa.Column('grupo_padre_id', sa.BigInteger(), nullable=True, comment='FK al grupo padre (NULL si es raíz)'),
        sa.Column('nivel', sa.Integer(), nullable=False, default=1, comment='Nivel en jerarquía (1=raíz, 2=hijo, etc.)'),
        sa.Column('ruta_jerarquica', sa.String(500), nullable=True, comment='Ruta completa: "1/5/12" para navegación'),
        
        # ==================== CONFIGURACIÓN ====================
        sa.Column('correos_corporativos', sa.JSON(), nullable=True, comment='Array de correos asociados'),
        sa.Column('permite_subsedes', sa.Boolean(), nullable=False, default=True, comment='¿Puede tener hijos?'),
        sa.Column('max_nivel_subsedes', sa.Integer(), nullable=False, default=3, comment='Profundidad máxima'),
        
        # ==================== ESTADO ====================
        sa.Column('activo', sa.Boolean(), nullable=False, default=True, server_default='1', comment='Estado activo/inactivo'),
        sa.Column('eliminado', sa.Boolean(), nullable=False, default=False, server_default='0', comment='Soft delete'),
        sa.Column('fecha_eliminacion', sa.DateTime(timezone=True), nullable=True, comment='Cuándo se eliminó'),
        sa.Column('eliminado_por', sa.String(255), nullable=True, comment='Usuario que eliminó'),
        
        # ==================== AUDITORÍA ====================
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('creado_por', sa.String(255), nullable=False, default='SYSTEM'),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('actualizado_por', sa.String(255), nullable=True),
        
        # ==================== CONSTRAINTS ====================
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['grupo_padre_id'], ['grupos.id'], name='fk_grupo_padre'),
        # NOTE: MySQL no permite CHECK constraints en columnas AUTO_INCREMENT
        # La validación id != grupo_padre_id se hace a nivel de aplicación
    )
    
    # Crear índices
    op.create_index('idx_grupo_padre', 'grupos', ['grupo_padre_id'])
    op.create_index('idx_grupo_activo_eliminado', 'grupos', ['activo', 'eliminado'])
    op.create_index('idx_grupo_ruta', 'grupos', ['ruta_jerarquica'])
    op.create_index('idx_grupo_codigo', 'grupos', ['codigo_corto'])
    
    # ==================== DATOS INICIALES ====================
    
    # Insertar grupo raíz: AVIDANTI
    op.execute("""
        INSERT INTO grupos (id, nombre, codigo_corto, descripcion, grupo_padre_id, nivel, ruta_jerarquica, 
                           correos_corporativos, permite_subsedes, max_nivel_subsedes, activo, creado_por)
        VALUES (1, 'AVIDANTI', 'AVID', 'Clínica Avidanti - Grupo Principal', 
                NULL, 1, '1', 
                '["facturacionelectronica@avidanti.com"]', 
                1, 3, 1, 'SYSTEM')
    """)
    
    # Insertar sub-sedes de AVIDANTI
    op.execute("""
        INSERT INTO grupos (id, nombre, codigo_corto, descripcion, grupo_padre_id, nivel, ruta_jerarquica,
                           correos_corporativos, permite_subsedes, max_nivel_subsedes, activo, creado_por)
        VALUES
        (5, 'CLINICA AVIDANTI MANIZALES', 'CAM', 'Clínica Avidanti - Sede Manizales',
         1, 2, '1/5',
         '["facturacionelectronica@avidanti.com"]',
         1, 3, 1, 'SYSTEM'),

        (6, 'CLINICA AVIDANTI IBAGUE', 'CAI', 'Clínica Avidanti - Sede Ibagué',
         1, 2, '1/6',
         '["facturacionelectronica@avidanti.com"]',
         1, 3, 1, 'SYSTEM'),

        (7, 'CLINICA AVIDANTI SANTA MARTA', 'CASM', 'Clínica Avidanti - Sede Santa Marta',
         1, 2, '1/7',
         '["facturacionelectronica@avidanti.com"]',
         1, 3, 1, 'SYSTEM')
    """)
    
    # Insertar otras sedes principales (sin hijos por ahora)
    op.execute("""
        INSERT INTO grupos (id, nombre, codigo_corto, descripcion, grupo_padre_id, nivel, ruta_jerarquica,
                           correos_corporativos, permite_subsedes, max_nivel_subsedes, activo, creado_por)
        VALUES
        (2, 'ADC', 'ADC', 'Angiografía de Colombia',
         NULL, 1, '2',
         '["facturacion.electronica@angiografiadecolombia.com"]',
         1, 3, 1, 'SYSTEM'),

        (3, 'DSZF', 'DSZF', 'Diacorsoacha Zona Franca',
         NULL, 1, '3',
         '["diacorsoacha@avidanti.com"]',
         1, 3, 1, 'SYSTEM'),

        (4, 'CAA', 'CAA', 'Armenia',
         NULL, 1, '4',
         '["facturacionarmenia@avidanti.com"]',
         1, 3, 1, 'SYSTEM')
    """)


def downgrade() -> None:
    """
    Elimina tabla grupos y todos sus datos.
    """
    op.drop_index('idx_grupo_codigo', table_name='grupos')
    op.drop_index('idx_grupo_ruta', table_name='grupos')
    op.drop_index('idx_grupo_activo_eliminado', table_name='grupos')
    op.drop_index('idx_grupo_padre', table_name='grupos')
    op.drop_table('grupos')
