/**
 * Microsoft OAuth Authentication Service
 * Maneja el flujo de autenticación con Microsoft Azure AD
 */

import apiClient from './api';

export interface MicrosoftAuthResponse {
  authorization_url: string;
  state: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    nombre: string;
    email: string;
    usuario: string;
    area: string;
    rol: string;
    activo: boolean;
    created_at: string;
  };
}

class MicrosoftAuthService {
  /**
   * Inicia el flujo de autenticación con Microsoft
   * Obtiene la URL de autorización y redirige al usuario
   */
  async loginWithMicrosoft(): Promise<void> {
    try {
      const response = await apiClient.get<MicrosoftAuthResponse>(
        '/auth/microsoft/authorize'
      );

      const { authorization_url, state } = response.data;

      // Guardar state en sessionStorage para validación CSRF
      sessionStorage.setItem('oauth_state', state);

      // Redirigir a Microsoft
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Error iniciando autenticación con Microsoft:', error);
      throw new Error('No se pudo iniciar sesión con Microsoft. Intente nuevamente.');
    }
  }

  /**
   * Procesa el callback de Microsoft OAuth
   * Intercambia el código por un token JWT
   */
  async handleCallback(code: string, state: string): Promise<AuthTokenResponse> {
    try {
      // Validar state (CSRF protection)
      const storedState = sessionStorage.getItem('oauth_state');
      if (storedState !== state) {
        throw new Error('Estado de seguridad inválido. Posible ataque CSRF.');
      }

      // Intercambiar código por token
      const response = await apiClient.get<AuthTokenResponse>(
        `/auth/microsoft/callback`,
        {
          params: { code, state },
        }
      );

      // Limpiar state del storage
      sessionStorage.removeItem('oauth_state');

      return response.data;
    } catch (error: any) {
      console.error('Error en callback de Microsoft:', error);
      throw new Error(
        error.response?.data?.detail ||
          'Error al procesar la autenticación con Microsoft.'
      );
    }
  }

  /**
   * Verifica si estamos en un callback de Microsoft OAuth
   */
  isOAuthCallback(): boolean {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.has('code') && urlParams.has('state');
  }

  /**
   * Obtiene los parámetros del callback OAuth
   */
  getCallbackParams(): { code: string; state: string } | null {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    if (code && state) {
      return { code, state };
    }

    return null;
  }
}

export const microsoftAuthService = new MicrosoftAuthService();
