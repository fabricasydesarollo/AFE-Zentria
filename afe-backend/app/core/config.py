# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


# Roles del sistema
class Roles:
    """
    Constantes para roles de usuario.

    NOTA TÉCNICA: Históricamente llamamos 'usuarios' a todos los usuarios
    del sistema (stored en tabla 'usuarios'). El término correcto sería
    'usuarios', pero para mantener compatibilidad con el código existente
    mantenemos la tabla 'usuarios'.

    Roles disponibles:
    - ADMIN: Acceso completo, gestiona usuarios y configuración
    - RESPONSABLE: Aprueba/rechaza facturas (el nombre real del rol de aprobador)
    - CONTADOR: Procesa pagos de facturas aprobadas, puede devolver facturas
    - VIEWER: Solo lectura, no puede aprobar/rechazar
    """
    ADMIN = "admin"
    RESPONSABLE = "responsable"  # Aprobador de facturas
    CONTADOR = "contador"  # Procesamiento contable (NUEVO 2025-11-18)
    VIEWER = "viewer"  # Solo lectura


class Settings(BaseSettings):
    # --- Core ---
    environment: str = Field("development", env="ENVIRONMENT")  

    # --- Seguridad / JWT ---
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # --- Base de datos ---
    database_url: str = Field(..., env="DATABASE_URL")

    # --- CORS ---
    backend_cors_origins: List[str] | str = Field("", env="BACKEND_CORS_ORIGINS")

    # --- Microsoft Graph (para envío de emails) ---
    graph_tenant_id: str = Field("", env="GRAPH_TENANT_ID")
    graph_client_id: str = Field("", env="GRAPH_CLIENT_ID")
    graph_client_secret: str = Field("", env="GRAPH_CLIENT_SECRET")
    graph_from_email: str = Field("", env="GRAPH_FROM_EMAIL")
    graph_from_name: str = Field("", env="GRAPH_FROM_NAME")

    # --- Microsoft OAuth (para autenticación de usuarios) ---
    # Usar el mismo tenant y client_id si se usa la misma app registration
    # O crear variables separadas si se usa una app diferente para auth
    oauth_microsoft_tenant_id: str = Field("", env="OAUTH_MICROSOFT_TENANT_ID")
    oauth_microsoft_client_id: str = Field("", env="OAUTH_MICROSOFT_CLIENT_ID")
    oauth_microsoft_client_secret: str = Field("", env="OAUTH_MICROSOFT_CLIENT_SECRET")
    oauth_microsoft_redirect_uri: str = Field("", env="OAUTH_MICROSOFT_REDIRECT_URI")
    oauth_microsoft_scopes: str = Field("openid email profile User.Read", env="OAUTH_MICROSOFT_SCOPES")

    # --- SMTP (fallback opcional) ---
    smtp_host: str = Field("", env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_user: str = Field("", env="SMTP_USER")
    smtp_password: str = Field("", env="SMTP_PASSWORD")
    smtp_from_email: str = Field("", env="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field("Sistema de Facturas", env="SMTP_FROM_NAME")
    smtp_use_tls: bool = Field(True, env="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(False, env="SMTP_USE_SSL")
    smtp_timeout: int = Field(30, env="SMTP_TIMEOUT")

    # --- Frontend URLs (para emails y redirecciones) ---
    frontend_url: str = Field("http://localhost:5173", env="FRONTEND_URL")
    api_base_url: str = Field("http://localhost:8000", env="API_BASE_URL")

    # ============================================================================
    # AUTO-CREACIÓN DE PROVEEDORES (NUEVO 2025-11-06)
    # ============================================================================
    # Configuración para auto-crear proveedores desde facturas
    # Cuando llega una factura con NIT que no tiene proveedor:
    # - Si PROVIDER_AUTO_CREATE_ENABLED=true → Crear automáticamente
    # - Si PROVIDER_AUTO_CREATE_ENABLED=false → Dejar para revisión manual
    # ============================================================================

    provider_auto_create_enabled: bool = Field(
        True,
        env="PROVIDER_AUTO_CREATE_ENABLED",
        description="Habilitar auto-creación de proveedores desde facturas"
    )

    provider_auto_create_log_audit: bool = Field(
        True,
        env="PROVIDER_AUTO_CREATE_LOG_AUDIT",
        description="Registrar auditoría completa de cada creación automática"
    )

    provider_auto_create_notify_admin: bool = Field(
        False,
        env="PROVIDER_AUTO_CREATE_NOTIFY_ADMIN",
        description="Enviar notificación a admin cuando se auto-cree proveedor"
    )

    provider_auto_create_admin_email: str = Field(
        "",
        env="PROVIDER_AUTO_CREATE_ADMIN_EMAIL",
        description="Email del admin para notificaciones de auto-creación"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
