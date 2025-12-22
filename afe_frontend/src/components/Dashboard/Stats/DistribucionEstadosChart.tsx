/**
 * Distribución de Estados Chart
 *
 * Gráfica de dona/torta para mostrar la distribución porcentual de estados de facturas.
 * Usa Recharts con diseño optimizado para Zentria.
 */

import React from 'react';
import { Card, CardContent, Typography, Box, Skeleton } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { DistribucionEstadosChartProps } from '../../../types/dashboard.types';
import { zentriaColors } from '../../../theme/colors';

/**
 * Colores para cada estado (consistente con KPICard)
 */
const COLORS = {
  en_revision: zentriaColors.naranja.main,  // Warning - requiere acción
  aprobadas: zentriaColors.verde.main,      // Success - aprobadas
  validadas: '#3b82f6',                     // Info - validadas
  rechazadas: '#ef4444',                    // Error - rechazadas
  devueltas: '#f59e0b',                     // Amber - devueltas
};

/**
 * Labels en español para cada estado
 */
const LABELS = {
  en_revision: 'En Revisión',
  aprobadas: 'Aprobadas',
  validadas: 'Validadas',
  rechazadas: 'Rechazadas',
  devueltas: 'Devueltas',
};

/**
 * Gráfica de Distribución de Estados
 */
export const DistribucionEstadosChart: React.FC<DistribucionEstadosChartProps> = ({
  data,
  loading = false,
  height = 350,
  title = 'Distribución por Estado',
}) => {
  if (loading) {
    return (
      <Card sx={{ borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <CardContent sx={{ p: 3 }}>
          <Skeleton variant="text" width="50%" height={32} sx={{ mb: 3 }} />
          <Skeleton variant="circular" width={height} height={height} sx={{ mx: 'auto' }} />
        </CardContent>
      </Card>
    );
  }

  // Transformar datos para Recharts
  const chartData = Object.entries(data)
    .map(([key, value]) => ({
      name: LABELS[key as keyof typeof LABELS] || key,
      value: value.count,
      porcentaje: value.porcentaje,
    }))
    .filter((item) => item.value > 0); // Solo mostrar estados con datos

  // Si no hay datos
  if (chartData.length === 0) {
    return (
      <Card sx={{ borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ mb: 3, fontWeight: 600, color: '#1a202c' }}>
            {title}
          </Typography>
          <Box
            sx={{
              height,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#94a3b8',
            }}
          >
            <Typography variant="body2">No hay datos para mostrar</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  /**
   * Custom Tooltip
   */
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <Box
          sx={{
            backgroundColor: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: 2,
            p: 1.5,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
            {payload[0].name}
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748b' }}>
            Cantidad: {payload[0].value}
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748b' }}>
            Porcentaje: {payload[0].payload.porcentaje}%
          </Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Card sx={{ borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.08)', height: '100%' }}>
      <CardContent sx={{ p: 3 }}>
        {/* Title */}
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#1a202c' }}>
          {title}
        </Typography>

        {/* Chart */}
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="45%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
              label={({ porcentaje }) => `${porcentaje}%`}
              labelLine={false}
            >
              {chartData.map((entry, index) => {
                const colorKey = Object.keys(LABELS).find(
                  (k) => LABELS[k as keyof typeof LABELS] === entry.name
                );
                const color = colorKey ? COLORS[colorKey as keyof typeof COLORS] : '#94a3b8';
                return <Cell key={`cell-${index}`} fill={color} />;
              })}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              wrapperStyle={{ fontSize: '14px', paddingTop: '10px' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

export default DistribucionEstadosChart;
