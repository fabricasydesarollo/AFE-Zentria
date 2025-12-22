/**
 * UsuariosGlobalesPage - Gestión global de usuarios para SuperAdmin
 *
 * Características:
 * - Vista completa de todos los usuarios del sistema
 * - Gestión de roles y grupos
 * - Filtros avanzados por rol, estado, grupo
 * - Edición de información de usuario
 * - Asignación/desasignación de grupos
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { updateUser } from '../auth/authSlice';
import type { RootState } from '../../store/store';
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
  CircularProgress,
  Alert,
  Stack,
  InputAdornment,
  Grid,
  Card,
  CardContent,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
  MenuItem,
  Divider,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  Search as SearchIcon,
  AccountCircle,
  Delete as DeleteIcon,
  Business as BusinessIcon,
} from '@mui/icons-material';
import { zentriaColors } from '../../theme/colors';
import apiClient from '../../services/api';
import EditarUsuarioModal from './components/EditarUsuarioModal';

// ============================================================================
// TYPES
// ============================================================================

interface Usuario {
  id: number;
  usuario: string;
  nombre: string;
  email: string;
  area?: string;
  telefono?: string;
  activo: boolean;
  role: {
    id: number;
    nombre: string;
  };
  grupos?: GrupoAsignado[];
  last_login?: string;
  creado_en: string;
}

interface GrupoAsignado {
  id: number;
  codigo?: string;
  codigo_corto?: string;
  nombre: string;
  nivel?: number;
}

interface Role {
  id: number;
  nombre: string;
}

interface UsuarioStats {
  total: number;
  activos: number;
  inactivos: number;
  por_rol: Record<string, number>;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function UsuariosGlobalesPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useSelector((state: RootState) => state.auth.user);

  // Check if current user can delete (SuperAdmin or Admin)
  const canDelete = ['superadmin', 'admin'].includes(currentUser?.role?.nombre?.toLowerCase() || '');

  // ========================================================================
  // STATE
  // ========================================================================

  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [grupos, setGrupos] = useState<GrupoAsignado[]>([]);
  const [stats, setStats] = useState<UsuarioStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState('');
  const [filterStatus, setFilterStatus] = useState('activo'); // Por defecto mostrar solo activos
  const [filterGrupo, setFilterGrupo] = useState('');

  // Diálogos
  const [openUserModal, setOpenUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState<Usuario | null>(null);
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<Usuario | null>(null);
  const [deleteSuccess, setDeleteSuccess] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // ========================================================================
  // DATA LOADING
  // ========================================================================

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');

      // Cargar usuarios, roles y grupos en paralelo
      const [usuariosRes, rolesRes, gruposRes] = await Promise.all([
        apiClient.get('/usuarios/'),
        apiClient.get('/roles/'),
        apiClient.get('/grupos/'),
      ]);

      setUsuarios(usuariosRes.data);
      setRoles(rolesRes.data);
      // El endpoint /grupos/ devuelve { total: number, grupos: [] }
      setGrupos(gruposRes.data?.grupos || []);

      // Calcular estadísticas
      calculateStats(usuariosRes.data);
    } catch (err: any) {
      console.error('Error cargando datos:', err);
      setError(err.response?.data?.detail || 'Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (users: Usuario[]) => {
    const stats: UsuarioStats = {
      total: users.length,
      activos: users.filter(u => u.activo).length,
      inactivos: users.filter(u => !u.activo).length,
      por_rol: {},
    };

    users.forEach(u => {
      const rolNombre = u.role?.nombre || 'Sin rol';
      stats.por_rol[rolNombre] = (stats.por_rol[rolNombre] || 0) + 1;
    });

    setStats(stats);
  };

  // ========================================================================
  // HANDLERS
  // ========================================================================

  const handleOpenCreate = () => {
    setEditingUser(null);
    setIsCreatingUser(true);
    setOpenUserModal(true);
  };

  const handleOpenEdit = (user: Usuario) => {
    setEditingUser(user);
    setIsCreatingUser(false);
    setOpenUserModal(true);
  };

  const handleCloseUserModal = () => {
    setOpenUserModal(false);
    setEditingUser(null);
    setIsCreatingUser(false);
    // Recargar datos después de cerrar el modal
    loadData();
  };

  const navegarAGruposPage = () => {
    navigate('/superadmin/grupos');
  };

  const handleSaveUser = async (formData: any) => {
    try {
      if (editingUser) {
        // Editar usuario existente
        const updateData: any = {
          usuario: formData.usuario,
          nombre: formData.nombre,
          email: formData.email,
          area: formData.area || null,
          telefono: formData.telefono || null,
          role_id: parseInt(formData.role_id),
          activo: editingUser.activo, // Mantener el estado actual
        };

        if (formData.password) {
          updateData.password = formData.password;
        }

        await apiClient.put(`/usuarios/${editingUser.id}`, updateData);

        // Si se editó el usuario actual, actualizar el estado global
        if (currentUser && editingUser.id === currentUser.id) {
          try {
            const response = await apiClient.get('/usuarios/me');
            dispatch(updateUser(response.data));
          } catch (meError) {
            console.error('Error al actualizar perfil del usuario actual:', meError);
          }
        }
      } else {
        // Crear nuevo usuario
        await apiClient.post('/usuarios/', {
          ...formData,
          role_id: parseInt(formData.role_id),
        });
      }

      // NO cerramos el modal aquí - dejamos que el usuario vea el mensaje de éxito
      // NO recargamos datos aquí - esperamos a que el usuario cierre el modal
      // Los datos se recargarán en handleCloseUserModal()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar usuario');
      throw err; // Re-throw para que el modal lo maneje
    }
  };

  const handleToggleStatus = async (user: Usuario) => {
    try {
      await apiClient.put(`/usuarios/${user.id}`, {
        activo: !user.activo,
      });
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cambiar estado');
    }
  };

  const handleOpenDeleteDialog = (user: Usuario) => {
    setUserToDelete(user);
    setDeleteDialogOpen(true);
    setDeleteSuccess(false);
    setError('');
  };

  const handleCloseDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setUserToDelete(null);
    setDeleteSuccess(false);
    setError('');
    if (deleteSuccess) {
      loadData(); // Recargar datos solo cuando se cierra después de éxito
    }
  };

  const handleConfirmDelete = async () => {
    if (!userToDelete) return;

    try {
      setDeleting(true);
      setError('');

      await apiClient.delete(`/usuarios/${userToDelete.id}`);

      setDeleteSuccess(true);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error al eliminar usuario';
      setError(errorMsg);
    } finally {
      setDeleting(false);
    }
  };

  // ========================================================================
  // FILTERING
  // ========================================================================

  const filteredUsuarios = usuarios.filter(user => {
    // Search term
    const matchesSearch = !searchTerm ||
      user.nombre?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.usuario?.toLowerCase().includes(searchTerm.toLowerCase());

    // Role filter
    const matchesRole = !filterRole || user.role?.nombre === filterRole;

    // Status filter
    const matchesStatus = !filterStatus ||
      (filterStatus === 'activo' && user.activo) ||
      (filterStatus === 'inactivo' && !user.activo);

    // Grupo filter
    const matchesGrupo = !filterGrupo ||
      (filterGrupo === 'sin-grupos' && (!user.grupos || user.grupos.length === 0)) ||
      (user.grupos && user.grupos.some(g => g.id === parseInt(filterGrupo)));

    return matchesSearch && matchesRole && matchesStatus && matchesGrupo;
  });

  // ========================================================================
  // HELPERS
  // ========================================================================

  const getRoleColor = (roleName: string): string => {
    // Usar variaciones de violeta (color corporativo primario)
    // Superadmin (más autoridad) = violeta oscuro
    // Admin = violeta principal
    // Otros = violeta claro
    switch (roleName?.toLowerCase()) {
      case 'superadmin': return zentriaColors.violeta.dark;
      case 'admin': return zentriaColors.violeta.main;
      case 'responsable': return zentriaColors.violeta.light;
      case 'contador': return zentriaColors.violeta.light;
      case 'viewer': return zentriaColors.violeta.light;
      default: return zentriaColors.violeta.main;
    }
  };

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'Nunca';
    const date = new Date(dateString);
    return date.toLocaleString('es-CO', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // ========================================================================
  // RENDER
  // ========================================================================

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header */}
      <Box mb={4}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Usuarios Globales
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Gestión completa de todos los usuarios del sistema
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Stats Cards */}
      {stats && (
        <Grid container spacing={2} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ bgcolor: '#e3f2fd' }}>
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Total Usuarios
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {stats.total}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ bgcolor: '#e8f5e9' }}>
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Activos
                </Typography>
                <Typography variant="h4" fontWeight="bold" color="success.main">
                  {stats.activos}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ bgcolor: '#ffebee' }}>
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Inactivos
                </Typography>
                <Typography variant="h4" fontWeight="bold" color="error.main">
                  {stats.inactivos}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ bgcolor: '#fff3e0' }}>
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Roles Únicos
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {Object.keys(stats.por_rol).length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Filters and Actions */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2.5} alignItems="center">
          <Grid item xs={12} md={3.5}>
            <TextField
              fullWidth
              label="Buscar Usuario"
              placeholder="Nombre, email o usuario..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} sm={4} md={2}>
            <FormControl fullWidth>
              <InputLabel shrink>Rol</InputLabel>
              <Select
                value={filterRole}
                label="Rol"
                onChange={(e: SelectChangeEvent) => setFilterRole(e.target.value)}
                displayEmpty
                notched
                renderValue={(value) => {
                  if (!value) return 'Todos los roles';
                  return value;
                }}
              >
                <MenuItem value="">Todos los roles</MenuItem>
                {roles.map((rol) => (
                  <MenuItem key={rol.id} value={rol.nombre}>
                    {rol.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4} md={2}>
            <FormControl fullWidth>
              <InputLabel shrink>Estado</InputLabel>
              <Select
                value={filterStatus}
                label="Estado"
                onChange={(e: SelectChangeEvent) => setFilterStatus(e.target.value)}
                displayEmpty
                notched
                renderValue={(value) => {
                  if (!value) return 'Todos los estados';
                  if (value === 'activo') return 'Activos';
                  if (value === 'inactivo') return 'Inactivos';
                  return value;
                }}
              >
                <MenuItem value="">Todos los estados</MenuItem>
                <MenuItem value="activo">Activos</MenuItem>
                <MenuItem value="inactivo">Inactivos</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4} md={2.5}>
            <FormControl fullWidth>
              <InputLabel shrink>Grupo</InputLabel>
              <Select
                value={filterGrupo}
                label="Grupo"
                onChange={(e: SelectChangeEvent) => setFilterGrupo(e.target.value)}
                displayEmpty
                notched
                renderValue={(value) => {
                  if (!value) return 'Todos los grupos';
                  if (value === 'sin-grupos') return '⚠️ Sin grupos';
                  const grupo = grupos.find(g => g.id.toString() === value);
                  return grupo ? `${grupo.codigo_corto || grupo.codigo}` : value;
                }}
              >
                <MenuItem value="">Todos los grupos</MenuItem>
                <MenuItem value="sin-grupos">⚠️ Sin grupos</MenuItem>
                <Divider />
                {Array.isArray(grupos) && grupos.map((grupo) => (
                  <MenuItem key={grupo.id} value={grupo.id.toString()}>
                    {grupo.codigo_corto || grupo.codigo} - {grupo.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <Stack direction="row" spacing={1.5} justifyContent="flex-end">
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={loadData}
                fullWidth
              >
                Actualizar
              </Button>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleOpenCreate}
                fullWidth
              >
                Nuevo Usuario
              </Button>
            </Stack>
          </Grid>
        </Grid>
      </Paper>

      {/* Users Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ bgcolor: '#f5f5f5' }}>
              <TableCell>Usuario</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Rol</TableCell>
              <TableCell>Grupos</TableCell>
              <TableCell>Área</TableCell>
              <TableCell align="center">Estado</TableCell>
              <TableCell>Último Login</TableCell>
              <TableCell align="center">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredUsuarios.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    No se encontraron usuarios
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredUsuarios.map((user) => (
                <TableRow key={user.id} hover>
                  <TableCell>
                    <Stack direction="row" alignItems="center" spacing={1}>
                      <AccountCircle fontSize="small" color="action" />
                      <Typography variant="body2" fontWeight="medium">
                        {user.usuario}
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>{user.nombre}</TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {user.email}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={user.role?.nombre || 'Sin rol'}
                      size="small"
                      sx={{
                        bgcolor: `${getRoleColor(user.role?.nombre)}20`,
                        color: getRoleColor(user.role?.nombre),
                        fontWeight: 600,
                        height: 28,
                        minWidth: 100,
                        '& .MuiChip-label': {
                          px: 2,
                        },
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    {user.grupos && user.grupos.length > 0 ? (
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5}>
                        {user.grupos.map((grupo) => (
                          <Tooltip
                            key={grupo.id}
                            title={`Ver grupo ${grupo.codigo || grupo.nombre} en Grupos y Sedes`}
                            arrow
                          >
                            <Chip
                              label={grupo.codigo || grupo.codigo_corto}
                              size="small"
                              variant="outlined"
                              icon={<BusinessIcon />}
                              onClick={navegarAGruposPage}
                              sx={{
                                cursor: 'pointer',
                                borderColor: zentriaColors.violeta.main,
                                color: zentriaColors.violeta.main,
                                '&:hover': {
                                  bgcolor: `${zentriaColors.violeta.main}10`,
                                  borderColor: zentriaColors.violeta.dark,
                                },
                              }}
                            />
                          </Tooltip>
                        ))}
                      </Stack>
                    ) : (
                      <Tooltip title="Ir a Grupos y Sedes para asignar" arrow>
                        <Chip
                          label="Sin grupos"
                          size="small"
                          variant="outlined"
                          color="warning"
                          icon={<BusinessIcon />}
                          onClick={navegarAGruposPage}
                          sx={{
                            cursor: 'pointer',
                            '&:hover': {
                              bgcolor: '#fff3e0',
                            },
                          }}
                        />
                      </Tooltip>
                    )}
                  </TableCell>
                  <TableCell>{user.area || '-'}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={user.activo ? 'Activo' : 'Inactivo'}
                      size="small"
                      color={user.activo ? 'success' : 'default'}
                      onClick={() => handleToggleStatus(user)}
                      sx={{ cursor: 'pointer' }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(user.last_login)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Stack direction="row" spacing={0.5} justifyContent="center">
                      <Tooltip title="Editar">
                        <IconButton
                          size="small"
                          onClick={() => handleOpenEdit(user)}
                          color="primary"
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {canDelete && (
                        <Tooltip title="Eliminar">
                          <IconButton
                            size="small"
                            onClick={() => handleOpenDeleteDialog(user)}
                            color="error"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Modal de Editar/Crear Usuario */}
      <EditarUsuarioModal
        open={openUserModal}
        onClose={handleCloseUserModal}
        usuario={editingUser}
        roles={roles}
        onSave={handleSaveUser}
        error={error}
        isCreating={isCreatingUser}
      />

      {/* Dialog de Confirmación de Eliminación */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleCloseDeleteDialog}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 2,
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          },
        }}
      >
        <DialogTitle
          sx={{
            background: deleteSuccess
              ? 'linear-gradient(135deg, #4caf50, #81c784)'
              : 'linear-gradient(135deg, #f44336, #e57373)',
            color: 'white',
            fontWeight: 700,
            py: 2.5,
          }}
        >
          {deleteSuccess ? '✓ Usuario Eliminado' : '⚠️ Confirmar Eliminación'}
        </DialogTitle>

        <DialogContent sx={{ mt: 3, pb: 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {deleteSuccess ? (
            <Alert severity="success" sx={{ mb: 2 }}>
              El usuario "{userToDelete?.nombre}" ha sido eliminado permanentemente del sistema.
            </Alert>
          ) : (
            <>
              <DialogContentText sx={{ mb: 2, color: 'text.primary', fontSize: '1rem' }}>
                ¿Estás seguro de que deseas <strong>ELIMINAR PERMANENTEMENTE</strong> al usuario:
              </DialogContentText>

              <Box
                sx={{
                  p: 2,
                  bgcolor: '#fff3e0',
                  borderRadius: 1,
                  border: '1px solid #ffb74d',
                  mb: 2,
                }}
              >
                <Typography variant="body1" fontWeight="bold">
                  {userToDelete?.nombre}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Usuario: {userToDelete?.usuario}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Email: {userToDelete?.email}
                </Typography>
              </Box>

              <Alert severity="warning" sx={{ mb: 2 }}>
                <Typography variant="body2" fontWeight="bold" gutterBottom>
                  ⚠️ ADVERTENCIA: Esta acción NO se puede deshacer
                </Typography>
                <Typography variant="body2">
                  El usuario será eliminado permanentemente si no tiene facturas o workflows asociados.
                </Typography>
              </Alert>
            </>
          )}
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2 }}>
          {deleteSuccess ? (
            <Button
              onClick={handleCloseDeleteDialog}
              variant="contained"
              fullWidth
              sx={{
                background: 'linear-gradient(135deg, #4caf50, #81c784)',
                color: 'white',
                fontWeight: 700,
                py: 1.5,
                borderRadius: 2,
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
            <Stack direction="row" spacing={2} width="100%">
              <Button
                onClick={handleCloseDeleteDialog}
                disabled={deleting}
                variant="outlined"
                sx={{ flex: 1 }}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleConfirmDelete}
                disabled={deleting}
                variant="contained"
                color="error"
                sx={{
                  flex: 1,
                  fontWeight: 700,
                  background: 'linear-gradient(135deg, #f44336, #e57373)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #d32f2f, #f44336)',
                  },
                }}
              >
                {deleting ? <CircularProgress size={24} color="inherit" /> : 'Eliminar Permanentemente'}
              </Button>
            </Stack>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}
