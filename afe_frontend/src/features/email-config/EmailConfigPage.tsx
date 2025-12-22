/**
 * Email Config Page - Gestión de Configuración de Correos
 * Diseño profesional y moderno con Material-UI
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  FormControlLabel,
  Grid,
  IconButton,
  InputAdornment,
  Switch,
  TextField,
  Tooltip,
  Typography,
  Alert,
  CircularProgress,
  Stack,
  Divider,
  Badge,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  Email as EmailIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  Business as BusinessIcon,
  Numbers as NumbersIcon,
  Clear as ClearIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { format, formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { zentriaColors } from '../../theme/colors';
import {
  cargarCuentas,
  setFiltros,
  toggleCuentaActiva,
  eliminarCuenta,
  limpiarError,
} from './emailConfigSlice';
import CreateCuentaDialog from './components/CreateCuentaDialog';
import ConfirmDialog from '../../components/common/ConfirmDialog';
import { CuarentenaTab } from './components/CuarentenaTab';

const EmailConfigPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const { cuentas, loadingCuentas, filtros, error } = useAppSelector(
    (state) => state.emailConfig
  );

  const [dialogCrearOpen, setDialogCrearOpen] = useState(false);
  const [cuentaAEliminar, setCuentaAEliminar] = useState<number | null>(null);
  const [searchLocal, setSearchLocal] = useState('');

  // Tab management con URL query params
  const tabParam = searchParams.get('tab');
  const [activeTab, setActiveTab] = useState(tabParam === 'cuarentena' ? 1 : 0);

  // Sincronizar tab con URL query params
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'cuarentena') {
      setActiveTab(1);
    } else {
      setActiveTab(0);
    }
  }, [searchParams]);

  // Cargar cuentas al montar
  useEffect(() => {
    dispatch(cargarCuentas({ solo_activas: filtros.solo_activas }));
  }, [dispatch, filtros.solo_activas]);

  // Filtrar cuentas localmente
  const cuentasFiltradas = cuentas.filter((cuenta) => {
    const matchSearch =
      !searchLocal ||
      cuenta.email.toLowerCase().includes(searchLocal.toLowerCase()) ||
      cuenta.nombre_descriptivo?.toLowerCase().includes(searchLocal.toLowerCase()) ||
      cuenta.organizacion?.toLowerCase().includes(searchLocal.toLowerCase());

    const matchOrganizacion =
      !filtros.organizacion ||
      cuenta.organizacion?.toLowerCase() === filtros.organizacion.toLowerCase();

    return matchSearch && matchOrganizacion;
  });

  const handleToggleActiva = async (cuentaId: number, activa: boolean) => {
    await dispatch(toggleCuentaActiva({ cuentaId, activa: !activa }));
    dispatch(cargarCuentas({ solo_activas: filtros.solo_activas }));
  };

  const handleEliminar = async () => {
    if (cuentaAEliminar) {
      await dispatch(eliminarCuenta(cuentaAEliminar));
      setCuentaAEliminar(null);
      dispatch(cargarCuentas({ solo_activas: filtros.solo_activas }));
    }
  };

  const handleRefresh = () => {
    dispatch(cargarCuentas({ solo_activas: filtros.solo_activas }));
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    // Actualizar URL query param
    if (newValue === 1) {
      setSearchParams({ tab: 'cuarentena' });
    } else {
      setSearchParams({});
    }
  };

  const handleSwitchToConfig = (nit?: string) => {
    // Cambiar al tab de configuración (tab 0)
    setActiveTab(0);
    setSearchParams({});
    // Si viene con NIT, pre-llenar búsqueda
    if (nit) {
      setSearchLocal(nit);
    }
  };

  // Estadísticas globales
  const totalCuentas = cuentas.length;
  const cuentasActivas = cuentas.filter((c) => c.activa).length;
  const totalNits = cuentas.reduce((sum, c) => sum + c.total_nits, 0);
  const totalNitsActivos = cuentas.reduce((sum, c) => sum + c.total_nits_activos, 0);

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 700, color: 'text.primary' }}>
              Configuración de Correos
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Gestiona las cuentas de correo corporativo y los NITs para extracción de facturas
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Tooltip title={loadingCuentas ? "Cargando datos..." : "Refrescar datos"} arrow>
              <span>
                <IconButton
                  onClick={handleRefresh}
                  disabled={loadingCuentas}
                  sx={{
                    color: zentriaColors.violeta.main,
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: zentriaColors.violeta.main + '15',
                      transform: loadingCuentas ? 'none' : 'rotate(180deg)',
                    },
                    '&.Mui-disabled': {
                      color: zentriaColors.violeta.main + '60',
                    }
                  }}
                >
                  {loadingCuentas ? (
                    <CircularProgress size={24} sx={{ color: zentriaColors.violeta.main }} />
                  ) : (
                    <RefreshIcon />
                  )}
                </IconButton>
              </span>
            </Tooltip>
            <Button
              variant="contained"
              size="large"
              startIcon={<AddIcon />}
              onClick={() => setDialogCrearOpen(true)}
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
                boxShadow: '0 4px 14px rgba(128, 0, 106, 0.25)',
                fontWeight: 700,
                textTransform: 'none',
                px: 3,
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: '0 8px 20px rgba(128, 0, 106, 0.35)',
                },
                '&:active': {
                  transform: 'translateY(0)',
                }
              }}
            >
              Nueva Cuenta
            </Button>
          </Box>
        </Box>

        {/* Estadísticas Globales */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card
              elevation={0}
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.violeta.main}15, ${zentriaColors.violeta.main}05)`,
                border: `1px solid ${zentriaColors.violeta.main}30`,
                borderRadius: 3,
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: '4px',
                  background: zentriaColors.violeta.main,
                  opacity: 0,
                  transition: 'opacity 0.3s ease',
                },
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: `0 12px 24px ${zentriaColors.violeta.main}20`,
                  borderColor: zentriaColors.violeta.main,
                  '&::before': { opacity: 1 },
                }
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box>
                    <Typography variant="caption" sx={{ color: 'text.secondary', mb: 1, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                      Cuentas Totales
                    </Typography>
                    <Typography variant="h3" sx={{ color: zentriaColors.violeta.main, fontWeight: 800, mb: 0.5, fontFeatureSettings: '"tnum"' }}>
                      {totalCuentas}
                    </Typography>
                  </Box>
                  <Box sx={{
                    bgcolor: zentriaColors.violeta.main + '15',
                    borderRadius: 2,
                    p: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <EmailIcon sx={{ fontSize: 28, color: zentriaColors.violeta.main }} />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card
              elevation={0}
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.verde.main}15, ${zentriaColors.verde.main}05)`,
                border: `1px solid ${zentriaColors.verde.main}30`,
                borderRadius: 3,
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: '4px',
                  background: zentriaColors.verde.main,
                  opacity: 0,
                  transition: 'opacity 0.3s ease',
                },
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: `0 12px 24px ${zentriaColors.verde.main}20`,
                  borderColor: zentriaColors.verde.main,
                  '&::before': { opacity: 1 },
                }
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box>
                    <Typography variant="caption" sx={{ color: 'text.secondary', mb: 1, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                      Cuentas Activas
                    </Typography>
                    <Typography variant="h3" sx={{ color: zentriaColors.verde.main, fontWeight: 800, mb: 0.5, fontFeatureSettings: '"tnum"' }}>
                      {cuentasActivas}
                    </Typography>
                  </Box>
                  <Box sx={{
                    bgcolor: zentriaColors.verde.main + '15',
                    borderRadius: 2,
                    p: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <ActiveIcon sx={{ fontSize: 28, color: zentriaColors.verde.main }} />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card
              elevation={0}
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.naranja.main}15, ${zentriaColors.naranja.main}05)`,
                border: `1px solid ${zentriaColors.naranja.main}30`,
                borderRadius: 3,
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: '4px',
                  background: zentriaColors.naranja.main,
                  opacity: 0,
                  transition: 'opacity 0.3s ease',
                },
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: `0 12px 24px ${zentriaColors.naranja.main}20`,
                  borderColor: zentriaColors.naranja.main,
                  '&::before': { opacity: 1 },
                }
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box>
                    <Typography variant="caption" sx={{ color: 'text.secondary', mb: 1, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                      NITs Configurados
                    </Typography>
                    <Typography variant="h3" sx={{ color: zentriaColors.naranja.main, fontWeight: 800, mb: 0.5, fontFeatureSettings: '"tnum"' }}>
                      {totalNits}
                    </Typography>
                  </Box>
                  <Box sx={{
                    bgcolor: zentriaColors.naranja.main + '15',
                    borderRadius: 2,
                    p: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <NumbersIcon sx={{ fontSize: 28, color: zentriaColors.naranja.main }} />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card
              elevation={0}
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.amarillo.dark}15, ${zentriaColors.amarillo.dark}05)`,
                border: `1px solid ${zentriaColors.amarillo.dark}30`,
                borderRadius: 3,
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: '4px',
                  background: zentriaColors.amarillo.dark,
                  opacity: 0,
                  transition: 'opacity 0.3s ease',
                },
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: `0 12px 24px ${zentriaColors.amarillo.dark}20`,
                  borderColor: zentriaColors.amarillo.dark,
                  '&::before': { opacity: 1 },
                }
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box>
                    <Typography variant="caption" sx={{ color: 'text.secondary', mb: 1, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                      NITs Activos
                    </Typography>
                    <Typography variant="h3" sx={{ color: zentriaColors.amarillo.dark, fontWeight: 800, mb: 0.5, fontFeatureSettings: '"tnum"' }}>
                      {totalNitsActivos}
                    </Typography>
                  </Box>
                  <Box sx={{
                    bgcolor: zentriaColors.amarillo.dark + '15',
                    borderRadius: 2,
                    p: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <TrendingUpIcon sx={{ fontSize: 28, color: zentriaColors.amarillo.dark }} />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Tabs Navigation */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            sx={{
              '& .MuiTab-root': {
                textTransform: 'none',
                fontWeight: 600,
                fontSize: '1rem',
                minHeight: 56,
                px: 3,
              },
              '& .Mui-selected': {
                color: zentriaColors.violeta.main,
              },
              '& .MuiTabs-indicator': {
                backgroundColor: zentriaColors.violeta.main,
                height: 3,
              },
            }}
          >
            <Tab
              label="Cuentas de Correo"
              icon={<EmailIcon />}
              iconPosition="start"
            />
            <Tab
              label="Facturas en Cuarentena"
              icon={<WarningIcon />}
              iconPosition="start"
            />
          </Tabs>
        </Box>
      </Box>

      {/* Tab Panel 0: Cuentas de Correo */}
      {activeTab === 0 && (
        <Box>
          {/* Filtros y Búsqueda */}
          <Card
          elevation={0}
          sx={{
            mb: 4,
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 3
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Grid container spacing={3} alignItems="center">
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  fullWidth
                  placeholder="Buscar por email, nombre o número..."
                  value={searchLocal}
                  onChange={(e) => setSearchLocal(e.target.value)}
                  variant="outlined"
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      height: 48,
                      borderRadius: 2,
                      bgcolor: 'background.default',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        bgcolor: 'background.paper',
                      },
                      '&.Mui-focused': {
                        bgcolor: 'background.paper',
                        boxShadow: `0 0 0 3px ${zentriaColors.violeta.main}15`,
                      },
                    }
                  }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon sx={{ color: 'text.secondary' }} />
                      </InputAdornment>
                    ),
                    endAdornment: searchLocal && (
                      <InputAdornment position="end">
                        <IconButton
                          size="small"
                          onClick={() => setSearchLocal('')}
                          sx={{
                            '&:hover': {
                              bgcolor: 'action.hover',
                            }
                          }}
                        >
                          <ClearIcon fontSize="small" />
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Stack direction="row" spacing={2} alignItems="center" justifyContent="flex-end">
                  <FormControlLabel
                    control={
                      <Switch
                        checked={filtros.solo_activas}
                        onChange={(e) =>
                          dispatch(setFiltros({ solo_activas: e.target.checked }))
                        }
                        color="success"
                      />
                    }
                    label={<Typography variant="body2" fontWeight={500}>Solo activas</Typography>}
                  />
                  <Chip
                    label={`${cuentasFiltradas.length} resultado${cuentasFiltradas.length !== 1 ? 's' : ''}`}
                    color="primary"
                    sx={{
                      fontWeight: 600,
                      px: 1
                    }}
                  />
                </Stack>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => dispatch(limpiarError())}>
            {error}
          </Alert>
        )}

        {/* Loading */}
        {loadingCuentas && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress size={60} />
          </Box>
        )}

        {/* Lista de Cuentas - Diseño Tipo Tabla Profesional */}
        {!loadingCuentas && (
          <Box>
          {cuentasFiltradas.map((cuenta) => (
            <Card
              key={cuenta.id}
              elevation={0}
              sx={{
                mb: 1.5,
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 2,
                transition: 'all 0.2s ease',
                '&:hover': {
                  borderColor: zentriaColors.violeta.main + '50',
                  boxShadow: '0 2px 8px rgba(128, 0, 106, 0.08)',
                },
              }}
            >
              <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
                <Grid container spacing={3} alignItems="center">

                  {/* Email + Estado */}
                  <Grid size={{ xs: 12, md: 4 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: 2,
                          bgcolor: zentriaColors.violeta.main + '15',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        <EmailIcon sx={{ fontSize: 20, color: zentriaColors.violeta.main }} />
                      </Box>
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography
                          variant="body1"
                          sx={{
                            fontWeight: 600,
                            color: 'text.primary',
                            fontSize: '0.9375rem',
                            mb: 0.5,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {cuenta.email}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                          <Chip
                            label={cuenta.activa ? 'Activa' : 'Inactiva'}
                            size="small"
                            sx={{
                              height: 22,
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              bgcolor: cuenta.activa ? zentriaColors.verde.main : '#757575',
                              color: 'white',
                              '& .MuiChip-label': { px: 1.5, py: 0.25 },
                            }}
                          />
                          {cuenta.grupo_codigo && (
                            <Chip
                              icon={<BusinessIcon sx={{ fontSize: 14 }} />}
                              label={cuenta.grupo_codigo}
                              size="small"
                              sx={{
                                height: 22,
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                bgcolor: zentriaColors.violeta.main + '20',
                                color: zentriaColors.violeta.main,
                                borderColor: zentriaColors.violeta.main + '50',
                                border: '1px solid',
                                '& .MuiChip-label': { px: 1, py: 0.25 },
                                '& .MuiChip-icon': { ml: 0.5, color: zentriaColors.violeta.main },
                              }}
                            />
                          )}
                          {cuenta.organizacion && (
                            <Chip
                              label={cuenta.organizacion}
                              size="small"
                              variant="outlined"
                              sx={{
                                height: 22,
                                fontSize: '0.75rem',
                                fontWeight: 500,
                                borderColor: 'divider',
                                color: 'text.secondary',
                                '& .MuiChip-label': { px: 1.5, py: 0.25 },
                              }}
                            />
                          )}
                        </Box>
                      </Box>
                    </Box>
                  </Grid>

                  {/* NITs Totales */}
                  <Grid size={{ xs: 4, md: 1.5 }}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography
                        variant="h5"
                        sx={{
                          fontWeight: 700,
                          color: zentriaColors.naranja.main,
                          fontSize: '1.75rem',
                          lineHeight: 1,
                          mb: 0.5,
                          fontFeatureSettings: '"tnum"',
                        }}
                      >
                        {cuenta.total_nits}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          color: 'text.secondary',
                          fontSize: '0.75rem',
                          fontWeight: 500,
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          display: 'block',
                        }}
                      >
                        NITs Totales
                      </Typography>
                    </Box>
                  </Grid>

                  {/* NITs Activos */}
                  <Grid size={{ xs: 4, md: 1.5 }}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography
                        variant="h5"
                        sx={{
                          fontWeight: 700,
                          color: zentriaColors.verde.main,
                          fontSize: '1.75rem',
                          lineHeight: 1,
                          mb: 0.5,
                          fontFeatureSettings: '"tnum"',
                        }}
                      >
                        {cuenta.total_nits_activos}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          color: 'text.secondary',
                          fontSize: '0.75rem',
                          fontWeight: 500,
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          display: 'block',
                        }}
                      >
                        NITs Activos
                      </Typography>
                    </Box>
                  </Grid>

                  {/* Fecha */}
                  <Grid size={{ xs: 4, md: 2 }}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ fontSize: '0.75rem', mb: 0.5, fontWeight: 500 }}>
                        Creada hace
                      </Typography>
                      <Typography variant="body2" fontWeight={600} color="text.primary" sx={{ fontSize: '0.875rem' }}>
                        {formatDistanceToNow(new Date(cuenta.creada_en), { locale: es })}
                      </Typography>
                    </Box>
                  </Grid>

                  {/* Acciones */}
                  <Grid size={{ xs: 12, md: 3 }}>
                    <Stack direction="row" spacing={1.5} justifyContent="flex-end">
                      <Button
                        variant="contained"
                        size="medium"
                        startIcon={<ViewIcon />}
                        onClick={() => navigate(`/email-config/${cuenta.id}`)}
                        sx={{
                          bgcolor: zentriaColors.violeta.main,
                          color: 'white',
                          fontWeight: 600,
                          textTransform: 'none',
                          fontSize: '0.875rem',
                          px: 3,
                          py: 0.875,
                          boxShadow: 'none',
                          '&:hover': {
                            bgcolor: zentriaColors.violeta.dark,
                            boxShadow: '0 4px 8px rgba(128, 0, 106, 0.25)',
                          }
                        }}
                      >
                        Detalles
                      </Button>
                      <Button
                        variant="outlined"
                        size="medium"
                        onClick={() => handleToggleActiva(cuenta.id, cuenta.activa)}
                        sx={{
                          color: cuenta.activa ? 'error.main' : 'success.main',
                          borderColor: cuenta.activa ? 'error.main' : 'success.main',
                          fontWeight: 600,
                          textTransform: 'none',
                          fontSize: '0.875rem',
                          px: 2.5,
                          py: 0.875,
                          minWidth: 120,
                          '&:hover': {
                            bgcolor: cuenta.activa ? 'error.main' : 'success.main',
                            borderColor: cuenta.activa ? 'error.main' : 'success.main',
                            color: 'white',
                          }
                        }}
                      >
                        {cuenta.activa ? 'Desactivar' : 'Activar'}
                      </Button>
                    </Stack>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          ))}

            {/* Empty State */}
            {cuentasFiltradas.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 8 }}>
                <EmailIcon sx={{ fontSize: 100, color: 'text.disabled', mb: 2 }} />
                <Typography variant="h5" color="text.secondary" gutterBottom>
                  No se encontraron cuentas
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  {filtros.solo_activas
                    ? 'No hay cuentas activas. Prueba desactivando el filtro.'
                    : 'Comienza agregando tu primera cuenta de correo corporativo.'}
                </Typography>
                {!filtros.solo_activas && (
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => setDialogCrearOpen(true)}
                    size="large"
                  >
                    Agregar Primera Cuenta
                  </Button>
                )}
              </Box>
            )}
          </Box>
        )}
        </Box>
      )}

      {/* Tab Panel 1: Facturas en Cuarentena */}
      {activeTab === 1 && (
        <CuarentenaTab onSwitchToConfig={handleSwitchToConfig} />
      )}

      {/* Dialog Crear Cuenta */}
      <CreateCuentaDialog
        open={dialogCrearOpen}
        onClose={() => setDialogCrearOpen(false)}
        onSuccess={() => {
          setDialogCrearOpen(false);
          handleRefresh();
        }}
      />

      {/* Dialog Confirmar Eliminación */}
      <ConfirmDialog
        open={cuentaAEliminar !== null}
        title="¿Eliminar cuenta?"
        message="Esta acción eliminará la cuenta y todos sus NITs asociados. Esta operación no se puede deshacer."
        confirmText="Eliminar"
        onConfirm={handleEliminar}
        onCancel={() => setCuentaAEliminar(null)}
        severity="error"
      />
    </Container>
  );
};

export default EmailConfigPage;
