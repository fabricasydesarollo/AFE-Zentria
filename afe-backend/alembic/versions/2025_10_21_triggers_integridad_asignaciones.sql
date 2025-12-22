-- ============================================================================
-- TRIGGERS PARA INTEGRIDAD REFERENCIAL DE ASIGNACIONES
-- ============================================================================
-- Fecha: 2025-10-21
-- Nivel: ENTERPRISE - Garantías a nivel de base de datos
-- Propósito: Sincronización automática facturas ↔ asignaciones sin depender de código Python
-- ============================================================================

DELIMITER $$

-- ============================================================================
-- TRIGGER 1: Desasignar facturas cuando se elimina (soft delete) asignación
-- ============================================================================
-- Se ejecuta DESPUÉS de marcar asignación como inactiva
-- Garantiza que las facturas pierdan su responsable_id automáticamente
-- ============================================================================

DROP TRIGGER IF EXISTS after_asignacion_soft_delete$$

CREATE TRIGGER after_asignacion_soft_delete
AFTER UPDATE ON asignacion_nit_responsable
FOR EACH ROW
BEGIN
    -- Solo actuar cuando se marca como inactiva (soft delete)
    IF OLD.activo = TRUE AND NEW.activo = FALSE THEN

        -- Desasignar todas las facturas de este responsable
        UPDATE facturas
        SET responsable_id = NULL,
            actualizado_en = NOW()
        WHERE responsable_id = OLD.responsable_id;

        -- Log para auditoría (opcional - requiere tabla de logs)
        -- INSERT INTO audit_log (evento, detalle, timestamp)
        -- VALUES (
        --     'DESASIGNACION_AUTOMATICA',
        --     CONCAT('Trigger desasignó facturas del responsable ', OLD.responsable_id, ' por soft delete de asignación NIT ', OLD.nit),
        --     NOW()
        -- );

    END IF;
END$$


-- ============================================================================
-- TRIGGER 2: Asignar facturas cuando se crea/restaura asignación
-- ============================================================================
-- Se ejecuta DESPUÉS de crear o reactivar asignación
-- Garantiza que las facturas del NIT se asignen automáticamente
-- ============================================================================

DROP TRIGGER IF EXISTS after_asignacion_activate$$

CREATE TRIGGER after_asignacion_activate
AFTER INSERT ON asignacion_nit_responsable
FOR EACH ROW
BEGIN
    -- Solo actuar si la asignación está activa
    IF NEW.activo = TRUE THEN

        -- Asignar facturas de proveedores con ese NIT al responsable
        -- Usa LIKE para manejar dígito de verificación
        UPDATE facturas f
        INNER JOIN proveedores p ON f.proveedor_id = p.id
        SET f.responsable_id = NEW.responsable_id,
            f.actualizado_en = NOW()
        WHERE p.nit LIKE CONCAT(NEW.nit, '%')
          AND f.responsable_id IS NULL;  -- Solo asignar facturas sin responsable

    END IF;
END$$


-- ============================================================================
-- TRIGGER 3: Reasignar facturas cuando se restaura asignación
-- ============================================================================
-- Se ejecuta DESPUÉS de reactivar asignación (activo FALSE → TRUE)
-- Garantiza que las facturas vuelvan a asignarse al restaurar
-- ============================================================================

DROP TRIGGER IF EXISTS after_asignacion_restore$$

CREATE TRIGGER after_asignacion_restore
AFTER UPDATE ON asignacion_nit_responsable
FOR EACH ROW
BEGIN
    -- Solo actuar cuando se restaura (inactiva → activa)
    IF OLD.activo = FALSE AND NEW.activo = TRUE THEN

        -- Reasignar facturas de proveedores con ese NIT al responsable
        UPDATE facturas f
        INNER JOIN proveedores p ON f.proveedor_id = p.id
        SET f.responsable_id = NEW.responsable_id,
            f.actualizado_en = NOW()
        WHERE p.nit LIKE CONCAT(NEW.nit, '%')
          AND f.responsable_id IS NULL;  -- Solo reasignar facturas sin responsable

    END IF;
END$$

DELIMITER ;

-- ============================================================================
-- VERIFICACIÓN DE TRIGGERS
-- ============================================================================
-- Para verificar que los triggers se crearon correctamente:
-- SHOW TRIGGERS WHERE `Table` = 'asignacion_nit_responsable';
-- ============================================================================

-- ============================================================================
-- NOTAS DE IMPLEMENTACIÓN
-- ============================================================================
-- 1. Los triggers garantizan sincronización SIEMPRE, incluso si:
--    - El código Python tiene bugs
--    - Se hacen cambios manuales en SQL
--    - Se usa otro lenguaje/framework en el futuro
--
-- 2. Performance:
--    - Los triggers son muy eficientes (ejecutan en el mismo proceso MySQL)
--    - No hay overhead de red
--    - Usan los mismos índices que las queries normales
--
-- 3. Auditabilidad:
--    - Considera agregar tabla audit_log para rastrear cambios
--    - Los triggers pueden insertar logs automáticamente
--
-- 4. Testing:
--    - Probar crear asignación → verificar facturas asignadas
--    - Probar soft delete → verificar facturas desasignadas
--    - Probar restaurar → verificar facturas reasignadas
--
-- 5. Rollback:
--    - Para eliminar triggers: DROP TRIGGER IF EXISTS nombre_trigger;
--    - Los triggers no afectan datos existentes (solo nuevos cambios)
-- ============================================================================
