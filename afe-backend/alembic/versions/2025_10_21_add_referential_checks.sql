-- ============================================================================
-- CONSTRAINTS ADICIONALES PARA INTEGRIDAD REFERENCIAL
-- ============================================================================
-- Fecha: 2025-10-21
-- Nivel: ENTERPRISE - Constraints de validación
-- ============================================================================

-- Agregar índice compuesto para optimizar queries de sincronización
CREATE INDEX IF NOT EXISTS idx_facturas_responsable_proveedor
ON facturas(responsable_id, proveedor_id);

-- Agregar índice en proveedores.nit para queries LIKE
CREATE INDEX IF NOT EXISTS idx_proveedores_nit_prefix
ON proveedores(nit(15));

-- Agregar índice compuesto en asignaciones para queries de actividad
CREATE INDEX IF NOT EXISTS idx_asignacion_responsable_activo
ON asignacion_nit_responsable(responsable_id, activo);

-- ============================================================================
-- NOTAS
-- ============================================================================
-- Estos índices mejoran significativamente la performance de:
-- 1. Queries de sincronización en triggers
-- 2. Verificación de facturas huérfanas
-- 3. Consultas de facturas por responsable
-- 4. Búsquedas de proveedores por NIT con LIKE
-- ============================================================================
