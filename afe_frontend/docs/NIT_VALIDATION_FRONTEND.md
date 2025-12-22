# Validación de NITs en el Frontend

## Resumen

El frontend de AFE implementa validación de NITs en tiempo real integrándose con el backend. Los componentes de diálogo ahora muestran feedback visual instantáneo y normalizan NITs automáticamente.

## Arquitectura

### Servicio: nitValidation.service.ts

**Ubicación:** `src/services/nitValidation.service.ts`

**Responsabilidades:**
- Comunicación HTTP con el backend
- Validación básica en cliente (antes de enviar)
- Manejo de errores de red
- Tipado TypeScript de respuestas

**Interfaz pública:**

```typescript
interface ValidationResult {
  isValid: boolean;
  normalizedNit?: string;
  errorMessage?: string;
}

class NitValidationService {
  async validateNit(nit: string): Promise<ValidationResult>
  async validateMultipleNits(nits: string[]): Promise<ValidationResult[]>
  isValidBasicFormat(nit: string): boolean
}
```

**Ejemplo de uso:**

```typescript
import nitValidationService from '@/services/nitValidation.service';

// Validar un NIT
const result = await nitValidationService.validateNit('800185449');
if (result.isValid) {
  console.log(`NIT válido: ${result.normalizedNit}`); // 800185449-8
} else {
  console.error(`Error: ${result.errorMessage}`);
}

// Validar múltiples NITs
const results = await nitValidationService.validateMultipleNits([
  '800185449',
  '900399741',
  'INVALIDO'
]);
// → [
//   { isValid: true, normalizedNit: '800185449-8' },
//   { isValid: true, normalizedNit: '900399741-7' },
//   { isValid: false, errorMessage: '...' }
// ]
```

## Componentes

### AddNitDialog.tsx

**Ubicación:** `src/features/email-config/components/AddNitDialog.tsx`

**Características:**
- ✅ Validación en tiempo real (debounced 500ms)
- ✅ Spinner mientras valida
- ✅ Checkmark verde si es válido
- ✅ Error icon rojo si es inválido
- ✅ Chip mostrando NIT normalizado
- ✅ Botón deshabilitado hasta ser válido

**Props:**
```typescript
interface Props {
  open: boolean;           // Dialog abierto/cerrado
  onClose: () => void;     // Callback al cerrar
  cuentaId: number;        // ID de cuenta a agregar NIT
  onSuccess: () => void;   // Callback al agregar exitosamente
}
```

**Flujo:**
```
Usuario escribe NIT
  ↓ (después de 500ms)
Llamar nitValidationService.validateNit()
  ↓
Backend retorna validación
  ↓
Mostrar feedback visual
  ↓
Si válido → Habilitar botón "Agregar NIT"
Si inválido → Mostrar error, deshabilitar botón
```

**Estados visuales:**

| Estado | Icono | Color | Mensaje |
|--------|-------|-------|---------|
| Escribiendo | - | - | Helper text |
| Validando | Spinner | - | "Validando NIT..." |
| Válido | ✓ | Verde | Chip: "NIT normalizado: 800185449-8" |
| Inválido | ✗ | Rojo | Error message del backend |

### AddNitsBulkDialog.tsx

**Ubicación:** `src/features/email-config/components/AddNitsBulkDialog.tsx`

**Características:**
- ✅ Validación de múltiples NITs en paralelo
- ✅ Vista previa con indicadores de validez
- ✅ Contador de "X/Y válidos"
- ✅ Botón solo habilitado si todos son válidos
- ✅ Acepta NITs separados por comas, espacios o saltos de línea

**Flujo de validación bulk:**

```
Usuario pega NITs en textarea
  ↓
Parsear (split por separadores)
  ↓ (después de 800ms)
Validar todos en paralelo (Promise.all)
  ↓
Actualizar mapa de validaciones
  ↓
Mostrar vista previa con indicadores
  ↓
Si alguno es inválido → Deshabilitar botón
Si todos válidos → Habilitar botón
```

**Ejemplo visual:**

```
Vista previa (5/7 válidos):

✓ 800185449-8     ✓ 900399741-7     ✗ INVALIDO     ✓ 823000999-0
✗ 12345           ✓ 800058607-4     +2 más
```

**Instrucciones mostradas:**
- Acepta NITs con o sin dígito verificador (DV)
- Se normalizarán automáticamente al formato XXXXXXXXX-D
- Los NITs duplicados se ignorarán automáticamente

## Flujo completo

### Diagrama de secuencia

```
┌────────────┐              ┌──────────────────────┐              ┌────────────┐
│  Usuario   │              │   AddNitDialog       │              │  Backend   │
└─────┬──────┘              └──────────┬───────────┘              └─────┬──────┘
      │                                │                                 │
      │ Abre dialog                     │                                 │
      ├───────────────────────────────→│                                 │
      │                                │                                 │
      │ Escribe "800185449"            │                                 │
      ├───────────────────────────────→│                                 │
      │                                │ [debounce 500ms]                │
      │                                ├─────────────────────────────────→
      │                                │ POST /validate-nit              │
      │                                │                                 │
      │                                │                  Valida DIAN   │
      │                                │←─────────────────────────────────
      │                                │ { is_valid: true,              │
      │                                │   nit_normalizado: "800185449-8"}
      │ Muestra: ✓ NIT normalizado     │                                 │
      │ 800185449-8                    │                                 │
      │←───────────────────────────────┤                                 │
      │                                │                                 │
      │ Click "Agregar NIT"            │                                 │
      ├───────────────────────────────→│                                 │
      │                                │ Usa NIT normalizado             │
      │                                ├─────────────────────────────────→
      │                                │ POST /nits                      │
      │                                │ { nit: "800185449-8", ... }    │
      │                                │                                 │
      │                                │          Crea en BD             │
      │                                │←─────────────────────────────────
      │ ✓ Éxito                        │                                 │
      │←───────────────────────────────┤                                 │
      │ Dialog cierra                  │                                 │
      └────────────────────────────────┘                                 │
```

## Manejo de Errores

### Validación fallida (NIT inválido)

```typescript
// Usuario escribe: "800185449-9" (DV incorrecto)
// Backend retorna:
{
  is_valid: false,
  nit_normalizado: null,
  error: "Dígito verificador incorrecto para NIT 800185449. Proporcionado: 9, Correcto: 8"
}

// Frontend muestra:
- Error icon rojo
- Helper text rojo: "Dígito verificador incorrecto..."
- Botón deshabilitado
```

### Error de red

```typescript
// Si el backend no responde:
{
  isValid: false,
  errorMessage: "Error al validar NIT. Intente nuevamente."
}

// Frontend muestra:
- Error icon rojo
- Helper text: "Error al validar NIT. Intente nuevamente."
```

## Performance

### Optimizaciones implementadas

1. **Debouncing:**
   - AddNitDialog: 500ms (usuario normal)
   - AddNitsBulkDialog: 800ms (validar múltiples)

2. **Validación paralela:**
   ```typescript
   // En lugar de:
   for (const nit of nits) {
     await validateNit(nit);  // Secuencial
   }

   // Se hace:
   await Promise.all(nits.map(nit => validateNit(nit)))  // Paralelo
   ```

3. **No re-validar innecesariamente:**
   - Solo valida si el NIT cambió
   - useEffect tiene dependencia `[nitValue]`

### Límites

- Máximo 20 NITs mostrados en preview (con "+N más" si hay más)
- Validación de NITs muy largos (>20 caracteres) rechazada en cliente

## Integración con Redux

### Actions utilizadas

```typescript
// Crear NIT individual
dispatch(crearNit({
  cuenta_correo_id: 1,
  nit: "800185449-8",  // ← NIT normalizado
  nombre_proveedor: "Proveedor ABC",
  notas: "Notas opcionales"
}))

// Crear NITs bulk
dispatch(crearNitsBulk({
  cuenta_correo_id: 1,
  nits: ["800185449-8", "900399741-7"]  // ← NITs normalizados
}))
```

## Testing

### Pruebas unitarias recomendadas

```typescript
describe('NitValidationService', () => {
  it('debe validar NIT sin DV', async () => {
    const result = await nitService.validateNit('800185449');
    expect(result.isValid).toBe(true);
    expect(result.normalizedNit).toBe('800185449-8');
  });

  it('debe rechazar NIT con DV incorrecto', async () => {
    const result = await nitService.validateNit('800185449-9');
    expect(result.isValid).toBe(false);
    expect(result.errorMessage).toContain('incorrecto');
  });

  it('debe validar múltiples NITs en paralelo', async () => {
    const nits = ['800185449', '900399741', 'INVALIDO'];
    const results = await nitService.validateMultipleNits(nits);
    expect(results.length).toBe(3);
    expect(results[0].isValid).toBe(true);
    expect(results[2].isValid).toBe(false);
  });
});

describe('AddNitDialog', () => {
  it('debe mostrar spinner mientras valida', async () => {
    // Mock API delay
    // Escribir NIT
    // Verificar que aparece spinner
  });

  it('debe habilitar botón solo cuando NIT es válido', async () => {
    // Escribir NIT inválido → botón deshabilitado
    // Escribir NIT válido → botón habilitado
  });

  it('debe usar NIT normalizado al guardar', async () => {
    // Escribir "800185449" (sin DV)
    // Click "Agregar"
    // Verificar que se envía "800185449-8"
  });
});
```

### Pruebas de integración

```typescript
// E2E test con Cypress
describe('NIT Validation E2E', () => {
  it('debe validar NIT y mostrar normalizado', () => {
    cy.visit('/email-config');
    cy.get('[data-testid="add-nit-btn"]').click();
    cy.get('input[name="nit"]').type('800185449');
    cy.wait(600); // Esperar debounce
    cy.get('[data-testid="nit-success-chip"]').should('contain', '800185449-8');
    cy.get('[data-testid="add-btn"]').should('not.be.disabled');
  });
});
```

## Cambios de comportamiento para usuarios

### Antes (sin validación en tiempo real)
```
Usuario ingresa: "800185449"
        ↓ (click Agregar)
Backend rechaza si es inválido
Usuario ve error después de hacer submit
```

### Después (con validación en tiempo real)
```
Usuario ingresa: "800185449"
        ↓ (automático en 500ms)
Servicio valida con backend
Usuario ve feedback inmediato: ✓ 800185449-8
Usuario sabe exactamente qué se guardará
        ↓ (click Agregar - si es válido)
Backend acepta y crea
```

## Migración para desarrolladores

Si estabas usando `nit.ts`:

### ❌ Antes (NO usar)
```typescript
import { calcularDigitoVerificador, normalizarNit } from '@/utils/nit';
// Estas funciones ya no existen
```

### ✅ Ahora (Usar)
```typescript
import nitValidationService from '@/services/nitValidation.service';

const result = await nitValidationService.validateNit(nit);
if (result.isValid) {
  const normalizedNit = result.normalizedNit;
  // ... usar NIT normalizado
}
```

## FAQ

**P: ¿Por qué el NIT se normaliza solo en el backend?**
R: Para garantizar que todo el sistema usa la misma lógica DIAN. Si DIAN cambia el algoritmo, solo actualizamos en un lugar.

**P: ¿Qué pasa si el backend no está disponible?**
R: El usuario vería "Error al validar NIT" y no podría agregar. Esto es correcto porque necesitamos validación robusta.

**P: ¿Puedo enviar NITs sin validar?**
R: No. El botón está deshabilitado hasta que el NIT sea válido. Previene errores.

**P: ¿Se pueden agregar NITs duplicados?**
R: El backend rechazará duplicados en la misma cuenta. El frontend ya lo previene en bulk.

---

**Última actualización:** 30 de octubre de 2025
**Versión:** 1.0
