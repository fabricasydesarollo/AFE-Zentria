/**
 * Tipos TypeScript para Dashboard Multi-Tenant
 *
 * Sincronizados con schemas del backend:
 * - app/api/v1/routers/dashboard.py::EstadisticasGraficasResponse
 */

/**
 * Distribución de estados para gráficas
 */
export interface EstadoDistribucion {
  count: number;
  porcentaje: number;
}

/**
 * Datos mensuales para gráfica de barras
 */
export interface FacturasPorMes {
  mes: string; // Ej: "Diciembre 2025"
  total: number;
  aprobadas: number;
  rechazadas: number;
}

/**
 * Datos de tendencia para gráfica de línea
 */
export interface TendenciaAprobacion {
  mes: string; // Ej: "Diciembre 2025"
  tasa_aprobacion: number; // Porcentaje (0-100)
}

/**
 * Respuesta del endpoint /dashboard/stats
 */
export interface EstadisticasGraficasResponse {
  // KPIs principales
  total_facturas: number;
  pendientes_revision: number;
  pendientes_validacion: number;
  validadas: number;
  rechazadas: number;
  devueltas: number;

  // Distribución por estado (gráfica de dona/torta)
  distribucion_estados: {
    en_revision: EstadoDistribucion;
    aprobadas: EstadoDistribucion;
    validadas: EstadoDistribucion;
    rechazadas: EstadoDistribucion;
    devueltas: EstadoDistribucion;
  };

  // Datos para gráficas
  facturas_por_mes: FacturasPorMes[];
  tendencia_aprobacion: TendenciaAprobacion[];

  // Metadata
  periodo: string;
  grupo_id: number | null;
  rol: string;
}

/**
 * Props para KPI Card Component
 */
export interface KPICardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: 'primary' | 'success' | 'warning' | 'error' | 'info';
  subtitle?: string;
  loading?: boolean;
}

/**
 * Props para Chart Component (genérico)
 */
export interface ChartProps {
  data: any[];
  loading?: boolean;
  height?: number;
  title?: string;
}

/**
 * Props para componente de distribución de estados
 */
export interface DistribucionEstadosChartProps extends ChartProps {
  data: EstadisticasGraficasResponse['distribucion_estados'];
}

/**
 * Props para componente de facturas por mes
 */
export interface FacturasPorMesChartProps extends ChartProps {
  data: FacturasPorMes[];
}

/**
 * Props para componente de tendencia
 */
export interface TendenciaAprobacionChartProps extends ChartProps {
  data: TendenciaAprobacion[];
}
