import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../app/hooks';
import { setCredentials, setLoading } from '../features/auth/authSlice';
import authService from '../services/authService';
import { TokenResponse } from '../services/authService';

/**
 * useLogin Hook - Login simple con JWT
 *
 * REFACTORED 2025-12-04: Simplificado a login directo
 * Eliminado sistema multi-sede de 2-pasos que nunca fue implementado.
 *
 * ENHANCED 2025-12-04: Soporte multi-tenant con grupos
 * - setCredentials ahora inicializa grupo_id automáticamente en localStorage
 * - Backend debe retornar user.grupos[] en la respuesta del login
 */

export interface LoginState {
  error: string | null;
  isLoading: boolean;
}

const initialState: LoginState = {
  error: null,
  isLoading: false,
};

export const useLogin = () => {
  const [state, setState] = useState<LoginState>(initialState);
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  /**
   * Login con usuario y contraseña
   */
  const handleLogin = async (usuario: string, password: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    dispatch(setLoading(true));

    try {
      const response: TokenResponse = await authService.login(usuario, password);

      // Actualizar Redux state
      // NOTA: setCredentials automáticamente inicializa grupo_id en localStorage
      // basándose en user.grupo_principal_id o user.grupos[0].id
      dispatch(
        setCredentials({
          user: response.user,
          token: response.access_token,
        })
      );

      // Actualizar state local
      setState((prev) => ({
        ...prev,
        isLoading: false,
      }));

      // Navegar al dashboard
      navigate('/dashboard');

      return response;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        'Error de autenticación. Verifica tus credenciales.';

      setState((prev) => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
      dispatch(setLoading(false));

      throw err;
    }
  };

  /**
   * Limpiar error
   */
  const clearError = () => {
    setState((prev) => ({ ...prev, error: null }));
  };

  /**
   * Reset del estado
   */
  const reset = () => {
    setState(initialState);
  };

  return {
    ...state,
    handleLogin,
    clearError,
    reset,
  };
};
