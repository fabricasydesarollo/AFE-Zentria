import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  CircularProgress,
  Alert,
  Stack,
  Divider,
  InputAdornment,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Person,
  Email,
  Business,
  Lock,
  Security,
  AdminPanelSettings,
  AssignmentInd,
  Visibility,
  AccountBalance,
  Close,
} from '@mui/icons-material';
import { zentriaColors } from '../../theme/colors';
import apiClient from '../../services/api';
import { useAppSelector } from '../../app/hooks';
import { hasPermission } from '../../constants/roles';

interface Responsable {
  id: number;
  usuario: string;
  nombre: string;
  email: string;
  area?: string;
  activo: boolean;
  role: {
    id: number;
    nombre: string;
  };
}

interface Role {
  id: number;
  nombre: string;
}

/**
 * ResponsablesPage Component
 * Página de administración de responsables (admin y viewer)
 */
function ResponsablesPage() {
  const user = useAppSelector((state) => state.auth.user);
  const canManage = hasPermission(user?.rol || '', 'canManageUsers');
  const canViewFullData = hasPermission(user?.rol || '', 'canViewFullUserData');

  // Función para ocultar email parcialmente
  const maskEmail = (email: string): string => {
    if (!email || canViewFullData) return email;
    const [local, domain] = email.split('@');
    if (!domain) return email;
    const maskedLocal = local.substring(0, 3) + '***';
    return `${maskedLocal}@${domain}`;
  };

  const [responsables, setResponsables] = useState<Responsable[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    usuario: '',
    nombre: '',
    email: '',
    area: '',
    password: '',
    role_id: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [responsablesRes, rolesRes] = await Promise.all([
        apiClient.get('/usuarios/'),
        apiClient.get('/roles/'),
      ]);
      setResponsables(responsablesRes.data);
      setRoles(rolesRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (responsable?: Responsable) => {
    if (responsable) {
      setEditingId(responsable.id);
      setFormData({
        usuario: responsable.usuario,
        nombre: responsable.nombre,
        email: responsable.email,
        area: responsable.area || '',
        password: '',
        role_id: responsable.role.id.toString(),
      });
    } else {
      setEditingId(null);
      setFormData({
        usuario: '',
        nombre: '',
        email: '',
        area: '',
        password: '',
        role_id: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingId(null);
    setError('');
  };

  const handleSave = async () => {
    try {
      const payload = {
        ...formData,
        role_id: parseInt(formData.role_id),
        activo: true,
      };

      if (editingId) {
        // Editar
        if (!payload.password) {
          delete (payload as any).password;
        }
        await apiClient.put(`/usuarios/${editingId}`, payload);
      } else {
        // Crear
        await apiClient.post('/usuarios/', payload);
      }

      handleCloseDialog();
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar usuario');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('¿Está seguro de eliminar este usuario?')) return;

    try {
      await apiClient.delete(`/usuarios/${id}`);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar usuario');
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={700} color={zentriaColors.violeta.main}>
          Gestión de Usuarios
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadData}
            sx={{ borderColor: zentriaColors.violeta.main, color: zentriaColors.violeta.main }}
          >
            Actualizar
          </Button>
          {canManage && (
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => handleOpenDialog()}
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
              }}
            >
              Nuevo Usuario
            </Button>
          )}
        </Box>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper} elevation={2}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: zentriaColors.violeta.main }}>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Usuario</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Nombre</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Email</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Área</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Rol</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Estado</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }} align="center">
                Acciones
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {responsables && responsables.length > 0 ? (
              responsables.map((responsable) => (
                <TableRow key={responsable.id} hover>
                  <TableCell>{responsable?.usuario || '-'}</TableCell>
                  <TableCell>{responsable?.nombre || '-'}</TableCell>
                  <TableCell>{maskEmail(responsable?.email || '-')}</TableCell>
                  <TableCell>{responsable?.area || '-'}</TableCell>
                  <TableCell>
                    {(() => {
                      const roleName = responsable?.role?.nombre?.toLowerCase() || '';
                      let bgcolor = zentriaColors.cinza; // Cinza neutro para todos los roles
                      if (roleName.includes('admin')) bgcolor = zentriaColors.cinza;
                      else if (roleName.includes('responsable')) bgcolor = zentriaColors.cinza;
                      else if (roleName.includes('viewer')) bgcolor = zentriaColors.cinza;
                      else if (roleName.includes('contador')) bgcolor = zentriaColors.cinza;

                      const capitalize = (str: string) => {
                        if (!str) return str;
                        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
                      };

                      return (
                        <Chip
                          label={capitalize(responsable?.role?.nombre) || 'Sin rol'}
                          size="small"
                          sx={{
                            backgroundColor: bgcolor,
                            color: '#333333',
                            fontWeight: 700,
                            width: '110px', // Ancho fijo para consistencia
                            fontSize: '0.75rem',
                            '& .MuiChip-label': {
                              width: '100%',
                              textAlign: 'center'
                            }
                          }}
                        />
                      );
                    })()}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={responsable?.activo ? 'Activo' : 'Inactivo'}
                      size="small"
                      color={responsable?.activo ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell align="center">
                    {canManage ? (
                      <>
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDialog(responsable)}
                          sx={{ color: zentriaColors.naranja.main }}
                          title="Editar usuario"
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(responsable.id)}
                          sx={{ color: 'error.main' }}
                          title="Eliminar usuario"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </>
                    ) : (
                      <Typography variant="caption" color="text.disabled">
                        Solo lectura
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography variant="body2" color="text.secondary" py={4}>
                    No hay usuarios disponibles
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Dialog para crear/editar */}
      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            width: '100%',
            maxWidth: '750px !important',
            borderRadius: 3,
            boxShadow: '0 24px 48px rgba(0,0,0,0.2)',
            overflow: 'hidden'
          }
        }}
      >
        <DialogTitle
          sx={{
            background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
            color: 'white',
            p: 0,
            overflow: 'hidden',
            position: 'relative'
          }}
        >
          <Box sx={{ p: 3.5, px: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box
              sx={{
                p: 1,
                borderRadius: 2,
                backgroundColor: 'rgba(255,255,255,0.15)',
                display: 'flex',
                backdropFilter: 'blur(4px)'
              }}
            >
              <EditIcon sx={{ fontSize: 32 }} />
            </Box>
            <Box>
              <Typography variant="h5" fontWeight={700}>
                {editingId ? 'Editar Usuario' : 'Nuevo Usuario'}
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
                {editingId ? 'Modifique los datos y permisos del usuario' : 'Complete la información para registrar un nuevo usuario'}
              </Typography>
            </Box>
            <IconButton
              onClick={handleCloseDialog}
              sx={{
                ml: 'auto',
                color: 'white',
                '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' }
              }}
            >
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent
          sx={{
            pt: '40px !important',
            pb: '40px !important',
            px: '40px !important',
            backgroundColor: '#fff'
          }}
        >
          {error && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          {/* Sección Información Personal */}
          <Paper
            elevation={0}
            sx={{
              p: 3.5,
              mb: 3.5,
              border: `1px solid ${zentriaColors.violeta.main}30`,
              borderLeft: `6px solid ${zentriaColors.violeta.main}`,
              borderRadius: 3,
              backgroundColor: '#FAFAFA',
              boxShadow: '0 4px 12px rgba(0,0,0,0.03)'
            }}
          >
            <Stack direction="row" spacing={2} alignItems="center" mb={3}>
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  backgroundColor: `${zentriaColors.violeta.main}15`,
                  color: zentriaColors.violeta.main
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
                  label="Usuario"
                  value={formData.usuario}
                  onChange={(e) => setFormData({ ...formData, usuario: e.target.value })}
                  required
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
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
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
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
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
                  label="Área / Departamento"
                  value={formData.area}
                  onChange={(e) => setFormData({ ...formData, area: e.target.value })}
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
            </Stack>
          </Paper>

          <Divider sx={{ my: 3.5, borderStyle: 'dashed', borderColor: `${zentriaColors.cinza}90` }} />

          {/* Sección Seguridad y Permisos */}
          <Paper
            elevation={0}
            sx={{
              p: 3.5,
              border: `1px solid ${zentriaColors.naranja.main}30`,
              borderLeft: `6px solid ${zentriaColors.naranja.main}`,
              borderRadius: 3,
              backgroundColor: '#fff5f2',
              boxShadow: '0 4px 12px rgba(0,0,0,0.03)'
            }}
          >
            <Stack direction="row" spacing={2} alignItems="center" mb={3}>
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  backgroundColor: `${zentriaColors.naranja.main}15`,
                  color: zentriaColors.naranja.main
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
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required={!editingId}
                  helperText={editingId ? 'Dejar en blanco para mantener la actual' : ''}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Lock color={!editingId ? "primary" : "action"} />
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
                  onChange={(e) => setFormData({ ...formData, role_id: e.target.value })}
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
                          mt: 1
                        }
                      }
                    }
                  }}
                >
                  {roles.map((role) => {
                    // Configuración visual por rol
                    let icon = '👤';
                    let desc = 'Usuario estándar';
                    let color = zentriaColors.cinza;

                    if (role.nombre.toLowerCase().includes('admin')) {
                      icon = '👑';
                      desc = 'Acceso total al sistema';
                      color = zentriaColors.cinza;
                    } else if (role.nombre.toLowerCase().includes('responsable')) {
                      icon = '📋';
                      desc = 'Gestión de facturas';
                      color = zentriaColors.cinza;
                    } else if (role.nombre.toLowerCase().includes('viewer')) {
                      icon = '👁️';
                      desc = 'Solo lectura';
                      color = zentriaColors.cinza;
                    } else if (role.nombre.toLowerCase().includes('contador')) {
                      icon = '💼';
                      desc = 'Gestión contable';
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
                            boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
                          },
                          '&.Mui-selected': {
                            backgroundColor: `${zentriaColors.violeta.main}15 !important`,
                            borderColor: `${zentriaColors.violeta.main} !important`,
                            boxShadow: '0 4px 12px rgba(128, 0, 106, 0.15)',
                            '&:hover': {
                              backgroundColor: `${zentriaColors.violeta.main}20 !important`,
                            }
                          }
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
                              borderRadius: '50%'
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

        <DialogActions
          sx={{
            px: '40px !important',
            py: '28px !important',
            backgroundColor: '#fff',
            borderTop: `1px solid ${zentriaColors.cinza}30`
          }}
        >
          <Button
            onClick={handleCloseDialog}
            sx={{
              borderRadius: 2.5,
              px: 4,
              py: 1.2,
              fontWeight: 600,
              color: 'text.secondary',
              fontSize: '0.95rem'
            }}
          >
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={
              !formData.usuario ||
              !formData.nombre ||
              !formData.email ||
              !formData.role_id ||
              (!editingId && !formData.password)
            }
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
                transform: 'translateY(-2px)'
              }
            }}
          >
            {editingId ? 'Guardar Cambios' : 'Crear Usuario'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ResponsablesPage;
