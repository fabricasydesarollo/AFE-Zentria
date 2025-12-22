import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Autocomplete,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  PersonAdd as PersonAddIcon,
  Close as CloseIcon,
  People as PeopleIcon,
  Person as PersonIcon,
  Email as EmailIcon,
  Security as SecurityIcon,
  Business as BusinessIcon,
  AccountCircle as AccountCircleIcon,
} from '@mui/icons-material';
import gruposService from '../../../services/grupos.api';
import { Grupo } from '../../../types/grupo.types';
import { zentriaColors } from '../../../theme/colors';

interface GrupoUsuariosModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  grupo: Grupo | null;
}

interface Usuario {
  id: number;
  nombre: string;
  email: string;
  usuario?: string;
  area?: string;
  telefono?: string;
  rol?: string;
  role?: {
    id: number;
    nombre: string;
  };
  activo: boolean;
  grupos?: any[];
}

/**
 * Modal para asignar/remover usuarios de un grupo
 */
export default function GrupoUsuariosModal({ open, onClose, onSuccess, grupo }: GrupoUsuariosModalProps) {
  const [usuariosAsignados, setUsuariosAsignados] = useState<Usuario[]>([]);
  const [todosUsuarios, setTodosUsuarios] = useState<Usuario[]>([]);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState<number | ''>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (open && grupo) {
      cargarDatos();
    }
  }, [open, grupo]);

  const cargarDatos = async () => {
    if (!grupo) return;

    try {
      setLoading(true);
      setError(null);

      // Cargar usuarios asignados al grupo
      const asignadosRaw = await gruposService.obtenerUsuariosGrupo(grupo.id);

      // Transformar datos del backend al formato esperado por el frontend
      const asignados = asignadosRaw.map((asignacion: any) => ({
        id: asignacion.responsable_id,
        nombre: asignacion.responsable_nombre,
        email: asignacion.responsable_email,
        usuario: asignacion.responsable_usuario,
        rol: asignacion.responsable_rol,
        area: asignacion.responsable_area,
        activo: asignacion.activo,
      }));

      setUsuariosAsignados(asignados);

      // Cargar todos los usuarios disponibles
      const todos = await gruposService.obtenerTodosUsuarios();
      setTodosUsuarios(todos);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar usuarios');
    } finally {
      setLoading(false);
    }
  };

  const handleAsignar = async () => {
    if (!grupo || !usuarioSeleccionado) return;

    try {
      setLoading(true);
      setError(null);
      await gruposService.asignarUsuario(grupo.id, usuarioSeleccionado as number);
      setSuccess('Usuario asignado correctamente');
      setUsuarioSeleccionado('');
      await cargarDatos();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al asignar usuario');
    } finally {
      setLoading(false);
    }
  };

  const handleRemover = async (usuarioId: number) => {
    if (!grupo) return;

    if (!confirm('¿Está seguro de remover este usuario del grupo?')) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await gruposService.removerUsuario(grupo.id, usuarioId);
      setSuccess('Usuario removido correctamente');
      await cargarDatos();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al remover usuario');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setUsuarioSeleccionado('');
    setError(null);
    setSuccess(null);
    onClose();
  };

  const usuariosDisponibles = todosUsuarios.filter(
    (u) => !usuariosAsignados.some((ua) => ua.id === u.id) && u.activo
  );

  const getRoleName = (usuario: Usuario): string => {
    return usuario.role?.nombre || usuario.rol || 'Sin rol';
  };

  const getRolColor = (roleName: string): string => {
    const rol = roleName.toLowerCase();
    if (rol.includes('superadmin')) return zentriaColors.violeta.dark;
    if (rol.includes('admin')) return zentriaColors.violeta.main;
    if (rol.includes('responsable')) return zentriaColors.violeta.light;
    if (rol.includes('contador')) return zentriaColors.naranja.main;
    if (rol.includes('viewer')) return '#9e9e9e';
    return zentriaColors.violeta.main;
  };

  const getGruposCount = (usuario: Usuario): number => {
    return usuario.grupos?.length || 0;
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          width: '100%',
          maxWidth: '900px !important',
          borderRadius: 2,
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          overflow: 'hidden',
        },
      }}
    >
      {/* Header Premium */}
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
            <PeopleIcon sx={{ fontSize: 32 }} />
          </Box>
          <Box flex={1}>
            <Typography variant="h5" fontWeight={700}>
              Gestionar Equipo
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
              {grupo?.nombre} ({grupo?.codigo_corto})
            </Typography>
          </Box>
          <IconButton
            onClick={handleClose}
            sx={{
              color: 'white',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' },
            }}
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent
        sx={{
          pt: '24px !important',
          pb: '24px !important',
          px: '24px !important',
          backgroundColor: '#fff',
        }}
      >
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
            {success}
          </Alert>
        )}

        {loading && !usuariosAsignados.length ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {/* Sección Asignar Usuario - Estilo Premium */}
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
                  <PersonAddIcon sx={{ fontSize: 28 }} />
                </Box>
                <Box>
                  <Typography variant="h6" fontWeight={700} color="text.primary" sx={{ lineHeight: 1.2 }}>
                    Asignar Miembro al Equipo
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                    Seleccione un usuario disponible para agregarlo a este equipo
                  </Typography>
                </Box>
              </Stack>

              <Stack direction="row" spacing={2} alignItems="flex-start">
                <Autocomplete
                  fullWidth
                  options={usuariosDisponibles}
                  getOptionLabel={(option) => `${option.nombre} (${option.email})`}
                  value={usuariosDisponibles.find(u => u.id === usuarioSeleccionado) || null}
                  onChange={(_, newValue) => setUsuarioSeleccionado(newValue?.id || '')}
                  disabled={loading || usuariosDisponibles.length === 0}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Buscar usuario"
                      placeholder={usuariosDisponibles.length === 0 ? "No hay usuarios disponibles" : "Escriba para buscar..."}
                      InputProps={{
                        ...params.InputProps,
                        startAdornment: (
                          <InputAdornment position="start">
                            <PersonIcon color="action" />
                          </InputAdornment>
                        ),
                      }}
                      sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                    />
                  )}
                  renderOption={(props, option) => {
                    const { key, ...otherProps } = props;
                    const rolName = getRoleName(option);
                    const gruposCount = getGruposCount(option);

                    return (
                      <li key={key} {...otherProps}>
                        <Stack direction="row" spacing={2} alignItems="center" width="100%">
                          <Box
                            sx={{
                              p: 1,
                              borderRadius: '50%',
                              bgcolor: `${getRolColor(rolName)}15`,
                              color: getRolColor(rolName),
                            }}
                          >
                            <AccountCircleIcon />
                          </Box>
                          <Box flex={1}>
                            <Typography variant="body2" fontWeight={600}>
                              {option.nombre}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {option.email}
                            </Typography>
                          </Box>
                          <Stack spacing={0.5} alignItems="flex-end">
                            <Chip
                              label={rolName}
                              size="small"
                              sx={{
                                bgcolor: `${getRolColor(rolName)}20`,
                                color: getRolColor(rolName),
                                fontWeight: 600,
                                fontSize: '0.7rem',
                                height: 20,
                              }}
                            />
                            <Typography variant="caption" color="text.secondary" fontSize="0.65rem">
                              {gruposCount} {gruposCount === 1 ? 'grupo' : 'grupos'}
                            </Typography>
                          </Stack>
                        </Stack>
                      </li>
                    );
                  }}
                  noOptionsText="No hay usuarios disponibles"
                />
                <Button
                  variant="contained"
                  startIcon={<PersonAddIcon />}
                  onClick={handleAsignar}
                  disabled={!usuarioSeleccionado || loading}
                  sx={{
                    background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
                    borderRadius: 2.5,
                    px: 4,
                    py: 1.8,
                    fontWeight: 700,
                    fontSize: '0.95rem',
                    minWidth: 140,
                    boxShadow: '0 4px 20px rgba(128, 0, 106, 0.25)',
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': {
                      boxShadow: '0 8px 28px rgba(128, 0, 106, 0.4)',
                      transform: 'translateY(-2px)',
                    },
                  }}
                >
                  Asignar
                </Button>
              </Stack>
            </Paper>

            <Divider sx={{ my: 2.5, borderStyle: 'dashed', borderColor: `${zentriaColors.violeta.main}30` }} />

            {/* Sección Usuarios Asignados - Tabla Premium */}
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
                  <BusinessIcon sx={{ fontSize: 28 }} />
                </Box>
                <Box flex={1}>
                  <Typography variant="h6" fontWeight={700} color="text.primary" sx={{ lineHeight: 1.2 }}>
                    Miembros del Equipo
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                    {usuariosAsignados.length} {usuariosAsignados.length === 1 ? 'miembro' : 'miembros'} en este equipo
                  </Typography>
                </Box>
              </Stack>

              {usuariosAsignados.length === 0 ? (
                <Box
                  sx={{
                    textAlign: 'center',
                    py: 6,
                    bgcolor: '#fff',
                    borderRadius: 2,
                    border: '2px dashed #e0e0e0',
                  }}
                >
                  <PeopleIcon sx={{ fontSize: 48, color: '#bdbdbd', mb: 2 }} />
                  <Typography variant="body2" color="text.secondary" fontWeight={600}>
                    No hay miembros en este equipo
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Use el formulario superior para asignar miembros
                  </Typography>
                </Box>
              ) : (
                <TableContainer
                  component={Paper}
                  elevation={0}
                  sx={{
                    border: '1px solid #e0e0e0',
                    borderRadius: 2,
                    maxHeight: 400,
                    overflow: 'auto',
                  }}
                >
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                        <TableCell sx={{ fontWeight: 700, bgcolor: '#fafafa' }}>Usuario</TableCell>
                        <TableCell sx={{ fontWeight: 700, bgcolor: '#fafafa' }}>Nombre</TableCell>
                        <TableCell sx={{ fontWeight: 700, bgcolor: '#fafafa' }}>Email</TableCell>
                        <TableCell sx={{ fontWeight: 700, bgcolor: '#fafafa' }}>Rol</TableCell>
                        <TableCell sx={{ fontWeight: 700, bgcolor: '#fafafa' }}>Área</TableCell>
                        <TableCell align="center" sx={{ fontWeight: 700, bgcolor: '#fafafa' }}>Acción</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {usuariosAsignados.map((usuario) => {
                        const rolName = getRoleName(usuario);
                        return (
                          <TableRow
                            key={usuario.id}
                            hover
                            sx={{ '&:hover': { bgcolor: `${zentriaColors.violeta.main}08` } }}
                          >
                            <TableCell>
                              <Stack direction="row" alignItems="center" spacing={1}>
                                <Box
                                  sx={{
                                    p: 0.5,
                                    borderRadius: '50%',
                                    bgcolor: `${getRolColor(rolName)}15`,
                                    color: getRolColor(rolName),
                                    display: 'flex',
                                  }}
                                >
                                  <AccountCircleIcon fontSize="small" />
                                </Box>
                                <Typography variant="body2" fontWeight={600}>
                                  {usuario.nombre || usuario.usuario || (usuario.email ? usuario.email.split('@')[0] : 'Usuario')}
                                </Typography>
                              </Stack>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" fontWeight={500}>
                                {usuario.nombre}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Stack direction="row" alignItems="center" spacing={0.5}>
                                <EmailIcon fontSize="small" sx={{ color: '#9e9e9e', fontSize: 16 }} />
                                <Typography variant="body2" color="text.secondary">
                                  {usuario.email}
                                </Typography>
                              </Stack>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={rolName}
                                size="small"
                                sx={{
                                  bgcolor: `${getRolColor(rolName)}20`,
                                  color: getRolColor(rolName),
                                  fontWeight: 600,
                                  height: 24,
                                  minWidth: 80,
                                  fontSize: '0.75rem',
                                }}
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" color="text.secondary">
                                {usuario.area || '-'}
                              </Typography>
                            </TableCell>
                            <TableCell align="center">
                              <IconButton
                                size="small"
                                onClick={() => handleRemover(usuario.id)}
                                disabled={loading}
                                sx={{
                                  color: '#ef4444',
                                  '&:hover': {
                                    bgcolor: '#fef2f2',
                                  },
                                }}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Paper>
          </>
        )}
      </DialogContent>

      {/* Footer Premium */}
      <DialogActions
        sx={{
          px: '24px !important',
          py: '20px !important',
          backgroundColor: '#fff',
          borderTop: `1px solid ${zentriaColors.violeta.main}30`,
        }}
      >
        {success ? (
          // Cuando hay éxito, botón verde Aceptar
          <Button
            variant="contained"
            onClick={() => {
              setSuccess(null);
              onSuccess(); // Recargar datos en la página padre
              handleClose();
            }}
            fullWidth
            sx={{
              background: 'linear-gradient(135deg, #4caf50, #81c784)',
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
          // Botón normal Cerrar
          <Button
            onClick={handleClose}
            variant="outlined"
            sx={{
              borderRadius: 2.5,
              px: 4,
              py: 1.2,
              fontWeight: 600,
              fontSize: '0.95rem',
            }}
          >
            Cerrar
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
