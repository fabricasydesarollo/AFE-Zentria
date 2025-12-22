/**
 * Statistics cards component for Dashboard
 */

import { Grid } from '@mui/material';
import {
  AttachFile,
  RemoveRedEye,
  CheckCircle,
  SmartToy,
  Cancel,
} from '@mui/icons-material';
import { zentriaColors } from '../../../theme/colors';
import type { DashboardStats } from '../types';
import { EnhancedStatCard } from './EnhancedStatCard';

interface StatsCardsProps {
  stats: DashboardStats;
  previousStats?: DashboardStats;
  onCardClick?: (filter: string) => void;
}

interface StatCard {
  key: keyof DashboardStats;
  label: string;
  value: number;
  color: string;
  bgGradient: string;
  border: string;
  icon: React.ReactElement;
  filter: string;
  textColor?: string;
  iconColor?: string;
}

export const StatsCards: React.FC<StatsCardsProps> = ({ stats, previousStats, onCardClick }) => {
  // Paleta de colores y configuración de tarjetas
  const statsConfig: StatCard[] = [
    {
      key: 'total',
      label: 'TOTAL FACTURAS',
      value: stats.total,
      color: zentriaColors.violeta.main,
      bgGradient: `linear-gradient(135deg, ${zentriaColors.violeta.main}10, ${zentriaColors.violeta.main}05)`,
      border: `1px solid ${zentriaColors.violeta.main}30`,
      icon: <AttachFile />,
      filter: 'todos',
      textColor: '#000000',
      iconColor: '#000000',
    },
    {
      key: 'en_revision',
      label: 'EN REVISIÓN',
      value: stats.en_revision,
      // Amarillo para estados pendientes/en revisión
      color: '#FFF280', // Amarillo claro
      bgGradient: 'linear-gradient(135deg, #f8eba939, #f6e79e39)',
      border: '1px solid #fbd20884',
      icon: <RemoveRedEye />,
      filter: 'en_revision',
      textColor: '#000000', // Texto negro
      iconColor: '#000000', // Ícono negro
    },
    {
      key: 'aprobadas',
      label: 'APROBADAS',
      value: stats.aprobadas,
      // Verde corporativo para aprobados manuales
      color: zentriaColors.verde.main, // #00B094
      bgGradient: `linear-gradient(135deg, ${zentriaColors.verde.main}10, ${zentriaColors.verde.main}05)`,
      border: `1px solid ${zentriaColors.verde.main}30`,
      icon: <CheckCircle />,
      filter: 'aprobada',
      textColor: '#000000',
      iconColor: '#000000',
    },
    {
      key: 'aprobadas_auto',
      label: 'APROBADAS AUTO',
      value: stats.aprobadas_auto,
      // Verde más claro (cyan) para aprobados automáticos 
      color: '#45E3C9', // zentriaColors.verde.light 
      bgGradient: 'linear-gradient(135deg, #45E3C910, #45E3C905)',
      border: '1px solid #45E3C930',
      icon: <SmartToy />,
      filter: 'aprobada_auto',
      textColor: '#000000',
      iconColor: '#000000',
    },
    {
      key: 'rechazadas',
      label: 'RECHAZADAS',
      value: stats.rechazadas,
      // Naranja 
      color: zentriaColors.naranja.main, // #FF5F3F
      bgGradient: `linear-gradient(135deg, ${zentriaColors.naranja.main}10, ${zentriaColors.naranja.main}05)`,
      border: `1px solid ${zentriaColors.naranja.main}30`,
      icon: <Cancel />,
      filter: 'rechazada',
      textColor: '#000000',
      iconColor: '#000000',
    },
  ];

  return (
    <Grid container spacing={3} sx={{ mb: 4 }}>
      {statsConfig.map((stat, index) => (
        <Grid size={{ xs: 12, sm: 6, md: 2.4, lg: 2.4 }} key={index}>
          <EnhancedStatCard
            label={stat.label}
            value={stat.value}
            previousValue={previousStats?.[stat.key]}
            color={stat.color}
            bgGradient={stat.bgGradient}
            border={stat.border}
            icon={stat.icon}
            textColor={stat.textColor}
            iconColor={stat.iconColor}
            onClick={onCardClick ? () => onCardClick(stat.filter) : undefined}
          />
        </Grid>
      ))}
    </Grid>
  );
};
