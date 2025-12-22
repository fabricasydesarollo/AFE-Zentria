/**
 * LineChartMontos - Line Chart showing monetary trends over time
 * Displays total amounts, subtotal, and IVA trends
 */

import { Box, Typography, Paper, Skeleton } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { zentriaColors } from '../../../../theme/colors';
import type { MonthlyStats } from '../../hooks/useDashboardStats';

interface LineChartMontosProps {
  data: MonthlyStats[];
  loading?: boolean;
}

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const formatCurrencyShort = (value: number): string => {
  if (value >= 1000000000) {
    return `$${(value / 1000000000).toFixed(1)}B`;
  }
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
};

export const LineChartMontos: React.FC<LineChartMontosProps> = ({ data, loading }) => {
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

  // Transform data for line chart
  const chartData = data.map((item) => ({
    periodo: item.periodo_display,
    'Monto Total': item.monto_total || 0,
    'Subtotal': item.subtotal || 0,
    'IVA': item.iva || 0,
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
          Evolución de Montos
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Tendencias de facturación en los últimos meses
        </Typography>
      </Box>

      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
            tickFormatter={formatCurrencyShort}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e0e0e0',
              borderRadius: 8,
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            }}
            formatter={(value: number) => formatCurrency(value)}
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            iconType="line"
          />
          <Line
            type="monotone"
            dataKey="Monto Total"
            stroke={zentriaColors.violeta.main}
            strokeWidth={3}
            dot={{ fill: zentriaColors.violeta.main, r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="Subtotal"
            stroke={zentriaColors.verde.main}
            strokeWidth={2}
            dot={{ fill: zentriaColors.verde.main, r: 3 }}
            strokeDasharray="5 5"
          />
          <Line
            type="monotone"
            dataKey="IVA"
            stroke={zentriaColors.naranja.main}
            strokeWidth={2}
            dot={{ fill: zentriaColors.naranja.main, r: 3 }}
            strokeDasharray="5 5"
          />
        </LineChart>
      </ResponsiveContainer>
    </Paper>
  );
};
