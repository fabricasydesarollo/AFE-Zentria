/**
 * Dashboard Stats Page
 *
 * Página de ejemplo que demuestra cómo usar los componentes de estadísticas.
 * Implementa el diseño multi-tenant con filtrado automático por grupo.
 *
 * Características:
 * - Auto-sincronizado con grupo seleccionado
 * - Responsive design
 * - Manejo de estados loading/error
 * - Componentes reutilizables sin duplicación
 */

import React from 'react';
import { Box, Grid, Alert, IconButton, Typography, Chip } from '@mui/material';
import {
  Assessment as AssessmentIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Cancel as CancelIcon,
  Replay as ReplayIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import {
  KPICard,
  DistribucionEstadosChart,
  FacturasPorMesChart,
  TendenciaAprobacionChart,
} from './Stats';
import { useDashboardStats } from '../../hooks/useDashboardStats';
import { useAppSelector } from '../../app/hooks';
import { zentriaColors } from '../../theme/colors';

/**
 * Dashboard Stats Page - Implementación de ejemplo
 */
const DashboardStatsPage: React.FC = () => {
  const { stats, loading, error, refetch } = useDashboardStats();
  const user = useAppSelector((state) => state.auth.user);

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, color: '#1a202c', mb: 0.5 }}>
            Dashboard de Estadísticas
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748b' }}>
            {stats?.periodo || 'Cargando período...'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          {/* Badge de Rol */}
          <Chip
            label={stats?.rol || user?.rol || 'Usuario'}
            size="small"
            sx={{
              backgroundColor: `${zentriaColors.violeta.main}15`,
              color: zentriaColors.violeta.main,
              fontWeight: 600,
              textTransform: 'uppercase',
            }}
          />
          {/* Botón de refetch */}
          <IconButton
            onClick={refetch}
            disabled={loading}
            sx={{
              backgroundColor: 'white',
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
              '&:hover': {
                backgroundColor: '#f8fafc',
              },
            }}
          >
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
          {error}
        </Alert>
      )}

      {/* KPI Cards Grid */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Total Facturas"
            value={stats?.total_facturas || 0}
            icon={<AssessmentIcon />}
            color="primary"
            loading={loading}
            subtitle={stats ? `${stats.periodo.split(' ')[0]} ${stats.periodo.split(' ')[1]} meses` : undefined}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Pendientes Revisión"
            value={stats?.pendientes_revision || 0}
            icon={<ScheduleIcon />}
            color="warning"
            loading={loading}
            subtitle="Requieren acción responsable"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Validadas"
            value={stats?.validadas || 0}
            icon={<CheckCircleIcon />}
            color="success"
            loading={loading}
            subtitle="Validadas por contador"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Rechazadas"
            value={stats?.rechazadas || 0}
            icon={<CancelIcon />}
            color="error"
            loading={loading}
          />
        </Grid>
      </Grid>

      {/* Charts Grid */}
      <Grid container spacing={3}>
        {/* Distribución de Estados (Gráfica de Dona) */}
        <Grid item xs={12} md={5}>
          <DistribucionEstadosChart
            data={stats?.distribucion_estados || {
              en_revision: { count: 0, porcentaje: 0 },
              aprobadas: { count: 0, porcentaje: 0 },
              validadas: { count: 0, porcentaje: 0 },
              rechazadas: { count: 0, porcentaje: 0 },
              devueltas: { count: 0, porcentaje: 0 },
            }}
            loading={loading}
            height={350}
          />
        </Grid>

        {/* Tendencia de Aprobación (Gráfica de Línea) */}
        <Grid item xs={12} md={7}>
          <TendenciaAprobacionChart
            data={stats?.tendencia_aprobacion || []}
            loading={loading}
            height={350}
          />
        </Grid>

        {/* Facturas por Mes (Gráfica de Barras) */}
        <Grid item xs={12}>
          <FacturasPorMesChart
            data={stats?.facturas_por_mes || []}
            loading={loading}
            height={350}
          />
        </Grid>
      </Grid>

      {/* Información adicional para Responsables */}
      {stats?.rol === 'responsable' && (
        <Alert
          severity="info"
          icon={<AssessmentIcon />}
          sx={{ mt: 3, borderRadius: 2 }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Vista de Responsable
          </Typography>
          <Typography variant="body2">
            Estas estadísticas muestran únicamente las facturas asignadas a ti. Si ves números bajos,
            es porque solo se cuentan las facturas donde eres el responsable.
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

export default DashboardStatsPage;
