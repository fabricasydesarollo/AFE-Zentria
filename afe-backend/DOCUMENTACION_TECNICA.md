#  DOCUMENTACIÓN TÉCNICA - AFE BACKEND


---

## 📑 Tabla de Contenidos

1. [Resumen del Proyecto](#resumen-del-proyecto)
2. [Arquitectura del Backend](#arquitectura-del-backend)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Configuración y Despliegue](#configuración-y-despliegue)
5. [API / Endpoints](#api--endpoints)
6. [Autenticación y Autorización](#autenticación-y-autorización)
7. [Base de Datos](#base-de-datos)
8. [Servicios Principales](#servicios-principales)
9. [Errores, Logs y Manejo de Excepciones](#errores-logs-y-manejo-de-excepciones)
10. [Pruebas (Testing)](#pruebas-testing)
11. [Buenas Prácticas y Estándares](#buenas-prácticas-y-estándares)
12. [Futuras Mejoras](#futuras-mejoras)

---

## 🎯 Resumen del Proyecto

### Descripción General

**AFE Backend** es un sistema empresarial de gestión de facturas y proveedores construido con tecnologías modernas y escalables. Proporciona una plataforma robusta para:

-  Ingesta y procesamiento automático de facturas
-  Automatización inteligente de aprobaciones
-  Gestión de proveedores y usuarios
-  Auditoria completa de cambios
-  Notificaciones por email en tiempo real
-  Integración con OAuth Microsoft para SSO

**Propósito Principal:** Automatizar y agilizar el flujo de aprobación de facturas mediante inteligencia artificial y machine learning, reduciendo tiempos de revisión manual y minimizando errores.

### Stack Tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| **Framework Web** | FastAPI | ≥ 0.111.0 |
| **Servidor ASGI** | Uvicorn | ≥ 0.29.0 |
| **Lenguaje** | Python | ≥ 3.10 |
| **ORM** | SQLAlchemy | ≥ 2.0.0 |
| **BD Principal** | MySQL | ≥ 8.0 |
| **Migraciones** | Alembic | ≥ 1.13.0 |
| **Autenticación** | JWT + OAuth2 + Microsoft MSAL | PyJWT 2.8.0+ |
| **Encriptación** | Bcrypt | 3.2.0 |
| **Email** | SMTP + Microsoft Graph API | requests 2.31.0+ |
| **Tareas Async** | APScheduler | ≥ 3.10.0 |
| **Validación** | Pydantic | ≥ 2.7.0 |
| **Testing** | pytest | ≥ 8.0.0 |
| **Procesamiento Datos** | Pandas | ≥ 2.0.0 |

---

## 🏗️ Arquitectura del Backend

### Visión General



### Patrones de Arquitectura

#### 1. **MVC Adaptado a REST API**
```
Router (Controller) → Schema (Validation) → Service (Business Logic) → CRUD (Data Access) → Model (ORM)
```

#### 2. **Dependency Injection**
```python
# FastAPI usa inyección de dependencias para:
def endpoint(
    db: Session = Depends(get_db),                    # Database
    current_user = Depends(get_current_responsable),  # Auth
    role = Depends(require_role("admin"))             # Authorization
):
    pass
```

#### 3. **Asincronía y Tasks en Background**
```python
# APScheduler para tareas periódicas
# async/await para operaciones I/O no-bloqueantes
# Notificaciones enviadas en background
```

### Flujo de Datos

```
1. Request HTTP llega
   ↓
2. Router recibe y valida con Schema (Pydantic)
   ↓
3. Autenticación: get_current_responsable() valida JWT
   ↓
4. Autorización: require_role() verifica permisos
   ↓
5. Service Layer: Lógica compleja de negocio
   ├─ Comparación de facturas
   ├─ Automatización de aprobaciones
   ├─ Notificaciones por email
   └─ Auditoría de cambios
   ↓
6. CRUD Layer: Acceso a datos
   └─ SQLAlchemy ORM queries
   ↓
7. MySQL: Persistencia
   ↓
8. Response: Serialización a JSON + Status HTTP
```

---

## 📁 Estructura del Proyecto

### Árbol de Directorios

```
c:\Users\jhont\PRIVADO_ODO\afe-backend/
│
├── alembic/                          # Migraciones de BD
│   ├── env.py                        # Config Alembic
│   ├── script.py.mako                # Template migraciones
│   ├── versions/                     # Migraciones versionadas
│   │   ├── da7367e01cd7_initial_migration.py
│   │   ├── ab8f4888b5b5_add_approval_fields.py
│   │   ├── e4b2063b3d6e_add_automation_fields.py
│   │   └── ... (6 migraciones en total)
│   └── alembic.ini
│
├── app/                              # Aplicación principal
│   ├── __init__.py
│   ├── main.py                       # Punto de entrada FastAPI
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── routers/              # Endpoints
│   │           ├── auth.py           # POST /api/v1/auth/login
│   │           ├── facturas.py       # CRUD facturas
│   │           ├── proveedores.py    # CRUD proveedores
│   │           ├── responsables.py   # CRUD usuarios
│   │           ├── roles.py          # Gestión roles
│   │           ├── workflow.py       # Aprobación/rechazo
│   │           ├── automation.py     # Automatización
│   │           ├── asignacion_nit.py # NIT-responsable
│   │           ├── email_config.py   # Config emails
│   │           ├── health.py         # Health checks
│   │           ├── historial_pagos.py
│   │           ├── flujo_automatizacion.py
│   │           └── ... (14 routers en total)
│   │
│   ├── core/                         # Configuración central
│   │   ├── config.py                 # Settings (env vars)
│   │   ├── security.py               # JWT, OAuth, bcrypt
│   │   ├── database.py               # Engine, SessionLocal
│   │   └── lifespan.py               # Startup/shutdown
│   │
│   ├── db/                           # Base de datos
│   │   ├── base.py                   # Base declarativa
│   │   ├── session.py                # SessionLocal, get_db
│   │   └── init_db.py                # Inicialización
│   │
│   ├── models/                       # Modelos ORM (SQLAlchemy)
│   │   ├── responsable.py            # Usuario/responsable
│   │   ├── role.py                   # Rol
│   │   ├── proveedor.py              # Proveedor
│   │   ├── factura.py                # Factura (principal)
│   │   ├── factura_item.py           # Items/líneas
│   │   ├── workflow_aprobacion.py    # Workflow
│   │   ├── historial_pagos.py        # Pagos
│   │   ├── audit_log.py              # Auditoría
│   │   └── email_config.py           # Config emails
│   │
│   ├── schemas/                      # Validación Pydantic
│   │   ├── auth.py                   # LoginRequest, TokenResponse
│   │   ├── factura.py                # FacturaCreate, FacturaRead
│   │   ├── proveedor.py              # ProveedorCreate
│   │   ├── responsable.py            # ResponsableCreate
│   │   ├── role.py                   # RoleBase
│   │   ├── common.py                 # PaginatedResponse
│   │   ├── presupuesto.py
│   │   └── email_config.py
│   │
│   ├── crud/                         # Operaciones CRUD
│   │   ├── factura.py                # read, create, update, delete
│   │   ├── proveedor.py
│   │   ├── responsable.py
│   │   ├── role.py
│   │   ├── audit.py
│   │   ├── email_config.py
│   │   └── presupuesto.py
│   │
│   ├── services/                     # Lógica de negocio
│   │   ├── auth_service.py           # Autenticación
│   │   ├── workflow_automatico.py    # Workflow automático
│   │   ├── automation/
│   │   │   ├── automation_service.py
│   │   │   ├── notification_service.py
│   │   │   └── fingerprint_generator.py
│   │   ├── email_service.py          # SMTP
│   │   ├── microsoft_graph_email_service.py  # Graph API
│   │   ├── microsoft_oauth_service.py        # OAuth
│   │   ├── comparador_items.py       # Matching
│   │   ├── item_normalizer.py        # Normalización
│   │   ├── clasificacion_proveedores.py
│   │   ├── auto_vinculacion.py       # Auto-vinculación NITs
│   │   ├── invoice_service.py        # Procesamiento
│   │   ├── export_service.py         # Excel
│   │   ├── audit_service.py          # Auditoría
│   │   ├── notificaciones.py
│   │   ├── scheduler_notificaciones.py
│   │   └── ... (25+ servicios)
│   │
│   ├── utils/                        # Utilidades
│   │   ├── logger.py                 # Logging
│   │   ├── cors.py                   # CORS setup
│   │   ├── nit_validator.py          # Validación NITs
│   │   └── cursor_pagination.py      # Paginación cursor
│   │
│   ├── tasks/                        # Tareas background
│   │   └── automation_tasks.py
│   │
│   ├── templates/                    # HTML templates
│   │   └── emails/
│   │
│   └── scripts/                      # Scripts utilitarios
│       ├── init_db.py
│       └── ... (scripts varios)
│
├── tests/                            # Tests
│   ├── test_auth.py
│   ├── test_factura.py
│   └── test_*.py
│
├── logs/                             # Archivos de logs
│
├── requirements.txt                  # Dependencias
├── alembic.ini                       # Config Alembic
├── .env.example                      # Variables entorno
├── pyproject.toml                    # Config del proyecto
├── DOCUMENTACION_TECNICA.md          # Este archivo
└── README.md                         # Readme principal
```

### Convenciones de Nombres

#### Archivos y Carpetas
```
 snake_case para archivos y carpetas
   - router_usuarios.py
   - servicio_facturas.py
   - utils/



#### Clases
```
 PascalCase para clases
   class FacturaService:
   class Responsable(Base):
   class FacturaCreate(BaseModel):


#### Funciones y Métodos
```
 snake_case para funciones
   def procesar_factura():
   def obtener_responsable_por_id():
   async def crear_notificacion():



#### Constantes
```
 UPPER_SNAKE_CASE para constantes
   MAX_ITEMS_PER_PAGE = 500
   DEFAULT_TIMEOUT = 30
   JWT_ALGORITHM = "HS256"
```

#### Variables
```
 snake_case para variables
   usuario_id = 123
   es_aprobada = True
   total_monto = Decimal("1000.00")
```

### Organización del Código


app/
├── api/v1/routers/
│   ├── auth.py          # Solo endpoints de autenticación
│   ├── facturas.py      # Solo endpoints de facturas
│   └── ...
├── services/
│   ├── auth_service.py              # Lógica de autenticación
│   ├── workflow_automatico.py       # Lógica de workflow
│   └── ...
├── models/
│   └── responsable.py       # Solo modelo Responsable
└── schemas/
    └── factura.py           # Solo schemas de facturas



---

## ⚙️ Configuración y Despliegue

### Variables de Entorno

Crear archivo `.env` en la raíz del proyecto basado en `.env.example`:

```env
# ============================================
# CONFIGURACIÓN CORE
# ============================================
ENVIRONMENT=development                    # development|staging|production
SECRET_KEY=your-super-secret-key-change-in-prod
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ============================================
# BASE DE DATOS
# ============================================
# Formato: mysql+pymysql://usuario:contraseña@host:puerto/base_datos
DATABASE_URL=mysql+pymysql://afe_user:secure_password@localhost:3306/bd_afe

# ============================================
# CORS (Origenes permitidos)
# ============================================
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://app.empresa.com

# ============================================
# MICROSOFT GRAPH API (Email notifications)
# ============================================
GRAPH_TENANT_ID=[YOUR_TENANT_ID]
GRAPH_CLIENT_ID=[YOUR_CLIENT_ID]
GRAPH_CLIENT_SECRET=[YOUR_CLIENT_SECRET]
GRAPH_FROM_EMAIL=notificacionrpa.auto@zentria.com.co
GRAPH_FROM_NAME=Sistema AFE - Notificaciones

# ============================================
# MICROSOFT OAUTH (Autenticación usuarios)
# ============================================
OAUTH_MICROSOFT_TENANT_ID=[YOUR_TENANT_ID]
OAUTH_MICROSOFT_CLIENT_ID=[YOUR_CLIENT_ID]
OAUTH_MICROSOFT_CLIENT_SECRET=[YOUR_CLIENT_SECRET]
OAUTH_MICROSOFT_REDIRECT_URI=http://localhost:3000/auth/microsoft/callback
OAUTH_MICROSOFT_SCOPES=openid email profile User.Read

# ============================================
# SMTP (Fallback, opcional)
# ============================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM_EMAIL=noreply@afe.com
SMTP_FROM_NAME=AFE Sistema de Facturas
SMTP_USE_TLS=True
SMTP_USE_SSL=False
SMTP_TIMEOUT=30
```

### Instalación de Dependencias

#### Requisitos Previos
```bash
# Windows
python --version              # Python ≥ 3.10
pip --version                 # pip ≥ 23.0
mysql --version               # MySQL ≥ 8.0

# Verificar instalación de MySQL
mysql -u root -p -e "SELECT VERSION();"
```

#### Instalación Local

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd afe-backend

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Crear archivo .env
cp .env.example .env
# Editar .env con valores reales

# 6. Ejecutar migraciones
alembic upgrade head

# 7. Inicializar BD (crear roles, usuario admin)
python app/db/init_db.py

# 8. Ejecutar servidor
uvicorn app.main:app --reload --port 8000
```

**Salida esperada:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

#### Acceso a Documentación API

```
Swagger UI: http://localhost:8000/docs
ReDoc:      http://localhost:8000/redoc
OpenAPI:    http://localhost:8000/openapi.json
```

### Despliegue en Producción

#### 1. Preparación del Servidor

```bash
# Instalar dependencias del sistema
sudo apt-get update
sudo apt-get install python3.10 python3-pip mysql-server

# Crear usuario específico para la aplicación
sudo useradd -m -s /bin/bash afeapp
sudo -u afeapp mkdir -p /home/afeapp/afe-backend
```

#### 2. Deploy con Systemd

Crear archivo `/etc/systemd/system/afe-backend.service`:

```ini
[Unit]
Description=AFE Backend FastAPI Service
After=network.target mysql.service

[Service]
Type=notify
User=afeapp
WorkingDirectory=/home/afeapp/afe-backend
Environment="PATH=/home/afeapp/afe-backend/venv/bin"
ExecStart=/home/afeapp/afe-backend/venv/bin/uvicorn \
    app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --env-file .env

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Activar servicio:**
```bash
sudo systemctl daemon-reload
sudo systemctl start afe-backend
sudo systemctl enable afe-backend
sudo systemctl status afe-backend
```

#### 3. Proxy Inverso (Nginx)

Crear `/etc/nginx/sites-available/afe-backend`:

```nginx
server {
    listen 80;
    server_name api.empresa.com;

    # Redirigir HTTP a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.empresa.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Headers de seguridad
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # CORS headers
    add_header Access-Control-Allow-Origin "https://app.empresa.com" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**Activar site:**
```bash
sudo ln -s /etc/nginx/sites-available/afe-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 4. Variables de Entorno en Producción

```bash
# /home/afeapp/afe-backend/.env (con permisos 600)
ENVIRONMENT=production
SECRET_KEY=<usar-comando-abajo>
DATABASE_URL=mysql+pymysql://afe_prod:secure_pwd@db-prod.empresa.com:3306/bd_afe_prod
BACKEND_CORS_ORIGINS=https://app.empresa.com
GRAPH_TENANT_ID=<desde-azure>
# ... resto de variables
```

**Generar SECRET_KEY seguro:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 5. Backup y Mantenimiento

```bash
# Script de backup diario (/etc/cron.daily/afe-backup)
#!/bin/bash
mysqldump -u afe_prod -p$(cat /home/afeapp/.db_password) bd_afe_prod | \
    gzip > /backups/afe_$(date +%Y%m%d).sql.gz

# Limpiar backups antiguos
find /backups -name "afe_*.sql.gz" -mtime +30 -delete
```

---

## 🔌 API / Endpoints

### Autenticación

#### POST `/api/v1/auth/login`
**Descripción:** Autenticar usuario con usuario y contraseña

**Método:** `POST`
**Autenticación:** No requerida

**Request Body:**
```json
{
  "usuario": "admin",
  "password": "123456"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImlhdCI6MTcwMTkxMjM0MCwiZXhwIjoxNzAxOTE1OTQwfQ.abc123",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "usuario": "admin",
    "nombre": "Administrador",
    "email": "admin@empresa.com",
    "role": "admin",
    "area": "IT"
  }
}
```

**Errores:**
- `401 Unauthorized`: Usuario o contraseña incorrectos

---

#### GET `/api/v1/auth/microsoft/authorize`
**Descripción:** Obtener URL de autorización Microsoft OAuth

**Método:** `GET`
**Autenticación:** No requerida

**Response (200 OK):**
```json
{
  "authorization_url": "https://login.microsoftonline.com/c9ef7bf6-bbe0-4c50-b2e9-ea58d635ca46/oauth2/v2.0/authorize?client_id=79dc4cdc-137b-415f-8193-a7a5b3fdd47b&response_type=code&..."
}
```

---

#### GET `/api/v1/auth/microsoft/callback`
**Descripción:** Callback de OAuth Microsoft (redirigido desde Azure)

**Parámetros:**
- `code`: Authorization code de Azure AD
- `state`: State para CSRF protection

---

### Facturas

#### GET `/api/v1/facturas/cursor`
**Descripción:** Listar facturas con cursor pagination (optimizado para 10k+ registros)

**Método:** `GET`
**Autenticación:** JWT requerido

**Parámetros Query:**
```
?limit=500                    # Items por página (default 500)
&cursor=MjAyNS0xMC0wOFQxMDowMDowMHwxMjM0NQ==  # Cursor para siguiente página
&filtro_estado=aprobada      # Estado: en_revision|aprobada|rechazada|pagada
&filtro_proveedor_id=5       # Filtrar por proveedor
&filtro_fecha_desde=2024-01-01
&filtro_fecha_hasta=2024-12-31
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": 1001,
      "numero_factura": "INV-2024-0001",
      "fecha_emision": "2024-10-08",
      "proveedor": {
        "id": 5,
        "nit": "123456789-0",
        "razon_social": "Tech Solutions SAS"
      },
      "subtotal": 1000.00,
      "iva": 190.00,
      "total_a_pagar": 1190.00,
      "estado": "aprobada",
      "confianza_automatica": 0.98,
      "responsable": {
        "id": 3,
        "nombre": "Carlos López"
      },
      "creado_en": "2024-10-08T10:30:00"
    }
  ],
  "cursor": {
    "has_more": true,
    "next_cursor": "MjAyNS0xMC0wOFQxMDowMDowMHwxMjM0NQ==",
    "prev_cursor": null,
    "count": 500
  }
}
```

---

#### GET `/api/v1/facturas/{id}`
**Descripción:** Obtener detalle de una factura

**Método:** `GET`
**Autenticación:** JWT requerido

**Parámetros Path:**
- `id`: ID de la factura

**Response (200 OK):**
```json
{
  "id": 1001,
  "numero_factura": "INV-2024-0001",
  "cufe": "12345abc67890def",
  "fecha_emision": "2024-10-08",
  "fecha_vencimiento": "2024-10-28",
  "proveedor_id": 5,
  "proveedor": {
    "id": 5,
    "nit": "123456789-0",
    "razon_social": "Tech Solutions SAS",
    "contacto_email": "contacto@techsolutions.com"
  },
  "subtotal": 1000.00,
  "iva": 190.00,
  "total_a_pagar": 1190.00,
  "estado": "aprobada",
  "confianza_automatica": 0.98,
  "tipo_factura": "COMPRA",
  "patron_recurrencia": "FIJO",
  "orden_compra_numero": "OP-2024-001",
  "responsable_id": 3,
  "responsable": {
    "id": 3,
    "nombre": "Carlos López"
  },
  "items": [
    {
      "id": 10001,
      "numero_linea": 1,
      "descripcion": "Licencia Software Enterprise",
      "codigo_producto": "LIC-ENT-001",
      "cantidad": 1,
      "unidad_medida": "UND",
      "precio_unitario": 1000.00,
      "subtotal": 1000.00,
      "categoria": "software",
      "es_recurrente": true
    }
  ],
  "workflow_history": [
    {
      "id": 1,
      "estado": "APROBADA_AUTO",
      "tipo_aprobacion": "AUTOMATICA",
      "confianza": 0.98,
      "fecha_registro": "2024-10-08T10:35:00"
    }
  ],
  "creado_en": "2024-10-08T10:30:00",
  "actualizado_en": "2024-10-08T10:35:00"
}
```

---

#### POST `/api/v1/facturas/`
**Descripción:** Crear nueva factura

**Método:** `POST`
**Autenticación:** JWT requerido
**Permisos:** admin, responsable

**Request Body:**
```json
{
  "numero_factura": "INV-2024-0002",
  "fecha_emision": "2024-10-09",
  "fecha_vencimiento": "2024-10-29",
  "proveedor_id": 5,
  "subtotal": 2000.00,
  "iva": 380.00,
  "total_a_pagar": 2380.00,
  "tipo_factura": "COMPRA",
  "orden_compra_numero": "OP-2024-002",
  "cufe": "12345abc67890def",
  "items": [
    {
      "numero_linea": 1,
      "descripcion": "Hardware - Monitor 4K",
      "codigo_producto": "HW-MON-001",
      "cantidad": 2,
      "unidad_medida": "UND",
      "precio_unitario": 1000.00,
      "subtotal": 2000.00,
      "categoria": "hardware"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "id": 1002,
  "numero_factura": "INV-2024-0002",
  "estado": "en_revision",
  "confianza_automatica": null,
  "creado_en": "2024-10-09T09:00:00"
}
```

---

#### PUT `/api/v1/facturas/{id}`
**Descripción:** Actualizar factura

**Método:** `PUT`
**Autenticación:** JWT requerido
**Permisos:** admin, responsable

**Parámetros Path:**
- `id`: ID de la factura

**Request Body:** (parcial, solo campos a actualizar)
```json
{
  "orden_compra_numero": "OP-2024-002-REV",
  "estado": "en_revision"
}
```

**Response (200 OK):**
```json
{
  "id": 1002,
  "numero_factura": "INV-2024-0002",
  "orden_compra_numero": "OP-2024-002-REV",
  "estado": "en_revision",
  "actualizado_en": "2024-10-09T09:15:00"
}
```

---

#### DELETE `/api/v1/facturas/{id}`
**Descripción:** Eliminar factura

**Método:** `DELETE`
**Autenticación:** JWT requerido
**Permisos:** admin

**Parámetros Path:**
- `id`: ID de la factura

**Response (204 No Content):** (sin body)

**Errores:**
- `404 Not Found`: Factura no existe
- `403 Forbidden`: Sin permisos para eliminar

---

### Workflow / Aprobaciones

#### POST `/api/v1/workflow/aprobar`
**Descripción:** Aprobar una factura manualmente

**Método:** `POST`
**Autenticación:** JWT requerido
**Permisos:** admin, responsable

**Request Body:**
```json
{
  "factura_id": 1001,
  "motivo": "Revisión completada, conforme."
}
```

**Response (200 OK):**
```json
{
  "id": 1001,
  "estado": "aprobada",
  "responsable_asignado": "Carlos López",
  "fecha_aprobacion": "2024-10-09T10:00:00",
  "tipo_aprobacion": "MANUAL",
  "mensaje": "Factura aprobada exitosamente"
}
```

---

#### POST `/api/v1/workflow/rechazar`
**Descripción:** Rechazar una factura

**Método:** `POST`
**Autenticación:** JWT requerido
**Permisos:** admin, responsable

**Request Body:**
```json
{
  "factura_id": 1001,
  "motivo_rechazo": "INCONSISTENCIA_DATOS",
  "detalle": "El total no coincide con el desglose de items."
}
```

**Response (200 OK):**
```json
{
  "id": 1001,
  "estado": "rechazada",
  "responsable_rechaza": "Carlos López",
  "fecha_rechazo": "2024-10-09T10:05:00",
  "motivo_rechazo": "INCONSISTENCIA_DATOS",
  "detalle_rechazo": "El total no coincide con el desglose de items.",
  "tipo_aprobacion": "MANUAL",
  "mensaje": "Factura rechazada"
}
```

---

### Automatización

#### POST `/api/v1/automation/procesar-facturas`
**Descripción:** Procesar lote de facturas con automatización

**Método:** `POST`
**Autenticación:** JWT requerido
**Permisos:** admin

**Request Body:**
```json
{
  "factura_ids": [1001, 1002, 1003],
  "umbral_confianza": 0.85
}
```

**Response (200 OK):**
```json
{
  "procesadas": 3,
  "aprobadas_automaticamente": 2,
  "pendientes_revision": 1,
  "rechazadas": 0,
  "detalle": [
    {
      "factura_id": 1001,
      "resultado": "aprobada_auto",
      "confianza": 0.98,
      "razon": "Coincidencia 98% con factura anterior"
    },
    {
      "factura_id": 1002,
      "resultado": "aprobada_auto",
      "confianza": 0.92,
      "razon": "Patrón recurrente identificado"
    },
    {
      "factura_id": 1003,
      "resultado": "pendiente_revision",
      "confianza": 0.72,
      "razon": "Confianza menor al umbral"
    }
  ],
  "duracion_segundos": 2.34
}
```

---

### Salud del Sistema

#### GET `/api/v1/health/`
**Descripción:** Health check general del sistema

**Método:** `GET`
**Autenticación:** No requerida

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-09T10:30:00Z",
  "database": {
    "status": "connected",
    "latency_ms": 5
  },
  "version": "2.0.0",
  "environment": "production"
}
```

---

#### GET `/api/v1/health/email`
**Descripción:** Health check del servicio de email

**Método:** `GET`
**Autenticación:** JWT requerido
**Permisos:** admin

**Response (200 OK):**
```json
{
  "status": "healthy",
  "smtp": {
    "status": "connected",
    "host": "smtp.gmail.com",
    "port": 587
  },
  "microsoft_graph": {
    "status": "connected",
    "tenant": "c9ef7bf6-bbe0-4c50-b2e9-ea58d635ca46"
  },
  "last_test": "2024-10-09T10:25:00Z"
}
```

---

### Códigos HTTP Estándar

| Código | Significado | Ejemplo |
|--------|------------|---------|
| **200** | OK | GET exitoso, actualización exitosa |
| **201** | Created | Recurso creado exitosamente |
| **204** | No Content | Eliminación exitosa (sin body) |
| **400** | Bad Request | Datos inválidos en request |
| **401** | Unauthorized | Token JWT inválido/expirado |
| **403** | Forbidden | Usuario sin permisos (RBAC) |
| **404** | Not Found | Recurso no encontrado |
| **409** | Conflict | Violación de constraint (ej: NIT duplicado) |
| **422** | Unprocessable Entity | Validación Pydantic falló |
| **500** | Internal Server Error | Error en el servidor |
| **503** | Service Unavailable | BD o servicio externo caído |

---

##  Autenticación y Autorización

### Métodos de Autenticación

#### 1. Autenticación Local (Usuario + Contraseña)

```python
# app/api/v1/routers/auth.py
@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Responsable).filter(
        Responsable.usuario == credentials.usuario
    ).first()

    if not usuario or not verify_password(
        credentials.password,
        usuario.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Usuario o contraseña incorrectos"
        )

    access_token = create_access_token(
        data={"sub": usuario.usuario, "id": usuario.id}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UsuarioResponse(...)
    )
```

**Flujo:**
```
1. Usuario envía: POST /api/v1/auth/login
   {"usuario": "admin", "password": "123456"}

2. Backend busca usuario en BD

3. Verifica contraseña con bcrypt.verify()

4. Genera JWT token:
   header: {"alg": "HS256", "typ": "JWT"}
   payload: {"sub": "admin", "id": 1, "iat": ..., "exp": ...}
   signature: HMACSHA256(header.payload, SECRET_KEY)

5. Retorna token al cliente

6. Cliente almacena en localStorage

7. Cliente envía en cada request:
   Authorization: Bearer <token>

8. Backend valida JWT en cada request
```

#### 2. JWT (JSON Web Tokens)

**Archivo:** `app/core/security.py`

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

# Hash password context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# JWT Configuration
ALGORITHM = "HS256"  # HS256, RS256, etc.
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Crea un JWT token con expiración automática."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decodifica y valida un JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado"
        )

def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """Verifica contraseña con bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """Hash de contraseña con bcrypt."""
    return pwd_context.hash(password)
```

**Estructura JWT:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
.
eyJzdWIiOiJhZG1pbiIsImlkIjoxLCJpYXQiOjE3MDE5MTIzNDAsImV4cCI6MTcwMTkxNTk0MH0
.
HKb3C7z4z9K2m8L5p0Q1R6S7T8U9V0W1X2Y3Z4a5b6

[HEADER]  .  [PAYLOAD]  .  [SIGNATURE]
```

**Decodificación (para demostración):**
```python
import base64
import json

header = base64.urlsafe_b64decode(
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9=="
)
print(json.loads(header))
# {"alg": "HS256", "typ": "JWT"}

payload = base64.urlsafe_b64decode(
    "eyJzdWIiOiJhZG1pbiIsImlkIjoxLCJpYXQiOjE3MDE5MTIzNDAsImV4cCI6MTcwMTkxNTk0MH0=="
)
print(json.loads(payload))
# {"sub": "admin", "id": 1, "iat": 1701912340, "exp": 1701915940}
```

#### 3. OAuth2 (Microsoft Azure AD)

**Archivo:** `app/services/microsoft_oauth_service.py`

```python
from msal import PublicClientApplication
from authlib.integrations.requests_client import OAuth2Session

class MicrosoftOAuthService:
    def __init__(self, settings):
        self.client_id = settings.oauth_microsoft_client_id
        self.client_secret = settings.oauth_microsoft_client_secret
        self.tenant_id = settings.oauth_microsoft_tenant_id
        self.redirect_uri = settings.oauth_microsoft_redirect_uri

        # Authority: https://login.microsoftonline.com/{tenant}/oauth2/v2.0
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        self.app = PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority
        )

    def get_authorization_url(self) -> str:
        """Genera URL para redirigir a login Microsoft."""
        # https://login.microsoftonline.com/.../authorize?
        # client_id=...&response_type=code&redirect_uri=...&scope=...
        pass

    def exchange_code_for_token(self, code: str) -> dict:
        """Intercambia authorization code por access token."""
        # POST a https://login.microsoftonline.com/.../token
        # body: grant_type=authorization_code&code=...&client_id=...
        pass

    def get_user_info(self, access_token: str) -> dict:
        """Obtiene info del usuario desde Microsoft Graph API."""
        # GET https://graph.microsoft.com/v1.0/me
        # Authorization: Bearer {access_token}
        pass
```

**Flujo OAuth2:**
```
1. Usuario hace click en "Login con Microsoft"
   ↓
2. Frontend redirige a /api/v1/auth/microsoft/authorize
   ↓
3. Backend genera URL de Azure AD y retorna
   ↓
4. Frontend redirige a Microsoft (usuario ve login Microsoft)
   ↓
5. Usuario ingresa credenciales Microsoft
   ↓
6. Microsoft redirige a /api/v1/auth/microsoft/callback?code=...
   ↓
7. Backend intercambia code por access_token
   ↓
8. Backend obtiene info del usuario desde Graph API
   ↓
9. Backend busca o crea usuario en BD
   ↓
10. Backend genera JWT token propio
    ↓
11. Frontend almacena JWT en localStorage
```

### Control de Acceso Basado en Roles (RBAC)

#### Definición de Roles

**Archivo:** `app/core/config.py`

```python
class Roles:
    ADMIN = "admin"              # Acceso total
    RESPONSABLE = "responsable"  # Aprobación, lectura
    VIEWER = "viewer"            # Solo lectura
```

#### Tabla de Permisos

| Rol | Crear | Leer | Actualizar | Eliminar | Aprobar/Rechazar |
|-----|-------|------|------------|----------|------------------|
| **admin** |  |  |  |  |  |
| **responsable** |  |  | Propias | ❌ |  |
| **viewer** | ❌ |  | ❌ | ❌ | ❌ |

#### Implementación

```python
# app/core/security.py

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)

def get_current_responsable(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Responsable:
    """Extrae usuario autenticado del JWT token."""
    payload = decode_access_token(token)
    user_id = payload.get("id")

    usuario = db.query(Responsable).filter(
        Responsable.id == user_id
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado"
        )

    return usuario

def require_role(*role_names: str):
    """Dependency para verificar roles."""
    def role_checker(
        current_user: Responsable = Depends(get_current_responsable)
    ) -> Responsable:
        if not current_user.role:
            raise HTTPException(
                status_code=403,
                detail="Usuario sin rol asignado"
            )

        if current_user.role.nombre not in role_names:
            raise HTTPException(
                status_code=403,
                detail=f"Rol '{current_user.role.nombre}' no permitido"
            )

        return current_user

    return role_checker
```

#### Uso en Endpoints

```python
# app/api/v1/routers/facturas.py

@router.delete(
    "/{factura_id}",
    status_code=204,
    dependencies=[Depends(require_role(Roles.ADMIN))]
)
def eliminar_factura(
    factura_id: int,
    current_user: Responsable = Depends(get_current_responsable),
    db: Session = Depends(get_db)
):
    """Solo admins pueden eliminar facturas."""
    # Lógica de eliminación
    pass

@router.post(
    "/{factura_id}/aprobar",
    dependencies=[Depends(require_role(Roles.ADMIN, Roles.RESPONSABLE))]
)
def aprobar_factura(
    factura_id: int,
    current_user: Responsable = Depends(get_current_responsable),
    db: Session = Depends(get_db)
):
    """Admins y responsables pueden aprobar facturas."""
    # Lógica de aprobación
    pass

@router.get("/")
def listar_facturas(
    current_user: Responsable = Depends(get_current_responsable),
    db: Session = Depends(get_db)
):
    """Todos los usuarios autenticados pueden leer."""
    # Retorna facturas según rol
    pass
```

---

## 💾 Base de Datos

### Configuración

**Archivo:** `app/core/database.py`

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Engine con pool de conexiones
engine = create_engine(
    settings.database_url,
    echo=False,  # True para debug SQL
    pool_size=20,           # Conexiones simultáneas
    max_overflow=0,         # Conexiones overflow
    pool_pre_ping=True,     # Verificar conexión activa
    pool_recycle=3600,      # Reciclar cada hora
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

def get_db():
    """Dependency para obtener sesión BD."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Modelos Principales

#### 1. **Responsable** (Usuario)

**Archivo:** `app/models/responsable.py`

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime

class Responsable(Base):
    __tablename__ = "responsables"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)

    # Autenticación
    usuario = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Información Personal
    nombre = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    telefono = Column(String(20), nullable=True)
    area = Column(String(100), nullable=True)

    # Estado
    activo = Column(Boolean, default=True, index=True)
    must_change_password = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)

    # Foreign Key
    role_id = Column(BigInteger, ForeignKey("roles.id"), nullable=True)

    # OAuth
    auth_provider = Column(String(50), default="local")  # local, microsoft, google
    oauth_id = Column(String(255), unique=True, nullable=True)
    oauth_picture = Column(String(500), nullable=True)

    # Timestamps
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    role = relationship("Role", back_populates="responsables")
    facturas = relationship("Factura", back_populates="responsable")
```

**Tabla responsables (SQL):**
```sql
CREATE TABLE responsables (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usuario VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    area VARCHAR(100),
    activo BOOLEAN DEFAULT 1,
    must_change_password BOOLEAN DEFAULT 1,
    last_login DATETIME,
    role_id BIGINT,
    auth_provider VARCHAR(50) DEFAULT 'local',
    oauth_id VARCHAR(255) UNIQUE,
    oauth_picture VARCHAR(500),
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (role_id) REFERENCES roles(id),
    INDEX idx_usuario (usuario),
    INDEX idx_email (email),
    INDEX idx_activo (activo)
);
```

#### 2. **Factura** (Principal)

**Archivo:** `app/models/factura.py`

```python
class Factura(Base):
    __tablename__ = "facturas"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)

    # Información Básica
    numero_factura = Column(String(100), index=True, nullable=False)
    cufe = Column(String(100), unique=True, index=True, nullable=True)

    # Fechas
    fecha_emision = Column(Date, index=True, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)

    # Foreign Keys
    proveedor_id = Column(BigInteger, ForeignKey("proveedores.id"), nullable=False)
    responsable_id = Column(BigInteger, ForeignKey("responsables.id"), nullable=True)

    # Montos
    subtotal = Column(Numeric(15, 2), nullable=False)
    iva = Column(Numeric(15, 2), nullable=False)
    total_a_pagar = Column(Numeric(15, 2), nullable=False)

    # Estado
    estado = Column(
        Enum('en_revision', 'aprobada', 'rechazada', 'aprobada_auto', 'pagada'),
        default='en_revision',
        index=True
    )

    # Automatización
    confianza_automatica = Column(Numeric(3, 2), nullable=True)  # 0.00 - 1.00
    fecha_procesamiento_auto = Column(DateTime, nullable=True)
    factura_referencia_id = Column(
        BigInteger,
        ForeignKey("facturas.id"),
        nullable=True
    )
    motivo_decision = Column(Text, nullable=True)

    # Clasificación
    tipo_factura = Column(
        Enum('COMPRA', 'VENTA', 'NOTA_CREDITO', 'NOTA_DEBITO'),
        nullable=True
    )
    patron_recurrencia = Column(
        Enum('FIJO', 'VARIABLE', 'UNICO', 'DESCONOCIDO'),
        nullable=True
    )

    # Matching
    concepto_principal = Column(String(500), nullable=True)
    concepto_hash = Column(String(32), index=True, nullable=True)  # MD5
    concepto_normalizado = Column(String(500), nullable=True)

    # Orden de Compra
    orden_compra_numero = Column(String(100), index=True, nullable=True)

    # Auditoría
    accion_por = Column(String(200), nullable=True)
    estado_asignacion = Column(
        Enum('sin_asignar', 'asignado', 'huerfano', 'inconsistente'),
        nullable=True
    )

    # Timestamps
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    proveedor = relationship("Proveedor", back_populates="facturas")
    responsable = relationship("Responsable", back_populates="facturas")
    items = relationship("FacturaItem", back_populates="factura", cascade="all, delete-orphan")
    workflow_history = relationship(
        "WorkflowAprobacionFactura",
        back_populates="factura",
        cascade="all, delete-orphan"
    )
```

**Índices Importantes:**
```sql
-- Búsquedas rápidas
CREATE INDEX idx_numero_factura ON facturas(numero_factura);
CREATE INDEX idx_estado ON facturas(estado);
CREATE INDEX idx_fecha_emision ON facturas(fecha_emision);
CREATE INDEX idx_proveedor_id ON facturas(proveedor_id);
CREATE INDEX idx_responsable_id ON facturas(responsable_id);

-- Matching de items
CREATE INDEX idx_concepto_hash ON facturas(concepto_hash);
CREATE INDEX idx_orden_compra ON facturas(orden_compra_numero);

-- Cursor pagination
CREATE UNIQUE INDEX idx_creado_en_id ON facturas(creado_en DESC, id DESC);
```

#### 3. **FacturaItem** (Líneas)

```python
class FacturaItem(Base):
    __tablename__ = "factura_items"

    id = Column(BigInteger, primary_key=True, index=True)
    factura_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=False)

    # Información de línea
    numero_linea = Column(Integer, nullable=False)
    descripcion = Column(String(2000), nullable=False)
    codigo_producto = Column(String(100), nullable=True)
    codigo_estandar = Column(String(100), nullable=True)

    # Cantidades y precios
    cantidad = Column(Numeric(15, 4), nullable=False)
    unidad_medida = Column(String(20), nullable=True)
    precio_unitario = Column(Numeric(15, 4), nullable=False)

    # Montos
    subtotal = Column(Numeric(15, 2), nullable=False)
    total_impuestos = Column(Numeric(15, 2), nullable=False)
    total = Column(Numeric(15, 2), nullable=False)

    # Descuentos
    descuento_porcentaje = Column(Numeric(5, 2), nullable=True)
    descuento_valor = Column(Numeric(15, 2), nullable=True)

    # Clasificación
    categoria = Column(
        Enum('software', 'hardware', 'servicio', 'consumible'),
        nullable=True
    )
    es_recurrente = Column(Boolean, default=False)

    # Normalización
    descripcion_normalizada = Column(String(2000), index=True, nullable=True)
    item_hash = Column(String(32), index=True, nullable=True)  # MD5

    # Extra
    notas = Column(Text, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    # Relación
    factura = relationship("Factura", back_populates="items")
```

#### 4. **WorkflowAprobacionFactura**

```python
class WorkflowAprobacionFactura(Base):
    __tablename__ = "workflow_aprobacion_facturas"

    id = Column(BigInteger, primary_key=True, index=True)
    factura_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=False)

    # Estado del workflow
    estado = Column(
        Enum('RECIBIDA', 'EN_ANALISIS', 'APROBADA_AUTO', 'PENDIENTE_REVISION', 'APROBADA', 'RECHAZADA'),
        nullable=False
    )

    # Usuario asignado
    responsable_asignado_id = Column(BigInteger, ForeignKey("responsables.id"), nullable=True)

    # Aprobación automática
    aprobada_por = Column(String(200), nullable=True)  # "automatica", usuario
    fecha_aprobacion = Column(DateTime, nullable=True)
    confianza = Column(Numeric(3, 2), nullable=True)  # 0.00-1.00
    motivo_aprobacion = Column(Text, nullable=True)

    # Rechazo
    rechazada_por = Column(String(200), nullable=True)
    fecha_rechazo = Column(DateTime, nullable=True)
    detalle_rechazo = Column(Text, nullable=True)
    motivo_rechazo = Column(
        Enum('INCONSISTENCIA_DATOS', 'DUPLICADA', 'MONTO_INCORRECTO', 'DOCUMENTACION', 'OTRO'),
        nullable=True
    )

    # Tipo de aprobación
    tipo_aprobacion = Column(
        Enum('AUTOMATICA', 'MANUAL', 'MASIVA', 'FORZADA'),
        default='MANUAL'
    )

    # Timestamps
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    # Relación
    factura = relationship("Factura", back_populates="workflow_history")
```

### Diagrama Entidad-Relación

```
responsables (1) ─────────── (*) facturas
   (PK: id)                  (FK: responsable_id)

roles (1) ─────────── (*) responsables
(PK: id)             (FK: role_id)

proveedores (1) ─────────── (*) facturas
  (PK: id)                 (FK: proveedor_id)

facturas (1) ─────────── (*) factura_items
 (PK: id)              (FK: factura_id)

facturas (1) ─────────── (*) workflow_aprobacion_facturas
 (PK: id)                  (FK: factura_id)

facturas (1) ─────────── (*) facturas  (self-reference)
(PK: id)               (FK: factura_referencia_id)
```

### Migraciones (Alembic)

**Archivo:** `alembic.ini`

```ini
[alembic]
sqlalchemy.url = driver://user:password@localhost/dbname
script_location = alembic
```

**Comandos de Migración:**

```bash
# Crear nueva migración (auto-genera cambios)
alembic revision --autogenerate -m "Descripción del cambio"

# Ver migraciones pendientes
alembic current
alembic history

# Aplicar todas las migraciones
alembic upgrade head

# Revertir la última migración
alembic downgrade -1

# Aplicar hasta versión específica
alembic upgrade 123abc456def
```

**Ejemplo de Migración:**

```python
# alembic/versions/129ab8035fa8_add_periodo_fields.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column(
        'facturas',
        sa.Column('periodo', sa.String(10), nullable=True)
    )
    op.create_index('idx_periodo', 'facturas', ['periodo'])

def downgrade():
    op.drop_index('idx_periodo', 'facturas')
    op.drop_column('facturas', 'periodo')
```

---

## 🔧 Servicios Principales

### 1. AuthService

**Archivo:** `app/services/auth_service.py`

```python
class AuthService:
    """Servicio de autenticación y gestión de usuarios."""

    def __init__(self, db: Session):
        self.db = db

    def crear_usuario(
        self,
        usuario: str,
        password: str,
        nombre: str,
        email: str,
        role_id: int
    ) -> Responsable:
        """Crear nuevo usuario con contraseña hasheada."""
        responsable = Responsable(
            usuario=usuario,
            hashed_password=hash_password(password),
            nombre=nombre,
            email=email,
            role_id=role_id,
            auth_provider="local"
        )
        self.db.add(responsable)
        self.db.commit()
        self.db.refresh(responsable)
        return responsable

    def validar_credenciales(
        self,
        usuario: str,
        password: str
    ) -> Optional[Responsable]:
        """Valida usuario y contraseña."""
        responsable = self.db.query(Responsable).filter(
            Responsable.usuario == usuario,
            Responsable.activo == True
        ).first()

        if not responsable:
            return None

        if not verify_password(password, responsable.hashed_password):
            return None

        return responsable

    def cambiar_password(
        self,
        responsable_id: int,
        password_actual: str,
        password_nuevo: str
    ) -> bool:
        """Cambia contraseña de usuario."""
        responsable = self.db.query(Responsable).get(responsable_id)

        if not verify_password(password_actual, responsable.hashed_password):
            return False

        responsable.hashed_password = hash_password(password_nuevo)
        responsable.must_change_password = False
        self.db.commit()
        return True
```

### 2. WorkflowAutomaticoService

**Archivo:** `app/services/workflow_automatico.py`

```python
class WorkflowAutomaticoService:
    """Servicio de automatización de aprobación de facturas."""

    def __init__(self, db: Session):
        self.db = db

    def procesar_factura_nueva(self, factura_id: int) -> dict:
        """
        Procesa una factura nueva:
        1. Asigna responsable automáticamente
        2. Compara con factura anterior del mismo proveedor
        3. Aprueba automáticamente si coincide 95%+
        """
        factura = self.db.query(Factura).get(factura_id)
        if not factura:
            return {"error": "Factura no encontrada"}

        # 1. Obtener responsable por NIT
        responsable = self._asignar_responsable(factura.proveedor_id)
        factura.responsable_id = responsable.id if responsable else None

        # 2. Buscar factura anterior del mismo proveedor
        factura_anterior = self._obtener_factura_anterior(
            factura.proveedor_id,
            factura.fecha_emision
        )

        if not factura_anterior:
            # Primera factura del proveedor
            self._guardar_workflow(
                factura_id,
                estado="PENDIENTE_REVISION",
                tipo="MANUAL"
            )
            return {"resultado": "pendiente_revision", "razon": "Primera factura"}

        # 3. Comparar items
        coincidencia = self._comparar_items(factura, factura_anterior)

        if coincidencia >= 0.95:
            # Aprobar automáticamente
            factura.estado = "aprobada_auto"
            factura.confianza_automatica = Decimal(str(coincidencia))
            factura.accion_por = "automatica"

            self._guardar_workflow(
                factura_id,
                estado="APROBADA_AUTO",
                tipo="AUTOMATICA",
                confianza=coincidencia,
                motivo=f"Coincidencia {coincidencia*100:.1f}% con factura anterior"
            )

            self.db.commit()
            return {"resultado": "aprobada_auto", "confianza": coincidencia}
        else:
            # Pendiente revisión manual
            self._guardar_workflow(
                factura_id,
                estado="PENDIENTE_REVISION",
                tipo="MANUAL"
            )
            return {
                "resultado": "pendiente_revision",
                "confianza": coincidencia,
                "razon": f"Coincidencia {coincidencia*100:.1f}% (menor al 95%)"
            }

    def _comparar_items(self, factura1: Factura, factura2: Factura) -> float:
        """
        Compara items de dos facturas.
        Retorna 0.0-1.0 (coincidencia porcentual).
        """
        if not factura1.items or not factura2.items:
            return 0.0

        items1 = sorted([i.item_hash for i in factura1.items])
        items2 = sorted([i.item_hash for i in factura2.items])

        coincidencias = len(set(items1) & set(items2))
        total = max(len(items1), len(items2))

        return coincidencias / total if total > 0 else 0.0
```

### 3. EmailService

**Archivo:** `app/services/email_service.py`

```python
class EmailService:
    """Servicio de envío de emails (SMTP)."""

    def __init__(self, settings):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.from_name = settings.smtp_from_name

    def enviar_email(
        self,
        destinatario: str,
        asunto: str,
        html: str,
        archivos: Optional[List[tuple]] = None
    ) -> bool:
        """
        Envía email HTML.
        archivos: [("archivo.pdf", contenido_bytes), ...]
        """
        try:
            servidor = smtplib.SMTP(self.smtp_host, self.smtp_port)
            servidor.starttls()
            servidor.login(self.smtp_user, self.smtp_password)

            # Crear mensaje
            mensaje = MIMEMultipart("alternative")
            mensaje["From"] = f"{self.from_name} <{self.from_email}>"
            mensaje["To"] = destinatario
            mensaje["Subject"] = asunto

            # Body HTML
            parte_html = MIMEText(html, "html", "utf-8")
            mensaje.attach(parte_html)

            # Adjuntos (opcional)
            if archivos:
                for nombre, contenido in archivos:
                    adjunto = MIMEApplication(contenido)
                    adjunto.add_header("Content-Disposition", "attachment", filename=nombre)
                    mensaje.attach(adjunto)

            # Enviar
            servidor.send_message(mensaje)
            servidor.quit()
            return True

        except Exception as e:
            logger.error(f"Error enviando email a {destinatario}: {str(e)}")
            return False
```

### 4. ComparadorItemsService

**Archivo:** `app/services/comparador_items.py`

```python
class ComparadorItemsService:
    """Compara y normaliza items de facturas."""

    @staticmethod
    def normalizar_item(descripcion: str) -> str:
        """
        Normaliza descripción de item:
        - Convierte a minúsculas
        - Elimina espacios extras
        - Quita caracteres especiales
        """
        import re

        # Minúsculas
        texto = descripcion.lower()

        # Eliminar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto).strip()

        # Eliminar caracteres especiales pero mantener alfanuméricos
        texto = re.sub(r'[^\w\s]', '', texto)

        return texto

    @staticmethod
    def generar_hash_item(descripcion: str) -> str:
        """Genera MD5 hash de item normalizado."""
        import hashlib
        normalizado = ComparadorItemsService.normalizar_item(descripcion)
        return hashlib.md5(normalizado.encode()).hexdigest()

    @staticmethod
    def calcular_similitud(texto1: str, texto2: str) -> float:
        """
        Calcula similitud entre dos textos (0.0-1.0).
        Usa algoritmo SequenceMatcher.
        """
        from difflib import SequenceMatcher

        ratio = SequenceMatcher(
            None,
            texto1.lower(),
            texto2.lower()
        ).ratio()

        return ratio
```

---

## ⚠️ Errores, Logs y Manejo de Excepciones

### Estructura de Mensajes de Error

```python
# Respuesta de error estándar (422 - Validation Error)
{
    "detail": [
        {
            "loc": ["body", "numero_factura"],
            "msg": "campo requerido",
            "type": "value_error.missing"
        }
    ]
}

# Respuesta de error general (4xx/5xx)
{
    "detail": "Usuario no encontrado",
    "error_code": "USUARIO_NO_ENCONTRADO",
    "timestamp": "2024-10-09T10:30:00Z",
    "path": "/api/v1/responsables/999"
}
```

### Excepciones Personalizadas

```python
# app/core/exceptions.py

class FacturaError(Exception):
    """Base para errores de factura."""
    pass

class FacturaNoEncontradaError(FacturaError):
    """Factura no existe."""
    http_status_code = 404
    error_code = "FACTURA_NO_ENCONTRADA"

class FacturaDuplicadaError(FacturaError):
    """Factura ya existe (mismo número + proveedor)."""
    http_status_code = 409
    error_code = "FACTURA_DUPLICADA"

class FacturaEstadoInvalidoError(FacturaError):
    """Cambio de estado inválido."""
    http_status_code = 400
    error_code = "ESTADO_INVALIDO"
```

### Sistema de Logging

**Archivo:** `app/utils/logger.py`

```python
import logging
import json
from datetime import datetime

class CustomJSONFormatter(logging.Formatter):
    """Formatea logs en JSON estructurado."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

# Configurar loggers
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        # File handler
        logging.FileHandler("logs/app.log"),
        # Console handler (formato legible)
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

**Uso:**

```python
# En servicios
logger.info(f"Procesando factura {factura_id}")
logger.warning(f"Confianza baja: {confianza}")
logger.error(f"Error conectando a BD: {error_message}", exc_info=True)
logger.debug(f"Query: {query}")
```

**Archivos de Logs:**

```
logs/
├── app.log              # Logs generales
├── error.log            # Solo errores
├── access.log           # Requests HTTP
└── automation.log       # Logs de automatización
```

---

## 🧪 Pruebas (Testing)

### Frameworks y Herramientas

- **pytest** ≥ 8.0.0: Framework de testing
- **httpx** ≥ 0.27.0: Cliente HTTP asincrónico para tests
- **pytest-cov**: Coverage de código
- **TestClient**: Cliente de test de FastAPI

### Estructura de Tests

```
tests/
├── __init__.py
├── conftest.py           # Fixtures compartidas
├── test_auth.py          # Tests de autenticación
├── test_facturas.py      # Tests de facturas
├── test_workflow.py      # Tests de workflow
├── test_services/
│   ├── test_email_service.py
│   ├── test_workflow_automatico.py
│   └── ...
└── fixtures/
    ├── usuarios.py       # Datos de test
    ├── facturas.py
    └── ...
```

### Ejemplo de Test

```python
# tests/test_facturas.py

import pytest
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy.orm import Session

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def usuario_token(client, db):
    """Crea usuario de test y retorna token."""
    respuesta = client.post("/api/v1/auth/login", json={
        "usuario": "test_user",
        "password": "test123"
    })
    return respuesta.json()["access_token"]

def test_listar_facturas_sin_autenticacion(client):
    """Test: No permite listar sin JWT token."""
    respuesta = client.get("/api/v1/facturas/")
    assert respuesta.status_code == 401
    assert "detail" in respuesta.json()

def test_listar_facturas_con_autenticacion(client, usuario_token):
    """Test: Lista facturas con token válido."""
    headers = {"Authorization": f"Bearer {usuario_token}"}
    respuesta = client.get("/api/v1/facturas/", headers=headers)
    assert respuesta.status_code == 200

    data = respuesta.json()
    assert "data" in data
    assert isinstance(data["data"], list)

def test_crear_factura_valida(client, usuario_token):
    """Test: Crea factura con datos válidos."""
    headers = {"Authorization": f"Bearer {usuario_token}"}

    payload = {
        "numero_factura": "TEST-001",
        "fecha_emision": "2024-10-09",
        "proveedor_id": 1,
        "subtotal": 1000.00,
        "iva": 190.00,
        "total_a_pagar": 1190.00
    }

    respuesta = client.post(
        "/api/v1/facturas/",
        json=payload,
        headers=headers
    )

    assert respuesta.status_code == 201
    data = respuesta.json()
    assert data["numero_factura"] == "TEST-001"

def test_crear_factura_sin_proveedor(client, usuario_token):
    """Test: Valida que proveedor sea requerido."""
    headers = {"Authorization": f"Bearer {usuario_token}"}

    payload = {
        "numero_factura": "TEST-002",
        "fecha_emision": "2024-10-09",
        # Falta proveedor_id
        "subtotal": 1000.00,
        "iva": 190.00,
        "total_a_pagar": 1190.00
    }

    respuesta = client.post(
        "/api/v1/facturas/",
        json=payload,
        headers=headers
    )

    assert respuesta.status_code == 422  # Validation Error
```

### Ejecutar Tests

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app

# Test específico
pytest tests/test_facturas.py::test_crear_factura_valida

# Modo verbose
pytest -v

# Detener al primer fallo
pytest -x

# Mostrar prints
pytest -s

# Generar reporte HTML
pytest --cov=app --cov-report=html
# Abrir: htmlcov/index.html
```

### Coverage Goal

```bash
# Verificar cobertura mínima
pytest --cov=app --cov-fail-under=80

# Salida esperada:
# Name                     Stmts   Miss  Cover   Missing
# ─────────────────────────────────────────────────────
# app/api/v1/routers       200     10    95%     45-50,67
# app/services             500     50    90%     100-120
# app/models               100      5    95%     45,67
# ─────────────────────────────────────────────────────
# TOTAL                    800     65    91%
```

---

##  Buenas Prácticas y Estándares

### Guía de Estilo del Código

#### 1. **Formato con Black**

```bash
# Formatea automáticamente todo el proyecto
black app/ tests/

# Verificar sin cambiar
black --check app/
```

**Configuración (.pyproject.toml):**
```toml
[tool.black]
line-length = 100
target-version = ['py310']
```

#### 2. **Linting con Flake8**

```bash
# Verifica estilo y errores
flake8 app/ tests/
```

**Configuración (.flake8):**
```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,.venv
ignore = E203,W503
```

#### 3. **Type Checking con MyPy**

```bash
# Verifica tipos
mypy app/

# Modo estricto
mypy --strict app/
```

**Configuración (pyproject.toml):**
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Convenciones de Código

#### Imports

```python
#  CORRECTO
from typing import Optional, List
from sqlalchemy import Column, String
from app.core.config import settings
from app.models.factura import Factura



#### Docstrings

```python
#  CORRECTO: Google-style docstrings
def procesar_factura(factura_id: int) -> dict:
    """Procesa factura con automatización inteligente.

    Realiza comparación con factura anterior y aprueba
    automáticamente si la similitud es >= 95%.

    Args:
        factura_id: ID de la factura a procesar.

    Returns:
        dict: {
            "resultado": "aprobada_auto" | "pendiente_revision",
            "confianza": float (0-1),
            "razon": str
        }

    Raises:
        FacturaNoEncontradaError: Si factura no existe.
    """
    pass

# Clases
class FacturaService:
    """Servicio para gestionar operaciones de facturas.

    Attributes:
        db: Sesión de base de datos.
        logger: Logger de la aplicación.
    """
    pass
```

#### Type Hints

```python
#  CORRECTO
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from decimal import Decimal

def obtener_facturas(
    usuario_id: int,
    estado: Optional[str] = None,
    limit: int = 10
) -> List[Factura]:
    """Obtiene facturas del usuario."""
    pass

def calcular_promedio(valores: List[Decimal]) -> Decimal:
    """Calcula promedio de valores."""
    pass


#### Constantes

```python
#  CORRECTO: En archivo separado o al inicio del módulo
# app/core/constants.py
ESTADOS_FACTURA = {
    "en_revision": "En Revisión",
    "aprobada": "Aprobada",
    "rechazada": "Rechazada"
}

CONFIANZA_AUTOMATICA_MINIMA = Decimal("0.95")
MAX_ITEMS_PER_PAGE = 500
JWT_ALGORITHM = "HS256"

# En uso:
from app.core.constants import CONFIANZA_AUTOMATICA_MINIMA

if confianza >= CONFIANZA_AUTOMATICA_MINIMA:
    aprobar_automaticamente()
```

#### Nombres Significativos

```python
#  CORRECTO
responsable_por_factura = obtener_responsable(factura.proveedor_id)
items_normalizados = normalizar_items(factura.items)
es_duplicada = verificar_duplicidad(factura)


```

### Normas de Commits

#### Formato de Mensaje

```
<tipo>(<alcance>): <descripción corta>

<descripción detallada (opcional)>

Closes #<issue-number>
```

#### Tipos de Commits

```
feat:     Nueva característica
fix:      Corrección de bug
docs:     Cambios en documentación
style:    Cambios de formato (sin lógica)
refactor: Refactorización de código
perf:     Mejora de performance
test:     Cambios en tests
ci:       Cambios en CI/CD
```

#### Ejemplos

```bash
# Bueno
git commit -m "feat(facturas): agregar validación de NIT"
git commit -m "fix(workflow): corregir cálculo de confianza en automatización"
git commit -m "docs: actualizar documentación de API endpoints"
git commit -m "refactor(services): separar lógica de email en servicios"

# Malo
git commit -m "cambios varios"
git commit -m "arreglar"
git commit -m "update"
```

### Estrategia de Ramas

```
main (producción)
 ├── develop (integración)
 │    ├── feature/auth-oauth
 │    ├── feature/automation-workflow
 │    ├── bugfix/email-service
 │    └── hotfix/security-patch
 │
 └── release/v2.1
```

**Naming Convention:**
```
feature/<descripción>      # Nuevas características
bugfix/<descripción>       # Correcciones de bugs
hotfix/<descripción>       # Fixes urgentes en producción
release/v<versión>         # Ramas de release
```

### Versionado Semántico

```
v<MAJOR>.<MINOR>.<PATCH>

v2.0.0    # Mayor: cambios API incompatibles
v2.1.0    # Minor: nuevas features compatibles
v2.1.1    # Patch: bug fixes

Ejemplos:
v1.0.0    → v2.0.0    # Breaking changes (nueva arquitectura)
v2.0.0    → v2.1.0    # Nueva feature de workflow automático
v2.1.0    → v2.1.1    # Fix en comparador de items
```

---

## 🚀 Futuras Mejoras

### Limitaciones Actuales

#### 1. **Performance de Paginación**
- Actualmente usa offset pagination para compatibilidad
- Cursor pagination está implementada pero no es default
- **Impacto:** Queries lentas con datos grandes (10k+)

**Solución:** Usar cursor pagination por defecto
```python
# Antes (offset - O(n))
SELECT * FROM facturas ORDER BY id LIMIT 500 OFFSET 10000

# Después (cursor - O(1))
SELECT * FROM facturas WHERE creado_en < '2024-10-01' ORDER BY creado_en DESC LIMIT 500
```

#### 2. **Caché de Comparaciones**
- Cada comparación de items recalcula hashes
- Sin caché distribuido (Redis)
- **Impacto:** Performance en automatización masiva

**Solución:** Implementar Redis para caché de hashes
```python
# Antes: recalcula cada vez
hash_item = calcular_hash(descripcion)

# Después: cachea en Redis
hash_item = redis.get(cache_key) or calcular_hash(descripcion)
```

#### 3. **Auditoría Básica**
- Solo registra cambios simples
- Sin seguimiento de "quién" y "cuándo" en todos los cambios
- Sin versioning de datos anteriores

**Solución:** Implementar Audit Trail completo
```python
# Guardar snapshot de datos antes/después cada cambio
class AuditLog(Base):
    id = Column(Integer, PK)
    tabla = Column(String)
    registro_id = Column(Integer)
    accion = Column(Enum("INSERT", "UPDATE", "DELETE"))
    datos_anterior = Column(JSON)
    datos_nuevo = Column(JSON)
    usuario_id = Column(Integer, FK)
    timestamp = Column(DateTime)
```

#### 4. **Notificaciones en Tiempo Real**
- Usa polling/emails
- Sin WebSockets para actualización instantánea
- Sin push notifications

**Solución:** Implementar WebSockets + Redis Pub/Sub
```python
# WebSocket para notificaciones en vivo
@app.websocket("/ws/notificaciones/{usuario_id}")
async def websocket_endpoint(websocket: WebSocket, usuario_id: int):
    await websocket.accept()
    async for message in redis_pubsub.subscribe(f"notif:{usuario_id}"):
        await websocket.send_json(message)
```

#### 5. **Escalabilidad Horizontal**
- Diseño monolítico
- Sin soporte para múltiples instancias
- Tasks en APScheduler sin distribuir

**Solución:** Arquitectura de microservicios
```
api-gateway (load balancer)
 ├── api-instance-1 (FastAPI)
 ├── api-instance-2 (FastAPI)
 ├── api-instance-3 (FastAPI)
 ├── worker-1 (Celery)
 ├── worker-2 (Celery)
 └── services externos (Redis, RabbitMQ, etc.)
```

### Roadmap Técnico (6-12 meses)

#### Q1 2025
- [ ] Implementar cursor pagination como default
- [ ] Agregar Redis para caché
- [ ] Documentación OpenAPI mejorada

#### Q2 2025
- [ ] Migrar a Celery + RabbitMQ para tasks distribuidas
- [ ] Implementar WebSockets para notificaciones en vivo
- [ ] Audit trail completo con versioning

#### Q3 2025
- [ ] Descomponer en microservicios (API, Workers, Scheduler)
- [ ] Agregar GraphQL endpoint
- [ ] Implementar API rate limiting y throttling

#### Q4 2025
- [ ] Machine Learning para predicción de aprobaciones
- [ ] Dashboard de analítica avanzada
- [ ] Internacionalización (i18n) multi-idioma

### Características Planeadas

#### **Machine Learning**
```python
# Modelo de predicción de confianza
class MLConfidencePredictor:
    """Usa ML para predecir confianza de aprobación."""

    def predecir(self, factura: Factura) -> float:
        """
        Features:
        - Similitud items con histórico
        - Desviación de montos
        - Patrón de recurrencia
        - Historia de proveedores

        Retorna: confianza (0-1)
        """
        features = self.extraer_features(factura)
        return self.modelo.predict(features)[0]
```

#### **GraphQL API**
```graphql
query {
  facturas(primeras: 10) {
    nodos {
      id
      numeroFactura
      estado
      proveedor {
        razonSocial
      }
      items {
        descripcion
        total
      }
    }
  }
}
```

#### **Dashboard Analítico**
- Tendencias de aprobación
- Heatmap de proveedores riesgosos
- Predicción de cash flow
- Anomaly detection automático

