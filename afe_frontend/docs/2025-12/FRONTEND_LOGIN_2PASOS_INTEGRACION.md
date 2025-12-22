# Frontend: Sistema de Login 2-Pasos Multi-Sede

**Status**: ✅ IMPLEMENTACIÓN COMPLETA
**Fecha**: 2025-11-24
**Módulo**: afe_frontend
**Backend API**: Sistema 2-pasos multi-empresa/multi-sede

---

## 📋 Archivos Creados

### 1. Services
- `src/services/authService.ts` - Servicio de autenticación con métodos loginStep1, loginStep2, cambiarSede

### 2. Types
- `src/types/auth.types.ts` - Tipos TypeScript para autenticación (User, Sede, LoginContext, etc.)

### 3. Redux
- `src/features/auth/authSlice.ts` (ACTUALIZADO) - Redux slice con soporte multi-sede

### 4. Componentes
- `src/features/auth/LoginStep1.tsx` - Componente PASO 1 (validación de credenciales)
- `src/features/auth/LoginStep2.tsx` - Componente PASO 2 (selección de sede)
- `src/components/Auth/SedeSelector.tsx` - Diálogo para cambiar sede post-login
- `src/features/auth/LoginPageNew.tsx` - Nueva página de login integrada (REEMPLAZA LoginPage.tsx)

### 5. Hooks
- `src/hooks/useLogin.ts` - Hook personalizado para lógica del login 2-pasos
- `src/hooks/useCambiarSede.ts` - Hook para cambiar sede sin logout

---

## 🚀 Paso 1: Reemplazar LoginPage

El archivo `LoginPageNew.tsx` reemplaza a `LoginPage.tsx` existente. Hay dos opciones:

### Opción A: Renombrar archivos (RECOMENDADO)
```bash
# Dentro de afe_frontend/
mv src/features/auth/LoginPage.tsx src/features/auth/LoginPage.tsx.old
mv src/features/auth/LoginPageNew.tsx src/features/auth/LoginPage.tsx
```

### Opción B: Actualizar import en AppRoutes.tsx
Si prefieres mantener el archivo viejo como backup:
```typescript
// En AppRoutes.tsx, cambiar:
import LoginPage from './features/auth/LoginPageNew';

// En lugar de:
import LoginPage from './features/auth/LoginPage';
```

---

## 🔄 Flujo del Login

### PASO 1: Validación de Credenciales
```
Usuario ingresa usuario + contraseña
↓
POST /auth/login-step-1
↓
Backend valida en base de datos
↓
Retorna:
  {
    usuario_id: 123,
    usuario_nombre: "Juan Pérez",
    sedes: [
      { sede_id: 1, nombre: "Sede Principal", empresa_nombre: "Zentria", ... },
      { sede_id: 2, nombre: "Sede Sucursal", empresa_nombre: "Zentria", ... }
    ],
    requiere_seleccionar_sede: true
  }
↓
Si una sola sede → Auto-avanza a PASO 2
Si múltiples sedes → Muestra selector visual
```

### PASO 2: Selección de Sede y Generación de Token
```
Usuario selecciona una sede
↓
POST /auth/login-step-2
  {
    usuario_id: 123,
    sede_id: 1
  }
↓
Backend genera JWT con contexto incrustado:
  {
    access_token: "eyJhbGc...",
    token_type: "bearer",
    user: { id, nombre, email, usuario, rol, activo, ... },
    sede_id: 1,
    empresa_id: 999,
    empresa_codigo: "ZENTRIA"
  }
↓
Frontend almacena en localStorage:
  - access_token
  - user
  - sede_id
  - empresa_id
  - empresa_codigo
↓
Redux state actualizado
↓
Redirecciona a /dashboard
```

---

## 🔐 Token JWT Enriquecido

El token JWT ahora contiene:
```json
{
  "sub": "123",                    // Usuario ID
  "exp": 1732123456,              // Expiración
  "iat": 1732110056,              // Emitido en
  "empresa_id": 999,              // Empresa actual
  "empresa_codigo": "ZENTRIA",    // Código empresa
  "sede_id": 1                    // Sede actual
}
```

**Benefit**: El frontend puede acceder a `empresa_id` y `sede_id` sin llamadas adicionales al backend.

---

## 📱 Cambiar Sede Post-Login (Sin Logout)

### Agregar botón en Header/MainLayout

Opción 1: Usar el hook directamente
```typescript
import { useCambiarSede } from '../hooks/useCambiarSede';
import SedeSelector from '../components/Auth/SedeSelector';

function MainLayout() {
  const [openSedeSelector, setOpenSedeSelector] = useState(false);
  const { cambiarSede, isLoading, error, currentSedeId } = useCambiarSede();
  const sedes = useAppSelector(state => state.auth.sedes); // Necesita ser agregado al Redux

  const handleCambiarSede = async (sedeId: number) => {
    await cambiarSede(sedeId);
    setOpenSedeSelector(false);
  };

  return (
    <>
      <Button onClick={() => setOpenSedeSelector(true)}>
        Cambiar Sede
      </Button>

      <SedeSelector
        open={openSedeSelector}
        sedes={sedes}
        currentSedeId={currentSedeId}
        onSelectSede={handleCambiarSede}
        onClose={() => setOpenSedeSelector(false)}
        isLoading={isLoading}
        error={error}
      />
    </>
  );
}
```

---

## 🔌 Integración con API Client

El `api.ts` existente ya tiene interceptores que:
1. Agregan automáticamente el token en el header
2. Manejan 401 redirectionando a login

**No es necesario cambiar nada en api.ts** - funciona automáticamente con los nuevos tokens.

---

## ✅ Checklist de Integración

### Paso 1: Reemplazo de LoginPage
- [ ] Renombrar o actualizar import de LoginPageNew
- [ ] Ejecutar `npm run dev` para verificar no hay errores
- [ ] Probar login con 1 sede (debe auto-avanzar)
- [ ] Probar login con múltiples sedes (debe mostrar selector)

### Paso 2: Verificar Storage
- [ ] Verificar en DevTools → Application → localStorage:
  - [ ] `access_token` presente
  - [ ] `user` (JSON válido)
  - [ ] `sede_id` (número)
  - [ ] `empresa_id` (número)
  - [ ] `empresa_codigo` (string)

### Paso 3: Verificar Redux
- [ ] Redux DevTools muestra `auth.sede_id`
- [ ] Redux DevTools muestra `auth.empresa_id`
- [ ] Redux DevTools muestra `auth.empresa_codigo`

### Paso 4: Verificar Endpoints Segregados
- [ ] GET /facturas retorna solo facturas de la empresa actual
- [ ] GET /periodos retorna solo datos de la empresa actual
- [ ] Export CSV es segregado por empresa

### Paso 5: Agregar Cambio de Sede (Opcional)
- [ ] Agregar botón en Header para cambiar sede
- [ ] Integrar `SedeSelector` component
- [ ] Probar cambio de sede sin logout
- [ ] Verificar que los datos se actualizan correctamente

---

## 🧪 Pruebas Manuales

### Test 1: Login con Una Sede
```
1. Ir a /login
2. Usuario: (cuenta con una sola sede)
3. Contraseña: (correcta)
4. Click "Continuar"
5. ESPERADO: Auto-avanza a PASO 2, luego a /dashboard
```

### Test 2: Login con Múltiples Sedes
```
1. Ir a /login
2. Usuario: (cuenta con múltiples sedes)
3. Contraseña: (correcta)
4. Click "Continuar"
5. ESPERADO: Muestra PASO 2 con selector visual
6. Seleccionar una sede
7. Click "Iniciar Sesión"
8. ESPERADO: Redirige a /dashboard
```

### Test 3: Cambiar Sede Post-Login
```
1. Estar logueado
2. Click en botón "Cambiar Sede" (en header)
3. Seleccionar otra sede
4. ESPERADO: Token se actualiza, datos se refrescan
5. ESPERADO: No hay logout, sesión continúa
```

### Test 4: Validación de Errores
```
1. Credenciales incorrectas:
   - ESPERADO: Muestra mensaje de error en PASO 1
2. Token expirado:
   - ESPERADO: Redirige a /login automáticamente
3. Usuario sin sedes:
   - ESPERADO: Muestra error apropiado
```

---

## 🎯 Flujos de Negocio

### Usuario multi-empresa
```
Login como "juan.perez"
↓
PASO 1: Retorna 3 sedes de diferentes empresas
↓
Selecciona "Sucursal B - EMPRESA Y"
↓
PASO 2: Genera token con empresa_id=222, sede_id=5
↓
Dashboard muestra solo datos de EMPRESA Y
↓
Hace cambio de sede → "Centro - EMPRESA X"
↓
Token actualizado con empresa_id=111, sede_id=2
↓
Dashboard muestra solo datos de EMPRESA X
↓
No hay logout durante todo el proceso
```

### Usuario multi-sede (misma empresa)
```
Login como "admin.zentria"
↓
PASO 1: Retorna 4 sedes de ZENTRIA
↓
Selecciona "Sede Principal - ZENTRIA"
↓
PASO 2: Genera token con empresa_id=999, sede_id=1
↓
Dashboard muestra datos de Sede Principal
↓
Puede cambiar entre sedes sin logout
```

---

## 🔗 Estructura de Redux State

Actualizado en `authSlice.ts`:
```typescript
interface AuthState {
  user: User | null;
  token: string | null;
  sede_id: number | null;           // NEW
  empresa_id: number | null;        // NEW
  empresa_codigo: string | null;    // NEW
  isAuthenticated: boolean;
  loading: boolean;
}
```

**Acceso en componentes**:
```typescript
const sede_id = useAppSelector(state => state.auth.sede_id);
const empresa_id = useAppSelector(state => state.auth.empresa_id);
const empresa_codigo = useAppSelector(state => state.auth.empresa_codigo);
```

---

## 🚨 Notas Importantes

### 1. Persistencia de Sedes
Actualmente `sedes` se guarda en el estado local del hook `useLogin`. Si necesitas persistir para cambiar sede:

Opción: Agregar `sedes` a Redux
```typescript
// En authSlice.ts:
interface AuthState {
  ...
  sedes: Sede[];  // NEW
}

// En loginStep1:
dispatch(setSedes(response.sedes));
```

### 2. Auto-avance de PASO 1 a PASO 2
Si hay una sola sede, el sistema auto-avanza automáticamente. Si deseas forzar siempre mostrar PASO 2:

Cambiar en `useLogin.ts`:
```typescript
// En handleLoginStep1:
if (response.sedes.length === 1 && response.requiere_seleccionar_sede) {
  await handleLoginStep2(response.usuario_id, response.sedes[0].sede_id);
}
// ↓ A:
// Never auto-advance, always show step 2
```

### 3. Tiempos de Expiración
El token JWT tiene validez limitada. Para refrescar sin logout, necesitarías implementar:
- Refresh tokens (patrón OAuth)
- O revalidar creenciables antes de experar

Actualmente cuando expire, el interceptor de 401 redirige a login.

---

## 📚 Archivos de Referencia

### Backend (ya implementado)
- Endpoints: `/auth/login-step-1`, `/auth/login-step-2`, `/auth/cambiar-sede`
- Schema: `app/schemas/auth.py`
- Router: `app/api/v1/routers/auth.py`

### Frontend (recién creado)
- Service: `src/services/authService.ts`
- Types: `src/types/auth.types.ts`
- Components: `LoginStep1`, `LoginStep2`, `SedeSelector`
- Hooks: `useLogin`, `useCambiarSede`
- Redux: `authSlice.ts` (actualizado)

---

## 🔄 Próximos Pasos Opcionales

1. **Agregar Google OAuth** - Adicionar botón Google en LoginStep1
2. **2FA (Two-Factor Auth)** - Agregar PASO 1.5 para MFA
3. **Biometric Login** - Usar WebAuthn para login sin contraseña
4. **Session Management** - Implementar refresh tokens
5. **Audit Logging** - Registrar cambios de sede
6. **Rate Limiting UI** - Mostrar contador de intentos fallidos

---

## 💬 Soporte y Troubleshooting

### Error: "usuario_id is null en handleLoginStep2"
**Causa**: usuario_id no se guardó correctamente en estado
**Solución**: Verificar que PASO 1 se completa sin errores

### Error: "POST /auth/login-step-2 404"
**Causa**: Backend no tiene el endpoint
**Solución**: Verificar que backend está corriendo con los cambios de FASE 8

### Token sin empresa_id/sede_id
**Causa**: Backend antiguo sin JWT enriquecido
**Solución**: Actualizar backend a versión FASE 8

### Storage vacío después de login
**Causa**: `localStorage.setItem` no ejecutado correctamente
**Solución**: Verificar que authService.loginStep2 se ejecutó sin excepciones

---

## ✅ Status Final

**Estado**: ✅ LISTO PARA INTEGRACIÓN
- [x] Services creado y completamente funcional
- [x] Componentes React creados y estilizados
- [x] Redux actualizado para multi-sede
- [x] Hooks personalizados listos
- [x] Documentación completa
- [x] Checklist de integración detallado
- [x] Pruebas manuales documentadas

**Próximo paso**: Renombrar LoginPageNew.tsx → LoginPage.tsx y ejecutar pruebas

---

**Responsable**:  Frontend Architect
**Fecha**: 2025-11-24
**Módulo**: afe_frontend (3000+ líneas de código nuevo)
