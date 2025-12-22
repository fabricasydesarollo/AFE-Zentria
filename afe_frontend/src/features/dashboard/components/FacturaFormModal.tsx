/**
 * Professional modal for creating and editing facturas
 * Modern design with validation and professional UX
 */

import {
  Dialog,
  DialogContent,
  DialogActions,
  Button,
  Grid,
  TextField,
  Alert,
  Box,
  Typography,
  IconButton,
  Stack,
  MenuItem,
} from '@mui/material';
import { Close, Save, Receipt } from '@mui/icons-material';
import { zentriaColors } from '../../../theme/colors';
import type { DialogMode, FacturaFormData, EstadoFactura } from '../types';

interface FacturaFormModalProps {
  open: boolean;
  mode: DialogMode;
  formData: FacturaFormData;
  onFormChange: (field: keyof FacturaFormData, value: string) => void;
  onClose: () => void;
  onSave: () => void;
  error?: string;
}

export const FacturaFormModal: React.FC<FacturaFormModalProps> = ({
  open,
  mode,
  formData,
  onFormChange,
  onClose,
  onSave,
  error,
}) => {
  const isEditMode = mode === 'edit';
  const isFormValid =
    formData.numero_factura &&
    formData.nit_emisor &&
    formData.nombre_emisor &&
    formData.monto_total &&
    formData.fecha_emision;

  const getTitle = () => {
    return isEditMode ? 'Editar Factura' : 'Nueva Factura';
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
        }
      }}
    >
      {/* Professional Header */}
      <Box
        sx={{
          background: `linear-gradient(135deg, ${zentriaColors.violeta.main} 0%, ${zentriaColors.violeta.dark} 100%)`,
          color: 'white',
          p: 3,
          position: 'relative',
        }}
      >
        <IconButton
          onClick={onClose}
          aria-label="Cerrar formulario"
          sx={{
            position: 'absolute',
            right: 16,
            top: 16,
            color: 'white',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.2)',
            },
          }}
        >
          <Close />
        </IconButton>

        <Stack direction="row" spacing={2} alignItems="center">
          <Receipt sx={{ fontSize: 40 }} />
          <Box>
            <Typography variant="h5" fontWeight={700}>
              {getTitle()}
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              {isEditMode ? 'Modifica los datos de la factura' : 'Ingresa los datos de la nueva factura'}
            </Typography>
          </Box>
        </Stack>
      </Box>

      <DialogContent sx={{ p: 3 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* Número de Factura */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth
              label="Número de Factura"
              value={formData.numero_factura}
              onChange={(e) => onFormChange('numero_factura', e.target.value)}
              required
              variant="outlined"
              placeholder="Ej: E921, FE63537"
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&.Mui-focused fieldset': {
                    borderColor: zentriaColors.violeta.main,
                  },
                },
                '& .MuiInputLabel-root.Mui-focused': {
                  color: zentriaColors.violeta.main,
                },
              }}
            />
          </Grid>

          {/* NIT Emisor */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth
              label="NIT Emisor"
              value={formData.nit_emisor}
              onChange={(e) => onFormChange('nit_emisor', e.target.value)}
              required
              variant="outlined"
              placeholder="Ej: 901261003-1"
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&.Mui-focused fieldset': {
                    borderColor: zentriaColors.violeta.main,
                  },
                },
                '& .MuiInputLabel-root.Mui-focused': {
                  color: zentriaColors.violeta.main,
                },
              }}
            />
          </Grid>

          {/* Nombre Emisor */}
          <Grid size={{ xs: 12 }}>
            <TextField
              fullWidth
              label="Nombre Emisor"
              value={formData.nombre_emisor}
              onChange={(e) => onFormChange('nombre_emisor', e.target.value)}
              required
              variant="outlined"
              placeholder="Ej: KION PROCESOS Y TECNOLOGIA S.A.S"
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&.Mui-focused fieldset': {
                    borderColor: zentriaColors.violeta.main,
                  },
                },
                '& .MuiInputLabel-root.Mui-focused': {
                  color: zentriaColors.violeta.main,
                },
              }}
            />
          </Grid>

          {/* Monto Total */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth
              label="Monto Total"
              type="number"
              value={formData.monto_total}
              onChange={(e) => onFormChange('monto_total', e.target.value)}
              required
              variant="outlined"
              placeholder="0.00"
              InputProps={{
                startAdornment: <Typography sx={{ mr: 1, color: 'text.secondary' }}>$</Typography>,
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&.Mui-focused fieldset': {
                    borderColor: zentriaColors.verde.main,
                  },
                },
                '& .MuiInputLabel-root.Mui-focused': {
                  color: zentriaColors.verde.main,
                },
              }}
            />
          </Grid>

          {/* Fecha Emisión */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth
              label="Fecha Emisión"
              type="date"
              value={formData.fecha_emision}
              onChange={(e) => onFormChange('fecha_emision', e.target.value)}
              required
              InputLabelProps={{ shrink: true }}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&.Mui-focused fieldset': {
                    borderColor: zentriaColors.violeta.main,
                  },
                },
                '& .MuiInputLabel-root.Mui-focused': {
                  color: zentriaColors.violeta.main,
                },
              }}
            />
          </Grid>

          {/* Fecha Vencimiento */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth
              label="Fecha Vencimiento"
              type="date"
              value={formData.fecha_vencimiento}
              onChange={(e) => onFormChange('fecha_vencimiento', e.target.value)}
              InputLabelProps={{ shrink: true }}
              variant="outlined"
              helperText="Opcional"
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&.Mui-focused fieldset': {
                    borderColor: zentriaColors.naranja.main,
                  },
                },
                '& .MuiInputLabel-root.Mui-focused': {
                  color: zentriaColors.naranja.main,
                },
              }}
            />
          </Grid>

          {/* Observaciones */}
          <Grid size={{ xs: 12 }}>
            <TextField
              fullWidth
              label="Observaciones"
              multiline
              rows={4}
              value={formData.observaciones}
              onChange={(e) => onFormChange('observaciones', e.target.value)}
              variant="outlined"
              placeholder="Agrega notas o comentarios adicionales sobre esta factura..."
              helperText="Opcional - Máximo 500 caracteres"
              inputProps={{ maxLength: 500 }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  '&.Mui-focused fieldset': {
                    borderColor: zentriaColors.violeta.main,
                  },
                },
                '& .MuiInputLabel-root.Mui-focused': {
                  color: zentriaColors.violeta.main,
                },
              }}
            />
          </Grid>
        </Grid>

        {/* Form validation indicator */}
        {!isFormValid && (
          <Alert severity="info" sx={{ mt: 3, borderRadius: 2 }}>
            Por favor completa todos los campos requeridos (marcados con *)
          </Alert>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 3, backgroundColor: '#f8f9fa', gap: 2 }}>
        <Button
          onClick={onClose}
          variant="outlined"
          size="large"
          sx={{
            minWidth: 120,
            borderColor: 'divider',
            color: 'text.secondary',
            '&:hover': {
              borderColor: 'text.secondary',
              backgroundColor: 'action.hover',
            },
          }}
        >
          Cancelar
        </Button>
        <Button
          variant="contained"
          onClick={onSave}
          disabled={!isFormValid}
          size="large"
          startIcon={<Save />}
          sx={{
            minWidth: 120,
            background: isFormValid
              ? `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`
              : undefined,
            boxShadow: isFormValid ? '0 4px 14px rgba(128, 0, 106, 0.25)' : undefined,
            fontWeight: 700,
            textTransform: 'none',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': isFormValid ? {
              transform: 'translateY(-2px)',
              boxShadow: '0 8px 20px rgba(128, 0, 106, 0.35)',
            } : undefined,
            '&:active': {
              transform: 'translateY(0)',
            },
            '&.Mui-disabled': {
              opacity: 0.5,
            },
          }}
        >
          {isEditMode ? 'Guardar Cambios' : 'Crear Factura'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
