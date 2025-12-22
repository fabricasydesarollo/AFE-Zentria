# AFE Backend - Sistema de Gestión de Facturas Electrónicas


**Stack:** FastAPI + MySQL + React + Alembic


---

## Índice

1. [Quickstart](#quickstart)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Módulos Principales](#módulos-principales)
4. [Automatización Completa](#automatización-completa)
5. [Configuración](#configuración)
6. [Deployment](#deployment)
7. [Documentación Técnica](#documentación-técnica)

---

## Quickstart

### Requisitos
- Python 3.9+
- MySQL 8.0+
- Node.js 18+ (para frontend)

### Instalación Backend

```bash
# 1. Clonar y entrar al proyecto
cd afe-backend

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Ejecutar migraciones
alembic upgrade head

# 6. Inicializar datos base (opcional)
python scripts/init_db.py

# 7. Levantar servidor
uvicorn app.main:app --reload --port 8000
```

**Servidor corriendo en:** http://localhost:8000
**Documentación API:** http://localhost:8000/docs

### Instalación Frontend

```bash
cd frontend
npm install
npm run dev
# Frontend en http://localhost:5173
```

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  Dashboard • Facturas • Workflow Aprobación • Configuración    │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP REST API
┌────────────────────────▼────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│  API Routes                                                     │
│  ├─ /facturas          (CRUD facturas)                         │
│  ├─ /clientes          (Gestión clientes)                      │
│  ├─ /workflow          (Aprobación facturas)                   │
│  ├─ /email-config      (Config extracción)                     │
│  └─ /export            (Exportar Excel)                        │
├─────────────────────────────────────────────────────────────────┤
│  Services                                                       │
│  ├─ Workflow Service        (Lógica aprobación)                │
│  ├─ Export Service          (Generación Excel)                 │
│  ├─ Inicialización Sistema  (Setup automático)                 │
│  └─ Email Config Service    (Config extractor)                 │
├─────────────────────────────────────────────────────────────────┤
│  Database (SQLAlchemy + Alembic)                               │
│  └─ MySQL                                                       │
└─────────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              INVOICE EXTRACTOR (Módulo externo)                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Microsoft Graph API → Extracción XML → Parse → Ingest  │  │
│  └─────────────────────────────────────────────────────────┘  │
│  • Extracción incremental (desde última ejecución)             │
│  • Límite: 10,000 correos/ejecución                           │
│  • Config desde API: /email-config/configuracion-extractor     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Módulos Principales

### 1. Sistema de Facturas

**Archivos:** `app/models/factura.py`, `app/crud/factura.py`, `app/api/v1/routers/facturas.py`

**Funcionalidades:**
- CRUD completo de facturas
- Comparación de totales (XML vs cálculo por ítems)
- Clasificación automática por mes
- Búsqueda y filtrado avanzado
- Paginación empresarial (10,000+ registros)

**Endpoints principales:**
```
GET    /api/v1/facturas              # Listar con filtros
GET    /api/v1/facturas/{id}         # Detalle
POST   /api/v1/facturas              # Crear
PUT    /api/v1/facturas/{id}         # Actualizar
DELETE /api/v1/facturas/{id}         # Eliminar
GET    /api/v1/facturas/export       # Exportar Excel
```

### 2. Workflow de Aprobación

**Archivos:** `app/services/workflow_automatico.py`, `app/api/v1/routers/workflow.py`

**Funcionalidades:**
- Aprobación automática de facturas
- Estados: PENDIENTE → APROBADA/RECHAZADA
- Reglas configurables por mes
- Comparación inteligente de totales
- Historial de cambios

**Flujo:**
```
1. Factura ingresada → Estado: PENDIENTE
2. Sistema valida:
   ✓ Total XML vs calculado (tolerancia ±2)
   ✓ Mes de clasificación
   ✓ Datos completos
3. Si pasa validación → APROBADA
4. Si falla → RECHAZADA (con motivo)
```

**Endpoints:**
```
POST /api/v1/workflow/ejecutar-mes-anterior  # Aprobar mes anterior
GET  /api/v1/workflow/estadisticas           # Stats del workflow
```

### 3. Sistema de Extracción Incremental

**Archivos:** Ver `SISTEMA_EXTRACCION_INCREMENTAL.md`

**Funcionalidades:**
- Extracción desde Microsoft Graph API
- Modo incremental (solo correos nuevos)
- Primera ejecución: últimos 30 días
- Ejecuciones posteriores: desde última vez
- Sin pérdida de datos (límite 10,000)

**Configuración:**
```
GET /api/v1/email-config/configuracion-extractor-public
```

### 4. Exportación Excel Empresarial

**Archivos:** `app/services/export_service.py`

**Funcionalidades:**
- Exportación optimizada (10,000+ registros)
- Formato profesional (anchos de columna, headers)
- Filtros aplicados (mes, estado, etc.)
- Streaming para grandes volúmenes

**Uso:**
```
GET /api/v1/facturas/export?mes=2024-12&estado=APROBADA
```

### 5. Gestión de Clientes

**Archivos:** `app/models/cliente.py`, `app/crud/cliente.py`

**Funcionalidades:**
- CRUD de clientes
- Sincronización automática desde facturas
- Deduplicación por NIT
- Validación de campos

---

## Automatización Completa

### Flujo Automático End-to-End

```
1. INVOICE_EXTRACTOR (Módulo independiente)
   ├─ Descarga correos desde Microsoft Graph
   ├─ Extrae XMLs de facturas
   ├─ Parse y validación
   └─ INSERT en tabla `facturas` (estado: PENDIENTE)
           │
           ▼
2. AFE-BACKEND (Automatización)
   ├─ Script detecta facturas pendientes
   ├─ Workflow automático por cada factura:
   │  ├─ Identifica NIT del proveedor
   │  ├─ Asigna al responsable
   │  ├─ Compara item por item con mes anterior
   │  ├─ Si es idéntica → APROBADA AUTO  
   │  └─ Si hay diferencias → EN REVISIÓN 
   └─ Actualiza estados en BD
```

### Opción 1: Ejecución Manual (Recomendado para inicio)

**Después de ejecutar invoice_extractor:**

```bash
# 1. Extraer facturas (invoice_extractor)
cd ../invoice_extractor
python -m src.main

# 2. Procesar facturas pendientes (afe-backend)
cd ../afe-backend
python scripts/procesar_facturas_pendientes.py --limite 100
```

**Salida esperada:**
```
======================================================================
PROCESAMIENTO AUTOMÁTICO DE FACTURAS PENDIENTES
======================================================================

 Facturas encontradas: 45
 Iniciando procesamiento...

[1/45] Procesando factura FE-001...
    APROBADA AUTOMÁTICAMENTE
[2/45] Procesando factura FE-002...
    EN REVISIÓN (similitud: 87%)
...

======================================================================
RESUMEN DEL PROCESAMIENTO
======================================================================
Total procesadas:              45
Exitosas:                      45
  ├─ Aprobadas automáticamente: 38
  └─ Requieren revisión:        7
Errores:                       0
======================================================================
```

### Opción 2: API Endpoint (Para integración)

**Endpoint:**
```http
POST /api/v1/workflow/procesar-lote?limite=100
```

**Ejemplo con curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/workflow/procesar-lote?limite=100"
```

**Response:**
```json
{
  "total_procesadas": 45,
  "exitosas": 45,
  "errores": [],
  "workflows_creados": [
    {
      "factura_id": 1234,
      "workflow_id": 567,
      "estado": "APROBADA_AUTO"
    },
    ...
  ]
}
```

### Opción 3: Automatización con Cron (Producción)

**Linux/Mac** - Agregar a crontab:
```bash
# Ejecutar cada hora
0 * * * * cd /ruta/afe-backend && python scripts/procesar_facturas_pendientes.py --limite 200 >> /var/log/workflow-auto.log 2>&1
```

**Windows** - Programador de Tareas:
```powershell
# Crear tarea programada
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "C:\ruta\afe-backend\scripts\procesar_facturas_pendientes.py"
$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"
Register-ScheduledTask -TaskName "WorkflowFacturas" -Action $action -Trigger $trigger
```

### Opción 4: Scheduler Integrado (Avanzado)

Usar **APScheduler** o **Celery** dentro de la aplicación:

```python
# app/tasks/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.workflow_automatico import WorkflowAutomaticoService

def procesar_facturas_job():
    db = SessionLocal()
    try:
        servicio = WorkflowAutomaticoService(db)
        # Lógica de procesamiento
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(procesar_facturas_job, 'interval', hours=1)
scheduler.start()
```

### Estados del Workflow

| Estado | Descripción | Acción Requerida |
|--------|-------------|------------------|
| **APROBADA_AUTO** | Idéntica al mes anterior | Ninguna - Ya aprobada   |
| **PENDIENTE_REVISION** | Tiene diferencias | Revisión manual |
| **EN_REVISION** | Asignada a responsable | Aprobar o rechazar |
| **APROBADA_MANUAL** | Revisada y aprobada | Ninguna |
| **RECHAZADA** | No procede | Ninguna |

### Consultar Estado del Workflow

**Dashboard general:**
```bash
curl http://localhost:8000/api/v1/workflow/dashboard
```

**Facturas pendientes de un responsable:**
```bash
curl "http://localhost:8000/api/v1/workflow/mis-facturas-pendientes?responsable_id=1"
```

**Detalle de una factura:**
```bash
curl http://localhost:8000/api/v1/workflow/factura-detalle/1234
```

---

## Configuración

### Variables de Entorno (`.env`)

```bash
# Base de datos
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/afe_db

# Seguridad
SECRET_KEY=tu-secret-key-super-segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS (Frontend)
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Microsoft Graph (para invoice_extractor)
TENANT_ID_CORREOS=tu-tenant-id
CLIENT_ID_CORREOS=tu-client-id
CLIENT_SECRET_CORREOS=tu-client-secret

# Logging
LOG_LEVEL=INFO
```

### Migraciones Alembic

```bash
# Crear nueva migración
alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Ver historial
alembic history
```

### Inicialización del Sistema

```bash
# Script automático de inicialización
python scripts/init_db.py

# Crea:
# - Usuario admin por defecto
# - Responsables del sistema
# - Configuraciones base
```

---

## Deployment

### Producción con Gunicorn

```bash
# Instalar Gunicorn
pip install gunicorn

# Ejecutar
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Construir y ejecutar
docker build -t afe-backend .
docker run -p 8000:8000 --env-file .env afe-backend
```

### Nginx (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name api.tudominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## Documentación Técnica

Este documento único consolida toda la información técnica del sistema:
- Arquitectura general end-to-end
- Módulo de extracción automática (Microsoft Graph)
- Módulo de clasificación de proveedores (Enterprise)
- Módulo de workflow de auto-aprobación
- Sistema de notificaciones
- Base de datos y migraciones
- Operación, mantenimiento y troubleshooting
- KPIs y monitoreo

### Estructura del Proyecto

```
afe-backend/
├── alembic/                    # Migraciones de BD
├── app/
│   ├── api/v1/routers/        # Endpoints REST
│   ├── core/                  # Config, seguridad, DB
│   ├── crud/                  # Operaciones de BD
│   ├── models/                # Modelos SQLAlchemy
│   ├── schemas/               # Schemas Pydantic
│   └── services/              # Lógica de negocio
├── frontend/                  # Aplicación React
├── scripts/                   # Scripts de utilidad
├── .env.example              # Plantilla de variables
├── requirements.txt          # Dependencias Python
└── README.md                 # Este archivo
```

### Modelos de Base de Datos

**Principales tablas:**

```
facturas                       # Facturas electrónicas
├── id
├── numero_factura
├── fecha_emision
├── total_factura
├── mes_clasificado
├── estado_aprobacion
└── cliente_id (FK)

clientes                       # Clientes/Proveedores
├── id
├── nit
├── nombre
└── correo

factura_items                  # Ítems de factura
├── id
├── factura_id (FK)
├── descripcion
├── cantidad
├── precio_unitario
└── total_item

cuentas_correo                 # Config extracción
├── id
├── email
├── max_correos_por_ejecucion
├── ventana_inicial_dias
├── ultima_ejecucion_exitosa
└── fecha_ultimo_correo_procesado

historial_extracciones         # Historial de extracciones
├── id
├── cuenta_correo_id (FK)
├── fecha_ejecucion
├── correos_procesados
├── facturas_creadas
└── exito
```

### Testing

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=app tests/

# Test específico
pytest tests/test_facturas.py
```

### Logging

```python
# El sistema usa logging estándar de Python
import logging

logger = logging.getLogger(__name__)
logger.info("Mensaje informativo")
logger.error("Error detectado")
```

**Logs se almacenan en:**
- Desarrollo: `stdout`
- Producción: `/var/log/afe-backend/app.log`

---

## Troubleshooting

### Error: Conexión a BD rechazada
```bash
# Verificar que MySQL esté corriendo
sudo systemctl status mysql

# Verificar credenciales en .env
cat .env | grep DATABASE_URL
```

### Error: ImportError en módulos
```bash
# Reinstalar dependencias
pip install --force-reinstall -r requirements.txt
```

### Error: Alembic no encuentra migraciones
```bash
# Verificar que alembic.ini existe
# Regenerar migraciones
alembic revision --autogenerate -m "fix"
alembic upgrade head
```

---

## Soporte y Contribución

**Contacto:** Tu equipo de desarrollo

**Reporte de bugs:** Crear issue en el repositorio

**Contribuir:**
1. Fork del proyecto
2. Crear branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m "Agregar nueva funcionalidad"`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

---

