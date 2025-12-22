# 🔄 ESTRATEGIA DE SINCRONIZACIÓN DE RAZÓN SOCIAL

**Fecha:** 15 de Diciembre de 2025  
**Versión:** 1.0 (Architecture Design)

---

## 📋 PROBLEMA IDENTIFICADO

### Estado Actual del Sistema

```
TABLA PROVEEDORES (Master Data)
├─ id: 1
├─ nit: "830185449-0"
├─ razon_social: "EMPRESA S.A."      ← FUENTE DE VERDAD
├─ area: "Operaciones"
└─ activo: true

TABLA ASIGNACION_NIT_RESPONSABLE (Relación)
├─ id: 100
├─ nit: "830185449-0"
├─ nombre_proveedor: "EMPRESA S.A."  ← COPIA/CACHÉ (duplicado)
├─ responsable_id: 5
└─ activo: true
```

### ❌ PROBLEMA DE DESINCRONIZACIÓN

```
ESCENARIO: Admin edita Proveedor

ANTES:
Proveedor.razon_social = "EMPRESA S.A."
AsignacionNit.nombre_proveedor = "EMPRESA S.A."
✅ Sincronizados

DESPUÉS (Si no hay triggers):
Proveedor.razon_social = "NUEVA EMPRESA S.A." ← Cambio
AsignacionNit.nombre_proveedor = "EMPRESA S.A."  ← DESINCRONIZADO ❌

IMPACTO:
❌ Reportes muestran nombre incorrecto
❌ Frontend muestra datos inconsistentes
❌ Auditoría fallida
❌ Confusión en trazabilidad
```

---

## ✅ SOLUCIÓN: PRINCIPIO SSOT (Single Source of Truth)

### **Arquitectura Correcta**

```
┌──────────────────────────────────────────────────────────┐
│                    DATOS MAESTROS                        │
├──────────────────────────────────────────────────────────┤
│                   PROVEEDORES                            │
│  ├─ razon_social ← ÚNICA FUENTE DE VERDAD               │
│  └─ (Cambios aquí se propagan automáticamente)           │
└──────────────────────────────────────────────────────────┘
                         ↓ TRIGGER/CASCADA
┌──────────────────────────────────────────────────────────┐
│             DATOS RELACIONALES                           │
├──────────────────────────────────────────────────────────┤
│      ASIGNACION_NIT_RESPONSABLE                          │
│  ├─ nombre_proveedor ← COPIA (mantenida en sync)        │
│  └─ (Se actualiza automáticamente por triggers)          │
└──────────────────────────────────────────────────────────┘
```

---

## 🛠️ IMPLEMENTACIÓN TÉCNICA

### **1. LADO BACKEND (Base de Datos)**

#### Opción A: Trigger SQL (Recomendado)

```sql
-- Crear trigger para sincronizar cambios en Proveedor
CREATE OR REPLACE TRIGGER sync_proveedor_nombre_on_update
AFTER UPDATE OF razon_social ON proveedores
FOR EACH ROW
BEGIN
  -- Si cambió razon_social, actualizar en asignaciones
  UPDATE asignacion_nit_responsable
  SET nombre_proveedor = NEW.razon_social,
      actualizado_en = NOW()
  WHERE nit = NEW.nit AND activo = true;
END;

-- Crear trigger para validar y copiar al crear asignación
CREATE OR REPLACE TRIGGER sync_proveedor_nombre_on_create_asignacion
BEFORE INSERT ON asignacion_nit_responsable
FOR EACH ROW
BEGIN
  -- Si no incluye nombre_proveedor, obtenerlo del proveedor
  IF NEW.nombre_proveedor IS NULL OR NEW.nombre_proveedor = '' THEN
    SELECT razon_social INTO NEW.nombre_proveedor
    FROM proveedores
    WHERE nit = NEW.nit AND activo = true
    LIMIT 1;
  END IF;
  
  -- Validar que el NIT exista
  IF NOT EXISTS (SELECT 1 FROM proveedores WHERE nit = NEW.nit) THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'El NIT no existe en la tabla de proveedores';
  END IF;
END;
```

#### Opción B: ORM Listener (SQLAlchemy)

```python
# app/models/events.py
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.models import Proveedor, AsignacionNitResponsable

@event.listens_for(Proveedor, 'after_update')
def sync_nombre_proveedor_on_update(mapper, connection, target):
    """Sincronizar nombre_proveedor cuando cambia razon_social"""
    if hasattr(target, 'razon_social'):
        connection.execute(
            AsignacionNitResponsable.__table__.update()
            .where(AsignacionNitResponsable.nit == target.nit)
            .values(nombre_proveedor=target.razon_social)
        )
```

---

### **2. LADO FRONTEND (Lógica de Sincronización)**

#### Paso 1: Crear Asignación (Sincronización al Crear)

```typescript
// src/features/proveedores/tabs/AsignacionesTab.tsx

const handleSubmit = async () => {
  // ... validaciones ...
  
  const proveedor = proveedores.find((p) => p.id === formData.proveedor_id);
  
  if (!proveedor) {
    setError('Proveedor no encontrado');
    return;
  }

  try {
    // ✅ CORRECTO: Enviar razon_social como nombre_proveedor
    // El backend lo validará y sincronizará
    await dispatch(
      createAsignacionThunk({
        nit: proveedor.nit,
        nombre_proveedor: proveedor.razon_social, // ← SINCRONIZACIÓN AL CREAR
        responsable_id: formData.responsable_id,
        area: proveedor.area,
        permitir_aprobacion_automatica: true,
      })
    ).unwrap();

    setSuccess('Asignación creada exitosamente');
    
    // Recargar asignaciones para ver cambios sincronizados
    await dispatch(fetchAsignaciones({ skip: 0, limit: 1000 }));
    
    handleCloseDialog();
  } catch (err) {
    // Manejo de errores...
  }
};
```

#### Paso 2: Editar Proveedor (Disparar Sincronización)

```typescript
// src/features/proveedores/tabs/ProveedoresTab.tsx

const handleSubmit = async () => {
  try {
    if (editMode && selectedProveedor) {
      // ✅ Al editar proveedor, cambios en razon_social
      // se propagarán automáticamente a asignaciones (backend)
      await dispatch(
        updateProveedorThunk({ id: selectedProveedor.id, data: formData })
      ).unwrap();
      
      // Recargar ASIGNACIONES también (porque nombre_proveedor pudo cambiar)
      await dispatch(fetchAsignaciones({ skip: 0, limit: 1000 }));
      
      setDialogOpen(false);
    } else {
      // Crear nuevo proveedor
      await dispatch(createProveedorThunk(formData)).unwrap();
      setDialogOpen(false);
    }
    
    // Recargar lista de proveedores
    await dispatch(fetchProveedores({ skip: 0, limit: 1000 }));
  } catch (error) {
    // Manejo de errores...
  }
};
```

#### Paso 3: Mostrar Asignaciones (Lectura Sincronizada)

```typescript
// src/features/proveedores/tabs/AsignacionesTab.tsx

// ✅ CORRECTO: nombre_proveedor viene del backend (sincronizado)
return (
  <TableCell>
    <Typography variant="body2" fontWeight={500}>
      {asignacion.nombre_proveedor} {/* ← Siempre sincronizado con Proveedor */}
    </Typography>
  </TableCell>
);
```

#### Paso 4: Transformación de Datos (Otras vistas)

```typescript
// src/features/proveedores/tabs/PorResponsableTab.tsx

// ✅ CORRECTO: Usar nombre_proveedor del asignacion (que ya está sincronizado)
const transformedData = {
  responsable_id: data.responsable_id,
  responsable: data.responsable,
  proveedores: data.asignaciones.map((asig) => ({
    asignacion_id: asig.id,
    nit: asig.nit,
    razon_social: asig.nombre_proveedor, // ← Ya sincronizado
    area: asig.area,
    activo: asig.activo,
  })),
  total: data.total,
};
```

---

## 🔄 FLUJO DE SINCRONIZACIÓN COMPLETO

### **Escenario 1: Crear Nueva Asignación**

```
1. Usuario selecciona Proveedor con:
   ├─ nit: "830185449-0"
   └─ razon_social: "EMPRESA S.A."

2. Frontend envía POST /asignacion-nit/:
   ├─ nit: "830185449-0"
   ├─ nombre_proveedor: "EMPRESA S.A." ← COPIA EXPLÍCITA
   └─ responsable_id: 5

3. Backend recibe y:
   ├─ Valida que NIT existe en Proveedor ✅
   ├─ Guarda nombre_proveedor en BD ✅
   └─ Activa triggers para mantener en sync ✅

4. Frontend recarga AsignacionesTab:
   └─ Muestra nombre_proveedor (sincronizado)
```

### **Escenario 2: Editar Razón Social de Proveedor**

```
1. Usuario edita Proveedor:
   ├─ razon_social: "EMPRESA S.A." → "NUEVA EMPRESA S.A."
   └─ Envía PUT /proveedores/1

2. Backend recibe y:
   ├─ Actualiza Proveedor.razon_social ✅
   ├─ TRIGGER: Ejecuta UPDATE en AsignacionNit ✅
   │  └─ SET nombre_proveedor = "NUEVA EMPRESA S.A."
   └─ WHERE nit = "830185449-0"

3. Frontend recargar AsignacionesTab:
   └─ Muestra nombre_proveedor = "NUEVA EMPRESA S.A." (sincronizado)
```

### **Escenario 3: Búsqueda/Filtro**

```
1. Usuario busca por "NUEVA EMPRESA":
   ├─ Busca en Proveedor.razon_social ✅
   └─ También busca en AsignacionNit.nombre_proveedor ✅

2. Resultado: Consistente porque:
   ├─ Proveedor.razon_social = "NUEVA EMPRESA S.A."
   ├─ AsignacionNit.nombre_proveedor = "NUEVA EMPRESA S.A."
   └─ Ambas en SYNC
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Backend

- [ ] Crear/Verificar triggers en BD
- [ ] Validar que INSERT asignacion_nit copia razon_social correctamente
- [ ] Verificar que UPDATE proveedores sincroniza con asignaciones
- [ ] Probar: Editar proveedor → nombre_proveedor actualizado en asignaciones
- [ ] Tests: CREATE asignación sin nombre_proveedor → Se copia automáticamente
- [ ] Tests: UPDATE proveedor.razon_social → Se propaga a asignaciones

### Frontend

- [ ] Enviar `nombre_proveedor: proveedor.razon_social` al crear asignación ✅
- [ ] Recargar asignaciones después de crear/editar proveedor ✅
- [ ] Mostrar `nombre_proveedor` en tablas (siempre sincronizado) ✅
- [ ] Usar `nombre_proveedor` en transformaciones de datos ✅
- [ ] Tests: Crear asignación → nombre_proveedor = razon_social ✅
- [ ] Tests: Editar proveedor → nombre_proveedor actualizado en vista

---

## 🧪 PRUEBAS DE VALIDACIÓN

### Test 1: Sincronización al Crear

```javascript
// En browser console (F12)
const proveedor = { nit: "830185449-0", razon_social: "EMPRESA S.A." };
const response = await fetch('/api/v1/asignacion-nit/', {
  method: 'POST',
  body: JSON.stringify({
    nit: proveedor.nit,
    nombre_proveedor: proveedor.razon_social,
    responsable_id: 1
  })
});
const asignacion = await response.json();
console.assert(
  asignacion.nombre_proveedor === "EMPRESA S.A.",
  "nombre_proveedor debe estar sincronizado"
);
```

### Test 2: Sincronización al Editar Proveedor

```javascript
// 1. Obtener asignación original
const asignaciones = await fetch('/api/v1/asignacion-nit/?nit=830185449-0')
  .then(r => r.json());
console.log("Nombre antes:", asignaciones[0].nombre_proveedor);

// 2. Editar proveedor
await fetch('/api/v1/proveedores/1', {
  method: 'PUT',
  body: JSON.stringify({ razon_social: "NUEVA EMPRESA S.A." })
});

// 3. Verificar sincronización
const asignacionesActualizadas = await fetch('/api/v1/asignacion-nit/?nit=830185449-0')
  .then(r => r.json());
console.assert(
  asignacionesActualizadas[0].nombre_proveedor === "NUEVA EMPRESA S.A.",
  "nombre_proveedor debe estar actualizado después de editar proveedor"
);
```

---

## 📊 TABLA DE SINCRONIZACIÓN

| Operación | Frontend | Backend | Resultado |
|-----------|----------|---------|-----------|
| Crear Asignación | Envía nombre_proveedor | Copia y valida | ✅ Sincronizado |
| Editar Proveedor.razon_social | Recarga asignaciones | Trigger actualiza | ✅ Sincronizado |
| Eliminar Proveedor | N/A | Cascada o soft delete | ✅ Integridad |
| Búsqueda | Busca en ambas tablas | Índices en razon_social | ✅ Consistente |
| Reportes | Lee nombre_proveedor | Datos actualizados | ✅ Correcto |

---

## 🚀 IMPLEMENTACIÓN EN FASES

### Fase 1: Backend (CRÍTICO)
```
Semana 1:
[ ] Crear triggers en BD
[ ] Validar sincronización
[ ] Tests automatizados
```

### Fase 2: Frontend (VALIDACIÓN)
```
Semana 1-2:
[ ] Verificar que frontend ya envía nombre_proveedor ✅
[ ] Recargar asignaciones después de crear proveedor ✅
[ ] Validación manual en navegador ✅
```

### Fase 3: Testing (VERIFICACIÓN)
```
Semana 2:
[ ] Testing e2e completo
[ ] Validación en staging
[ ] Monitoreo post-deployment
```

---

## 🔒 GARANTÍAS

✅ **Integridad Referencial:** FK aseguran que NITs existen  
✅ **Consistencia:** Triggers mantienen SSOT  
✅ **Trazabilidad:** Auditoría de cambios preservada  
✅ **Performance:** Caché (nombre_proveedor) evita JOINs costosos  
✅ **Backward Compatibility:** API sigue funcionando  

---

## 📝 CONCLUSIÓN

**La solución es:**
1. ✅ Usar `Proveedor.razon_social` como ÚNICA FUENTE DE VERDAD
2. ✅ Mantener `AsignacionNit.nombre_proveedor` como CACHÉ sincronizado
3. ✅ Usar triggers en BD para sincronización automática
4. ✅ Recargar datos en frontend después de cambios
5. ✅ Buscar/filtrar en ambas tablas para consistencia

**No removemos `nombre_proveedor` de `AsignacionNit`, sino que lo mantenemos SINCRONIZADO.**

---

**Status:** 🔄 DISEÑO ARQUITECTÓNICO COMPLETADO  
**Próximo Paso:** Implementar triggers en BD  
*Última actualización: 2025-12-15*
