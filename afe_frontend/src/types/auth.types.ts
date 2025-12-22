/**
 * Authentication Types
 *
 * REFACTORED 2025-12-04: Eliminado código muerto de sistema multi-sede/empresa
 * que nunca fue implementado en el backend.
 *
 * ENHANCED 2025-12-04: Agregado soporte multi-tenant con grupos jerárquicos
 */

// Información básica de grupo (para lista en usuario)
export interface GrupoBasico {
  id: number;
  codigo: string;
  nombre: string;
  nivel: number;  // Nivel en jerarquía (1=raíz, 2=hijo, 3=nieto...)
  grupo_padre_id: number | null;  // NULL = grupo raíz (Vista Global para SuperAdmin)
}

export interface User {
  id: number;
  nombre: string;
  email: string;
  usuario: string;
  area?: string;
  rol: string;
  activo: boolean;

  // Multi-tenant: Grupos del usuario
  grupo_id?: number;  // Grupo actual/principal
  grupos?: GrupoBasico[];  // Lista de todos los grupos del usuario
  grupo_principal_id?: number;  // Grupo por defecto al hacer login
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isLoggedIn: boolean;

  // Métodos
  login: (usuario: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  error?: string | null;
}

export interface TokenPayload {
  sub: string;
  exp: number;
  iat: number;
}
