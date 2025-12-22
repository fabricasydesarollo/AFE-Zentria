/**
 * Estilos estandarizados para botones de acción
 * Define hover effects consistentes en toda la aplicación
 */

import { SxProps, Theme } from '@mui/material';
import { zentriaColors } from './colors';

/**
 * Estilo base para IconButtons de acción
 */
const baseActionButtonStyle: SxProps<Theme> = {
  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    transform: 'scale(1.15)',
  },
  '&:active': {
    transform: 'scale(0.95)',
  },
};

/**
 * Estilos profesionales para botones de acción con hover mejorado
 */
export const actionButtonStyles = {
  /**
   * Botón "Ver detalles" (ojo)
   */
  view: {
    ...baseActionButtonStyle,
    color: zentriaColors.violeta.main,
    '&:hover': {
      bgcolor: `${zentriaColors.violeta.main}15`,
      transform: 'scale(1.15)',
      boxShadow: `0 2px 8px ${zentriaColors.violeta.main}40`,
    },
  } as SxProps<Theme>,

  /**
   * Botón "Editar" (lápiz)
   */
  edit: {
    ...baseActionButtonStyle,
    color: zentriaColors.naranja.main,
    '&:hover': {
      bgcolor: `${zentriaColors.naranja.main}15`,
      transform: 'scale(1.15)',
      boxShadow: `0 2px 8px ${zentriaColors.naranja.main}40`,
    },
  } as SxProps<Theme>,

  /**
   * Botón "Aprobar" (check)
   */
  approve: {
    ...baseActionButtonStyle,
    color: zentriaColors.verde.main,
    '&:hover': {
      bgcolor: `${zentriaColors.verde.main}15`,
      transform: 'scale(1.15)',
      boxShadow: `0 2px 8px ${zentriaColors.verde.main}40`,
    },
  } as SxProps<Theme>,

  /**
   * Botón "Rechazar" (X)
   */
  reject: {
    ...baseActionButtonStyle,
    color: '#f44336',
    '&:hover': {
      bgcolor: '#f4433615',
      transform: 'scale(1.15)',
      boxShadow: '0 2px 8px #f4433640',
    },
  } as SxProps<Theme>,

  /**
   * Botón "Eliminar" (trash)
   */
  delete: {
    ...baseActionButtonStyle,
    color: '#f44336',
    '&:hover': {
      bgcolor: '#f4433615',
      transform: 'scale(1.15)',
      boxShadow: '0 2px 8px #f4433640',
    },
  } as SxProps<Theme>,

  /**
   * Botón "Más acciones" (tres puntos)
   */
  more: {
    ...baseActionButtonStyle,
    '&:hover': {
      bgcolor: 'action.hover',
      transform: 'scale(1.15)',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
    },
  } as SxProps<Theme>,

  /**
   * Botón genérico
   */
  default: {
    ...baseActionButtonStyle,
    '&:hover': {
      bgcolor: 'action.hover',
      transform: 'scale(1.15)',
    },
  } as SxProps<Theme>,
};

/**
 * Tooltips estandarizados
 */
export const tooltipProps = {
  arrow: true,
  placement: 'top' as const,
  enterDelay: 300,
  leaveDelay: 0,
};
