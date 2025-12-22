/**
 * Facturas por Mes Chart
 *
 * Gráfica de barras para mostrar facturas de los últimos 6 meses.
 * Compara total, aprobadas y rechazadas por mes.
 */

import React from 'react';
import { Card, CardContent, Typography, Box, Skeleton } from '@mui/material';
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
import { FacturasPorMesChartProps } from '../../../types/dashboard.types';
import { zentriaColors } from '../../../theme/colors';

/**
 * Gráfica de Barras - Facturas por Mes
 */
export const FacturasPorMesChart: React.FC<FacturasPorMesChartProps> = ({
  data,
  loading = false,
  height = 350,
  title = 'Facturas por Mes (Últimos 6 Meses)',
}) => {
  if (loading) {
    return (
      <Card sx={{ borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <CardContent sx={{ p: 3 }}>
          <Skeleton variant="text" width="60%" height={32} sx={{ mb: 3 }} />
          <Skeleton variant="rectangular" width="100%" height={height} />
        </CardContent>
      </Card>
    );
  }

  // Si no hay datos
  if (!data || data.length === 0) {
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
  const CustomTooltip = ({ active, payload, label }: any) => {
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
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
            {label}
          </Typography>
          {payload.map((entry: any, index: number) => (
            <Typography
              key={index}
              variant="body2"
              sx={{ color: entry.color, display: 'flex', alignItems: 'center', gap: 1 }}
            >
              <Box
                component="span"
                sx={{
                  width: 12,
                  height: 12,
                  backgroundColor: entry.color,
                  borderRadius: '50%',
                  display: 'inline-block',
                }}
              />
              {entry.name}: {entry.value}
            </Typography>
          ))}
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
          <BarChart
            data={data}
            margin={{ top: 10, right: 10, left: -10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="mes"
              tick={{ fontSize: 12, fill: '#64748b' }}
              tickLine={{ stroke: '#cbd5e1' }}
              axisLine={{ stroke: '#cbd5e1' }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#64748b' }}
              tickLine={{ stroke: '#cbd5e1' }}
              axisLine={{ stroke: '#cbd5e1' }}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f1f5f9' }} />
            <Legend
              wrapperStyle={{ fontSize: '14px', paddingTop: '10px' }}
              iconType="circle"
            />
            <Bar
              dataKey="total"
              name="Total"
              fill={zentriaColors.violeta.main}
              radius={[8, 8, 0, 0]}
            />
            <Bar
              dataKey="aprobadas"
              name="Aprobadas"
              fill={zentriaColors.verde.main}
              radius={[8, 8, 0, 0]}
            />
            <Bar
              dataKey="rechazadas"
              name="Rechazadas"
              fill="#ef4444"
              radius={[8, 8, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

export default FacturasPorMesChart;
