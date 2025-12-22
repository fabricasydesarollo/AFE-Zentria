import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Typography,
  Alert,
  Box,
  CircularProgress,
} from '@mui/material';
import { Undo, Send } from '@mui/icons-material';
import { facturasService, type DevolucionRequest } from '../../features/facturas/services/facturas.service';

interface DevolucionDialogProps {
  open: boolean;
  onClose: () => void;
  facturaId: number;
  numeroFactura: string;
  onDevolucionSuccess?: () => void;
}

/**
 * Dialog profesional para que contadores devuelvan facturas aprobadas al proveedor
 * solicitando información adicional.
 *
 * NUEVO 2025-11-18
 */
function DevolucionDialog({
  open,
  onClose,
  facturaId,
  numeroFactura,
  onDevolucionSuccess,
}: DevolucionDialogProps) {
  const [observaciones, setObservaciones] = useState('');
  const [notificarProveedor, setNotificarProveedor] = useState(true);
  const [notificarResponsable, setNotificarResponsable] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    // Validaciones
    if (observaciones.trim().length < 10) {
      setError('Las observaciones deben tener al menos 10 caracteres');
      return;
    }

    if (observaciones.trim().length > 1000) {
      setError('Las observaciones no pueden exceder 1000 caracteres');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const request: DevolucionRequest = {
        observaciones: observaciones.trim(),
        notificar_proveedor: notificarProveedor,
        notificar_responsable: notificarResponsable,
      };

      await facturasService.devolverFactura(facturaId, request);

      // Limpiar formulario
      setObservaciones('');
      setNotificarProveedor(true);
      setNotificarResponsable(true);

      // Notificar éxito
      if (onDevolucionSuccess) {
        onDevolucionSuccess();
      }

      // Cerrar dialog
      onClose();
    } catch (err: any) {
      console.error('Error al devolver factura:', err);
      setError(
        err.response?.data?.detail ||
          'Error al devolver la factura. Por favor intente nuevamente.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setObservaciones('');
      setError(null);
      onClose();
    }
  };

  const caracteresRestantes = 1000 - observaciones.length;
  const isObservacionesValida =
    observaciones.trim().length >= 10 && observaciones.trim().length <= 1000;

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box display="flex" alignItems="center" gap={1}>
          <Undo color="warning" />
          <Typography variant="h6" fontWeight={600}>
            Devolver Factura {numeroFactura}
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Especifique la información adicional requerida. El proveedor y el responsable serán
          notificados por email.
        </Typography>
      </DialogTitle>

      <DialogContent sx={{ pt: 2 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <TextField
          label="Información Requerida"
          placeholder="Ejemplo: Falta especificar el centro de costos del departamento de IT. Por favor incluir esta información en las observaciones de la factura."
          multiline
          rows={6}
          fullWidth
          value={observaciones}
          onChange={(e) => setObservaciones(e.target.value)}
          error={observaciones.length > 0 && !isObservacionesValida}
          helperText={
            observaciones.length > 0 && !isObservacionesValida
              ? `Mínimo 10 caracteres. ${caracteresRestantes < 0 ? 'Excede el límite.' : `${caracteresRestantes} restantes.`}`
              : `${caracteresRestantes} caracteres restantes`
          }
          sx={{ mb: 3 }}
          disabled={loading}
        />

        <Typography variant="subtitle2" fontWeight={600} gutterBottom>
          Notificaciones
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Seleccione a quién desea notificar sobre la devolución
        </Typography>

        <FormGroup>
          <FormControlLabel
            control={
              <Checkbox
                checked={notificarProveedor}
                onChange={(e) => setNotificarProveedor(e.target.checked)}
                disabled={loading}
              />
            }
            label={
              <Box>
                <Typography variant="body2" fontWeight={600}>
                  Notificar al Proveedor
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Se enviará un email al proveedor solicitando la información faltante
                </Typography>
              </Box>
            }
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={notificarResponsable}
                onChange={(e) => setNotificarResponsable(e.target.checked)}
                disabled={loading}
              />
            }
            label={
              <Box>
                <Typography variant="body2" fontWeight={600}>
                  Notificar al Responsable que aprobó
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Se enviará un email informativo al responsable que aprobó esta factura
                </Typography>
              </Box>
            }
          />
        </FormGroup>

        {!notificarProveedor && !notificarResponsable && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            No se enviará ninguna notificación. El estado de la factura cambiará pero nadie será
            alertado.
          </Alert>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 3, gap: 1 }}>
        <Button onClick={handleClose} disabled={loading} variant="outlined">
          Cancelar
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={loading || !isObservacionesValida}
          variant="contained"
          color="warning"
          startIcon={loading ? <CircularProgress size={20} /> : <Send />}
        >
          {loading ? 'Devolviendo...' : 'Devolver Factura'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default DevolucionDialog;
