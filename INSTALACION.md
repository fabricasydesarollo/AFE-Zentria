# Guía de Instalación - Sistema AFE

Esta guía te ayudará a instalar y configurar el sistema AFE desde cero en una máquina nueva.

---

## 📋 Requisitos Previos

### Software Necesario
- **Python 3.10+** - [Descargar](https://www.python.org/downloads/)
- **Node.js 18+** - [Descargar](https://nodejs.org/)
- **MySQL 8.0+** - [Descargar](https://dev.mysql.com/downloads/mysql/)
- **Git** - [Descargar](https://git-scm.com/downloads)

### Credenciales de Azure AD (Opcional - para OAuth y extracción de emails)
- Tenant ID
- Client ID
- Client Secret
- Ver sección [Configuración Azure AD](#configuración-azure-ad) más abajo

---

## 🚀 Instalación Paso a Paso

### 1️⃣ Clonar el Repositorio

```bash
git clone https://github.com/JohnAlex2023/Proyecto_AFE.git
cd Proyecto_AFE
```

---

### 2️⃣ Configurar Base de Datos MySQL

#### Paso 1: Crear la Base de Datos

Conectarse a MySQL:

```bash
mysql -u root -p
```

Ejecutar los siguientes comandos SQL:

```sql
-- Crear base de datos
CREATE DATABASE afe_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Crear usuario (opcional pero recomendado)
CREATE USER 'afe_user'@'localhost' IDENTIFIED BY 'tu_password_seguro';

-- Otorgar permisos
GRANT ALL PRIVILEGES ON afe_db.* TO 'afe_user'@'localhost';
FLUSH PRIVILEGES;

-- Verificar
SHOW DATABASES;
USE afe_db;
```

Salir de MySQL:
```sql
EXIT;
```

#### Paso 2: Verificar Conexión

```bash
# Probar conexión con el nuevo usuario
mysql -u afe_user -p afe_db
# Si entra correctamente, la configuración es correcta
```

---

### 3️⃣ Configurar Backend (FastAPI)

```bash
cd afe-backend
```

#### Paso 1: Crear Entorno Virtual

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

#### Paso 2: Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Paso 3: Configurar Variables de Entorno

Copiar el archivo de ejemplo:
```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:

```bash
# ============================================
# BASE DE DATOS
# ============================================
DATABASE_URL=mysql+pymysql://afe_user:tu_password_seguro@localhost:3306/afe_db

# ============================================
# SEGURIDAD (Generar clave segura)
# ============================================
SECRET_KEY=genera-una-clave-super-segura-aqui-min-32-caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# ============================================
# CORS - Frontend
# ============================================
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# ============================================
# OAUTH MICROSOFT (SSO) - OPCIONAL
# ============================================
OAUTH_MICROSOFT_TENANT_ID=tu-tenant-id
OAUTH_MICROSOFT_CLIENT_ID=tu-client-id
OAUTH_MICROSOFT_CLIENT_SECRET=tu-client-secret
OAUTH_MICROSOFT_REDIRECT_URI=http://localhost:8000/api/v1/auth/microsoft-callback

# ============================================
# MICROSOFT GRAPH API (Extracción de Emails) - OPCIONAL
# ============================================
GRAPH_TENANT_ID=tu-tenant-id
GRAPH_CLIENT_ID=tu-client-id
GRAPH_CLIENT_SECRET=tu-client-secret

# ============================================
# LOGGING
# ============================================
LOG_LEVEL=INFO
```

**Generar SECRET_KEY seguro:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Paso 4: Ejecutar Migraciones (Crear Tablas)

```bash
# Verificar estado de migraciones
alembic current

# Aplicar todas las migraciones (crea las tablas)
alembic upgrade head

# Verificar que se crearon las tablas
mysql -u afe_user -p afe_db -e "SHOW TABLES;"
```

**Deberías ver tablas como:**
- `facturas`
- `usuarios`
- `proveedores`
- `grupos`
- `workflow_aprobacion_facturas`
- `asignacion_nit_responsable`
- `cuentas_correo`
- etc.

#### Paso 5: Crear Usuario Administrador Inicial

```bash
python scripts/create_user.py
```

Seguir las instrucciones en pantalla para crear el primer usuario admin.

#### Paso 6: Iniciar el Servidor Backend

```bash
uvicorn app.main:app --reload --port 8000
```

**Verificar:**
- API: http://localhost:8000
- Documentación: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

---

### 4️⃣ Configurar Frontend (React)

Abrir una **nueva terminal** (dejar el backend corriendo):

```bash
cd afe_frontend
```

#### Paso 1: Instalar Dependencias

```bash
npm install
```

#### Paso 2: Configurar Variables de Entorno

Crear archivo `.env.local`:

```bash
# Frontend - Conexión al Backend
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

#### Paso 3: Iniciar Servidor de Desarrollo

```bash
npm run dev
```

**Verificar:**
- Frontend: http://localhost:5173
- Debería ver la pantalla de login

#### Paso 4: Login Inicial

Usar las credenciales del usuario admin que creaste en el paso 3️⃣-5.

---

### 5️⃣ Configurar Invoice Extractor (Opcional)

Solo necesario si quieres extracción automática de facturas desde correo electrónico.

```bash
cd invoice_extractor
```

#### Paso 1: Crear Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### Paso 2: Instalar Dependencias

```bash
pip install -r requirements.txt
```

#### Paso 3: Configurar Credenciales

Copiar plantilla de configuración:
```bash
cp settings.json.template settings.json
```

Editar `settings.json`:

```json
{
  "database": {
    "host": "localhost",
    "port": 3306,
    "user": "afe_user",
    "password": "tu_password_seguro",
    "database": "afe_db"
  },
  "microsoft_graph": {
    "tenant_id": "tu-tenant-id",
    "client_id": "tu-client-id",
    "client_secret": "tu-client-secret"
  },
  "email_accounts": [
    "facturas@tuempresa.com"
  ]
}
```

#### Paso 4: Ejecutar Extracción Manual (Prueba)

```bash
python -m src.main
```

---

## 🔐 Configuración Azure AD

### Para OAuth SSO (Login con Microsoft)

1. Ir a [Azure Portal](https://portal.azure.com)
2. **Azure Active Directory** → **App registrations** → **New registration**
3. Configurar:
   - **Name:** AFE Backend OAuth
   - **Redirect URI:** `http://localhost:8000/api/v1/auth/microsoft-callback`
4. En **API permissions**:
   - Agregar: `User.Read` (Delegated)
   - Click: **Grant admin consent**
5. En **Certificates & secrets**:
   - Crear nuevo **Client Secret**
   - Copiar el valor (solo se muestra una vez)
6. Copiar **Application (client) ID** y **Directory (tenant) ID**
7. Pegar en `.env` del backend

### Para Microsoft Graph API (Extracción de Emails)

1. Crear **nueva App registration** (diferente a la anterior)
2. Configurar:
   - **Name:** AFE Invoice Extractor
   - **Redirect URI:** No necesario
3. En **API permissions**:
   - Agregar: `Mail.Read` (Application)
   - Agregar: `Mail.ReadWrite` (Application) - solo si necesitas marcar correos como leídos
   - Click: **Grant admin consent** ⚠️ **IMPORTANTE**
4. En **Certificates & secrets**:
   - Crear nuevo **Client Secret**
   - Copiar el valor
5. Copiar **Application (client) ID** y **Directory (tenant) ID**
6. Pegar en `settings.json` del invoice_extractor

---

## ✅ Verificación de Instalación

### 1. Backend

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Debería responder:
# {"status":"ok","database":"connected"}
```

### 2. Frontend

Abrir http://localhost:5173 y verificar:
- ✅ Página de login carga correctamente
- ✅ Puedes hacer login con el usuario admin
- ✅ El dashboard carga sin errores

### 3. Base de Datos

```bash
mysql -u afe_user -p afe_db -e "SELECT COUNT(*) FROM usuarios;"
# Debería mostrar al menos 1 usuario (el admin)
```

### 4. Invoice Extractor (si lo configuraste)

```bash
cd invoice_extractor
python -m src.main --test
# Debería conectarse a Microsoft Graph sin errores
```

---

## 🐛 Solución de Problemas Comunes

### Error: "Access denied for user"

```bash
# Verificar usuario y permisos en MySQL
mysql -u root -p
GRANT ALL PRIVILEGES ON afe_db.* TO 'afe_user'@'localhost';
FLUSH PRIVILEGES;
```

### Error: "alembic.util.exc.CommandError"

```bash
# Verificar DATABASE_URL en .env
# Debe tener formato: mysql+pymysql://usuario:password@host:puerto/base_datos

# Regenerar migraciones si es necesario
alembic upgrade head
```

### Error: "Module not found"

```bash
# Verificar que el entorno virtual esté activado
which python  # Linux/Mac
where python  # Windows

# Reinstalar dependencias
pip install --force-reinstall -r requirements.txt
```

### Error: "CORS policy"

Verificar en `afe-backend/.env`:
```bash
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
```

### Error: "Cannot connect to MySQL"

```bash
# Verificar que MySQL esté corriendo
# Linux/Mac:
sudo systemctl status mysql

# Windows:
net start MySQL80

# Verificar puerto
netstat -an | grep 3306  # Linux/Mac
netstat -an | findstr 3306  # Windows
```

---

## 📚 Próximos Pasos

Una vez instalado:

1. **Explorar el Sistema:**
   - Dashboard: http://localhost:5173
   - API Docs: http://localhost:8000/docs

2. **Leer Documentación:**
   - [README.md](README.md) - Descripción general
   - [afe-backend/DOCUMENTACION_TECNICA.md](afe-backend/DOCUMENTACION_TECNICA.md) - Detalles técnicos

3. **Configurar Usuarios y Grupos:**
   - Ir a **Configuración** → **Usuarios**
   - Crear grupos para multi-tenancy

4. **Configurar Proveedores:**
   - Ir a **Proveedores**
   - Agregar NITs y asignar responsables

5. **Probar Flujo Completo:**
   - Ejecutar invoice_extractor (si lo configuraste)
   - O crear facturas manualmente desde el frontend
   - Aprobar/rechazar en workflow

---

## 🆘 Soporte

Si tienes problemas durante la instalación:

1. Verificar los logs en terminal donde corre el backend
2. Verificar la consola del navegador (F12)
3. Revisar archivo `.env` que esté bien configurado
4. Consultar la documentación técnica completa

---

## 📝 Notas Importantes

- **Seguridad:** En producción, cambiar todos los secretos y passwords
- **HTTPS:** En producción, usar HTTPS y certificados SSL
- **Firewall:** Configurar firewall para solo permitir conexiones necesarias
- **Backups:** Configurar backups automáticos de la base de datos
- **Monitoreo:** Implementar logging y monitoreo en producción

---

**¡Instalación Completa!** 🎉

El sistema AFE debería estar corriendo correctamente en tu máquina local.
