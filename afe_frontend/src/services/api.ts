import axios from 'axios';

/**
 * API Client Configuration
 * Configuración centralizada para todas las llamadas al backend
 *
 * ENHANCED 2025-12-04: Agregado interceptor para X-Grupo-Id multi-tenant
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor para agregar token y grupo_id
apiClient.interceptors.request.use(
  (config) => {
    // 1. Agregar token de autenticación
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 2. MULTI-TENANT: Agregar grupo_id header automáticamente
    // El backend filtrará todos los datos según este grupo
    const grupoId = localStorage.getItem('grupo_id');
    if (grupoId) {
      config.headers['X-Grupo-Id'] = grupoId;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor para manejo de errores
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Solo redirigir si NO estamos en la página de login y hay un token almacenado
      const currentPath = window.location.pathname;
      const hasToken = localStorage.getItem('access_token');

      if (currentPath !== '/login' && hasToken) {
        // Token expirado o inválido - redirigir a login
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        localStorage.removeItem('grupo_id');  // Limpiar grupo también
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
