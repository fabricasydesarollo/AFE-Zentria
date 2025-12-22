from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app.core.config import settings

def setup_cors(app: FastAPI) -> None:
    """
    Configura CORS para la aplicación FastAPI de forma centralizada.
    """
    origins = []

    if settings.backend_cors_origins:
        if isinstance(settings.backend_cors_origins, str):
            # Permitir lista separada por comas en `.env`
            origins = [o.strip() for o in settings.backend_cors_origins.split(",") if o.strip()]
        else:
            origins = list(settings.backend_cors_origins)

    # En desarrollo, permitir todos los orígenes si no hay configuración
    if not origins or settings.environment == "development":
        origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
