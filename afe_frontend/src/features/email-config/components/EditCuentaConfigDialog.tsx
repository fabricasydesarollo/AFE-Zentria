/**
 * Dialog para Editar Configuración de Cuenta de Correo
 * Formulario validado con React Hook Form + Zod
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
  Grid,
  Typography,
  Alert,
  Box,
  IconButton,
  Divider,
  FormControlLabel,
  Switch,
} from '@mui/material';
import {
  Close as CloseIcon,
} from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../../../app/hooks';
import { actualizarCuenta } from '../emailConfigSlice';
import { CuentaCorreoDetalle } from '../../../services/emailConfigService';

// Validación con Zod
const schema = z.object({
  email: z.string().email('Email inválido').min(1, 'Email requerido'),
  nombre_descriptivo: z.string().optional(),
  max_correos_por_ejecucion: z.number().min(1).max(100000),
  ventana_inicial_dias: z.number().min(1).max(365),
  organizacion: z.string().optional(),
  activa: z.boolean(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  cuenta: CuentaCorreoDetalle | null;
}

const EditCuentaConfigDialog: React.FC<Props> = ({ open, onClose, onSuccess, cuenta }) => {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: '',
      nombre_descriptivo: '',
      max_correos_por_ejecucion: 500,
      ventana_inicial_dias: 90,
      organizacion: '',
      activa: true,
    },
  });

  // Verificar si el usuario es admin o superadmin
  const isAdmin = user?.rol === 'admin' || user?.rol === 'superadmin';

  // Actualizar valores por defecto cuando cuenta cambia
  useEffect(() => {
    if (cuenta && open) {
      reset({
        email: cuenta.email || '',
        nombre_descriptivo: cuenta.nombre_descriptivo || '',
        max_correos_por_ejecucion: cuenta.max_correos_por_ejecucion || 500,
        ventana_inicial_dias: cuenta.ventana_inicial_dias || 90,
        organizacion: cuenta.organizacion || '',
        activa: cuenta.activa,
      });
    }
  }, [cuenta, open, reset]);

  const handleClose = () => {
    reset();
    setError(null);
    onClose();
  };

  const onSubmit = async (data: FormData) => {
    if (!cuenta || !user) return;

    // Detectar cambios comparando con los valores originales
    const cambios: Record<string, any> = {};

    // Solo admin puede cambiar el email
    if (isAdmin && data.email !== cuenta.email) {
      cambios.email = data.email;
    }

    if ((data.nombre_descriptivo || '') !== (cuenta.nombre_descriptivo || '')) {
      cambios.nombre_descriptivo = data.nombre_descriptivo || undefined;
    }
    if (data.max_correos_por_ejecucion !== cuenta.max_correos_por_ejecucion) {
      cambios.max_correos_por_ejecucion = data.max_correos_por_ejecucion;
    }
    if (data.ventana_inicial_dias !== cuenta.ventana_inicial_dias) {
      cambios.ventana_inicial_dias = data.ventana_inicial_dias;
    }
    if (data.activa !== cuenta.activa) {
      cambios.activa = data.activa;
    }
    if ((data.organizacion || '') !== (cuenta.organizacion || '')) {
      cambios.organizacion = data.organizacion || undefined;
    }

    // Si no hay cambios, mostrar mensaje
    if (Object.keys(cambios).length === 0) {
      setError('No hay cambios para guardar');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await dispatch(
        actualizarCuenta({
          cuentaId: cuenta.id,
          data: {
            ...cambios,
            actualizada_por: user.usuario,
          },
        })
      ).unwrap();

      onSuccess();
      handleClose();
    } catch (err: any) {
      setError(err.message || 'Error al actualizar la cuenta');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth aria-modal="true" disableEnforceFocus>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
            ✏️ Editar Configuración de Correo
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

          <Grid container spacing={3}>
            {/* Información Básica */}
            <Grid size={{ xs: 12 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                Información Básica
              </Typography>
            </Grid>

            <Grid size={{ xs: 12 }}>
              <Controller
                name="email"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Email"
                    fullWidth
                    type="email"
                    error={!!errors.email}
                    helperText={
                      errors.email?.message ||
                      (isAdmin
                        ? 'Solo admin/super admin pueden modificar el email'
                        : 'El email no se puede modificar. Crea una nueva cuenta si necesitas cambiar el email.')
                    }
                    disabled={!isAdmin || loading}
                    placeholder="facturacion@empresa.com"
                  />
                )}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Controller
                name="nombre_descriptivo"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Nombre Descriptivo"
                    fullWidth
                    error={!!errors.nombre_descriptivo}
                    helperText={errors.nombre_descriptivo?.message || 'Nombre amigable (opcional)'}
                    placeholder="Angiografía de Colombia"
                    disabled={loading}
                  />
                )}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Controller
                name="organizacion"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Organización"
                    fullWidth
                    error={!!errors.organizacion}
                    helperText={errors.organizacion?.message || 'Ej: ANGIOGRAFIA, AVIDANTI'}
                    placeholder="ANGIOGRAFIA"
                    disabled={loading}
                  />
                )}
              />
            </Grid>

            {/* Configuración de Extracción */}
            <Grid size={{ xs: 12 }}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                Configuración de Extracción
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Controller
                name="max_correos_por_ejecucion"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    type="number"
                    label="Límite de Correos"
                    fullWidth
                    error={!!errors.max_correos_por_ejecucion}
                    helperText={errors.max_correos_por_ejecucion?.message || 'Correos a procesar por ejecución (1-100000)'}
                    onChange={(e) => field.onChange(Number(e.target.value))}
                    disabled={loading}
                  />
                )}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Controller
                name="ventana_inicial_dias"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    type="number"
                    label="Días Retroactivos"
                    fullWidth
                    error={!!errors.ventana_inicial_dias}
                    helperText={errors.ventana_inicial_dias?.message || 'Días hacia atrás para buscar (1-365)'}
                    onChange={(e) => field.onChange(Number(e.target.value))}
                    disabled={loading}
                  />
                )}
              />
            </Grid>

            {/* Estado de la Cuenta */}
            <Grid size={{ xs: 12 }}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                Estado
              </Typography>
            </Grid>

            <Grid size={{ xs: 12 }}>
              <Controller
                name="activa"
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={
                      <Switch
                        {...field}
                        checked={field.value}
                        disabled={loading}
                        color="success"
                      />
                    }
                    label={field.value ? 'Cuenta Activa' : 'Cuenta Inactiva'}
                  />
                )}
              />
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                Las cuentas inactivas no procesarán correos en las extracciones automáticas.
              </Typography>
            </Grid>
          </Grid>
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleClose} disabled={loading}>
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={loading}
            sx={{ minWidth: 120 }}
          >
            {loading ? 'Guardando...' : 'Guardar Cambios'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default EditCuentaConfigDialog;
