/**
 * Premium Error Dialog Component
 * Modal profesional para mostrar mensajes de error con diseño nivel 
 */

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Stack,
  IconButton,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { zentriaColors } from '../../theme/colors';

interface Props {
  open: boolean;
  title: string;
  message: string;
  onClose: () => void;
  severity?: 'error' | 'warning' | 'info';
  actionText?: string;
}

const ErrorDialog: React.FC<Props> = ({
  open,
  title,
  message,
  onClose,
  severity = 'error',
  actionText = 'Aceptar',
}) => {
  const theme = useTheme();

  const getIcon = () => {
    const iconSize = 56;
    switch (severity) {
      case 'error':
        return (
          <ErrorIcon
            sx={{
              fontSize: iconSize,
              color: theme.palette.error.main,
            }}
          />
        );
      case 'warning':
        return (
          <WarningIcon
            sx={{
              fontSize: iconSize,
              color: theme.palette.warning.main,
            }}
          />
        );
      case 'info':
        return (
          <InfoIcon
            sx={{
              fontSize: iconSize,
              color: theme.palette.info.main,
            }}
          />
        );
    }
  };

  const getColor = () => {
    switch (severity) {
      case 'error':
        return theme.palette.error.main;
      case 'warning':
        return theme.palette.warning.main;
      case 'info':
        return theme.palette.info.main;
      default:
        return theme.palette.error.main;
    }
  };

  const getBgGradient = () => {
    const color = getColor();
    return `linear-gradient(135deg, ${alpha(color, 0.05)} 0%, ${alpha(color, 0.02)} 100%)`;
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          boxShadow: '0 12px 40px rgba(0, 0, 0, 0.15)',
          overflow: 'hidden',
        },
      }}
    >
      {/* Header con icono de cerrar */}
      <Box
        sx={{
          position: 'relative',
          background: getBgGradient(),
          pt: 2,
          px: 2,
        }}
      >
        <IconButton
          onClick={onClose}
          aria-label="Cerrar"
          sx={{
            position: 'absolute',
            right: 12,
            top: 12,
            color: 'text.secondary',
            backgroundColor: alpha(theme.palette.background.paper, 0.7),
            '&:hover': {
              backgroundColor: alpha(theme.palette.background.paper, 0.9),
            },
          }}
        >
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Contenido */}
      <DialogContent
        sx={{
          textAlign: 'center',
          pt: 4,
          pb: 3,
          px: 4,
          background: getBgGradient(),
        }}
      >
        <Stack spacing={2.5} alignItems="center">
          {/* Icono con animación sutil */}
          <Box
            sx={{
              width: 88,
              height: 88,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: alpha(getColor(), 0.08),
              border: `3px solid ${alpha(getColor(), 0.2)}`,
              animation: 'pulse 2s ease-in-out infinite',
              '@keyframes pulse': {
                '0%, 100%': {
                  transform: 'scale(1)',
                },
                '50%': {
                  transform: 'scale(1.02)',
                },
              },
            }}
          >
            {getIcon()}
          </Box>

          {/* Título */}
          <Typography
            variant="h5"
            sx={{
              fontWeight: 700,
              color: 'text.primary',
              lineHeight: 1.3,
            }}
          >
            {title}
          </Typography>

          {/* Mensaje */}
          <Typography
            variant="body1"
            sx={{
              color: 'text.secondary',
              lineHeight: 1.7,
              whiteSpace: 'pre-line',
              maxWidth: 440,
            }}
          >
            {message}
          </Typography>
        </Stack>
      </DialogContent>

      {/* Acciones */}
      <DialogActions
        sx={{
          justifyContent: 'center',
          pb: 4,
          px: 4,
          pt: 1,
          background: getBgGradient(),
        }}
      >
        <Button
          onClick={onClose}
          variant="contained"
          size="large"
          sx={{
            minWidth: 160,
            px: 4,
            py: 1.5,
            borderRadius: 2,
            fontWeight: 600,
            fontSize: '1rem',
            textTransform: 'none',
            backgroundColor: zentriaColors.verde.main,
            color: '#fff',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
            '&:hover': {
              backgroundColor: zentriaColors.verde.dark,
              boxShadow: '0 6px 16px rgba(0, 0, 0, 0.15)',
              transform: 'translateY(-1px)',
            },
            transition: 'all 0.2s ease-in-out',
          }}
        >
          {actionText}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ErrorDialog;
