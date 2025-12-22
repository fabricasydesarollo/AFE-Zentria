/**
 * BarChartFacturas - Stacked Bar Chart showing facturas by month
 * Shows distribution of facturas by estado across months
 */

import { Box, Typography, Paper, Skeleton } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { zentriaColors } from '../../../../theme/colors';
import type { MonthlyStats } from '../../hooks/useDashboardStats';

interface BarChartFacturasProps {
  data: MonthlyStats[];
  loading?: boolean;
}

// Color palette for APPROVAL FLOW states only
const COLORS = {
  en_revision: '#FFF280',                      // Amarillo - Requiere revisión
  aprobada_auto: '#45E3C9',                    // Cyan - Aprobadas automáticamente
  aprobada: zentriaColors.verde.main,          // Verde - Aprobadas manualmente
  rechazada: zentriaColors.naranja.main,       // Naranja - Rechazadas
};

// Custom legend with black text (so yellow is readable)
const CustomLegend = (props: any) => {
  const { payload } = props;
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 2, fontSize: 12 }}>
      {payload.map((entry: any, index: number) => (
        <Box key={`legend-${index}`} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              backgroundColor: entry.color,
            }}
          />
          <Typography variant="body2" sx={{ color: '#000', fontWeight: 500 }}>
            {entry.value}
          </Typography>
        </Box>
      ))}
    </Box>
  );
};

// Custom tooltip with black text (ensures all colors readable, especially yellow)
const CustomTooltip = (props: any) => {
  const { active, payload } = props;
  if (active && payload && payload.length) {
    return (
      <Box
        sx={{
          backgroundColor: '#fff',
          border: '1px solid #e0e0e0',
          borderRadius: 2,
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          p: 1.5,
        }}
      >
        {payload.map((entry: any, index: number) => (
          <Box
            key={`tooltip-${index}`}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.75,
              fontSize: 12,
              mb: index < payload.length - 1 ? 0.5 : 0,
            }}
          >
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: entry.color,
                flexShrink: 0,
              }}
            />
            <Typography variant="body2" sx={{ color: '#000', fontWeight: 500 }}>
              {entry.name}: <strong>{entry.value}</strong>
            </Typography>
          </Box>
        ))}
      </Box>
    );
  }
  return null;
};

export const BarChartFacturas: React.FC<BarChartFacturasProps> = ({ data, loading }) => {
  if (loading) {
    return <Skeleton variant="rectangular" height={350} sx={{ borderRadius: 2 }} />;
  }

  if (!data || data.length === 0) {
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

  // Transform data for stacked bar chart
  // CORRECTED: Only APPROVAL flow states (4 estados)
  // Removed: 'Pendientes' (doesn't exist), 'Pagada' (belongs to Accounting module)
  const chartData = data.map((item) => ({
    periodo: item.periodo_display,
    'En Revisión': item.facturas_por_estado?.en_revision || 0,
    'Aprobadas Auto': item.facturas_por_estado?.aprobada_auto || 0,
    'Aprobadas': item.facturas_por_estado?.aprobada || 0,
    'Rechazadas': item.facturas_por_estado?.rechazada || 0,
    Total: item.total_facturas || 0,
  }));

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
          Facturas por Mes
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Distribución de estados en los últimos meses
        </Typography>
      </Box>

      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="periodo"
            tick={{ fontSize: 12 }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            content={<CustomLegend />}
          />
          {/* Stacked bars showing distribution of approval states */}
          <Bar
            dataKey="En Revisión"
            stackId="a"
            fill={COLORS.en_revision}
            radius={[4, 4, 0, 0]}
          />
          <Bar
            dataKey="Aprobadas Auto"
            stackId="a"
            fill={COLORS.aprobada_auto}
          />
          <Bar
            dataKey="Aprobadas"
            stackId="a"
            fill={COLORS.aprobada}
          />
          <Bar
            dataKey="Rechazadas"
            stackId="a"
            fill={COLORS.rechazada}
          />
        </BarChart>
      </ResponsiveContainer>
    </Paper>
  );
};
