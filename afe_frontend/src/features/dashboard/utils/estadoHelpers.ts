/**
 * Estado-related helper functions
 */

import type { EstadoFactura } from '../types';
import { ESTADO_COLORS, ESTADO_LABELS } from '../constants';

export const getEstadoColor = (estado: EstadoFactura): 'success' | 'info' | 'error' | 'warning' | 'default' => {
  return ESTADO_COLORS[estado] || 'default';
};

export const getEstadoLabel = (estado: EstadoFactura | 'todos'): string => {
  return ESTADO_LABELS[estado] || estado;
};

/**
 * Get custom styles for estados del Contador (colores distintivos)
 */
export const getEstadoChipStyles = (estado: EstadoFactura) => {
  // Estilo base para todos los chips
  const baseStyles = {
    minWidth: '150px',
    fontWeight: 600,
  };

  // Estados del Contador con colores personalizados
  if (estado === 'validada_contabilidad') {
    return {
      ...baseStyles,
      backgroundColor: '#7c4dff', // Violeta/Púrpura
      color: '#ffffff',
      '&:hover': {
        backgroundColor: '#651fff',
      }
    };
  }

  if (estado === 'devuelta_contabilidad') {
    return {
      ...baseStyles,
      backgroundColor: '#ff6e40', // Naranja intenso
      color: '#ffffff',
      '&:hover': {
        backgroundColor: '#ff5722',
      }
    };
  }

  // Para otros estados, aplicar solo estilos base
  return baseStyles;
};

/**
 * Normalize estado values (handles aprobado/aprobada variants)
 */
export const isEstadoAprobado = (estado: EstadoFactura): boolean => {
  return estado === 'aprobada' || estado === 'aprobado';
};

export const isEstadoRechazado = (estado: EstadoFactura): boolean => {
  return estado === 'rechazada' || estado === 'rechazado';
};
