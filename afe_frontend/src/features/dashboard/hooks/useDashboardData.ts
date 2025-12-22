/**
 * Custom hook for managing dashboard data
 * Handles fetching, filtering, and calculating statistics for facturas
 * Implements automatic cleanup by loading from appropriate endpoints based on selected period
 */

import { useState, useEffect, useCallback } from 'react';
import type { Factura, DashboardStats, EstadoFactura, VistaFacturas } from '../types';
import { facturasService } from '../services/facturas.service';
import { isEstadoAprobado, isEstadoRechazado } from '../utils';
import apiClient from '../../../services/api';

interface UseDashboardDataParams {
  userRole?: string;
  filterEstado: EstadoFactura | 'todos';
  vistaFacturas: VistaFacturas;
  mesSeleccionado?: number;
  anioSeleccionado?: number;
}

interface UseDashboardDataReturn {
  facturas: Factura[];
  stats: DashboardStats;
  totalTodasFacturas: number;
  totalAsignadas: number;
  loading: boolean;
  error: string;
  loadData: () => Promise<void>;
  clearError: () => void;
}

export const useDashboardData = ({
  userRole,
  filterEstado,
  vistaFacturas,
  mesSeleccionado,
  anioSeleccionado,
}: UseDashboardDataParams): UseDashboardDataReturn => {
  const [facturas, setFacturas] = useState<Factura[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    total: 0,
    pendientes: 0,
    en_revision: 0,
    aprobadas: 0,
    aprobadas_auto: 0,
    rechazadas: 0,
  });
  const [totalTodasFacturas, setTotalTodasFacturas] = useState(0);
  const [totalAsignadas, setTotalAsignadas] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const calculateStats = useCallback((allFacturas: Factura[]): DashboardStats => {
    return {
      total: allFacturas.length,
      pendientes: allFacturas.filter((f) => f.estado === 'en_revision').length,
      en_revision: allFacturas.filter((f) => f.estado === 'en_revision').length,
      aprobadas: allFacturas.filter((f) => isEstadoAprobado(f.estado)).length,
      aprobadas_auto: allFacturas.filter((f) => f.estado === 'aprobada_auto').length,
      rechazadas: allFacturas.filter((f) => isEstadoRechazado(f.estado)).length,
    };
  }, []);

  const filterByEstado = useCallback(
    (allFacturas: Factura[]): Factura[] => {
      if (filterEstado === 'todos') {
        return allFacturas;
      }
      return allFacturas.filter((f) => f.estado === filterEstado);
    },
    [filterEstado]
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      // Determine if viewing historical data or current month
      const hoy = new Date();
      const mesActual = hoy.getMonth() + 1;
      const anioActual = hoy.getFullYear();

      const isHistorico =
        (mesSeleccionado !== mesActual || anioSeleccionado !== anioActual) &&
        (mesSeleccionado !== undefined && anioSeleccionado !== undefined);

      if (isHistorico) {
        // Load historical data from /dashboard/historico endpoint
        const response = await apiClient.get('/dashboard/historico', {
          params: {
            mes: mesSeleccionado,
            anio: anioSeleccionado,
          },
        });

        const allFacturas = response.data?.facturas || [];
        const filtered = filterByEstado(allFacturas);

        setFacturas(filtered);
        setStats(calculateStats(allFacturas));
        setTotalTodasFacturas(response.data?.total_facturas || allFacturas.length);
        setTotalAsignadas(response.data?.total_facturas || allFacturas.length);
      } else {
        // Load current month data from /dashboard/mes-actual endpoint
        if (userRole === 'admin') {
          // Admin can see both "todas" and "asignadas" for current month
          const [mesActualResponse, asignadasResponse] = await Promise.all([
            apiClient.get('/dashboard/mes-actual'),
            facturasService.fetchFacturas({ solo_asignadas: true, mes_actual_only: true, page: 1, per_page: 2000 }),
          ]);

          const todasFacturasData = mesActualResponse.data?.facturas || [];
          const asignadasData = asignadasResponse.data || [];

          setTotalTodasFacturas(mesActualResponse.data?.total_facturas || todasFacturasData.length);
          setTotalAsignadas(asignadasResponse.pagination?.total || asignadasData.length);

          const allFacturas = vistaFacturas === 'todas' ? todasFacturasData : asignadasData;
          const filtered = filterByEstado(allFacturas);

          setFacturas(filtered);
          setStats(calculateStats(allFacturas));
        } else {
          // Responsable only sees assigned facturas for current month
          const response = await apiClient.get('/dashboard/mes-actual');
          const allFacturas = response.data?.facturas || [];

          const total = response.data?.total_facturas || allFacturas.length;
          setTotalAsignadas(total);
          setTotalTodasFacturas(total);

          const filtered = filterByEstado(allFacturas);

          setFacturas(filtered);
          setStats(calculateStats(allFacturas));
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar facturas');
    } finally {
      setLoading(false);
    }
  }, [userRole, filterEstado, vistaFacturas, mesSeleccionado, anioSeleccionado, filterByEstado, calculateStats]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const clearError = useCallback(() => {
    setError('');
  }, []);

  return {
    facturas,
    stats,
    totalTodasFacturas,
    totalAsignadas,
    loading,
    error,
    loadData,
    clearError,
  };
};
