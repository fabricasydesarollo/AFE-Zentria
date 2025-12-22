/**
 * Enhanced Statistics Card with trend indicators
 */

import { Card, CardContent, Box, Typography, Avatar } from '@mui/material';
import { TrendingUp, TrendingDown, Remove } from '@mui/icons-material';
import { zentriaColors } from '../../../theme/colors';

interface EnhancedStatCardProps {
  label: string;
  value: number;
  previousValue?: number;
  color: string;
  bgGradient: string;
  border: string;
  icon: React.ReactElement;
  onClick?: () => void;
  textColor?: string;
  iconColor?: string;
}

export const EnhancedStatCard: React.FC<EnhancedStatCardProps> = ({
  label,
  value,
  previousValue,
  color,
  bgGradient,
  border,
  icon,
  onClick,
  textColor,
  iconColor,
}) => {
  // Calcular tendencia
  const trend = previousValue && previousValue !== 0
    ? {
        value: Math.abs(((value - previousValue) / previousValue) * 100),
        direction: value > previousValue ? 'up' : value < previousValue ? 'down' : 'stable',
      }
    : null;

  const getTrendColor = () => {
    if (!trend || trend.direction === 'stable') return 'text.secondary';
    return trend.direction === 'up' ? 'success.main' : 'error.main';
  };

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.direction === 'up') return <TrendingUp sx={{ fontSize: 16 }} />;
    if (trend.direction === 'down') return <TrendingDown sx={{ fontSize: 16 }} />;
    return <Remove sx={{ fontSize: 16 }} />;
  };

  return (
    <Card
      onClick={onClick}
      sx={{
        background: bgGradient,
        border: border,
        borderRadius: 3,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: color,
          opacity: 0,
          transition: 'opacity 0.3s ease',
        },
        '&:hover': onClick ? {
          transform: 'translateY(-4px)',
          boxShadow: `0 12px 24px ${color}20`,
          borderColor: color,
          '&::before': {
            opacity: 1,
          }
        } : {},
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box flex={1}>
            <Typography
              variant="caption"
              color="text.secondary"
              fontWeight={700}
              letterSpacing="0.5px"
              sx={{ textTransform: 'uppercase' }}
            >
              {label}
            </Typography>
            <Typography
              variant="h4"
              fontWeight={800}
              sx={{
                mt: 0.5,
                lineHeight: 1,
                fontFeatureSettings: '"tnum"', // Tabular numbers
                color: textColor || color,
              }}
            >
              {value.toLocaleString('es-CO')}
            </Typography>

            {/* Trend Indicator */}
            {trend && (
              <Box display="flex" alignItems="center" gap={0.5} mt={1}>
                <Box sx={{ color: getTrendColor(), display: 'flex', alignItems: 'center' }}>
                  {getTrendIcon()}
                </Box>
                <Typography
                  variant="caption"
                  fontWeight={600}
                  color={getTrendColor()}
                >
                  {trend.value.toFixed(1)}%
                </Typography>
              </Box>
            )}
          </Box>
          <Avatar
            sx={{
              bgcolor: color,
              width: 56,
              height: 56,
              transition: 'transform 0.3s ease',
              color: iconColor,
              '&:hover': onClick ? {
                transform: 'rotate(10deg) scale(1.1)',
              } : {},
            }}
          >
            {icon}
          </Avatar>
        </Box>
      </CardContent>
    </Card>
  );
};
