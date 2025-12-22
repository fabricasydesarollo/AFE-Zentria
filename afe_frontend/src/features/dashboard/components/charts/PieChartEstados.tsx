/**
 * PieChartEstados - Pie Chart showing distribution of facturas by estado
 * Visual representation of current estado breakdown
 */

import { Box, Typography, Paper, Skeleton } from '@mui/material';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { zentriaColors } from '../../../../theme/colors';
import type { WorkflowStats } from '../../hooks/useDashboardStats';

interface PieChartEstadosProps {
  data: WorkflowStats | null;
  loading?: boolean;
}

// Paleta de colores sincronizada con el sistema
// - Amarillo (Amber): En revisión/pendiente (requiere atención)
// - Verde: Aprobadas manualmente (éxito confirmado)
// - Verde claro (Cyan): Aprobadas automáticamente (éxito automatizado)
// - Naranja: Rechazadas (error/negativo)
const COLORS = {
  pendientes: '#f59e0b',                  // Amber 500 - más visible para estados pendientes
  en_revision: '#f59e0b',                 // Amber 500 - consistente con pendientes
  aprobadas: zentriaColors.verde.main,    // #00B094 - Verde corporativo para aprobados manuales
  aprobadas_auto: '#45E3C9',              // Verde claro - diferenciado de aprobadas manuales
  rechazadas: zentriaColors.naranja.main, // #FF5F3F - Naranja corporativo para rechazos
};

const LABELS = {
  pendientes: 'Pendientes',
  en_revision: 'En Revisión',
  aprobadas: 'Aprobadas',
  aprobadas_auto: 'Aprobadas Auto',
  rechazadas: 'Rechazadas',
};

export const PieChartEstados: React.FC<PieChartEstadosProps> = ({ data, loading }) => {
  if (loading) {
    return <Skeleton variant="rectangular" height={350} sx={{ borderRadius: 2 }} />;
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

  // Transform workflow stats to pie chart data
  const chartData = [
    {
      name: LABELS.pendientes,
      value: data.total_pendientes || 0,
      color: COLORS.pendientes,
    },
    {
      name: LABELS.en_revision,
      value: data.total_en_revision || 0,
      color: COLORS.en_revision,
    },
    {
      name: LABELS.aprobadas,
      value: data.total_aprobadas || 0,
      color: COLORS.aprobadas,
    },
    {
      name: LABELS.aprobadas_auto,
      value: data.total_aprobadas_auto || 0,
      color: COLORS.aprobadas_auto,
    },
    {
      name: LABELS.rechazadas,
      value: data.total_rechazadas || 0,
      color: COLORS.rechazadas,
    },
  ].filter((item) => item.value > 0); // Only show items with values

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  if (total === 0) {
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
        <Typography color="text.secondary">No hay facturas para mostrar</Typography>
      </Paper>
    );
  }

  const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontSize={12}
        fontWeight={700}
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

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
          Distribución por Estados
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Estado actual de todas las facturas
        </Typography>
      </Box>

      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={CustomLabel}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e0e0e0',
              borderRadius: 8,
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            }}
            formatter={(value: number) => [
              `${value} (${((value / total) * 100).toFixed(1)}%)`,
              '',
            ]}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            wrapperStyle={{ fontSize: 12 }}
            iconType="circle"
          />
        </PieChart>
      </ResponsiveContainer>
    </Paper>
  );
};
