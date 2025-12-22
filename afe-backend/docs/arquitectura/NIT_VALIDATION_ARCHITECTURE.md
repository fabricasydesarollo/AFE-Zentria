# Arquitectura de Validación y Normalización de NITs

## Resumen

Este documento describe la arquitectura para validación y normalización de NITs (Números de Identificación Tributaria) colombianos en el sistema AFE. La solución implementa el algoritmo oficial DIAN (Orden Administrativa N°4 del 27/10/1989) y proporciona un único punto de validación para todo el sistema.

## Contexto

Los NITs son identificadores tributarios colombianos que constan de:
- **9 dígitos numéricos**: Ej: `800185449`
- **1 dígito verificador (DV)**: Ej: `9` (calculado usando algoritmo DIAN)
- **Formato normalizado**: `XXXXXXXXX-D` Ej: `800185449-9`

Antes de esta refactorización, existía **código duplicado** en:
- `afe_frontend/src/utils/nit.ts` (nunca usado)
- `afe-backend/app/utils/nit_validator.py` (correctamente implementado)

## Arquitectura de Tres Módulos

```
┌─────────────────────────────────────────────────────────────────┐
│                         afe_frontend                             │
│  (React/TypeScript)                                             │
├─────────────────────────────────────────────────────────────────┤
│  AddNitDialog.tsx          → Validación en tiempo real          │
│  AddNitsBulkDialog.tsx     → Validación múltiple con feedback  │
│  nitValidation.service.ts  → Llamadas HTTP al backend           │
└────────────┬──────────────────────────────────────────────────┘
             │
             │ POST /email-config/validate-nit
             │ { nit: "800185449" }
             │
             ↓
┌─────────────────────────────────────────────────────────────────┐
│                          afe-backend                             │
│  (FastAPI/Python)                                               │
├─────────────────────────────────────────────────────────────────┤
│  router:  /email-config/validate-nit (NEW)                      │
│           ↓                                                      │
│  NitValidator.normalizar_nit()  → Valida y calcula DV          │
│           ↓                                                      │
│  Response: {                                                    │
│    is_valid: true,                                             │
│    nit_normalizado: "800185449-9",                             │
│    error: null                                                 │
│  }                                                              │
└────────────┬──────────────────────────────────────────────────┘
             │
             │ GET /api/v1/email-config/configuracion-extractor-public
             │ (devuelve NITs normalizados)
             │
             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    invoice_extractor                             │
│  (Python standalone)                                            │
├─────────────────────────────────────────────────────────────────┤
│  src/core/config.py                                             │
│  → Obtiene configuración del backend                            │
│  → Usa NITs normalizados para filtrado de correos              │
│  → Busca mensajes por NIT en asuntos/remitentes                │
└─────────────────────────────────────────────────────────────────┘
```

## Flujo de Validación de NIT

### 1. Usuario ingresa NIT en el frontend

```typescript
// AddNitDialog.tsx
usuario ingresa: "800185449"  o  "800185449-9"  o  "800.185.449"
```

### 2. Validación en tiempo real (debounced 500ms)

```typescript
// nitValidation.service.ts
await nitValidationService.validateNit("800185449")
  ↓
POST /email-config/validate-nit
  ↓
// Email config router (backend)
NitValidator.normalizar_nit("800185449")
  ↓
return {
  is_valid: true,
  nit_normalizado: "800185449-9",
  error: null
}
```

### 3. Frontend muestra feedback

```typescript
// AddNitDialog.tsx
✓ Chip verde: "NIT normalizado: 800185449-9"
✓ Botón "Agregar NIT" habilitado
✓ Usuario puede enviar
```

### 4. Backend almacena NIT normalizado

```python
# email_config router
crud.create_nit_configuracion(db, {
    nit: "800185449-9",  # ← Siempre normalizado
    cuenta_correo_id: 1,
    activo: True
})
```

### 5. invoice_extractor consume configuración

```python
# src/core/config.py
response = fetch_config_from_api(
    "/api/v1/email-config/configuracion-extractor-public"
)

# Obtiene:
{
  "users": [
    {
      "email": "facturacion@empresa.com",
      "nits": ["800185449-9", "900399741-7"],  # ← Normalizados
      "ventana_inicial_dias": 365,
      "ultima_ejecucion_exitosa": "2025-01-15T10:30:00Z"
    }
  ]
}
```

## Componentes Clave

### Backend: NitValidator (app/utils/nit_validator.py)

**Responsabilidades:**
- Calcular dígito verificador usando algoritmo DIAN
- Normalizar NITs a formato `XXXXXXXXX-D`
- Validar que el DV sea correcto
- Manejar múltiples formatos de entrada

**Métodos públicos:**
```python
NitValidator.calcular_digito_verificador(nit_sin_dv: str) -> str
  # Calcula DV usando serie DIAN [41, 37, 29, 23, 19, 17, 13, 7, 3]

NitValidator.normalizar_nit(nit: str) -> str
  # Retorna "XXXXXXXXX-D"

NitValidator.validar_nit(nit: str) -> Tuple[bool, str]
  # Retorna (es_válido, resultado_o_error)

NitValidator.es_nit_normalizado(nit: str) -> bool
  # Verifica si ya está en formato XXXXXXXXX-D
```

**Algoritmo DIAN:**
```
1. Tomar los 9 dígitos del NIT
2. Multiplicar por serie: [41, 37, 29, 23, 19, 17, 13, 7, 3]
3. Sumar todos los productos
4. Aplicar módulo 11 al resultado
5. Si residuo = 0 → DV = 0
   Si residuo = 1 → DV = 1
   Si residuo > 1 → DV = 11 - residuo
```

**Ejemplo:**
```
NIT: 800185449
Multiplicaciones:
  8×41=328  0×37=0   0×29=0   1×23=23  8×19=152  5×17=85  4×13=52  4×7=28  9×3=27
Suma: 328+0+0+23+152+85+52+28+27 = 695
Módulo 11: 695 % 11 = 3
DV: 11 - 3 = 8

RESULTADO: 800185449-8
```

### Backend: Endpoint /validate-nit

**Ruta:** `POST /api/v1/email-config/validate-nit`

**Request:**
```json
{
  "nit": "800185449"
}
```

**Response (válido):**
```json
{
  "is_valid": true,
  "nit_normalizado": "800185449-8",
  "error": null
}
```

**Response (inválido):**
```json
{
  "is_valid": false,
  "nit_normalizado": null,
  "error": "Dígito verificador incorrecto para NIT 800185449. Proporcionado: 9, Correcto: 8"
}
```

**Autenticación:** No requiere (diseñado para frontend público)

### Frontend: NitValidationService

**Responsabilidades:**
- Llamar endpoint `/validate-nit` del backend
- Manejar errores de conexión
- Debouncing para no sobrecargar API
- Validación básica en cliente antes de llamar servidor

**Métodos públicos:**
```typescript
async validateNit(nit: string): Promise<ValidationResult>
  // Valida un NIT individual

async validateMultipleNits(nits: string[]): Promise<ValidationResult[]>
  // Valida múltiples NITs en paralelo

isValidBasicFormat(nit: string): boolean
  // Validación básica sin llamar servidor
```

### Frontend: Componentes actualizados

#### AddNitDialog.tsx
- Muestra spinner mientras valida
- Chip verde con NIT normalizado si es válido
- Error icon rojo si es inválido
- Botón deshabilitado hasta que sea válido

#### AddNitsBulkDialog.tsx
- Valida múltiples NITs en paralelo
- Vista previa con indicadores de éxito/error
- Contador de NITs válidos/inválidos
- Botón deshabilitado si hay algún NIT inválido
- Usa NITs normalizados al agregar

## Beneficios de esta Arquitectura

### 1. Backend como única fuente de verdad
-  Un solo lugar donde se implementa el algoritmo DIAN
-  Si DIAN cambia el algoritmo, solo se actualiza en un lugar
-  Todos los clientes (frontend, invoice_extractor, APIs externas) usan la misma lógica

### 2. Validación robusta
-  El frontend no puede engañar la validación
-  NITs siempre se almacenan normalizados
-  Consistencia garantizada en toda la base de datos

### 3. UX mejorada
-  Validación en tiempo real mientras el usuario escribe
-  Feedback visual inmediato (spinner, checkmark, error)
-  Usuario ve exactamente qué NIT se almacenará
-  No hay sorpresas al guardar

### 4. Eliminación de deuda técnica
-  Removido código muerto (nit.ts en frontend)
-  Eliminados archivos legacy en invoice_extractor
-  Código duplicado centralizado en backend

### 5. Mejor experiencia 
-  Un endpoint REST documentado para validación
-  Código mantenible y fácil de entender
-  Servicios TypeScript tipados
-  Errores descriptivos para debugging

## Cambios de Implementación

### Frontend (afe_frontend)

**Archivos creados:**
- `src/services/nitValidation.service.ts` → Servicio de validación

**Archivos modificados:**
- `src/features/email-config/components/AddNitDialog.tsx`
- `src/features/email-config/components/AddNitsBulkDialog.tsx`

**Archivos eliminados:**
- `src/utils/nit.ts` (código muerto)

### Backend (afe-backend)

**Archivos creados:**
- Nuevos schemas en `app/schemas/email_config.py`

**Archivos modificados:**
- `app/api/v1/routers/email_config.py` → Nuevo endpoint `/validate-nit`

**Código NO modificado:**
- `app/utils/nit_validator.py` (ya estaba correcto)

### invoice_extractor

**Archivos eliminados:**
- `settings.json.backup` (legacy)
- `settings.json.OLD` (legacy)

**Archivos creados:**
- `settings.json.template` (documentación)

## Configuración de invoice_extractor

**Jerarquía de configuración (ACTUALIZADA):**

1. **API del backend** (Primary) 
   - Endpoint: `/api/v1/email-config/configuracion-extractor-public`
   - Siempre se intenta primero
   - Proporciona NITs normalizados
   - Incluye timestamps para extracción incremental

2. ~~**settings.json.backup** (Legacy - REMOVIDO)~~

3. ~~**settings.json.OLD** (Legacy - REMOVIDO)~~

**Nuevo flujo:**
```python
# src/core/config.py
def load_config(settings_path=None, use_api=True):
    if use_api:
        try:
            users_data = fetch_config_from_api(api_endpoint)
            return Settings(users=users_data, ...)
        except Exception:
            raise RuntimeError("API no disponible y no hay fallback")
    else:
        raise RuntimeError("Se requiere API para obtener configuración")
```

## Testing

### Backend Testing

```bash
# Test endpoint /validate-nit
POST http://localhost:8000/api/v1/email-config/validate-nit
Content-Type: application/json

{
  "nit": "800185449"
}
```

**Casos de prueba:**
- ✓ NIT válido sin DV: `"800185449"` → `"800185449-8"`
- ✓ NIT válido con DV: `"800185449-8"` → `"800185449-8"`
- ✓ NIT con puntos: `"800.185.449"` → `"800185449-8"`
- ✓ NIT con puntos y guión: `"800.185.449-8"` → `"800185449-8"`
- ✓ NIT inválido (DV incorrecto): `"800185449-9"` → error
- ✓ NIT vacío: `""` → error
- ✓ NIT con letras: `"ABC185449"` → error

### Frontend Testing

```typescript
// Validación individual
await nitService.validateNit("800185449")
// → { isValid: true, normalizedNit: "800185449-8" }

// Validación bulk
await nitService.validateMultipleNits(["800185449", "900399741"])
// → [{ isValid: true, ... }, { isValid: true, ... }]

// Validación básica (sin API)
nitService.isValidBasicFormat("800185449")
// → true
```

## Migraciones (si aplica)

No se requieren migraciones de base de datos. Los NITs ya almacenados permanecen igual. El endpoint `/validate-nit` es puramente de validación.

Si hay NITs sin DV almacenados en la BD:
```sql
-- Los NITs sin DV continuarán funcionando (compatibilidad)
-- El endpoint los normalizará dinámicamente
SELECT * FROM nit_configuracion WHERE nit NOT LIKE '%-_'
```

## Conclusiones

Esta arquitectura implementa un sistema robusto y mantenible de validación de NITs:

1. **Centralizado:** Backend es única fuente de verdad
2. **Robusta:** No se pueden almacenar NITs inválidos
3. **Escalable:** Fácil agregar nuevos clientes (APIs, apps externas)
4. **Mantenible:** Código duplicado eliminado
5. **UX-first:** Validación en tiempo real para usuario
6. **Profesional:** Sigue estándares empresariales

---

**Última actualización:** 30 de octubre de 2025

