/**
 * Cuenta Detail Page - Vista detallada con NITs, Historial y Estadísticas
 * Diseño tipo Dashboard profesional con pestañas
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Grid,
  IconButton,
  Tab,
  Tabs,
  Typography,
  Alert,
  CircularProgress,
  Stack,
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  InputAdornment,
  Tooltip,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Edit as EditIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
  Search as SearchIcon,
  FileUpload as UploadIcon,
  Refresh as RefreshIcon,
  TrendingUp as StatsIcon,
  History as HistoryIcon,
  Numbers as NumbersIcon,
  Email as EmailIcon,
} from '@mui/icons-material';
import { format, formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import {
  cargarCuentaDetalle,
  cargarHistorial,
  cargarEstadisticas,
  toggleNitActivo,
  eliminarNit,
  limpiarCuentaActual,
} from './emailConfigSlice';
import AddNitsBulkDialog from './components/AddNitsBulkDialog';
import AddNitDialog from './components/AddNitDialog';
import ConfirmDialog from '../../components/common/ConfirmDialog';
import EditCuentaConfigDialog from './components/EditCuentaConfigDialog';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

const CuentaDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const {
    cuentaActual,
    nits,
    historial,
    estadisticas,
    loadingCuentaActual,
    loadingHistorial,
    loadingEstadisticas,
  } = useAppSelector((state) => state.emailConfig);

  const [tabActual, setTabActual] = useState(0);
  const [busquedaNit, setBusquedaNit] = useState('');
  const [soloNitsActivos, setSoloNitsActivos] = useState(false);
  const [dialogBulkOpen, setDialogBulkOpen] = useState(false);
  const [dialogAddNitOpen, setDialogAddNitOpen] = useState(false);
  const [dialogEditConfigOpen, setDialogEditConfigOpen] = useState(false);
  const [nitAEliminar, setNitAEliminar] = useState<number | null>(null);

  useEffect(() => {
    if (id) {
      dispatch(cargarCuentaDetalle(Number(id)));
      dispatch(cargarHistorial({ cuentaId: Number(id), limit: 50 }));
      dispatch(cargarEstadisticas({ cuentaId: Number(id), dias: 30 }));
    }

    return () => {
      dispatch(limpiarCuentaActual());
    };
  }, [dispatch, id]);

  const nitsFiltrados = nits.filter((nit) => {
    const matchBusqueda =
      !busquedaNit ||
      nit.nit.includes(busquedaNit) ||
      nit.nombre_proveedor?.toLowerCase().includes(busquedaNit.toLowerCase());

    const matchActivo = !soloNitsActivos || nit.activo;

    return matchBusqueda && matchActivo;
  });

  const handleToggleNit = async (nitId: number, activo: boolean) => {
    await dispatch(toggleNitActivo({ nitId, activo: !activo }));
    if (id) {
      dispatch(cargarCuentaDetalle(Number(id)));
    }
  };

  const handleEliminarNit = async () => {
    if (nitAEliminar) {
      await dispatch(eliminarNit(nitAEliminar));
      setNitAEliminar(null);
      if (id) {
        dispatch(cargarCuentaDetalle(Number(id)));
      }
    }
  };

  const handleRefresh = () => {
    if (id) {
      dispatch(cargarCuentaDetalle(Number(id)));
      dispatch(cargarHistorial({ cuentaId: Number(id), limit: 50 }));
      dispatch(cargarEstadisticas({ cuentaId: Number(id), dias: 30 }));
    }
  };

  if (loadingCuentaActual && !cuentaActual) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress size={60} />
        </Box>
      </Container>
    );
  }

  if (!cuentaActual) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">Cuenta no encontrada</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate('/email-config')}
          sx={{ mb: 2 }}
        >
          Volver a Cuentas
        </Button>

        <Card sx={{ mb: 3, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
          <CardContent sx={{ p: 3 }}>
            <Grid container spacing={3} alignItems="center">
              <Grid size={{ xs: 12, md: 8 }}>
                <Stack spacing={1}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <EmailIcon sx={{ fontSize: 40, color: 'white' }} />
                    <Box>
                      <Typography variant="h4" sx={{ color: 'white', fontWeight: 700 }}>
                        {cuentaActual.email}
                      </Typography>
                      {cuentaActual.nombre_descriptivo && (
                        <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                          {cuentaActual.nombre_descriptivo}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip
                      label={cuentaActual.activa ? 'ACTIVA' : 'INACTIVA'}
                      color={cuentaActual.activa ? 'success' : 'error'}
                      size="small"
                    />
                    {cuentaActual.organizacion && (
                      <Chip
                        label={cuentaActual.organizacion}
                        size="small"
                        sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
                      />
                    )}
                  </Box>
                </Stack>
              </Grid>

              <Grid size={{ xs: 12, md: 4 }}>
                <Stack spacing={1}>
                  <Button
                    variant="contained"
                    startIcon={<RefreshIcon />}
                    onClick={handleRefresh}
                    fullWidth
                    sx={{ bgcolor: 'white', color: 'primary.main', '&:hover': { bgcolor: 'grey.100' } }}
                  >
                    Actualizar
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<EditIcon />}
                    onClick={() => setDialogEditConfigOpen(true)}
                    fullWidth
                    sx={{ borderColor: 'white', color: 'white', '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.1)' } }}
                  >
                    Editar Configuración
                  </Button>
                </Stack>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Estadísticas Rápidas */}
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent>
                <Typography variant="h3" color="primary" sx={{ fontWeight: 700 }}>
                  {nits.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  NITs Totales
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent>
                <Typography variant="h3" color="success.main" sx={{ fontWeight: 700 }}>
                  {nits.filter((n) => n.activo).length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  NITs Activos
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent>
                <Typography variant="h3" color="info.main" sx={{ fontWeight: 700 }}>
                  {cuentaActual.fetch_limit}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Límite de Correos
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent>
                <Typography variant="h3" color="warning.main" sx={{ fontWeight: 700 }}>
                  {cuentaActual.fetch_days}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Días Retroactivos
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabActual}
          onChange={(_, newValue) => setTabActual(newValue)}
          variant="fullWidth"
        >
          <Tab icon={<NumbersIcon />} label="NITs Configurados" />
          <Tab icon={<StatsIcon />} label="Estadísticas" />
          <Tab icon={<HistoryIcon />} label="Historial" />
        </Tabs>
      </Paper>

      {/* Tab 1: NITs */}
      <TabPanel value={tabActual} index={0}>
        <Card>
          <CardContent>
            {/* Barra de herramientas */}
            <Box sx={{ mb: 3 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    fullWidth
                    placeholder="Buscar por NIT o nombre de proveedor..."
                    value={busquedaNit}
                    onChange={(e) => setBusquedaNit(e.target.value)}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <SearchIcon />
                        </InputAdornment>
                      ),
                    }}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <FormControlLabel
                      control={
                        <Switch
                          checked={soloNitsActivos}
                          onChange={(e) => setSoloNitsActivos(e.target.checked)}
                          color="success"
                        />
                      }
                      label="Solo activos"
                    />
                    <Button
                      variant="outlined"
                      startIcon={<AddIcon />}
                      onClick={() => setDialogAddNitOpen(true)}
                    >
                      Agregar NIT
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={<UploadIcon />}
                      onClick={() => setDialogBulkOpen(true)}
                    >
                      Importar Múltiples
                    </Button>
                  </Stack>
                </Grid>
              </Grid>
            </Box>

            {/* Tabla de NITs */}
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell width="20%"><strong>NIT</strong></TableCell>
                    <TableCell width="30%"><strong>Proveedor</strong></TableCell>
                    <TableCell width="20%"><strong>Estado</strong></TableCell>
                    <TableCell width="15%"><strong>Fecha Creación</strong></TableCell>
                    <TableCell width="15%" align="right"><strong>Acciones</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {nitsFiltrados.map((nit) => (
                    <TableRow key={nit.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                          {nit.nit}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {nit.nombre_proveedor || (
                            <span style={{ color: '#999', fontStyle: 'italic' }}>Sin nombre</span>
                          )}
                        </Typography>
                        {nit.notas && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                            {nit.notas}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={nit.activo ? 'Activo' : 'Inactivo'}
                          color={nit.activo ? 'success' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {format(new Date(nit.creado_en), 'dd/MM/yyyy', { locale: es })}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <Tooltip title={nit.activo ? 'Desactivar' : 'Activar'}>
                            <IconButton
                              size="small"
                              onClick={() => handleToggleNit(nit.id, nit.activo)}
                              color={nit.activo ? 'error' : 'success'}
                            >
                              {nit.activo ? <InactiveIcon /> : <ActiveIcon />}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Eliminar">
                            <IconButton
                              size="small"
                              onClick={() => setNitAEliminar(nit.id)}
                              color="error"
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}

                  {nitsFiltrados.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} align="center" sx={{ py: 8 }}>
                        <NumbersIcon sx={{ fontSize: 60, color: 'text.disabled', mb: 1 }} />
                        <Typography variant="body1" color="text.secondary">
                          No se encontraron NITs
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {busquedaNit || soloNitsActivos
                            ? 'Prueba ajustando los filtros'
                            : 'Comienza agregando tu primer NIT'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </TabPanel>

      {/* Tab 2: Estadísticas */}
      <TabPanel value={tabActual} index={1}>
        {loadingEstadisticas ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : estadisticas ? (
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    📊 Resumen General (30 días)
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Stack spacing={2}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography color="text.secondary">Total Ejecuciones:</Typography>
                      <Typography variant="h6">{estadisticas.total_ejecuciones}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography color="text.secondary">Tasa de Éxito:</Typography>
                      <Chip
                        label={`${estadisticas.tasa_exito.toFixed(1)}%`}
                        color={estadisticas.tasa_exito >= 90 ? 'success' : 'warning'}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography color="text.secondary">Facturas Encontradas:</Typography>
                      <Typography variant="h6">{estadisticas.total_facturas_encontradas}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography color="text.secondary">Facturas Creadas:</Typography>
                      <Typography variant="h6">{estadisticas.total_facturas_creadas}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography color="text.secondary">Tiempo Promedio:</Typography>
                      <Typography variant="h6">
                        {estadisticas.promedio_tiempo_ms
                          ? `${(estadisticas.promedio_tiempo_ms / 1000).toFixed(1)}s`
                          : 'N/A'}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    🕐 Última Ejecución
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  {estadisticas.ultima_ejecucion ? (
                    <Alert severity="success">
                      {formatDistanceToNow(new Date(estadisticas.ultima_ejecucion), {
                        addSuffix: true,
                        locale: es,
                      })}
                    </Alert>
                  ) : (
                    <Alert severity="info">Sin ejecuciones registradas</Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        ) : (
          <Alert severity="info">No hay estadísticas disponibles</Alert>
        )}
      </TabPanel>

      {/* Tab 3: Historial */}
      <TabPanel value={tabActual} index={2}>
        {loadingHistorial ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Fecha</strong></TableCell>
                  <TableCell align="center"><strong>Correos</strong></TableCell>
                  <TableCell align="center"><strong>Encontradas</strong></TableCell>
                  <TableCell align="center"><strong>Creadas</strong></TableCell>
                  <TableCell align="center"><strong>Ignoradas</strong></TableCell>
                  <TableCell align="center"><strong>Estado</strong></TableCell>
                  <TableCell align="right"><strong>Tiempo</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {historial.map((h) => (
                  <TableRow key={h.id} hover>
                    <TableCell>
                      {format(new Date(h.fecha_ejecucion), 'dd/MM/yyyy HH:mm', { locale: es })}
                    </TableCell>
                    <TableCell align="center">{h.correos_procesados}</TableCell>
                    <TableCell align="center">{h.facturas_encontradas}</TableCell>
                    <TableCell align="center">
                      <Chip label={h.facturas_creadas} color="success" size="small" />
                    </TableCell>
                    <TableCell align="center">{h.facturas_ignoradas}</TableCell>
                    <TableCell align="center">
                      <Chip
                        label={h.exito ? 'Éxito' : 'Error'}
                        color={h.exito ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      {h.tiempo_ejecucion_ms
                        ? `${(h.tiempo_ejecucion_ms / 1000).toFixed(1)}s`
                        : '-'}
                    </TableCell>
                  </TableRow>
                ))}

                {historial.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 8 }}>
                      <HistoryIcon sx={{ fontSize: 60, color: 'text.disabled', mb: 1 }} />
                      <Typography variant="body1" color="text.secondary">
                        Sin historial de extracciones
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </TabPanel>

      {/* Diálogos */}
      <AddNitsBulkDialog
        open={dialogBulkOpen}
        onClose={() => setDialogBulkOpen(false)}
        cuentaId={Number(id)}
        onSuccess={() => {
          setDialogBulkOpen(false);
          handleRefresh();
        }}
      />

      <AddNitDialog
        open={dialogAddNitOpen}
        onClose={() => setDialogAddNitOpen(false)}
        cuentaId={Number(id)}
        onSuccess={() => {
          setDialogAddNitOpen(false);
          handleRefresh();
        }}
      />

      <EditCuentaConfigDialog
        open={dialogEditConfigOpen}
        onClose={() => setDialogEditConfigOpen(false)}
        onSuccess={() => {
          setDialogEditConfigOpen(false);
          handleRefresh();
        }}
        cuenta={cuentaActual}
      />

      <ConfirmDialog
        open={nitAEliminar !== null}
        title="¿Eliminar NIT?"
        message="Esta acción no se puede deshacer. El NIT se eliminará de la configuración."
        confirmText="Eliminar"
        onConfirm={handleEliminarNit}
        onCancel={() => setNitAEliminar(null)}
        severity="error"
      />
    </Container>
  );
};

export default CuentaDetailPage;
