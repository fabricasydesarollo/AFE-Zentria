import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  Divider,
  Stack,
  Chip,
  Paper,
  IconButton,
} from '@mui/material';
import { Cancel, Warning, Receipt, Info, Close } from '@mui/icons-material';
import { zentriaColors } from '../../theme/colors';
import type { Workflow } from '../../types/factura.types';

interface RejectionDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (motivo: string, observaciones: string) => Promise<void>;
  facturaNumero: string;
  workflow?: Workflow | null;
  loading?: boolean;
}

/**
 * Diálogo de confirmación para rechazar facturas
 * Requiere motivo y permite agregar observaciones adicionales
 * Diseño profesional con colores corporativos Zentria
 */
function RejectionDialog({ open, onClose, onConfirm, facturaNumero, workflow, loading = false }: RejectionDialogProps) {
  const [motivo, setMotivo] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [error, setError] = useState('');

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '-';
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const motivosRechazo = [
    { value: 'datos_incorrectos', label: 'Datos incorrectos o incompletos' },
    { value: 'monto_no_coincide', label: 'Monto no coincide con lo esperado' },
    { value: 'proveedor_no_autorizado', label: 'Proveedor no autorizado' },
    { value: 'factura_duplicada', label: 'Factura duplicada' },
    { value: 'fuera_presupuesto', label: 'Fuera de presupuesto' },
    { value: 'sin_orden_compra', label: 'Sin orden de compra asociada' },
    { value: 'documentacion_faltante', label: 'Documentación faltante' },
    { value: 'otro', label: 'Otro (especificar en observaciones)' },
  ];

  const handleConfirm = async () => {
    if (!motivo) {
      setError('Debe seleccionar un motivo de rechazo');
      return;
    }

    if (motivo === 'otro' && !observaciones.trim()) {
      setError('Debe especificar el motivo en las observaciones');
      return;
    }

    setError('');
    try {
      await onConfirm(motivo, observaciones);
      setMotivo('');
      setObservaciones('');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Error al rechazar la factura');
    }
  };

  const handleClose = () => {
    if (!loading) {
      setMotivo('');
      setObservaciones('');
      setError('');
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      aria-modal="true"
      disableEnforceFocus
      PaperProps={{
        sx: {
          borderRadius: 3,
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
          overflow: 'hidden',
        }
      }}
    >
      {/* Header con Gradiente Corporativo */}
      <Box
        sx={{
          background: `linear-gradient(135deg, ${zentriaColors.naranja.main} 0%, ${zentriaColors.naranja.dark} 100%)`,
          color: 'white',
          p: 3,
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Stack direction="row" spacing={2} alignItems="center" flex={1}>
          <Box
            sx={{
              width: 50,
              height: 50,
              borderRadius: '50%',
              backgroundColor: 'rgba(255, 255, 255, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backdropFilter: 'blur(10px)',
            }}
          >
            <Cancel sx={{ fontSize: 28 }} />
          </Box>
          <Box>
            <Typography variant="h5" fontWeight={700}>
              Rechazar Factura
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.9 }}>
              {facturaNumero}
            </Typography>
          </Box>
        </Stack>
        <IconButton
          onClick={handleClose}
          disabled={loading}
          aria-label="Cerrar diálogo"
          sx={{
            color: 'white',
            backgroundColor: 'rgba(255, 255, 255, 0.15)',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.25)',
            },
            '&:disabled': {
              color: 'rgba(255, 255, 255, 0.5)',
            },
          }}
        >
          <Close />
        </IconButton>
      </Box>

      <DialogContent sx={{ p: 3, backgroundColor: '#fafafa' }}>
        {/* Alert Informativo */}
        <Alert
          severity="warning"
          icon={<Warning sx={{ color: zentriaColors.naranja.main }} />}
          sx={{
            mb: 3,
            backgroundColor: `${zentriaColors.naranja.light}15`,
            border: `1px solid ${zentriaColors.naranja.light}`,
            borderRadius: 2,
            '& .MuiAlert-message': {
              color: '#333',
            },
          }}
        >
          <Typography variant="body2" fontWeight={600} color="#333">
            El rechazo debe estar justificado. Esta acción quedará registrada en el historial de auditoría.
          </Typography>
        </Alert>

        {/* Información de la Factura en Tarjeta */}
        {workflow?.factura && (
          <Card
            elevation={0}
            sx={{
              mb: 3,
              backgroundColor: 'white',
              border: `1px solid ${zentriaColors.cinza}`,
              borderRadius: 2,
              overflow: 'hidden',
            }}
          >
            <Box
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.naranja.main}10 0%, ${zentriaColors.naranja.light}15 100%)`,
                p: 2,
                borderBottom: `1px solid ${zentriaColors.cinza}`,
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <Receipt sx={{ color: zentriaColors.naranja.main, fontSize: 24 }} />
              <Typography variant="subtitle2" fontWeight={700} color={zentriaColors.naranja.main}>
                Información de la Factura
              </Typography>
            </Box>
            <CardContent sx={{ p: 2 }}>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="caption" fontWeight={600} color="text.secondary">
                    PROVEEDOR
                  </Typography>
                  <Typography variant="body2" fontWeight={600} color="#333">
                    {workflow.factura.proveedor?.razon_social || '-'}
                  </Typography>
                </Box>
                <Divider />
                <Stack direction="row" spacing={2}>
                  <Box flex={1}>
                    <Typography variant="caption" fontWeight={600} color="text.secondary">
                      NIT
                    </Typography>
                    <Typography variant="body2" fontWeight={600} color="#333">
                      {workflow.factura.proveedor?.nit || '-'}
                    </Typography>
                  </Box>
                  <Box flex={1}>
                    <Typography variant="caption" fontWeight={600} color="text.secondary">
                      SUBTOTAL
                    </Typography>
                    <Typography variant="body2" fontWeight={600} color="#333">
                      {formatCurrency(workflow.factura.subtotal)}
                    </Typography>
                  </Box>
                </Stack>
                <Stack direction="row" spacing={2}>
                  <Box flex={1}>
                    <Typography variant="caption" fontWeight={600} color="text.secondary">
                      IVA
                    </Typography>
                    <Typography variant="body2" fontWeight={600} color="#333">
                      {formatCurrency(workflow.factura.iva)}
                    </Typography>
                  </Box>
                  <Box flex={1}>
                    <Typography variant="caption" fontWeight={600} color="text.secondary">
                      TOTAL A PAGAR
                    </Typography>
                    <Typography
                      variant="body2"
                      fontWeight={700}
                      sx={{
                        color: zentriaColors.naranja.main,
                        fontSize: '1.1rem',
                      }}
                    >
                      {formatCurrency(workflow.factura.total_a_pagar)}
                    </Typography>
                  </Box>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        )}

        {/* Error Alert */}
        {error && (
          <Alert
            severity="error"
            sx={{
              mb: 3,
              backgroundColor: '#ffebee',
              border: '1px solid #ef5350',
              borderRadius: 2,
              '& .MuiAlert-message': {
                color: '#c62828',
              },
            }}
          >
            <Typography variant="body2" fontWeight={600}>
              {error}
            </Typography>
          </Alert>
        )}

        {/* Sección de Motivo */}
        <Box mb={2}>
          <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Info sx={{ fontSize: 20, color: zentriaColors.naranja.main }} />
            Razón del Rechazo
          </Typography>
          <FormControl fullWidth>
            <InputLabel
              sx={{
                color: 'text.secondary',
                '&.Mui-focused': {
                  color: zentriaColors.naranja.main,
                },
              }}
            >
              Motivo de Rechazo *
            </InputLabel>
            <Select
              value={motivo}
              onChange={(e) => {
                setMotivo(e.target.value);
                setError('');
              }}
              label="Motivo de Rechazo *"
              disabled={loading}
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&.Mui-focused fieldset': {
                    borderColor: zentriaColors.naranja.main,
                  },
                },
              }}
            >
              {motivosRechazo.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  <Typography fontWeight={500}>{option.label}</Typography>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {/* Campo de Observaciones */}
        <Box>
          <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Info sx={{ fontSize: 20, color: zentriaColors.violeta.main }} />
            Detalles Adicionales
          </Typography>
          <TextField
            fullWidth
            label={motivo === 'otro' ? 'Especifique el motivo *' : 'Observaciones adicionales (opcional)'}
            placeholder={motivo === 'otro' ? 'Describa el motivo del rechazo...' : 'Agrega detalles sobre el rechazo...'}
            multiline
            rows={4}
            value={observaciones}
            onChange={(e) => {
              setObservaciones(e.target.value);
              if (error) setError('');
            }}
            disabled={loading}
            required={motivo === 'otro'}
            sx={{
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'white',
                borderRadius: 2,
                '&:hover fieldset': {
                  borderColor: zentriaColors.naranja.light,
                },
                '&.Mui-focused fieldset': {
                  borderColor: zentriaColors.naranja.main,
                  borderWidth: 2,
                },
              },
              '& .MuiOutlinedInput-input::placeholder': {
                color: 'text.secondary',
                opacity: 0.7,
              },
            }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', fontWeight: 500 }}>
            {motivo === 'otro' ? '* Campo obligatorio' : 'Este texto será registrado en el historial de auditoría'}
          </Typography>
        </Box>
      </DialogContent>

      {/* Footer de Acciones */}
      <Box
        sx={{
          backgroundColor: '#f5f5f5',
          p: 3,
          borderTop: `1px solid ${zentriaColors.cinza}`,
          display: 'flex',
          gap: 2,
          justifyContent: 'flex-end',
        }}
      >
        <Button
          onClick={handleClose}
          disabled={loading}
          variant="outlined"
          sx={{
            minWidth: 120,
            borderColor: zentriaColors.cinza,
            color: '#555',
            fontWeight: 600,
            '&:hover': {
              backgroundColor: '#f0f0f0',
              borderColor: zentriaColors.naranja.light,
            },
            '&:disabled': {
              color: '#999',
              borderColor: '#ddd',
            },
          }}
        >
          Cancelar
        </Button>
        <Button
          onClick={handleConfirm}
          disabled={loading || !motivo}
          variant="contained"
          sx={{
            minWidth: 160,
            background: `linear-gradient(135deg, ${zentriaColors.naranja.main} 0%, ${zentriaColors.naranja.dark} 100%)`,
            color: 'white',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            boxShadow: `0 4px 15px ${zentriaColors.naranja.main}40`,
            '&:hover': {
              boxShadow: `0 6px 20px ${zentriaColors.naranja.main}60`,
            },
            '&:disabled': {
              background: '#ccc',
              boxShadow: 'none',
            },
          }}
          startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <Cancel />}
        >
          {loading ? 'Rechazando...' : 'Confirmar Rechazo'}
        </Button>
      </Box>
    </Dialog>
  );
}

export default RejectionDialog;
