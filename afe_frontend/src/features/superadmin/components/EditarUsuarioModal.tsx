/**
 * EditarUsuarioModal - Modal reutilizable para crear/editar usuarios
 *
 * Diseño profesional con secciones:
 * - Información Personal
 * - Seguridad y Permisos
 */

import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Stack,
  Box,
  Typography,
  Paper,
  Divider,
  Alert,
  IconButton,
  InputAdornment,
  MenuItem,
} from '@mui/material';
import {
  Person,
  Email,
  Business,
  Lock,
  Security,
  EditNote,
  Close,
  AssignmentInd,
  Phone,
} from '@mui/icons-material';
import { zentriaColors } from '../../../theme/colors';

// ============================================================================
// TYPES
// ============================================================================

interface Role {
  id: number;
  nombre: string;
}

interface Usuario {
  id: number;
  usuario: string;
  nombre: string;
  email: string;
  area?: string;
  telefono?: string;
  role?: {
    id: number;
    nombre: string;
  };
}

interface EditarUsuarioModalProps {
  open: boolean;
  onClose: () => void;
  usuario: Usuario | null;
  roles: Role[];
  onSave: (data: any) => Promise<void>;
  error?: string;
  isCreating?: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function EditarUsuarioModal({
  open,
  onClose,
  usuario,
  roles,
  onSave,
  error,
  isCreating = false,
}: EditarUsuarioModalProps) {
  // ========================================================================
  // STATE
  // ========================================================================

  const [formData, setFormData] = React.useState({
    usuario: '',
    nombre: '',
    email: '',
    area: '',
    telefono: '',
    password: '',
    role_id: '',
  });

  const [saving, setSaving] = React.useState(false);
  const [localError, setLocalError] = React.useState('');
  const [successMessage, setSuccessMessage] = React.useState('');

  // ========================================================================
  // EFFECTS
  // ========================================================================

  React.useEffect(() => {
    if (open) {
      if (usuario) {
        // Modo edición
        setFormData({
          usuario: usuario.usuario || '',
          nombre: usuario.nombre || '',
          email: usuario.email || '',
          area: usuario.area || '',
          telefono: usuario.telefono || '',
          password: '',
          role_id: usuario.role?.id.toString() || '',
        });
      } else if (isCreating) {
        // Modo creación
        setFormData({
          usuario: '',
          nombre: '',
          email: '',
          area: '',
          telefono: '',
          password: '',
          role_id: '',
        });
      }
    }
  }, [open, usuario, isCreating]);

  // ========================================================================
  // HANDLERS
  // ========================================================================

  const handleSave = async () => {
    try {
      setSaving(true);
      setLocalError('');
      setSuccessMessage('');

      await onSave(formData);

      // Mostrar mensaje de éxito
      setSuccessMessage(
        usuario
          ? '✓ Cambios guardados exitosamente'
          : '✓ Usuario creado exitosamente'
      );

    } catch (err: any) {
      // Capturar y mostrar error
      const errorMsg = err.response?.data?.detail || err.message || 'Error al guardar cambios';
      setLocalError(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    // Limpiar estados al cerrar
    setLocalError('');
    setSuccessMessage('');
    onClose();
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // ========================================================================
  // VALIDATION
  // ========================================================================

  const isValid =
    formData.usuario &&
    formData.nombre &&
    formData.email &&
    formData.role_id &&
    (usuario || formData.password); // Password requerida solo al crear

  // ========================================================================
  // RENDER
  // ========================================================================

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          width: '100%',
          maxWidth: '600px !important',
          borderRadius: 2,
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          overflow: 'hidden',
        },
      }}
    >
      {/* Header */}
      <DialogTitle
        sx={{
          background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
          color: 'white',
          p: 0,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <Box sx={{ p: 3.5, px: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              p: 1,
              borderRadius: 2,
              backgroundColor: 'rgba(255,255,255,0.15)',
              display: 'flex',
              backdropFilter: 'blur(4px)',
            }}
          >
            <EditNote sx={{ fontSize: 32 }} />
          </Box>
          <Box>
            <Typography variant="h5" fontWeight={700}>
              {usuario ? 'Editar Usuario' : 'Nuevo Usuario'}
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
              {usuario
                ? 'Modifique los datos y permisos del usuario'
                : 'Complete la información para registrar un nuevo usuario'}
            </Typography>
          </Box>
          <IconButton
            onClick={handleClose}
            sx={{
              ml: 'auto',
              color: 'white',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' },
            }}
          >
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      {/* Content */}
      <DialogContent
        sx={{
          pt: '24px !important',
          pb: '24px !important',
          px: '24px !important',
          backgroundColor: '#fff',
        }}
      >
        {(error || localError) && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {localError || error}
          </Alert>
        )}

        {successMessage && (
          <Alert severity="success" sx={{ mb: 3, borderRadius: 2 }}>
            {successMessage}
          </Alert>
        )}

        {/* Sección Información Personal */}
        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 2.5,
            border: `1px solid ${zentriaColors.violeta.main}30`,
            borderLeft: `4px solid ${zentriaColors.violeta.main}`,
            borderRadius: 2,
            backgroundColor: '#FAFAFA',
            boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
          }}
        >
          <Stack direction="row" spacing={2} alignItems="center" mb={3}>
            <Box
              sx={{
                p: 1.5,
                borderRadius: 2,
                backgroundColor: `${zentriaColors.violeta.main}15`,
                color: zentriaColors.violeta.main,
              }}
            >
              <Person sx={{ fontSize: 28 }} />
            </Box>
            <Box>
              <Typography variant="h6" fontWeight={700} color="text.primary" sx={{ lineHeight: 1.2 }}>
                Información Personal
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                Datos básicos del usuario
              </Typography>
            </Box>
          </Stack>

          <Stack spacing={3}>
            <Stack direction="row" spacing={2}>
              <TextField
                fullWidth
                label="Usuario (Username)"
                value={formData.usuario}
                onChange={(e) => handleChange('usuario', e.target.value)}
                required
                helperText={usuario ? 'SuperAdmin puede modificar el username' : 'El username será el identificador de inicio de sesión'}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <AssignmentInd color="action" />
                    </InputAdornment>
                  ),
                }}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
              />
              <TextField
                fullWidth
                label="Nombre Completo"
                value={formData.nombre}
                onChange={(e) => handleChange('nombre', e.target.value)}
                required
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person color="action" />
                    </InputAdornment>
                  ),
                }}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
              />
            </Stack>

            <Stack direction="row" spacing={2}>
              <TextField
                fullWidth
                label="Correo Electrónico"
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                required
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Email color="action" />
                    </InputAdornment>
                  ),
                }}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
              />
              <TextField
                fullWidth
                label="Teléfono"
                value={formData.telefono}
                onChange={(e) => handleChange('telefono', e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Phone color="action" />
                    </InputAdornment>
                  ),
                }}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
              />
            </Stack>

            <TextField
              fullWidth
              label="Área / Departamento"
              value={formData.area}
              onChange={(e) => handleChange('area', e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Business color="action" />
                  </InputAdornment>
                ),
              }}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            />
          </Stack>
        </Paper>

        <Divider sx={{ my: 2.5, borderStyle: 'dashed', borderColor: `${zentriaColors.cinza}90` }} />

        {/* Sección Seguridad y Permisos */}
        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            border: `1px solid ${zentriaColors.naranja.main}30`,
            borderLeft: `4px solid ${zentriaColors.naranja.main}`,
            borderRadius: 2,
            backgroundColor: '#fff5f2',
            boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
          }}
        >
          <Stack direction="row" spacing={2} alignItems="center" mb={3}>
            <Box
              sx={{
                p: 1.5,
                borderRadius: 2,
                backgroundColor: `${zentriaColors.naranja.main}15`,
                color: zentriaColors.naranja.main,
              }}
            >
              <Lock sx={{ fontSize: 28 }} />
            </Box>
            <Box>
              <Typography variant="h6" fontWeight={700} color="text.primary" sx={{ lineHeight: 1.2 }}>
                Seguridad y Permisos
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                Contraseña y nivel de acceso
              </Typography>
            </Box>
          </Stack>

          <Stack spacing={3}>
            <Stack direction="row" spacing={2}>
              <TextField
                fullWidth
                label="Contraseña"
                type="password"
                value={formData.password}
                onChange={(e) => handleChange('password', e.target.value)}
                required={!usuario}
                helperText={usuario ? 'Dejar en blanco para mantener la actual' : 'Mínimo 8 caracteres'}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock color={!usuario ? 'primary' : 'action'} />
                    </InputAdornment>
                  ),
                }}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
              />

              <TextField
                fullWidth
                select
                label="Rol del Usuario"
                value={formData.role_id}
                onChange={(e) => handleChange('role_id', e.target.value)}
                required
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Security color="primary" />
                    </InputAdornment>
                  ),
                }}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                SelectProps={{
                  MenuProps: {
                    PaperProps: {
                      sx: {
                        borderRadius: 2,
                        boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
                        mt: 1,
                      },
                    },
                  },
                }}
              >
                {roles.map((role) => {
                  // Configuración visual por rol
                  let icon = '👤';
                  let desc = 'Usuario estándar';
                  let color: string = zentriaColors.cinza;

                  const roleName = role.nombre.toLowerCase();
                  if (roleName.includes('superadmin')) {
                    icon = '🔐';
                    desc = 'Acceso total al sistema';
                    color = zentriaColors.violeta.main;
                  } else if (roleName.includes('admin')) {
                    icon = '👑';
                    desc = 'Administrador de grupo';
                    color = zentriaColors.cinza;
                  } else if (roleName.includes('responsable')) {
                    icon = '📋';
                    desc = 'Gestión de facturas';
                    color = zentriaColors.cinza;
                  } else if (roleName.includes('contador')) {
                    icon = '💼';
                    desc = 'Gestión contable';
                    color = zentriaColors.cinza;
                  } else if (roleName.includes('viewer')) {
                    icon = '👁️';
                    desc = 'Solo lectura';
                    color = zentriaColors.cinza;
                  }

                  return (
                    <MenuItem
                      key={role.id}
                      value={role.id}
                      sx={{
                        py: 1.5,
                        px: 2.5,
                        my: 0.8,
                        mx: 1.5,
                        borderRadius: 2,
                        border: '2px solid',
                        borderColor: 'transparent',
                        backgroundColor: '#f8f9fa',
                        transition: 'all 0.2s ease-in-out',
                        '&:hover': {
                          backgroundColor: '#e9ecef',
                          borderColor: zentriaColors.cinza,
                          transform: 'scale(1.02)',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                        },
                        '&.Mui-selected': {
                          backgroundColor: `${zentriaColors.violeta.main}15 !important`,
                          borderColor: `${zentriaColors.violeta.main} !important`,
                          boxShadow: '0 4px 12px rgba(128, 0, 106, 0.15)',
                          '&:hover': {
                            backgroundColor: `${zentriaColors.violeta.main}20 !important`,
                          },
                        },
                      }}
                    >
                      <Box display="flex" alignItems="center" width="100%">
                        <Box
                          sx={{
                            fontSize: '24px',
                            mr: 2,
                            width: 40,
                            height: 40,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            backgroundColor: `${color}10`,
                            borderRadius: '50%',
                          }}
                        >
                          {icon}
                        </Box>
                        <Box flex={1}>
                          <Typography variant="subtitle2" fontWeight={700}>
                            {role.nombre.charAt(0).toUpperCase() + role.nombre.slice(1).toLowerCase()}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {desc}
                          </Typography>
                        </Box>
                      </Box>
                    </MenuItem>
                  );
                })}
              </TextField>
            </Stack>
          </Stack>
        </Paper>
      </DialogContent>

      {/* Footer */}
      <DialogActions
        sx={{
          px: '24px !important',
          py: '20px !important',
          backgroundColor: '#fff',
          borderTop: `1px solid ${zentriaColors.cinza}30`,
        }}
      >
        {successMessage ? (
          // Cuando hay éxito, solo mostrar botón Aceptar
          <Button
            variant="contained"
            onClick={handleClose}
            fullWidth
            sx={{
              background: `linear-gradient(135deg, #4caf50, #81c784)`,
              borderRadius: 2.5,
              px: 5,
              py: 1.5,
              fontWeight: 700,
              fontSize: '0.95rem',
              boxShadow: '0 4px 20px rgba(76, 175, 80, 0.25)',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              '&:hover': {
                boxShadow: '0 8px 28px rgba(76, 175, 80, 0.4)',
                transform: 'translateY(-2px)',
              },
            }}
          >
            Aceptar
          </Button>
        ) : (
          // Botones normales (Cancelar y Guardar)
          <>
            <Button
              onClick={handleClose}
              disabled={saving}
              sx={{
                borderRadius: 2.5,
                px: 4,
                py: 1.2,
                fontWeight: 600,
                color: 'text.secondary',
                fontSize: '0.95rem',
              }}
            >
              Cancelar
            </Button>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={!isValid || saving}
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
                borderRadius: 2.5,
                px: 5,
                py: 1.2,
                fontWeight: 700,
                fontSize: '0.95rem',
                boxShadow: '0 4px 20px rgba(128, 0, 106, 0.25)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  boxShadow: '0 8px 28px rgba(128, 0, 106, 0.4)',
                  transform: 'translateY(-2px)',
                },
              }}
            >
              {usuario ? 'Guardar Cambios' : 'Crear Usuario'}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}
