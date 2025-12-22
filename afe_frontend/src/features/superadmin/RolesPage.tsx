/**
 * RolesPage - Gestión y visualización de roles del sistema
 *
 * Características:
 * - Vista de todos los roles disponibles
 * - Estadísticas de usuarios por rol
 * - Descripción de permisos de cada rol
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Stack,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Security as SecurityIcon,
  People as PeopleIcon,
  CheckCircle as CheckIcon,
  AdminPanelSettings as AdminIcon,
  Person as PersonIcon,
  Visibility as ViewIcon,
  AccountBalance as ContadorIcon,
  Business as BusinessIcon,
} from '@mui/icons-material';
import { zentriaColors } from '../../theme/colors';
import apiClient from '../../services/api';

// ============================================================================
// TYPES
// ============================================================================

interface Role {
  id: number;
  nombre: string;
}

interface RoleStats {
  id: number;
  nombre: string;
  usuarios_count: number;
  descripcion: string;
  permisos: string[];
  icon: React.ReactNode;
  color: string;
}

// ============================================================================
// HELPERS
// ============================================================================

const getRoleColor = (roleName: string): string => {
  switch (roleName?.toLowerCase()) {
    case 'superadmin': return zentriaColors.violeta.dark;
    case 'admin': return zentriaColors.violeta.main;
    case 'responsable': return zentriaColors.violeta.light;
    case 'contador': return zentriaColors.violeta.light;
    case 'viewer': return zentriaColors.violeta.light;
    default: return zentriaColors.violeta.main;
  }
};

// ============================================================================
// CONSTANTS
// ============================================================================

const ROLE_DETAILS: Record<string, {
  descripcion: string;
  permisos: string[];
  icon: React.ReactNode;
}> = {
  'superadmin': {
    descripcion: 'Acceso total al sistema - Gestión global de infraestructura',
    permisos: [
      'Gestión de todos los grupos y sedes',
      'Gestión de todos los usuarios del sistema',
      'Configuración de roles y permisos',
      'Acceso a métricas administrativas',
      'Configuración global del sistema',
    ],
    icon: <SecurityIcon />,
  },
  'admin': {
    descripcion: 'Administrador de su grupo/sede - Gestión operativa',
    permisos: [
      'Gestión de usuarios de su grupo',
      'Asignación de responsables a proveedores',
      'Configuración de cuentas de correo',
      'Visualización de facturas de su grupo',
      'Gestión de workflows de su grupo',
    ],
    icon: <AdminIcon />,
  },
  'responsable': {
    descripcion: 'Responsable de aprobación de facturas',
    permisos: [
      'Aprobar/rechazar facturas asignadas',
      'Devolver facturas para corrección',
      'Ver facturas de proveedores asignados',
      'Solicitar información adicional',
    ],
    icon: <PersonIcon />,
  },
  'contador': {
    descripcion: 'Validación contable y cierre de facturas',
    permisos: [
      'Validar facturas aprobadas',
      'Devolver facturas con observaciones',
      'Ver historial completo de facturas',
      'Generar reportes contables',
    ],
    icon: <ContadorIcon />,
  },
  'viewer': {
    descripcion: 'Solo lectura - Visualización de información',
    permisos: [
      'Ver facturas (solo lectura)',
      'Consultar proveedores',
      'Ver estadísticas básicas',
      'Sin permisos de modificación',
    ],
    icon: <ViewIcon />,
  },
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function RolesPage() {
  // ========================================================================
  // STATE
  // ========================================================================

  const [roles, setRoles] = useState<RoleStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

      // Cargar roles y usuarios en paralelo
      const [rolesRes, usuariosRes] = await Promise.all([
        apiClient.get('/roles/'),
        apiClient.get('/usuarios/'),
      ]);

      // Calcular estadísticas por rol
      const rolesData: Role[] = rolesRes.data;
      const usuarios = usuariosRes.data;

      const rolesConStats: RoleStats[] = rolesData.map((rol) => {
        const usuariosDelRol = usuarios.filter((u: any) => u.role?.id === rol.id);
        const details = ROLE_DETAILS[rol.nombre.toLowerCase()] || {
          descripcion: 'Rol personalizado',
          permisos: [],
          icon: <BusinessIcon />,
          color: 'info' as const,
        };

        return {
          ...rol,
          usuarios_count: usuariosDelRol.length,
          descripcion: details.descripcion,
          permisos: details.permisos,
          icon: details.icon,
          color: getRoleColor(rol.nombre),
        };
      });

      setRoles(rolesConStats);
    } catch (err: any) {
      console.error('Error cargando datos:', err);
      setError(err.response?.data?.detail || 'Error al cargar datos');
    } finally {
      setLoading(false);
    }
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
          Roles del Sistema
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Gestión y visualización de roles con sus permisos y estadísticas
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Stats Summary */}
      <Grid container spacing={2} mb={4}>
        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ bgcolor: `${zentriaColors.violeta.main}15` }}>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    bgcolor: `${zentriaColors.violeta.main}30`,
                    color: zentriaColors.violeta.main,
                  }}
                >
                  <SecurityIcon />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Total Roles
                  </Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {roles.length}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ bgcolor: `${zentriaColors.verde.main}15` }}>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    bgcolor: `${zentriaColors.verde.main}30`,
                    color: zentriaColors.verde.main,
                  }}
                >
                  <PeopleIcon />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Total Usuarios
                  </Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {roles.reduce((sum, r) => sum + r.usuarios_count, 0)}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ bgcolor: `${zentriaColors.naranja.main}15` }}>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    bgcolor: `${zentriaColors.naranja.main}30`,
                    color: zentriaColors.naranja.main,
                  }}
                >
                  <CheckIcon />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Roles Activos
                  </Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {roles.filter(r => r.usuarios_count > 0).length}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Roles Cards */}
      <Grid container spacing={3}>
        {roles.map((rol) => (
          <Grid item xs={12} md={6} key={rol.id}>
            <Card>
              <CardContent>
                {/* Header */}
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Box
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        bgcolor: `${rol.color}20`,
                        color: rol.color,
                        display: 'flex',
                        alignItems: 'center',
                      }}
                    >
                      {rol.icon}
                    </Box>
                    <Box>
                      <Typography variant="h6" fontWeight="bold">
                        {rol.nombre}
                      </Typography>
                      <Chip
                        label={`${rol.usuarios_count} usuarios`}
                        size="small"
                        sx={{
                          bgcolor: `${rol.color}20`,
                          color: rol.color,
                          fontWeight: 600,
                        }}
                      />
                    </Box>
                  </Stack>
                </Stack>

                {/* Descripción */}
                <Typography variant="body2" color="text.secondary" mb={2}>
                  {rol.descripcion}
                </Typography>

                <Divider sx={{ my: 2 }} />

                {/* Permisos */}
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  Permisos:
                </Typography>
                <List dense disablePadding>
                  {rol.permisos.map((permiso, index) => (
                    <ListItem key={index} disableGutters>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        <CheckIcon fontSize="small" color="success" />
                      </ListItemIcon>
                      <ListItemText
                        primary={permiso}
                        primaryTypographyProps={{ variant: 'body2' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Roles Table */}
      <Paper sx={{ mt: 4 }}>
        <Box p={2}>
          <Typography variant="h6" fontWeight="bold" gutterBottom>
            Resumen de Roles
          </Typography>
        </Box>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                <TableCell>Rol</TableCell>
                <TableCell>Descripción</TableCell>
                <TableCell align="center">Usuarios</TableCell>
                <TableCell align="center">Estado</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {roles.map((rol) => (
                <TableRow key={rol.id} hover>
                  <TableCell>
                    <Stack direction="row" spacing={1} alignItems="center">
                      {rol.icon}
                      <Typography variant="body2" fontWeight="medium">
                        {rol.nombre}
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {rol.descripcion}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={rol.usuarios_count}
                      size="small"
                      sx={{
                        bgcolor: `${rol.color}20`,
                        color: rol.color,
                        fontWeight: 600,
                        height: 28,
                        minWidth: 80,
                        '& .MuiChip-label': {
                          px: 2,
                        },
                      }}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={rol.usuarios_count > 0 ? 'En uso' : 'Sin usuarios'}
                      size="small"
                      sx={{
                        bgcolor: rol.usuarios_count > 0 ? `${zentriaColors.verde.main}20` : 'default',
                        color: rol.usuarios_count > 0 ? zentriaColors.verde.main : 'text.secondary',
                        fontWeight: 600,
                        height: 28,
                        minWidth: 120,
                        '& .MuiChip-label': {
                          px: 2,
                        },
                      }}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
}
