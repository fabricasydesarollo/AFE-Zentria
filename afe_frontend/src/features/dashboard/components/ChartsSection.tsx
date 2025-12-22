/**
 * ChartsSection - Container component for all dashboard charts
 * Organizes charts in a responsive grid layout
 */

import { Box, Grid, Alert, AlertTitle } from '@mui/material';
import { useDashboardStats } from '../hooks/useDashboardStats';
import {
  BarChartFacturas,
  LineChartMontos,
  GaugeChartKPI,
} from './charts';
import type { DashboardStats } from '../types';
import type { ComparisonStats } from '../hooks/useDashboardStats';

interface ChartsSectionProps {
  stats?: DashboardStats;
}

export const ChartsSection: React.FC<ChartsSectionProps> = ({ stats: dashboardStats }) => {
  const { monthlyStats, comparisonStats, loading, error } = useDashboardStats();

  // Convert DashboardStats to ComparisonStats format for GaugeChartKPI
  const gaugeChartData: ComparisonStats | null = dashboardStats ? {
    aprobadas_automaticamente: dashboardStats.aprobadas_auto,
    requieren_revision: dashboardStats.en_revision,
    facturas_evaluadas: dashboardStats.total,
    tasa_aprobacion_auto: dashboardStats.total > 0
      ? dashboardStats.aprobadas_auto / dashboardStats.total
      : 0,
  } as ComparisonStats : comparisonStats;

  if (error) {
    return (
      <Alert severity="warning" sx={{ mb: 3 }}>
        <AlertTitle>Error al cargar estadísticas</AlertTitle>
        {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ mb: 4 }}>
      <Grid container spacing={3}>
        {/* 3-chart layout: Bar (stacked) | Line | Gauge */}
        {/* Responsive: Full width on mobile/tablet, 33% on desktop */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <BarChartFacturas data={monthlyStats} loading={loading} />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <LineChartMontos data={monthlyStats} loading={loading} />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <GaugeChartKPI data={gaugeChartData} loading={loading} />
        </Grid>
      </Grid>
    </Box>
  );
};
