/**
 * Tendencia de Aprobación Chart
 *
 * Gráfica de línea para mostrar la tasa de aprobación a lo largo del tiempo.
 * Útil para identificar tendencias y patrones de aprobación.
 */

import React from 'react';
import { Card, CardContent, Typography, Box, Skeleton } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { TendenciaAprobacionChartProps } from '../../../types/dashboard.types';
import { zentriaColors } from '../../../theme/colors';

/**
 * Gráfica de Línea - Tendencia de Aprobación
 */
export const TendenciaAprobacionChart: React.FC<TendenciaAprobacionChartProps> = ({
  data,
  loading = false,
  height = 300,
  title = 'Tendencia de Aprobación',
}) => {
  if (loading) {
    return (
      <Card sx={{ borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <CardContent sx={{ p: 3 }}>
          <Skeleton variant="text" width="50%" height={32} sx={{ mb: 3 }} />
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
      const value = payload[0].value;
      let color = zentriaColors.verde.main;

      // Color según el valor
      if (value < 50) {
        color = '#ef4444'; // Rojo si < 50%
      } else if (value < 75) {
        color = zentriaColors.naranja.main; // Naranja si < 75%
      }

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
            {label}
          </Typography>
          <Typography variant="body2" sx={{ color }}>
            Tasa de Aprobación: {value}%
          </Typography>
        </Box>
      );
    }
    return null;
  };

  /**
   * Custom Dot (punto en la línea)
   */
  const CustomDot = (props: any) => {
    const { cx, cy, payload } = props;
    const value = payload.tasa_aprobacion;

    let color = zentriaColors.verde.main;
    if (value < 50) {
      color = '#ef4444';
    } else if (value < 75) {
      color = zentriaColors.naranja.main;
    }

    return (
      <circle
        cx={cx}
        cy={cy}
        r={5}
        fill={color}
        stroke="white"
        strokeWidth={2}
      />
    );
  };

  return (
    <Card sx={{ borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.08)', height: '100%' }}>
      <CardContent sx={{ p: 3 }}>
        {/* Title */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, color: '#1a202c' }}>
            {title}
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, fontSize: '12px', color: '#64748b' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  backgroundColor: zentriaColors.verde.main,
                  borderRadius: '50%',
                }}
              />
              <Typography variant="caption">{'>'}75%</Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  backgroundColor: zentriaColors.naranja.main,
                  borderRadius: '50%',
                }}
              />
              <Typography variant="caption">50-75%</Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  backgroundColor: '#ef4444',
                  borderRadius: '50%',
                }}
              />
              <Typography variant="caption">{'<'}50%</Typography>
            </Box>
          </Box>
        </Box>

        {/* Chart */}
        <ResponsiveContainer width="100%" height={height}>
          <LineChart
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
              domain={[0, 100]}
              tick={{ fontSize: 12, fill: '#64748b' }}
              tickLine={{ stroke: '#cbd5e1' }}
              axisLine={{ stroke: '#cbd5e1' }}
              label={{
                value: 'Tasa de Aprobación (%)',
                angle: -90,
                position: 'insideLeft',
                style: { fontSize: 12, fill: '#64748b' },
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            {/* Líneas de referencia */}
            <ReferenceLine y={75} stroke={zentriaColors.verde.main} strokeDasharray="3 3" />
            <ReferenceLine y={50} stroke={zentriaColors.naranja.main} strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="tasa_aprobacion"
              stroke={zentriaColors.violeta.main}
              strokeWidth={3}
              dot={<CustomDot />}
              activeDot={{ r: 7 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

export default TendenciaAprobacionChart;
