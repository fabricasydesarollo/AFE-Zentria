/**
 * SuperAdminDashboard - Dashboard administrativo para SuperAdmin
 *
 * Focus en métricas de infraestructura y gestión del sistema,
 * NO en operaciones de facturas (eso es para admin/responsable/contador)
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Stack,
  Button,
} from '@mui/material';
import {
  People as PeopleIcon,
  Business as BusinessIcon,
  Description as DescriptionIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { zentriaColors } from '../../theme/colors';
import apiClient from '../../services/api';

// ============================================================================
// TYPES
// ============================================================================

interface GrupoStats {
  id: number;
  codigo: string;
  nombre: string;
  nivel: number;
  usuarios_asignados: number;
  facturas_mes_actual: number;
  facturas_pendientes: number;
  activo: boolean;
}

interface ActividadReciente {
  fecha: string;
  tipo: string;
  descripcion: string;
  usuario?: string;
  grupo?: string;
}

interface SuperAdminDashboardData {
  total_usuarios: number;
  usuarios_activos: number;
  total_grupos: number;
  grupos_activos: number;
  usuarios_por_rol: Record<string, number>;
  facturas_ultimos_30_dias: number;
  facturas_mes_actual: number;
  facturas_cuarentena: number; // MULTI-TENANT 2025-12-14
  grupos_mas_activos: GrupoStats[];
  actividad_reciente: ActividadReciente[];
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function SuperAdminDashboard() {
  const [data, setData] = useState<SuperAdminDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ========================================================================
  // DATA LOADING
  // ========================================================================

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get('/dashboard/superadmin');
      setData(response.data);
    } catch (err: any) {
      console.error('Error cargando dashboard SuperAdmin:', err);
      setError(
        err.response?.data?.detail ||
        'Error al cargar datos del dashboard'
      );
    } finally {
      setLoading(false);
    }
  };

  // ========================================================================
  // HELPERS
  // ========================================================================

  const getNivelLabel = (nivel: number): string => {
    switch (nivel) {
      case 0: return 'Corporativo';
      case 1: return 'Sede';
      case 2: return 'Sub-sede';
      default: return `Nivel ${nivel}`;
    }
  };

  const getTipoActividadLabel = (tipo: string): string => {
    switch (tipo) {
      case 'factura_creada': return 'Factura Creada';
      case 'usuario_creado': return 'Usuario Creado';
      case 'grupo_creado': return 'Grupo Creado';
      default: return tipo;
    }
  };

  const formatFecha = (fecha: string): string => {
    const date = new Date(fecha);
    return date.toLocaleString('es-CO', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
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

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Box>
    );
  }

  if (!data) {
    return (
      <Box p={3}>
        <Alert severity="warning">No se pudieron cargar los datos</Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header */}
      <Box mb={4}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Métricas Sistema
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Vista general del sistema - Métricas de infraestructura
        </Typography>
      </Box>

      {/* Métricas principales */}
      <Grid container spacing={3} mb={4}>
        {/* Usuarios */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', bgcolor: '#f3e5f5' }}>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    bgcolor: '#e1bee7',
                    color: '#7b1fa2'
                  }}
                >
                  <PeopleIcon />
                </Box>
                <Box flex={1}>
                  <Typography variant="body2" color="text.secondary">
                    Usuarios
                  </Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {data.total_usuarios}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {data.usuarios_activos} activos
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Grupos */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', bgcolor: '#e3f2fd' }}>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    bgcolor: '#bbdefb',
                    color: '#1565c0'
                  }}
                >
                  <BusinessIcon />
                </Box>
                <Box flex={1}>
                  <Typography variant="body2" color="text.secondary">
                    Grupos
                  </Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {data.total_grupos}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {data.grupos_activos} activos
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Facturas últimos 30 días */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', bgcolor: '#f3e5f5' }}>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    bgcolor: '#e1bee7',
                    color: '#7b1fa2'
                  }}
                >
                  <TrendingUpIcon />
                </Box>
                <Box flex={1}>
                  <Typography variant="body2" color="text.secondary">
                    Últimos 30 días
                  </Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {data.facturas_ultimos_30_dias}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    facturas
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Facturas mes actual */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', bgcolor: '#fff3e0' }}>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    bgcolor: '#ffe0b2',
                    color: '#e65100'
                  }}
                >
                  <DescriptionIcon />
                </Box>
                <Box flex={1}>
                  <Typography variant="body2" color="text.secondary">
                    Mes actual
                  </Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {data.facturas_mes_actual}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    facturas
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Distribución por roles */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                Usuarios por Rol
              </Typography>
              <Stack spacing={2} mt={2}>
                {Object.entries(data.usuarios_por_rol).map(([rol, count]) => (
                  <Box key={rol} display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2">{rol}</Typography>
                    <Chip
                      label={count}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Grupos más activos */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                Grupos Más Activos (Top 5)
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Grupo</TableCell>
                      <TableCell>Nivel</TableCell>
                      <TableCell align="center">Usuarios</TableCell>
                      <TableCell align="center">Facturas (mes)</TableCell>
                      <TableCell align="center">Pendientes</TableCell>
                      <TableCell align="center">Estado</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.grupos_mas_activos.map((grupo) => (
                      <TableRow key={grupo.id}>
                        <TableCell>
                          <Box>
                            <Typography variant="body2" fontWeight="medium">
                              {grupo.codigo}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {grupo.nombre}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={getNivelLabel(grupo.nivel)}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="center">{grupo.usuarios_asignados}</TableCell>
                        <TableCell align="center">{grupo.facturas_mes_actual}</TableCell>
                        <TableCell align="center">{grupo.facturas_pendientes}</TableCell>
                        <TableCell align="center">
                          <Chip
                            label={grupo.activo ? 'Activo' : 'Inactivo'}
                            size="small"
                            color={grupo.activo ? 'success' : 'default'}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Actividad reciente */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                Actividad Reciente del Sistema
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Fecha</TableCell>
                      <TableCell>Tipo</TableCell>
                      <TableCell>Descripción</TableCell>
                      <TableCell>Usuario Responsable</TableCell>
                      <TableCell>Grupo</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.actividad_reciente.map((actividad, index) => (
                      <TableRow key={index}>
                        <TableCell>
                          <Typography variant="caption">
                            {formatFecha(actividad.fecha)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={getTipoActividadLabel(actividad.tipo)}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>{actividad.descripcion}</TableCell>
                        <TableCell>
                          {actividad.usuario || '-'}
                        </TableCell>
                        <TableCell>
                          {actividad.grupo ? (
                            <Chip label={actividad.grupo} size="small" />
                          ) : '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
