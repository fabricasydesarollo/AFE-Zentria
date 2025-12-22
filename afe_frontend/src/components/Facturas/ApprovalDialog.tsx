import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  Button,
  TextField,
  Box,
  Typography,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Divider,
  Stack,
  IconButton,
} from '@mui/material';
import { CheckCircle, Close, Info as InfoIcon, Receipt } from '@mui/icons-material';
import { zentriaColors } from '../../theme/colors';
import type { Workflow } from '../../types/factura.types';

interface ApprovalDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (observaciones: string) => Promise<void>;
  facturaNumero: string;
  workflow?: Workflow | null;
  loading?: boolean;
}

/**
 * Diálogo de confirmación para aprobar facturas
 * Permite agregar observaciones opcionales
 * Diseño profesional con colores corporativos Zentria
 */
function ApprovalDialog({ open, onClose, onConfirm, facturaNumero, workflow, loading = false }: ApprovalDialogProps) {
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

  const handleConfirm = async () => {
    setError('');
    try {
      await onConfirm(observaciones);
      setObservaciones('');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Error al aprobar la factura');
    }
  };

  const handleClose = () => {
    if (!loading) {
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
          boxShadow: '0 12px 48px rgba(0, 0, 0, 0.2)',
          overflow: 'hidden',
        }
      }}
    >
      {/* Header con Gradiente Corporativo Verde */}
      <Box
        sx={{
          background: `linear-gradient(135deg, ${zentriaColors.verde.main} 0%, ${zentriaColors.verde.dark} 100%)`,
          color: 'white',
          p: 4,
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Stack direction="row" spacing={2} alignItems="center" flex={1}>
          <Box
            sx={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              backgroundColor: 'rgba(255, 255, 255, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backdropFilter: 'blur(10px)',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            }}
          >
            <CheckCircle sx={{ fontSize: 32 }} />
          </Box>
          <Box>
            <Typography variant="h5" fontWeight={700} sx={{ lineHeight: 1.2 }}>
              Aprobar Factura
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.95, mt: 0.5, fontSize: '0.9rem' }}>
              {facturaNumero}
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.85, display: 'block', mt: 0.5 }}>
              Confirma la aprobación para continuar el flujo
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

      <DialogContent sx={{
        pt: '32px !important',
        pb: '32px !important',
        px: '32px !important',
        backgroundColor: '#fafafa'
      }}>
        {/* Alert Informativo */}
        <Alert
          severity="info"
          icon={<InfoIcon sx={{ color: zentriaColors.verde.main, fontSize: 24 }} />}
          sx={{
            mb: 3,
            backgroundColor: `${zentriaColors.verde.light}15`,
            border: `2px solid ${zentriaColors.verde.light}`,
            borderRadius: 2.5,
            p: 2,
            '& .MuiAlert-message': {
              color: '#333',
            },
          }}
        >
          <Typography variant="body2" fontWeight={600} color="#333" sx={{ lineHeight: 1.6 }}>
            Al aprobar esta factura, el workflow avanzará automáticamente según las reglas configuradas.
          </Typography>
        </Alert>

        {/* Información de la Factura en Tarjeta */}
        {workflow?.factura && (
          <Card
            elevation={0}
            sx={{
              mb: 3,
              backgroundColor: 'white',
              border: `2px solid ${zentriaColors.verde.light}40`,
              borderRadius: 3,
              overflow: 'hidden',
              boxShadow: '0 2px 12px rgba(0, 179, 148, 0.08)',
            }}
          >
            <Box
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.verde.main}15 0%, ${zentriaColors.verde.light}20 100%)`,
                p: 2.5,
                borderBottom: `2px solid ${zentriaColors.verde.light}40`,
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
              }}
            >
              <Box sx={{
                p: 1,
                backgroundColor: `${zentriaColors.verde.main}20`,
                borderRadius: 1.5,
                display: 'flex',
                alignItems: 'center'
              }}>
                <Receipt sx={{ color: zentriaColors.verde.main, fontSize: 24 }} />
              </Box>
              <Typography variant="subtitle2" fontWeight={700} color={zentriaColors.verde.main} sx={{ fontSize: '1rem' }}>
                Información de la Factura
              </Typography>
            </Box>
            <CardContent sx={{ p: 3 }}>
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
                        color: zentriaColors.verde.main,
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

        {/* Campo de Observaciones */}
        <Box>
          <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
            <InfoIcon sx={{ fontSize: 20, color: zentriaColors.verde.main }} />
            Observaciones Adicionales
          </Typography>
          <TextField
            fullWidth
            label="Observaciones (opcional)"
            placeholder="Agrega cualquier comentario o nota sobre esta aprobación..."
            multiline
            rows={4}
            value={observaciones}
            onChange={(e) => {
              setObservaciones(e.target.value);
              if (error) setError('');
            }}
            disabled={loading}
            sx={{
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'white',
                borderRadius: 2.5,
                transition: 'all 0.2s ease',
                '&:hover': {
                  backgroundColor: 'white',
                  boxShadow: `0 0 0 2px ${zentriaColors.verde.light}40`,
                },
                '&:hover fieldset': {
                  borderColor: zentriaColors.verde.light,
                },
                '&.Mui-focused': {
                  backgroundColor: 'white',
                  boxShadow: `0 0 0 3px ${zentriaColors.verde.light}30`,
                },
                '&.Mui-focused fieldset': {
                  borderColor: zentriaColors.verde.main,
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
            Este texto será registrado en el historial de auditoría
          </Typography>
        </Box>
      </DialogContent>

      {/* Footer de Acciones */}
      <Box
        sx={{
          backgroundColor: 'white',
          p: 3.5,
          borderTop: `2px solid ${zentriaColors.cinza}`,
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
            minWidth: 130,
            px: 4,
            py: 1.5,
            borderRadius: 2.5,
            borderColor: zentriaColors.cinza,
            color: '#555',
            fontWeight: 600,
            fontSize: '0.95rem',
            transition: 'all 0.2s ease',
            '&:hover': {
              backgroundColor: '#f0f0f0',
              borderColor: zentriaColors.verde.light,
              transform: 'translateY(-1px)',
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
          disabled={loading}
          variant="contained"
          sx={{
            minWidth: 180,
            px: 5,
            py: 1.5,
            borderRadius: 2.5,
            background: `linear-gradient(135deg, ${zentriaColors.verde.main} 0%, ${zentriaColors.verde.dark} 100%)`,
            color: 'white',
            fontWeight: 700,
            fontSize: '0.95rem',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            boxShadow: `0 4px 20px ${zentriaColors.verde.main}50`,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': {
              boxShadow: `0 8px 28px ${zentriaColors.verde.main}70`,
              transform: 'translateY(-2px)',
            },
            '&:active': {
              transform: 'translateY(0)',
            },
            '&:disabled': {
              background: '#ccc',
              boxShadow: 'none',
            },
          }}
          startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <CheckCircle />}
        >
          {loading ? 'Aprobando...' : 'Confirmar Aprobación'}
        </Button>
      </Box>
    </Dialog>
  );
}

export default ApprovalDialog;
