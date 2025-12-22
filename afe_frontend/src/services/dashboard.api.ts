/**
 * Dashboard API Service
 *
 * Servicio para consumir endpoints del dashboard con soporte multi-tenant.
 * Los headers de autenticación y X-Grupo-Id se agregan automáticamente vía interceptor.
 */

import { apiClient } from './api';
import { EstadisticasGraficasResponse } from '../types/dashboard.types';

const DASHBOARD_BASE = '/dashboard';

/**
 * Dashboard API
 */
export const dashboardApi = {
  /**
   * Obtiene estadísticas para gráficas del dashboard
   *
   * MULTI-TENANT:
   * - SuperAdmin: Ve estadísticas globales o de grupo específico
   * - Admin: Ve estadísticas de sus grupos asignados
   * - Responsable: Ve estadísticas de sus facturas asignadas
   * - Contador: Ve estadísticas globales (lectura)
   * - Viewer: Ve estadísticas de sus grupos (lectura)
   *
   * El filtrado por grupo se hace automáticamente usando el header X-Grupo-Id
   * que se agrega en el interceptor desde localStorage.grupo_id
   *
   * @returns Estadísticas completas para KPIs y gráficas
   */
  getStats: async (): Promise<EstadisticasGraficasResponse> => {
    const response = await apiClient.get<EstadisticasGraficasResponse>(`${DASHBOARD_BASE}/stats`);
    return response.data;
  },

  /**
   * Obtiene estadísticas del mes actual
   *
   * Estados activos únicamente:
   * - en_revision (requiere acción responsable)
   * - aprobada (requiere acción contador)
   * - aprobada_auto (requiere acción contador)
   * - rechazada (para referencia)
   *
   * @returns Dashboard operacional del mes actual
   */
  getMesActual: async () => {
    const response = await apiClient.get(`${DASHBOARD_BASE}/mes-actual`);
    return response.data;
  },

  /**
   * Obtiene alerta contextual de fin de mes
   *
   * Solo muestra alerta si:
   * - días_restantes < 5 Y hay facturas pendientes
   *
   * @returns Información de alerta (mostrar/ocultar + mensaje)
   */
  getAlertaMes: async () => {
    const response = await apiClient.get(`${DASHBOARD_BASE}/alerta-mes`);
    return response.data;
  },

  /**
   * Obtiene histórico completo de un período
   *
   * Incluye TODOS los estados (para análisis y reportes)
   *
   * @param mes - Mes a consultar (1-12)
   * @param anio - Año a consultar
   * @returns Vista histórica completa
   */
  getHistorico: async (mes: number, anio: number) => {
    const response = await apiClient.get(`${DASHBOARD_BASE}/historico`, {
      params: { mes, anio },
    });
    return response.data;
  },

  /**
   * Dashboard administrativo para SuperAdmin
   *
   * SOLO para rol 'superadmin'.
   * Incluye métricas de infraestructura:
   * - Total usuarios y grupos
   * - Distribución por roles
   * - Grupos más activos
   * - Actividad reciente del sistema
   *
   * @returns Dashboard administrativo global
   */
  getSuperAdminDashboard: async () => {
    const response = await apiClient.get(`${DASHBOARD_BASE}/superadmin`);
    return response.data;
  },
};

export default dashboardApi;
