/**
 * Dialog para Agregar un NIT Individual
 *
 * Características:
 * - Validación de NIT en tiempo real a través del backend
 * - Muestra el NIT normalizado (XXXXXXXXX-D) mientras escribe
 * - Calcula automáticamente el dígito verificador DIAN
 * - Validación robusta de formato
 */

import React, { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Alert,
  Box,
  IconButton,
  CircularProgress,
  Chip,
} from '@mui/material';
import { Close as CloseIcon, CheckCircle as CheckCircleIcon, ErrorOutline as ErrorCircleIcon } from '@mui/icons-material';
import { useAppDispatch } from '../../../app/hooks';
import { crearNit } from '../emailConfigSlice';
import nitValidationService, { ValidationResult } from '../../../services/nitValidation.service';

const schema = z.object({
  nit: z
    .string()
    .min(5, 'El NIT debe tener al menos 5 caracteres')
    .max(20, 'El NIT no puede exceder 20 caracteres'),
  nombre_proveedor: z.string().optional(),
  notas: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onClose: () => void;
  cuentaId: number;
  onSuccess: () => void;
}

const AddNitDialog: React.FC<Props> = ({ open, onClose, cuentaId, onSuccess }) => {
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validatingNit, setValidatingNit] = useState(false);
  const [nitValidation, setNitValidation] = useState<ValidationResult | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
    watch: watchForm,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    mode: 'onChange',
  });

  const nitValue = watchForm('nit');

  // Validar NIT en tiempo real cuando el usuario escribe
  useEffect(() => {
    if (!nitValue || nitValue.trim().length < 5) {
      setNitValidation(null);
      return;
    }

    const validateNitDebounced = async () => {
      setValidatingNit(true);
      try {
        const result = await nitValidationService.validateNit(nitValue);
        setNitValidation(result);
      } catch (err) {
        console.error('Error validating NIT:', err);
        setNitValidation({
          isValid: false,
          errorMessage: 'Error al validar NIT',
        });
      } finally {
        setValidatingNit(false);
      }
    };

    // Debounce: esperar 500ms antes de validar
    const timer = setTimeout(validateNitDebounced, 500);
    return () => clearTimeout(timer);
  }, [nitValue]);

  const handleClose = () => {
    reset();
    setError(null);
    setNitValidation(null);
    onClose();
  };

  const onSubmit = async (data: FormData) => {
    // Validar que el NIT sea válido antes de enviar
    if (!nitValidation?.isValid) {
      setError('El NIT no es válido. Por favor, revise el formato.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Usar el NIT normalizado
      const normalizedNit = nitValidation.normalizedNit || data.nit;

      await dispatch(
        crearNit({
          cuenta_correo_id: cuentaId,
          nit: normalizedNit,
          nombre_proveedor: data.nombre_proveedor || undefined,
          notas: data.notas || undefined,
        })
      ).unwrap();

      onSuccess();
      handleClose();
    } catch (err: any) {
      setError(err.message || 'Error al agregar NIT');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth aria-modal="true" disableEnforceFocus>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
            ➕ Agregar NIT
          </Typography>
          <IconButton onClick={handleClose} size="small" disabled={loading}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent dividers>
          {error && (
            <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Controller
            name="nit"
            control={control}
            render={({ field }) => (
              <Box sx={{ mb: 2 }}>
                <TextField
                  {...field}
                  label="NIT *"
                  fullWidth
                  error={!!errors.nit || !!(nitValue && nitValidation && !nitValidation.isValid)}
                  helperText={
                    errors.nit?.message ||
                    (nitValue &&
                    validatingNit &&
                    'Validando NIT...') ||
                    (nitValue &&
                    nitValidation &&
                    nitValidation.errorMessage) ||
                    'Ingrese NIT sin o con dígito verificador (ej: 800185449)'
                  }
                  placeholder="901234567"
                  autoFocus
                  disabled={loading}
                  InputProps={{
                    endAdornment: validatingNit ? (
                      <CircularProgress size={20} />
                    ) : nitValue && nitValidation ? (
                      nitValidation.isValid ? (
                        <CheckCircleIcon sx={{ color: 'success.main' }} />
                      ) : (
                        <ErrorCircleIcon sx={{ color: 'error.main' }} />
                      )
                    ) : null,
                  }}
                />
                {nitValue && nitValidation?.isValid && (
                  <Box sx={{ mt: 1 }}>
                    <Chip
                      icon={<CheckCircleIcon />}
                      label={`NIT normalizado: ${nitValidation.normalizedNit}`}
                      color="success"
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                )}
              </Box>
            )}
          />

          <Controller
            name="nombre_proveedor"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Nombre del Proveedor"
                fullWidth
                error={!!errors.nombre_proveedor}
                helperText={errors.nombre_proveedor?.message || 'Opcional'}
                placeholder="Ej: Proveedor ABC S.A."
                sx={{ mb: 2 }}
                disabled={loading}
              />
            )}
          />

          <Controller
            name="notas"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Notas"
                fullWidth
                multiline
                rows={3}
                error={!!errors.notas}
                helperText={errors.notas?.message || 'Notas adicionales (opcional)'}
                placeholder="Información adicional sobre este proveedor..."
                disabled={loading}
              />
            )}
          />
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleClose} disabled={loading}>
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={loading || !nitValidation?.isValid}
            sx={{ minWidth: 120 }}
          >
            {loading ? 'Agregando...' : 'Agregar NIT'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default AddNitDialog;
