/**
 * Dashboard Stats Components - Barrel Export
 *
 * Exporta todos los componentes de estadísticas del dashboard.
 * Facilita la importación en otros módulos.
 */

export { KPICard } from './KPICard';
export { DistribucionEstadosChart } from './DistribucionEstadosChart';
export { FacturasPorMesChart } from './FacturasPorMesChart';
export { TendenciaAprobacionChart } from './TendenciaAprobacionChart';

// Re-export types for convenience
export type {
  KPICardProps,
  DistribucionEstadosChartProps,
  FacturasPorMesChartProps,
  TendenciaAprobacionChartProps,
} from '../../../types/dashboard.types';
