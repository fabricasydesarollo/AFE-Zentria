/**
 * KPI Card Component
 *
 * Componente reutilizable para mostrar indicadores clave de desempeño (KPIs).
 * Diseñado para ser consistente con el theme de Zentria.
 */

import React from 'react';
import { Card, CardContent, Typography, Box, Skeleton } from '@mui/material';
import { KPICardProps } from '../../../types/dashboard.types';
import { zentriaColors } from '../../../theme/colors';

/**
 * Mapa de colores según el tipo
 */
const colorMap = {
  primary: zentriaColors.violeta.main,
  success: zentriaColors.verde.main,
  warning: zentriaColors.naranja.main,
  error: '#ef4444',
  info: '#3b82f6',
};

/**
 * Mapa de colores de fondo (más claros)
 */
const bgColorMap = {
  primary: `${zentriaColors.violeta.main}15`,
  success: `${zentriaColors.verde.main}15`,
  warning: `${zentriaColors.naranja.main}15`,
  error: '#ef444415',
  info: '#3b82f615',
};

/**
 * KPI Card - Tarjeta para mostrar indicadores clave
 */
export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  icon,
  color = 'primary',
  subtitle,
  loading = false,
}) => {
  const mainColor = colorMap[color];
  const bgColor = bgColorMap[color];

  if (loading) {
    return (
      <Card
        sx={{
          height: '100%',
          borderRadius: 3,
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Skeleton variant="circular" width={48} height={48} sx={{ mb: 2 }} />
          <Skeleton variant="text" width="60%" height={32} sx={{ mb: 1 }} />
          <Skeleton variant="text" width="40%" height={24} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        height: '100%',
        borderRadius: 3,
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: `0 8px 24px ${mainColor}30`,
        },
      }}
    >
      <CardContent sx={{ p: 3 }}>
        {/* Icon Container */}
        <Box
          sx={{
            width: 56,
            height: 56,
            borderRadius: 2,
            backgroundColor: bgColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 2,
            color: mainColor,
          }}
        >
          {React.cloneElement(icon as React.ReactElement, {
            sx: { fontSize: 32 },
          })}
        </Box>

        {/* Value */}
        <Typography
          variant="h3"
          sx={{
            fontWeight: 700,
            color: '#1a202c',
            mb: 0.5,
            fontSize: { xs: '1.75rem', sm: '2rem', md: '2.25rem' },
          }}
        >
          {value.toLocaleString()}
        </Typography>

        {/* Title */}
        <Typography
          variant="body2"
          sx={{
            color: '#64748b',
            fontWeight: 500,
            mb: subtitle ? 0.5 : 0,
          }}
        >
          {title}
        </Typography>

        {/* Optional Subtitle */}
        {subtitle && (
          <Typography
            variant="caption"
            sx={{
              color: mainColor,
              fontWeight: 600,
              display: 'block',
              mt: 1,
            }}
          >
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default KPICard;
