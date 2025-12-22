from fastapi import FastAPI
from app.api.v1 import api_router
from app.core.config import settings
from app.core.lifespan import lifespan
from app.utils.cors import setup_cors


def create_app() -> FastAPI:
    """
    Factory function que crea y configura la aplicación FastAPI.

    NOTA sobre contacto en documentación:
    El email "soporte@empresa.com" en la documentación Swagger es un placeholder.
    Para cambiar el email de contacto real, editar esta función y redeployar.
    Alternativa: Parametrizar desde app.core.config.settings si es necesario.
    """
    app = FastAPI(
        title="AFE Backend",
        version="1.0.0",
        description="Backend empresarial para gestión de facturas y proveedores",
        lifespan=lifespan,  # Startup/shutdown moderno
        contact={
            "name": "Equipo Backend",
            "email": "soporte@empresa.com",  # TODO: Parametrizar o actualizar según entorno
        },
        license_info={
            "name": "MIT",
        },
    )

    # --- Configuración CORS ---
    setup_cors(app)

    # --- Rutas centralizadas ---
    app.include_router(api_router)

    return app


app = create_app()
