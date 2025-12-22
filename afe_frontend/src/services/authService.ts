import apiClient from './api';

/**
 * Auth Service - Autenticación simple con JWT
 *
 * REFACTORED 2025-12-04: Eliminado código muerto de sistema multi-sede
 * que nunca fue implementado en el backend.
 */

export interface LoginRequest {
  usuario: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    nombre: string;
    email: string;
    usuario: string;
    area?: string;
    rol: string;
    activo: boolean;
  };
}

class AuthService {
  /**
   * Login con usuario y contraseña
   * POST /api/v1/auth/login
   */
  async login(usuario: string, password: string): Promise<TokenResponse> {
    try {
      const response = await apiClient.post<TokenResponse>(
        '/auth/login',
        { usuario, password }
      );

      // Guardar token y user en localStorage
      if (response.data.access_token) {
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }

      return response.data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Obtener usuario actual desde localStorage
   */
  getCurrentUser() {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;

    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  /**
   * Obtener token JWT
   */
  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  /**
   * Verificar si el usuario está autenticado
   */
  isAuthenticated(): boolean {
    return !!this.getToken() && !!this.getCurrentUser();
  }

  /**
   * Verificar si el token está expirado (decodificar JWT)
   */
  isTokenExpired(): boolean {
    const token = this.getToken();
    if (!token) return true;

    try {
      // Decodificar JWT
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expirationTime = payload.exp * 1000; // Convertir a milisegundos
      return Date.now() >= expirationTime;
    } catch {
      return true;
    }
  }

  /**
   * Logout - Limpiar localStorage
   */
  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  }

  /**
   * Decodificar JWT para obtener claims
   */
  getTokenClaims(): any {
    const token = this.getToken();
    if (!token) return null;

    try {
      return JSON.parse(atob(token.split('.')[1]));
    } catch {
      return null;
    }
  }
}

export const authService = new AuthService();
export default authService;
