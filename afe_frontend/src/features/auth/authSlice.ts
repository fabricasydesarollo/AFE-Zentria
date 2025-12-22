import { createSlice } from '@reduxjs/toolkit';
import { User } from '../../types/auth.types';

/**
 * Authentication Slice
 *
 * REFACTORED 2025-12-04: Simplificado a autenticación simple con JWT
 * Eliminado código muerto de sistema multi-sede que nunca fue implementado.
 *
 * ENHANCED 2025-12-04: Agregado soporte multi-tenant con grupos jerárquicos
 */

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
}

const storedUser = localStorage.getItem('user');
const initialState: AuthState = {
  user: storedUser ? JSON.parse(storedUser) : null,
  token: localStorage.getItem('access_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),
  loading: false,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    /**
     * setCredentials: Almacenar credenciales de autenticación
     * ENHANCED: Ahora también maneja grupo_id para multi-tenancy
     */
    setCredentials: (state, action) => {
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.isAuthenticated = true;
      localStorage.setItem('access_token', action.payload.token);
      localStorage.setItem('user', JSON.stringify(action.payload.user));

      /**
       * ARQUITECTURA KISS 2025-12-09: Vista Global para SuperAdmin
       *
       * SuperAdmin:
       * - NO se guarda grupo_id en localStorage al hacer login
       * - Inicia en vista global (ve facturas de todos los grupos)
       * - Puede cambiar manualmente a un grupo específico vía GrupoSelector
       *
       * Otros roles:
       * - SÍ se guarda grupo_id para filtrar automáticamente
       */
      const esSuperAdmin = action.payload.user.rol?.toLowerCase() === 'superadmin';

      if (!esSuperAdmin) {
        // Solo guardar grupo_id para usuarios NO-SuperAdmin
        if (action.payload.user.grupo_id) {
          localStorage.setItem('grupo_id', action.payload.user.grupo_id.toString());
        } else if (action.payload.user.grupo_principal_id) {
          localStorage.setItem('grupo_id', action.payload.user.grupo_principal_id.toString());
        } else if (action.payload.user.grupos && action.payload.user.grupos.length > 0) {
          // Fallback: usar el primer grupo de la lista
          localStorage.setItem('grupo_id', action.payload.user.grupos[0].id.toString());
        }
      }
      // SuperAdmin: NO se guarda grupo_id → Vista global por defecto
    },

    /**
     * logout: Limpiar toda la información de autenticación
     * ENHANCED: También limpia grupo_id
     */
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      localStorage.removeItem('grupo_id');  // Limpiar grupo al cerrar sesión
    },

    /**
     * setLoading: Control de estado de carga
     */
    setLoading: (state, action) => {
      state.loading = action.payload;
    },

    /**
     * updateUser: Actualizar datos del usuario actual
     * Útil para refrescar perfil después de edición sin cerrar sesión
     */
    updateUser: (state, action) => {
      state.user = action.payload;
      localStorage.setItem('user', JSON.stringify(action.payload));
    },
  },
});

export const { setCredentials, logout, setLoading, updateUser } = authSlice.actions;
export default authSlice.reducer;
export type { User };
