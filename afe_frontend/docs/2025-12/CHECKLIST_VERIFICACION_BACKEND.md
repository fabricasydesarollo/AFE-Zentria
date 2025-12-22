# ✅ CHECKLIST DE VERIFICACIÓN - SINCRONIZACIÓN NOMBRE_PROVEEDOR

**Ejecutar HOYA en Backend para validar que todo está en orden**

---

## 🔍 VERIFICACIÓN RÁPIDA (5 minutos)

### Paso 1: ¿Existen los triggers?

```bash
# Conectar a BD
mysql -u root -p afe_backend

# Listar triggers
SHOW TRIGGERS;

# Buscar específicamente:
SHOW TRIGGERS LIKE '%sync%';
SHOW TRIGGERS LIKE '%proveedor%';
SHOW TRIGGERS LIKE '%asignacion%';
```

**Expected Output:**
```
sync_proveedor_nombre_on_update          (ON UPDATE proveedores)
sync_proveedor_nombre_on_create_asignacion (ON INSERT asignacion_nit)
```

**Status:**
- [ ] ✅ Ambos triggers existen
- [ ] ⚠️ Uno existe, otro falta
- [ ] ❌ Ninguno existe (CREAR INMEDIATAMENTE)

---

### Paso 2: ¿Los datos están sincronizados?

```sql
-- Encontrar desincronizaciones
SELECT 
  a.id,
  a.nit,
  a.nombre_proveedor AS asignacion_nombre,
  p.razon_social AS proveedor_nombre,
  (a.nombre_proveedor = p.razon_social) AS synchronized
FROM asignacion_nit_responsable a
JOIN proveedores p ON a.nit = p.nit
WHERE a.activo = true
AND a.nombre_proveedor != p.razon_social;
```

**Expected:** ✅ 0 filas (todo sincronizado)  
**Si retorna filas:** ❌ Hay desincronización

---

### Paso 3: ¿El trigger de UPDATE funciona?

```sql
-- 1. Seleccionar un proveedor
SELECT id, nit, razon_social FROM proveedores LIMIT 1;
-- Resultado: id=1, nit='830185449-0', razon_social='EMPRESA S.A.'

-- 2. Obtener su asignación
SELECT id, nombre_proveedor FROM asignacion_nit_responsable 
WHERE nit = '830185449-0' AND activo = true LIMIT 1;
-- Resultado: id=100, nombre_proveedor='EMPRESA S.A.'

-- 3. Editar el proveedor
UPDATE proveedores SET razon_social = 'NUEVA EMPRESA S.A.' WHERE id = 1;

-- 4. Verificar que se sincronizó automáticamente
SELECT nombre_proveedor FROM asignacion_nit_responsable 
WHERE nit = '830185449-0' AND activo = true LIMIT 1;
-- Expected: nombre_proveedor='NUEVA EMPRESA S.A.' ✅
-- Si sigue siendo 'EMPRESA S.A.': ❌ Trigger NO funciona
```

---

### Paso 4: ¿El trigger de INSERT funciona?

```sql
-- 1. Crear una nueva asignación
INSERT INTO asignacion_nit_responsable 
  (nit, responsable_id, area, nombre_proveedor, activo)
VALUES ('830185449-0', 1, 'Operaciones', NULL, true);

-- 2. Verificar que se llenó automáticamente
SELECT nombre_proveedor FROM asignacion_nit_responsable 
WHERE nit = '830185449-0' AND activo = true 
ORDER BY id DESC LIMIT 1;
-- Expected: 'EMPRESA S.A.' (copiado del proveedor) ✅
-- Si está NULL: ❌ Trigger NO funciona
```

---

## 📋 CHECKLIST FINAL

```
TRIGGERS:
[ ] sync_proveedor_nombre_on_update existe
[ ] sync_proveedor_nombre_on_create_asignacion existe

SINCRONIZACIÓN:
[ ] Todos los datos están en sync (query retorna 0 filas)

FUNCIONALIDAD:
[ ] UPDATE proveedor sincroniza nombre_proveedor ✅
[ ] INSERT asignacion sin nombre_proveedor lo copia ✅

INTEGRIDAD:
[ ] No hay NULL en nombre_proveedor cuando activo=true
[ ] Todos los NITs en asignacion_nit existen en proveedores
```

---

## 🚨 SI ALGO FALLA

### ❌ Los triggers no existen

**ACCIÓN:** Crear inmediatamente

Ver: `SINCRONIZACION_RAZON_SOCIAL.md` para código SQL

```bash
# Copiar y ejecutar los triggers desde ese documento
mysql afe_backend < triggers.sql
```

### ❌ Los datos están desincronizados

**ACCIÓN:** Sincronizar manualmente

```sql
-- SOLO ejecutar si hay desincronización
UPDATE asignacion_nit_responsable a
SET nombre_proveedor = (
  SELECT razon_social FROM proveedores p 
  WHERE p.nit = a.nit
)
WHERE nombre_proveedor != (
  SELECT razon_social FROM proveedores p 
  WHERE p.nit = a.nit
);

-- Verificar resultado
SELECT COUNT(*) FROM asignacion_nit_responsable a
JOIN proveedores p ON a.nit = p.nit
WHERE a.nombre_proveedor != p.razon_social;
-- Debe retornar: 0
```

### ❌ El trigger no funciona

**ACCIÓN:** Verificar sintaxis y recrear

```bash
# 1. Eliminar trigger incorrecto
DROP TRIGGER IF EXISTS sync_proveedor_nombre_on_update;

# 2. Crear versión correcta (ver documento SINCRONIZACION_RAZON_SOCIAL.md)
CREATE TRIGGER sync_proveedor_nombre_on_update
...
```

---

## 🧪 TESTING MANUAL

Después de verificar, hacer test end-to-end:

### Test 1: Frontend crea asignación

```bash
# Desde browser (F12 → Console)
fetch('/api/v1/asignacion-nit/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    nit: '830185449-0',
    nombre_proveedor: 'EMPRESA S.A.',
    responsable_id: 1,
    area: 'Operaciones'
  })
}).then(r => r.json()).then(d => console.log('✅ Creada:', d));
```

Expected: `nombre_proveedor: 'EMPRESA S.A.'` ✅

---

### Test 2: Backend sincroniza al cambiar proveedor

```javascript
// 1. Obtener asignación actual
fetch('/api/v1/asignacion-nit/?nit=830185449-0')
  .then(r => r.json())
  .then(d => console.log('ANTES:', d[0]?.nombre_proveedor));
// Resultado: "EMPRESA S.A."

// 2. Cambiar proveedor (en BD o UI)
// UPDATE proveedores SET razon_social = 'NUEVA EMPRESA' WHERE nit = '830185449-0'

// 3. Recargar asignación
fetch('/api/v1/asignacion-nit/?nit=830185449-0')
  .then(r => r.json())
  .then(d => console.log('DESPUÉS:', d[0]?.nombre_proveedor));
// Expected: "NUEVA EMPRESA" ✅
// Si sigue siendo "EMPRESA S.A.": ❌ Trigger no funciona
```

---

## 📊 RESUMEN

| Verificación | Comando | Expected | Status |
|--------------|---------|----------|--------|
| Triggers existen | `SHOW TRIGGERS LIKE '%sync%'` | 2 triggers | [ ] |
| Datos en sync | `SELECT ... WHERE != ...` | 0 filas | [ ] |
| UPDATE funciona | `UPDATE + SELECT` | Actualizado | [ ] |
| INSERT funciona | `INSERT + SELECT` | Copiado | [ ] |

---

## ✅ CONCLUSIÓN

Después de ejecutar este checklist:

- **Si TODO está ✅:** El sistema está listo, proceder con deployment
- **Si algo está ❌:** Crear/corregir triggers antes de deployment

**Criticidad:** ALTA - No deployar sin pasar este checklist

---

**Ejecutor:** Backend Team  
**Timeline:** Hoy  
**Reportar:** Arquitecto   
*Última actualización: 2025-12-15*
