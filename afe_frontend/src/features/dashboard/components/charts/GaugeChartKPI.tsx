/**
 * GaugeChartKPI - Gauge Chart showing automated approval rate KPI
 * Visual indicator of system efficiency
 */

import { Box, Typography, Paper, Skeleton, Chip } from '@mui/material';
import { TrendingUp, TrendingDown, TrendingFlat } from '@mui/icons-material';
import { zentriaColors } from '../../../../theme/colors';
import type { ComparisonStats } from '../../hooks/useDashboardStats';

interface GaugeChartKPIProps {
  data: ComparisonStats | null;
  loading?: boolean;
}

export const GaugeChartKPI: React.FC<GaugeChartKPIProps> = ({ data, loading }) => {
  if (loading) {
    return <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 2 }} />;
  }

  if (!data) {
    return (
      <Paper
        elevation={0}
        sx={{
          p: 3,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          textAlign: 'center',
        }}
      >
        <Typography color="text.secondary">No hay datos disponibles</Typography>
      </Paper>
    );
  }

  const rate = data.tasa_aprobacion_auto || 0;
  const percentage = Math.round(rate * 100);

  // Determine color based on percentage
  const getColor = (pct: number) => {
    if (pct >= 80) return zentriaColors.verde.main;
    if (pct >= 60) return '#42A5F5';
    if (pct >= 40) return zentriaColors.amarillo.dark;
    return zentriaColors.naranja.main;
  };

  const getStatus = (pct: number) => {
    if (pct >= 80) return { label: 'Excelente', icon: <TrendingUp /> };
    if (pct >= 60) return { label: 'Bueno', icon: <TrendingFlat /> };
    if (pct >= 40) return { label: 'Regular', icon: <TrendingFlat /> };
    return { label: 'Bajo', icon: <TrendingDown /> };
  };

  const color = getColor(percentage);
  const status = getStatus(percentage);

  // Calculate circle progress
  const circumference = 2 * Math.PI * 70; // radius = 70
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <Paper
      elevation={0}
      sx={{
        p: 3,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 3,
        height: '100%',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
        transition: 'box-shadow 0.3s ease',
        '&:hover': {
          boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
        },
      }}
    >
      <Box mb={2}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          Tasa de Aprobación Automática
        </Typography>
        <Typography variant="body2" color="text.secondary">
          KPI de eficiencia del sistema
        </Typography>
      </Box>

      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        sx={{ position: 'relative', py: 3 }}
      >
        {/* Circular Gauge */}
        <Box sx={{ position: 'relative', display: 'inline-flex' }}>
          <svg width="180" height="180" style={{ transform: 'rotate(-90deg)' }}>
            {/* Background circle */}
            <circle
              cx="90"
              cy="90"
              r="70"
              stroke="#f0f0f0"
              strokeWidth="12"
              fill="none"
            />
            {/* Progress circle */}
            <circle
              cx="90"
              cy="90"
              r="70"
              stroke={color}
              strokeWidth="12"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              style={{
                transition: 'stroke-dashoffset 0.5s ease',
              }}
            />
          </svg>
          {/* Center text */}
          <Box
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center',
            }}
          >
            <Typography
              variant="h2"
              fontWeight={800}
              sx={{ color, lineHeight: 1 }}
            >
              {percentage}%
            </Typography>
            <Chip
              label={status.label}
              size="small"
              icon={status.icon}
              sx={{
                mt: 1,
                bgcolor: `${color}20`,
                color,
                fontWeight: 600,
                '& .MuiChip-icon': {
                  color,
                },
              }}
            />
          </Box>
        </Box>

        {/* Statistics Grid */}
        <Box
          display="grid"
          gridTemplateColumns="1fr 1fr"
          gap={2}
          width="100%"
          mt={3}
        >
          <Box textAlign="center">
            <Typography variant="h4" fontWeight={700} color={zentriaColors.verde.main}>
              {data.aprobadas_automaticamente}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Aprobadas Auto
            </Typography>
          </Box>
          <Box textAlign="center">
            <Typography variant="h4" fontWeight={700} color={zentriaColors.amarillo.dark}>
              {data.requieren_revision}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Requieren Revisión
            </Typography>
          </Box>
        </Box>

        {/* Target indicator */}
        <Box mt={2} textAlign="center">
          <Typography variant="body2" color="text.secondary">
            Meta: ≥80% • Total Evaluadas: {data.facturas_evaluadas}
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};
