from fastapi import APIRouter

# Importa cada módulo de rutas
from app.api.v1.routers import (
    auth,
    proveedores,
    usuarios,
    roles,
    facturas,
    automation,
    workflow,
    asignacion_nit,  #   NUEVO: Reemplazo de responsable_proveedor
    flujo_automatizacion,
    email_config,
    email_health,  # Health check para servicios de email
    admin_sync,  # Admin: Sincronización de facturas
    accounting,  # Recepción y registro de facturas por contabilidad
    dashboard,  # Dashboard optimizado
    grupos,  # Gestión de grupos multi-tenant con jerarquía
    cuarentena,  # Gestión de facturas en cuarentena (2025-12-27)
)

# Router principal con prefijo global
# PERFORMANCE: redirect_slashes=False previene redirects 307 automáticos
api_router = APIRouter(prefix="/api/v1", redirect_slashes=False)

# Endpoint raíz para verificar que la API funciona
@api_router.get("/", tags=["Root"])
def read_root():
    return {"message": "Bienvenido a la API v1 de AFE Backend"}

# Registro de módulos de rutas
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])
api_router.include_router(proveedores.router, prefix="/proveedores", tags=["Proveedores"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(facturas.router, prefix="/facturas", tags=["Facturas"])
api_router.include_router(automation.router, prefix="/automation", tags=["Automatización"])
api_router.include_router(workflow.router, tags=["Workflow Aprobación"])
api_router.include_router(asignacion_nit.router, tags=["Asignación NIT"])  #   NUEVO
api_router.include_router(flujo_automatizacion.router, tags=["Flujo de Automatización"])
api_router.include_router(email_config.router, tags=["Email Configuration"])
api_router.include_router(email_health.router, tags=["Email Health"])
api_router.include_router(admin_sync.router, tags=["Admin Sync"])  # Admin: Sincronización
api_router.include_router(accounting.router, prefix="/accounting", tags=["Contabilidad"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(grupos.router, prefix="/grupos", tags=["Grupos"])
api_router.include_router(cuarentena.router, tags=["Cuarentena"])
