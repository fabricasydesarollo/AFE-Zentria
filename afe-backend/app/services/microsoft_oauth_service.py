"""
Servicio para autenticación OAuth con Microsoft Azure AD.
"""
import msal
import requests
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.usuario import Usuario


class MicrosoftOAuthService:
    """Servicio profesional para manejar autenticación OAuth con Microsoft."""

    def __init__(self):
        """Inicializa el servicio con configuración de Azure AD."""
        self.tenant_id = settings.oauth_microsoft_tenant_id
        self.client_id = settings.oauth_microsoft_client_id
        self.client_secret = settings.oauth_microsoft_client_secret
        self.redirect_uri = settings.oauth_microsoft_redirect_uri

        # IMPORTANTE: MSAL maneja automáticamente openid y profile
        # Solo incluir scopes que NO sean reservados
        scopes_str = str(settings.oauth_microsoft_scopes) if settings.oauth_microsoft_scopes else "User.Read"
        all_scopes = scopes_str.split()
        reserved_scopes = {'openid', 'profile', 'offline_access'}
        self.scopes = [s for s in all_scopes if s not in reserved_scopes]

        # URL de autorización de Microsoft
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        # Crear aplicación MSAL
        self.msal_app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Genera la URL de autorización para redirigir al usuario a Microsoft.

        Args:
            state: Estado opcional para CSRF protection

        Returns:
            URL de autorización de Microsoft

        PROMPT MODES:
        - select_account: Siempre muestra selector de cuentas (permite cambiar usuario)
        - login: Siempre pide credenciales (más restrictivo)
        - consent: Siempre pide consentimiento
        - none: No muestra UI (solo SSO silencioso)
        """
        auth_url = self.msal_app.get_authorization_request_url(
            scopes=self.scopes,
            state=state,
            redirect_uri=self.redirect_uri,
            prompt="select_account"  # Siempre muestra selector para elegir/cambiar cuenta
        )
        return auth_url

    def get_token_from_code(self, code: str) -> Dict[str, Any]:
        """
        Intercambia el código de autorización por un token de acceso.

        Args:
            code: Código de autorización recibido del callback

        Returns:
            Diccionario con tokens e información del usuario

        Raises:
            HTTPException: Si hay error al obtener el token
        """
        print(f" Intentando intercambiar código por token...")
        print(f"   Redirect URI configurado: {self.redirect_uri}")
        print(f"   Scopes solicitados: {self.scopes}")

        result = self.msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )

        print(f"   Resultado de MSAL: {result.keys() if isinstance(result, dict) else 'No es dict'}")

        if "error" in result:
            error_msg = result.get('error_description', result.get('error', 'Unknown error'))
            correlation_id = result.get('correlation_id', 'No correlation ID')
            print(f"    Error MSAL: {error_msg}")
            print(f"   Correlation ID: {correlation_id}")
            print(f"   Error completo: {result}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Microsoft OAuth Error: {error_msg}. Correlation ID: {correlation_id}"
            )

        print(f"   Token obtenido exitosamente")
        return result

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Obtiene información del usuario desde Microsoft Graph API.

        Args:
            access_token: Token de acceso de Microsoft

        Returns:
            Diccionario con información del usuario

        Raises:
            HTTPException: Si hay error al obtener la información
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Llamar a Microsoft Graph API
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error obteniendo información del usuario desde Microsoft"
            )

        user_data = response.json()

        # También obtener la foto de perfil
        photo_url = None
        try:
            photo_response = requests.get(
                "https://graph.microsoft.com/v1.0/me/photo/$value",
                headers=headers,
                timeout=10
            )
            if photo_response.status_code == 200:
                # En producción, guardar la foto en un storage y obtener URL
                # Por ahora, usar la URL del endpoint de Graph
                photo_url = "https://graph.microsoft.com/v1.0/me/photo/$value"
        except Exception:
            # Si no tiene foto, continuar sin ella
            pass

        return {
            "id": user_data.get("id"),
            "email": user_data.get("mail") or user_data.get("userPrincipalName"),
            "name": user_data.get("displayName"),
            "given_name": user_data.get("givenName"),
            "surname": user_data.get("surname"),
            "job_title": user_data.get("jobTitle"),
            "office_location": user_data.get("officeLocation"),
            "photo_url": photo_url
        }

    def get_logout_url(self) -> str:
        """
        Genera la URL de logout para Microsoft.
        Cuando se visita esta URL, cierra la sesión en Microsoft.

        Returns:
            URL de logout de Microsoft
        """
        # URL estándar de logout para Microsoft Azure AD
        logout_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri={self.redirect_uri.rsplit('/auth/microsoft/callback', 1)[0]}/login"
        )
        return logout_url

    def find_or_create_user(
        self,
        db: Session,
        user_info: Dict[str, Any],
        default_role_id: int = 2
    ) -> Usuario:
        """
        Busca o crea un usuario en base a la información de Microsoft.

        Args:
            db: Sesión de base de datos
            user_info: Información del usuario de Microsoft
            default_role_id: ID del rol por defecto (2 = usuario estándar)

        Returns:
            Usuario encontrado o creado

        Raises:
            HTTPException: Si hay error al crear el usuario
        """
        email = user_info.get("email")
        oauth_id = user_info.get("id")

        if not email or not oauth_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo obtener email o ID del usuario de Microsoft"
            )

        # Buscar usuario existente por oauth_id o email
        usuario = db.query(Usuario).filter(
            (Usuario.oauth_id == oauth_id) | (Usuario.email == email)
        ).first()

        if usuario:
            # Actualizar información del usuario existente
            usuario.oauth_id = oauth_id
            usuario.auth_provider = "microsoft"
            usuario.nombre = user_info.get("name") or usuario.nombre
            usuario.oauth_picture = user_info.get("photo_url")

            # Si el usuario tenía auth local, mantener su información
            # pero agregar capacidad de login con Microsoft

            db.commit()
            db.refresh(usuario)
            return usuario

        # Crear nuevo usuario
        # Generar username único basado en email
        username = email.split("@")[0]

        # Verificar si el username ya existe
        existing_user = db.query(Usuario).filter(
            Usuario.usuario == username
        ).first()

        if existing_user:
            # Agregar sufijo numérico si ya existe
            counter = 1
            while existing_user:
                username = f"{email.split('@')[0]}{counter}"
                existing_user = db.query(Usuario).filter(
                    Usuario.usuario == username
                ).first()
                counter += 1

        nuevo_usuario = Usuario(
            usuario=username,
            nombre=user_info.get("name", "Usuario Microsoft"),
            email=email,
            area=user_info.get("office_location") or "General",
            activo=True,
            role_id=default_role_id,
            auth_provider="microsoft",
            oauth_id=oauth_id,
            oauth_picture=user_info.get("photo_url"),
            hashed_password=None,  # No necesita password para OAuth
            must_change_password=False  # No aplica para OAuth
        )

        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)

        return nuevo_usuario


# Instancia singleton del servicio
microsoft_oauth_service = MicrosoftOAuthService()
