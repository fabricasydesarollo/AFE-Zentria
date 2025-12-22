/**
 * Custom hook for fetching advanced dashboard statistics
 * Connects to backend endpoints for charts and analytics
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../../services/api';

// Types for monthly summary statistics
// CORRECTED: Only REAL approval states (no "pendiente" which doesn't exist in backend)
export interface MonthlyStats {
  periodo: string; // "2024-10" format
  periodo_display: string; // "Oct 2024" format
  total_facturas: number;
  monto_total: number;
  subtotal: number;
  iva: number;
  facturas_por_estado: {
    en_revision: number;
    aprobada: number;
    aprobada_auto: number;
    rechazada: number;
  };
}

// Types for workflow statistics
export interface WorkflowStats {
  total_pendientes: number;
  total_en_revision: number;
  total_aprobadas: number;
  total_aprobadas_auto: number;
  total_rechazadas: number;
  pendientes_antiguas: number;
  tiempo_promedio_aprobacion_horas?: number;
  tasa_aprobacion_automatica: number;
}

// Types for comparison statistics
export interface ComparisonStats {
  facturas_evaluadas: number;
  aprobadas_automaticamente: number;
  requieren_revision: number;
  tasa_aprobacion_auto: number;
  alertas_frecuentes: Array<{
    tipo_alerta: string;
    cantidad: number;
  }>;
}

interface UseDashboardStatsReturn {
  monthlyStats: MonthlyStats[];
  workflowStats: WorkflowStats | null;
  comparisonStats: ComparisonStats | null;
  loading: boolean;
  error: string;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch all dashboard statistics from backend
 */
export const useDashboardStats = (): UseDashboardStatsReturn => {
  const [monthlyStats, setMonthlyStats] = useState<MonthlyStats[]>([]);
  const [workflowStats, setWorkflowStats] = useState<WorkflowStats | null>(null);
  const [comparisonStats, setComparisonStats] = useState<ComparisonStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAllStats = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      // CORRECTED: Fetch monthly summary WITH STATE BREAKDOWN (new endpoint)
      const monthlyResponse = await apiClient.get<any[]>(
        '/facturas/periodos/resumen-detallado'
      );

      // NOTE: These endpoints don't exist yet - will be implemented in Phase 2
      // For now, initialize with null/empty data
      const workflowResponse = { data: null };
      const comparisonResponse = { data: null };

      // Transform monthly data to include display format
      const transformedMonthly = ((monthlyResponse.data || []) as any[])
        .map((item: any) => {
          // Handle both "YYYY-MM" format and separate año/mes fields
          const periodo = item.periodo || `${item.año}-${String(item.mes).padStart(2, '0')}`;
          const parts = periodo.split('-');
          if (parts.length !== 2) {
            return null;
          }
          const [year, month] = parts;
          const monthNames = [
            'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
            'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
          ];
          const monthIndex = parseInt(month, 10) - 1;
          const monthDisplay = monthNames[monthIndex] || 'Mes';

          return {
            periodo: periodo,
            periodo_display: `${monthDisplay} ${year}`,
            total_facturas: item.total_facturas || 0,
            monto_total: item.monto_total || 0,
            subtotal: item.subtotal_total || item.subtotal || 0,
            iva: item.iva_total || item.iva || 0,
            // CORRECTED: Only REAL approval states (no "pendiente")
            facturas_por_estado: item.facturas_por_estado || {
              en_revision: 0,
              aprobada: 0,
              aprobada_auto: 0,
              rechazada: 0,
            },
          };
        })
        .filter((item: any) => item !== null)
        .slice(0, 6) // Take only the last 6 months
        .reverse(); // Reverse to show oldest first in charts

      setMonthlyStats(transformedMonthly as any);
      setWorkflowStats(workflowResponse.data);
      setComparisonStats(comparisonResponse.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar estadísticas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllStats();
  }, [fetchAllStats]);

  return {
    monthlyStats,
    workflowStats,
    comparisonStats,
    loading,
    error,
    refetch: fetchAllStats,
  };
};
