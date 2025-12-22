import { createTheme } from '@mui/material/styles';
import { zentriaColors } from './colors';

/**
 * Zentria  Theme
 * Tema corporativo basado en los colores oficiales de Zentria
 * Optimizado para densidad de información y responsividad
 */

const themeOptions = {
  palette: {
    mode: 'light' as const,
    primary: {
      main: zentriaColors.violeta.main,
      light: zentriaColors.violeta.light,
      dark: zentriaColors.violeta.dark,
      contrastText: zentriaColors.blanco,
      50: '#F3E5F5',
      100: '#E1BEE7',
    },
    secondary: {
      main: zentriaColors.naranja.main,
      light: zentriaColors.naranja.light,
      dark: zentriaColors.naranja.dark,
      contrastText: zentriaColors.blanco,
    },
    success: {
      main: zentriaColors.verde.main,
      light: zentriaColors.verde.light,
      dark: zentriaColors.verde.dark,
      50: '#E0F7F4',
      100: '#B3EDE5',
    },
    warning: {
      main: '#FFF280',
      light: '#FFFABF',
      dark: '#CCC266',
      contrastText: '#000000',
    },
    error: {
      main: zentriaColors.naranja.main,
      light: zentriaColors.naranja.light,
      dark: zentriaColors.naranja.dark,
    },
    info: {
      main: zentriaColors.verde.light,
      light: '#6EE8D3',
      dark: '#00A085',
    },
    background: {
      default: '#F5F7FA',
      paper: zentriaColors.blanco,
    },
    text: {
      primary: '#1A1A1A',
      secondary: '#666666',
    },
    divider: '#E0E0E0',
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    fontSize: 12, // Base font size ULTRA COMPACTO: 12px
    h1: {
      fontSize: '1.75rem',     // 28px (antes 32px)
      fontWeight: 700,
      lineHeight: 1.2,
    },
    h2: {
      fontSize: '1.5rem',      // 24px (antes 28px)
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h3: {
      fontSize: '1.25rem',     // 20px (antes 24px)
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontSize: '1.125rem',    // 18px (antes 20px)
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h5: {
      fontSize: '1rem',        // 16px (antes 18px)
      fontWeight: 600,
      lineHeight: 1.5,
    },
    h6: {
      fontSize: '0.875rem',    // 14px (antes 16px)
      fontWeight: 600,
      lineHeight: 1.5,
    },
    body1: {
      fontSize: '0.875rem',    // 14px - Texto principal (antes 14px, ahora relativo a 12px base)
      lineHeight: 1.5,
    },
    body2: {
      fontSize: '0.8125rem',   // 13px - Texto secundario
      lineHeight: 1.43,
    },
    button: {
      fontSize: '0.8125rem',   // 13px (antes 14px)
      textTransform: 'none' as const,
      fontWeight: 500,
    },
    caption: {
      fontSize: '0.75rem',     // 12px
      lineHeight: 1.66,
    },
    overline: {
      fontSize: '0.6875rem',   // 11px (antes 12px)
      lineHeight: 2.66,
      textTransform: 'uppercase' as const,
      letterSpacing: '0.08em',
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '6px 16px',       // Reducido de 8px 20px
          fontSize: '0.8125rem',     // 13px
          fontWeight: 500,
          textTransform: 'none' as const,
          letterSpacing: 0.3,
        },
        contained: {
          boxShadow: '0 2px 8px rgba(128, 0, 106, 0.2)',
          '&:hover': {
            boxShadow: '0 4px 16px rgba(128, 0, 106, 0.3)',
            transform: 'translateY(-1px)',
          },
        },
        outlined: {
          borderWidth: '1.5px',
          '&:hover': {
            borderWidth: '1.5px',
          },
        },
        sizeSmall: {
          padding: '4px 12px',       // Reducido de 5px 14px
          fontSize: '0.75rem',       // 12px
        },
        sizeLarge: {
          padding: '8px 24px',       // Reducido de 10px 28px
          fontSize: '0.875rem',      // 14px
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 12px rgba(0, 0, 0, 0.08)',
          transition: 'all 0.3s ease-in-out',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
          fontSize: '0.8125rem',     // 13px
          letterSpacing: 0.2,
        },
        outlined: {
          borderWidth: '1.5px',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: 'rgba(128, 0, 106, 0.3)',
              },
            },
            '&.Mui-focused': {
              '& .MuiOutlinedInput-notchedOutline': {
                borderWidth: '2px',
              },
            },
          },
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            transform: 'scale(1.1)',
          },
        },
      },
    },
  },
};

export const zentriaTheme = createTheme(themeOptions);
