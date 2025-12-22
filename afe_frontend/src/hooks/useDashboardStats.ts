/**
 * Hook personalizado para estadísticas del dashboard
 *
 * Maneja la carga de datos, estados de loading/error y refetch.
 * Sincronizado automáticamente con el grupo seleccionado (multi-tenant).
 */

import { useState, useEffect, useCallback } from 'react';
import { dashboardApi } from '../services/dashboard.api';
import { EstadisticasGraficasResponse } from '../types/dashboard.types';
import { useAppSelector } from '../app/hooks';

interface UseDashboardStatsReturn {
  stats: EstadisticasGraficasResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Hook para obtener estadísticas del dashboard
 *
 * Características:
 * - Auto-refetch cuando cambia el grupo seleccionado
 * - Manejo de estados loading/error
 * - Función refetch manual
 * - Integración con Redux para grupo actual
 *
 * Uso:
 * ```tsx
 * const { stats, loading, error, refetch } = useDashboardStats();
 * ```
 *
 * @returns Objeto con estadísticas, estados y función refetch
 */
export const useDashboardStats = (): UseDashboardStatsReturn => {
  const [stats, setStats] = useState<EstadisticasGraficasResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Obtener grupo seleccionado desde Redux (si existe)
  // NOTA: Si tu app no tiene estado de grupo en Redux, puedes usar localStorage directamente
  const grupoId = useAppSelector((state) => {
    // Ajustar según la estructura de tu Redux store
    // Ejemplo: state.grupo?.selectedGrupoId
    return localStorage.getItem('grupo_id');
  });

  /**
   * Función para cargar estadísticas
   */
  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // El header X-Grupo-Id se agrega automáticamente en el interceptor
      const data = await dashboardApi.getStats();

      setStats(data);
    } catch (err: any) {
      console.error('[useDashboardStats] Error al cargar estadísticas:', err);

      // Manejar errores específicos
      if (err.response?.status === 403) {
        setError('No tienes permisos para ver estas estadísticas.');
      } else if (err.response?.status === 401) {
        setError('Sesión expirada. Por favor, inicia sesión nuevamente.');
      } else {
        setError(
          err.response?.data?.detail ||
          'Error al cargar estadísticas del dashboard. Por favor, intenta de nuevo.'
        );
      }
    } finally {
      setLoading(false);
    }
  }, []); // No depende de grupoId porque el interceptor lo maneja

  /**
   * Cargar estadísticas al montar y cuando cambia el grupo
   */
  useEffect(() => {
    fetchStats();
  }, [fetchStats, grupoId]); // Re-fetch cuando cambia el grupo

  /**
   * Función pública para refetch manual
   */
  const refetch = useCallback(async () => {
    await fetchStats();
  }, [fetchStats]);

  return {
    stats,
    loading,
    error,
    refetch,
  };
};

export default useDashboardStats;
