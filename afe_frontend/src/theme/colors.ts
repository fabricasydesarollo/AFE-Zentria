/**
 * Zentria Corporate Colors
 * Paleta oficial de colores corporativos
 */

export const zentriaColors = {
  // Colores primarios
  violeta: {
    main: '#80006A',
    light: '#A65C99',
    dark: '#5C004D',
  },
  naranja: {
    main: '#FF5F3F',
    light: '#FFB5A6',
    dark: '#CC4B32',
  },

  // Colores de acción
  verde: {
    main: '#00B094',
    light: '#45E3C9',
    dark: '#008C75',
  },
  amarillo: {
    main: '#FFF280',
    light: '#FFFABF',
    dark: '#CCC266',
  },

  // Neutros
  blanco: '#FFFFFF',
  cinza: '#D7D7D7',
  preto: '#000000',

  // Estados
  success: '#00B094',
  warning: '#FFF280',
  error: '#FF5F3F',
  info: '#45E3C9',
} as const;

export type ZentriaColor = typeof zentriaColors;
