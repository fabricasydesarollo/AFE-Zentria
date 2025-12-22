/**
 * Confirm Dialog Component
 * Diálogo de confirmación reutilizable
 */

import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Box,
  Typography,
} from '@mui/material';
import { Warning as WarningIcon, Info as InfoIcon, Error as ErrorIcon } from '@mui/icons-material';

interface Props {
  open: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
  severity?: 'warning' | 'error' | 'info';
}

const ConfirmDialog: React.FC<Props> = ({
  open,
  title,
  message,
  confirmText = 'Confirmar',
  cancelText = 'Cancelar',
  onConfirm,
  onCancel,
  severity = 'warning',
}) => {
  const getIcon = () => {
    switch (severity) {
      case 'error':
        return <ErrorIcon sx={{ fontSize: 48, color: 'error.main' }} />;
      case 'info':
        return <InfoIcon sx={{ fontSize: 48, color: 'info.main' }} />;
      default:
        return <WarningIcon sx={{ fontSize: 48, color: 'warning.main' }} />;
    }
  };

  const getColor = () => {
    switch (severity) {
      case 'error':
        return 'error';
      case 'info':
        return 'info';
      default:
        return 'warning';
    }
  };

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="xs" fullWidth aria-modal="true" disableEnforceFocus>
      <DialogContent sx={{ textAlign: 'center', pt: 4 }}>
        <Box sx={{ mb: 2 }}>{getIcon()}</Box>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
          {title}
        </Typography>
        <DialogContentText>{message}</DialogContentText>
      </DialogContent>
      <DialogActions sx={{ justifyContent: 'center', pb: 3 }}>
        <Button onClick={onCancel} variant="outlined" sx={{ minWidth: 100 }}>
          {cancelText}
        </Button>
        <Button onClick={onConfirm} variant="contained" color={getColor()} sx={{ minWidth: 100 }}>
          {confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConfirmDialog;
