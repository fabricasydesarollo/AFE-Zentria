# Configuración de Azure AD para OAuth 2.0

## 🎯 Guía Profesional para Configurar Microsoft OAuth

Esta guía te permitirá configurar la autenticación con Microsoft Outlook/Azure AD de manera profesional.

---

## 1️⃣ Registrar Aplicación en Azure Portal

### Paso 1: Acceder al Portal
1. Ve a [Azure Portal](https://portal.azure.com)
2. Busca **"Azure Active Directory"** o **"Microsoft Entra ID"**
3. En el menú lateral, selecciona **"App registrations"** (Registros de aplicaciones)
4. Clic en **"+ New registration"**

### Paso 2: Configurar Registro
```
Nombre: ZENTRIA AFE - Sistema de Aprobación
Supported account types:
  ✓ Accounts in this organizational directory only (Single tenant)
    - Usar esta opción si solo empleados de tu empresa

  ✓ Accounts in any organizational directory (Multi-tenant)
    - Usar si quieres permitir otras organizaciones

Redirect URI:
  Plataforma: Web
  URL: http://localhost:3000/auth/microsoft/callback   (desarrollo)
       https://afe.zentria.com/auth/microsoft/callback (producción)
```

### Paso 3: Obtener Credenciales
Una vez creada la app, verás:

```
Application (client) ID:
  Ejemplo: a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8

Directory (tenant) ID:
  Ejemplo: x9y8z7w6-v5u4-t3s2-r1q0-p9o8n7m6l5k4
```

---

## 2️⃣ Configurar Permisos (API Permissions)

### Permisos Requeridos:
1. Ve a **"API permissions"** en el menú lateral
2. Clic en **"+ Add a permission"**
3. Selecciona **"Microsoft Graph"**
4. Selecciona **"Delegated permissions"**
5. Agrega estos permisos:

```
✓ openid              - Identificación básica
✓ email               - Email del usuario
✓ profile             - Información del perfil
✓ User.Read           - Leer información del usuario
✓ offline_access      - Refresh tokens (opcional)
```

6. Clic en **"Grant admin consent for [tu organización]"** (Requiere permisos de admin)

---

## 3️⃣ Crear Client Secret

1. Ve a **"Certificates & secrets"** en el menú lateral
2. Clic en **"+ New client secret"**
3. Configurar:
   ```
   Description: ZENTRIA AFE Backend Secret
   Expires: 24 months (recomendado)
   ```
4. Clic en **"Add"**
5. **⚠️ IMPORTANTE:** Copia el **Value** inmediatamente (solo se muestra una vez)
   ```
   Ejemplo: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
   ```

---

## 4️⃣ Configurar Variables de Entorno

### Archivo `.env` (Backend)
```bash
# === OAuth Microsoft ===
OAUTH_MICROSOFT_TENANT_ID=x9yxxx6-vxxxxxx9o8n7m6l5k4xxxxxxxx
OAUTH_MICROSOFT_CLIENT_ID=xxxxx-e5f6-xxxxxxxi3jxxxxxxm7n8
OAUTH_MICROSOFT_CLIENT_SECRET=a1b2c3xxxxxx0k1l2m3nxxxxxxxr8s9t0

# Desarrollo
OAUTH_MICROSOFT_REDIRECT_URI=http://localhost:3000/auth/microsoft/callback

# Producción
# OAUTH_MICROSOFT_REDIRECT_URI=https://afe.zentria.com/auth/microsoft/callback

OAUTH_MICROSOFT_SCOPES=openid email profile User.Read
```

---

## 5️⃣ Configurar Redirect URIs Adicionales

En Azure Portal → **"Authentication"**:

### Web Platform - Redirect URIs:
```
✓ http://localhost:3000/auth/microsoft/callback      (desarrollo)
✓ http://localhost:8000/api/v1/auth/microsoft/callback  (testing backend)
✓ https://afe.zentria.com/auth/microsoft/callback   (producción frontend)
✓ https://api.afe.zentria.com/api/v1/auth/microsoft/callback (producción backend)
```

### Implicit grant and hybrid flows:
```
☐ Access tokens
☐ ID tokens
```
(No necesario para Authorization Code Flow)

---

## 6️⃣ Arquitectura de Flujo OAuth 2.0

```
┌─────────────┐                 ┌──────────────┐                 ┌──────────────┐
│   Usuario   │                 │   Frontend   │                 │   Backend    │
│  (Browser)  │                 │  (React/Vue) │                 │  (FastAPI)   │
└──────┬──────┘                 └──────┬───────┘                 └──────┬───────┘
       │                               │                                │
       │ 1. Clic "Login Microsoft"     │                                │
       │──────────────────────────────>│                                │
       │                               │                                │
       │                               │ 2. GET /auth/microsoft/authorize │
       │                               │───────────────────────────────>│
       │                               │                                │
       │                               │ 3. {authorization_url, state}  │
       │                               │<───────────────────────────────│
       │                               │                                │
       │ 4. Redirect a Microsoft       │                                │
       │<──────────────────────────────│                                │
       │                                                                 │
┌──────▼──────────────────────────────────────────────────────────────┐│
│                  Microsoft Azure AD                                  ││
│  - Usuario ingresa credenciales                                     ││
│  - Microsoft valida y solicita consentimiento                       ││
└──────┬──────────────────────────────────────────────────────────────┘│
       │                                                                 │
       │ 5. Redirect con code y state                                   │
       │────────────────────────────────────────────────────────────────>│
       │                               │                                │
       │                               │ 6. GET /callback?code=...&state=... │
       │                               │───────────────────────────────>│
       │                               │                                │
       │                               │  Backend:                      │
       │                               │  - Intercambia code por token  │
       │                               │  - Obtiene info usuario (Graph)│
       │                               │  - Crea/actualiza usuario DB   │
       │                               │  - Genera JWT propio           │
       │                               │                                │
       │                               │ 7. {access_token, user}        │
       │                               │<───────────────────────────────│
       │                               │                                │
       │ 8. {token, user}              │                                │
       │<──────────────────────────────│                                │
       │                               │                                │
       │ 9. Redirect a dashboard       │                                │
       │   con token en localStorage   │                                │
       │                               │                                │
```

---

## 7️⃣ Testing Local

### 1. Instalar Dependencias
```bash
cd afe-backend
pip install -r requirements.txt
```

### 2. Ejecutar Migración
```bash
alembic upgrade head
```

### 3. Iniciar Backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Probar Endpoints

#### Opción A: Desde Frontend
```javascript
// 1. Obtener URL de autorización
const response = await fetch('http://localhost:8000/api/v1/auth/microsoft/authorize');
const { authorization_url } = await response.json();

// 2. Redirigir
window.location.href = authorization_url;
```

#### Opción B: Testing Manual
```bash
# 1. Obtener authorization_url
curl http://localhost:8000/api/v1/auth/microsoft/authorize

# 2. Abrir la URL en el navegador
# 3. Microsoft redirigirá a tu callback con el code
# 4. El backend procesará automáticamente
```

---

## 8️⃣ Seguridad - Mejores Prácticas

###  Production Checklist

- [ ] **Nunca commitear secretos** al repositorio
- [ ] **Usar HTTPS** en producción
- [ ] **Validar state** para prevenir CSRF
- [ ] **Implementar rate limiting** en endpoints OAuth
- [ ] **Rotar client secrets** cada 6-12 meses
- [ ] **Logs de auditoría** para autenticaciones
- [ ] **Validar dominios** de email permitidos
- [ ] **Implementar logout** que revoque tokens
- [ ] **Configurar CORS** apropiadamente
- [ ] **Monitorear intentos fallidos**

### Validación de Email por Dominio (Opcional)
```python
# app/services/microsoft_oauth_service.py

ALLOWED_DOMAINS = ["zentria.com.co", "zentria.com"]

def find_or_create_user(self, db, user_info, default_role_id=2):
    email = user_info.get("email")
    domain = email.split("@")[1]

    if domain not in ALLOWED_DOMAINS:
        raise HTTPException(
            status_code=403,
            detail=f"Dominio {domain} no autorizado"
        )
    # ... resto del código
```

---

## 9️⃣ Troubleshooting

### Error: "AADSTS50011: The redirect URI specified in the request does not match"
**Solución:** Verifica que la URL en `.env` coincida exactamente con la registrada en Azure Portal.

### Error: "AADSTS65001: The user or administrator has not consented"
**Solución:** Ve a Azure Portal → API Permissions → Grant admin consent.

### Error: "Invalid client secret provided"
**Solución:** Genera un nuevo client secret y actualiza el `.env`.

### Error: "Token expired"
**Solución:** Los access tokens expiran en 1 hora. Implementa refresh tokens o re-autenticación.

---

## 🔟 Frontend Integration Example

### React + TypeScript
```typescript
// src/services/authService.ts
export class AuthService {
  private readonly API_URL = import.meta.env.VITE_API_URL;

  async loginWithMicrosoft(): Promise<void> {
    const response = await fetch(`${this.API_URL}/auth/microsoft/authorize`);
    const { authorization_url } = await response.json();

    window.location.href = authorization_url;
  }

  async handleMicrosoftCallback(code: string, state: string): Promise<User> {
    const response = await fetch(
      `${this.API_URL}/auth/microsoft/callback?code=${code}&state=${state}`
    );

    if (!response.ok) throw new Error('Authentication failed');

    const { access_token, user } = await response.json();

    // Guardar token
    localStorage.setItem('access_token', access_token);

    return user;
  }
}
```

---

## 📚 Referencias

- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [OAuth 2.0 Authorization Code Flow](https://oauth.net/2/grant-types/authorization-code/)
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/overview)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)

---

##  Conclusión

Ahora tienes una implementación **enterprise-grade** de autenticación con Microsoft OAuth:

-  Backend API REST completo
-  Soporte multi-provider (local + Microsoft)
-  Base de datos preparada
-  Seguridad implementada
-  Documentación completa
