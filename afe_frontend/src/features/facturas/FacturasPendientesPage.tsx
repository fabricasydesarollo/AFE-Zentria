import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Button,
  Stack,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Checkbox,
  Grid,
  Card,
} from '@mui/material';
import {
  Refresh,
  PictureAsPdf,
  CheckCircle,
  Assessment,
  VerifiedUser,
  ReplyAll,
  Close,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { useNotification } from '../../components/Notifications/NotificationProvider';
import { zentriaColors } from '../../theme/colors';
import apiClient from '../../services/api';
import FacturaDetailModal from '../../components/Facturas/FacturaDetailModal';

/**
 * Página PROFESIONAL para Contador: Validación de Facturas
 *
 * RESPONSABILIDAD ÚNICA: Validar facturas aprobadas para Tesorería
 * - Ver facturas en estado: aprobada / aprobada_auto
 * - Validar factura → estado: validada_contabilidad (OK para Tesorería)
 * - Devolver factura → estado: devuelta_contabilidad (requiere corrección)
 *
 * NO TOCA: Pagos, Tesorería, Contabilización
 *
 * REFACTORIZADO: 2025-11-29 (Eliminado módulo de pagos completamente)
 */
interface ContadorFactura {
  id: number;
  numero_factura: string;
  estado: string;
  proveedor_id?: number | null;
  proveedor: {
    nit: string;
    razon_social: string;
  };
  subtotal: number;
  iva: number;
  total: number;
  total_a_pagar: number;
  moneda?: string;
  aprobado_por_workflow?: string;
  tipo_aprobacion_workflow?: string;
  fecha_aprobacion_workflow?: string;
  fecha_emision?: string;
  fecha_vencimiento?: string;
  cufe?: string;
  usuario?: {
    nombre: string;
    email: string;
  };
}

interface StatsData {
  total_pendiente: number;
  monto_pendiente: number;
  validadas_hoy: number;
}

function FacturasPendientesPage() {
  const { showNotification } = useNotification();

  // Estado de datos
  const [facturas, setFacturas] = useState<ContadorFactura[]>([]);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estados para modales
  const [validacionModalOpen, setValidacionModalOpen] = useState(false);
  const [devolucionModalOpen, setDevolucionModalOpen] = useState(false);
  const [detallesModalOpen, setDetallesModalOpen] = useState(false);
  const [selectedFactura, setSelectedFactura] = useState<ContadorFactura | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Estados para formularios
  const [validacionObs, setValidacionObs] = useState('');
  const [devolucionObs, setDevolucionObs] = useState('');
  const [notificarResponsable, setNotificarResponsable] = useState(true);

  // Cargar facturas aprobadas pendientes de validación
  const loadFacturas = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/accounting/facturas/por-revisar', {
        params: { pagina: 1, limit: 100, solo_pendientes: true }
      });

      // Validar que la respuesta tenga la estructura esperada
      if (response.data && response.data.facturas && Array.isArray(response.data.facturas)) {
        setFacturas(response.data.facturas);
        setStats(response.data.estadisticas || { total_pendiente: 0, monto_pendiente: 0, validadas_hoy: 0 });
      } else {
        console.error('Respuesta inesperada del servidor:', response.data);
        setError('Formato de respuesta inválido del servidor');
        setFacturas([]);
      }
    } catch (err: any) {
      console.error('Error cargando facturas:', err);
      const errorMessage = err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Error al cargar facturas pendientes de validación';
      setError(errorMessage);
      setFacturas([]);
      showNotification(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Validar factura (aprobada → validada_contabilidad)
  const handleValidarFactura = async () => {
    if (!selectedFactura) return;

    setActionLoading(true);
    try {
      await apiClient.post(`/accounting/facturas/${selectedFactura.id}/validar`, {
        observaciones: validacionObs || undefined
      });

      showNotification(`Factura ${selectedFactura.numero_factura} validada exitosamente. Lista para Tesorería.`, 'success');

      // Remover factura de la tabla
      setFacturas(facturas.filter(f => f.id !== selectedFactura.id));
      // Actualizar estadísticas
      if (stats) {
        setStats({
          ...stats,
          total_pendiente: stats.total_pendiente - 1,
          validadas_hoy: stats.validadas_hoy + 1
        });
      }

      // Cerrar modal
      setValidacionModalOpen(false);
      setSelectedFactura(null);
      setValidacionObs('');
    } catch (err: any) {
      console.error('Error validando factura:', err);
      showNotification(err.response?.data?.detail || 'Error al validar factura', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Devolver factura (aprobada → devuelta_contabilidad)
  const handleDevolverFactura = async () => {
    if (!selectedFactura || !devolucionObs.trim()) {
      showNotification('Debe especificar observaciones para devolver la factura', 'warning');
      return;
    }

    setActionLoading(true);
    try {
      await apiClient.post(`/accounting/facturas/${selectedFactura.id}/devolver`, {
        observaciones: devolucionObs,
        notificar_responsable: notificarResponsable
      });

      showNotification(`Factura ${selectedFactura.numero_factura} devuelta. Responsable ha sido notificado.`, 'success');

      // Remover factura de la tabla
      setFacturas(facturas.filter(f => f.id !== selectedFactura.id));
      // Actualizar estadísticas
      if (stats) {
        setStats({
          ...stats,
          total_pendiente: stats.total_pendiente - 1
        });
      }

      // Cerrar modal
      setDevolucionModalOpen(false);
      setSelectedFactura(null);
      setDevolucionObs('');
      setNotificarResponsable(true);
    } catch (err: any) {
      console.error('Error devolviendo factura:', err);
      showNotification(err.response?.data?.detail || 'Error al devolver factura', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    loadFacturas();
  }, []);

  const formatCurrency = (amount: string | number) => {
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(numAmount);
  };

  const formatDate = (date: string | null) => {
    if (!date) return '-';
    return new Date(date).toLocaleDateString('es-CO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // Esta función ya no es necesaria - usamos el modal de detalles en su lugar
  // Mantiene compatibilidad si se necesita en el futuro

  // Chip para tipo de aprobación
  const getTipoAprobacionChip = (tipo?: string, estado?: string) => {
    if (tipo === 'automatica' || estado === 'aprobada_auto') {
      return (
        <Chip
          label="Aprobado Automático"
          size="small"
          variant="outlined"
          color="primary"
          sx={{
            fontWeight: 600,
            borderColor: zentriaColors.violeta.main,
            color: zentriaColors.violeta.main
          }}
        />
      );
    }
    return (
      <Chip
        label="Aprobado Manualmente"
        size="small"
        variant="outlined"
        color="success"
        sx={{
          fontWeight: 600
        }}
      />
    );
  };

  // Abrir modal de validación
  const handleAbrirValidacion = (factura: ContadorFactura) => {
    setSelectedFactura(factura);
    setValidacionObs('');
    setValidacionModalOpen(true);
  };

  // Abrir modal de devolución
  const handleAbrirDevolucion = (factura: ContadorFactura) => {
    setSelectedFactura(factura);
    setDevolucionObs('');
    setNotificarResponsable(true);
    setDevolucionModalOpen(true);
  };

  // Abrir modal de detalles
  const handleAbrirDetalles = (factura: ContadorFactura) => {
    setSelectedFactura(factura);
    setDetallesModalOpen(true);
  };

  return (
    <Box>
      {/* HEADER PROFESIONAL */}
      <Box
        sx={{
          background: `linear-gradient(135deg, ${zentriaColors.violeta.main} 0%, ${zentriaColors.violeta.dark} 100%)`,
          color: 'white',
          p: 4,
          borderRadius: 2,
          mb: 3,
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        }}
      >
        <Stack direction="row" alignItems="center" spacing={2} mb={2}>
          <VerifiedUser sx={{ fontSize: 40 }} />
          <Box flex={1}>
            <Typography variant="h4" fontWeight={700}>
              Validación de Facturas
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              Revisa y valida facturas aprobadas. Solo facturas validadas llegan a Tesorería.
            </Typography>
          </Box>
        </Stack>
      </Box>

      {/* ESTADÍSTICAS */}
      {stats && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card sx={{ p: 2, textAlign: 'center', boxShadow: 1 }}>
              <Typography variant="h6" fontWeight={700} color="primary">
                {stats.total_pendiente}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Pendientes de Validar
              </Typography>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card sx={{ p: 2, textAlign: 'center', boxShadow: 1 }}>
              <Typography variant="h6" fontWeight={700} color="#1a1a1a">
                {formatCurrency(stats.monto_pendiente)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total a Pagar
              </Typography>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card sx={{ p: 2, textAlign: 'center', boxShadow: 1 }}>
              <Typography variant="h6" fontWeight={700} color="success.main">
                {stats.validadas_hoy}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Validadas Hoy
              </Typography>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* TOOLBAR */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" fontWeight={600}>
          {facturas.length === 0
            ? 'No hay facturas pendientes'
            : `${facturas.length} factura${facturas.length !== 1 ? 's' : ''} por validar`}
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={loadFacturas}
          disabled={loading}
        >
          Actualizar
        </Button>
      </Box>

      {/* CONTENIDO PRINCIPAL */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      ) : facturas.length === 0 ? (
        <Paper
          sx={{
            p: 8,
            textAlign: 'center',
            backgroundColor: '#f8f9fa',
            borderRadius: 2,
          }}
        >
          <CheckCircle sx={{ fontSize: 80, color: zentriaColors.verde.main, mb: 2 }} />
          <Typography variant="h6" fontWeight={600} gutterBottom>
            ¡Todo validado!
          </Typography>
          <Typography variant="body2" color="text.secondary">
            No hay facturas pendientes de validación en este momento
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: 2, boxShadow: 2 }}>
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f8f9fa' }}>
                <TableCell sx={{ fontWeight: 700 }}>Factura</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Proveedor</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>NIT</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">
                  Total a Pagar
                </TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Modo de Aprobación</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="center">
                  Detalles
                </TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="center">
                  Acciones
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {facturas.map((factura) => (
                <TableRow
                  key={factura.id}
                  hover
                  sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                >
                  <TableCell>
                    <Typography
                      variant="body2"
                      fontWeight={600}
                      sx={{ cursor: 'pointer', color: zentriaColors.violeta.main }}
                      onClick={() => handleAbrirDetalles(factura)}
                    >
                      {factura.numero_factura}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {factura.proveedor?.razon_social || 'Sin proveedor'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{factura.proveedor?.nit || '-'}</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(factura.total_a_pagar)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {getTipoAprobacionChip(factura.tipo_aprobacion_workflow, factura.estado)}
                  </TableCell>
                  <TableCell align="center">
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={() => handleAbrirDetalles(factura)}
                    >
                      <Assessment />
                    </IconButton>
                  </TableCell>
                  <TableCell align="center">
                    <Stack direction="row" spacing={1} justifyContent="center">
                      <Button
                        variant="contained"
                        size="small"
                        color="success"
                        startIcon={<VerifiedUser />}
                        onClick={() => handleAbrirValidacion(factura)}
                      >
                        Validar
                      </Button>
                      <Button
                        variant="contained"
                        size="small"
                        color="error"
                        startIcon={<ReplyAll />}
                        onClick={() => handleAbrirDevolucion(factura)}
                      >
                        Devolver
                      </Button>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* MODAL: VALIDACIÓN - DISEÑO PREMIUM */}
      <Dialog
        open={validacionModalOpen}
        onClose={() => setValidacionModalOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
          }
        }}
      >
        <DialogTitle sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          py: 3
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{
              backgroundColor: 'rgba(255,255,255,0.2)',
              borderRadius: 2,
              p: 1,
              display: 'flex'
            }}>
              <VerifiedUser sx={{ fontSize: 32 }} />
            </Box>
            <Box>
              <Typography variant="h5" fontWeight={700}>
                Validar Factura
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
                Confirmar validación contable
              </Typography>
            </Box>
          </Box>
        </DialogTitle>

        <DialogContent sx={{ p: 4 }}>
          {selectedFactura && (
            <Box>
              {/* Información de la factura - Card Premium */}
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  mb: 3,
                  background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
                  borderRadius: 2,
                  border: '1px solid rgba(102, 126, 234, 0.2)'
                }}
              >
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      NÚMERO DE FACTURA
                    </Typography>
                    <Typography variant="h6" fontWeight={700} sx={{ mt: 0.5 }}>
                      {selectedFactura.numero_factura}
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      PROVEEDOR
                    </Typography>
                    <Typography variant="body1" fontWeight={600} sx={{ mt: 0.5 }}>
                      {selectedFactura.proveedor?.razon_social}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      NIT: {selectedFactura.proveedor?.nit}
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      TOTAL A PAGAR
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight={700}
                      sx={{
                        mt: 0.5,
                        color: '#667eea'
                      }}
                    >
                      {formatCurrency(selectedFactura.total_a_pagar)}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>

              {/* Campo de observaciones mejorado */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5 }}>
                  Observaciones (Opcional)
                </Typography>
                <TextField
                  multiline
                  rows={4}
                  value={validacionObs}
                  onChange={(e) => setValidacionObs(e.target.value)}
                  fullWidth
                  placeholder="Ej: Verificada contra registros contables. Documentación completa y correcta..."
                  variant="outlined"
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 2,
                      backgroundColor: '#f8f9fa',
                      '&:hover': {
                        backgroundColor: '#fff',
                      },
                      '&.Mui-focused': {
                        backgroundColor: '#fff',
                      }
                    }
                  }}
                />
              </Box>

              {/* Alert mejorado */}
              <Alert
                severity="success"
                icon={<VerifiedUser />}
                sx={{
                  borderRadius: 2,
                  backgroundColor: '#e8f5e9',
                  border: '1px solid #4caf50',
                  '& .MuiAlert-icon': {
                    color: '#2e7d32'
                  }
                }}
              >
                <Typography variant="body2" fontWeight={600}>
                  Al validar, esta factura:
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  • Cambiará a estado <strong>validada_contabilidad</strong>
                  <br />
                  • Estará disponible para que Tesorería proceda con el pago
                  <br />
                  • Quedará registrada en el historial de validaciones
                </Typography>
              </Alert>
            </Box>
          )}
        </DialogContent>

        <DialogActions sx={{ p: 3, backgroundColor: '#f8f9fa', gap: 2 }}>
          <Button
            onClick={() => setValidacionModalOpen(false)}
            variant="outlined"
            size="large"
            sx={{
              minWidth: 120,
              borderRadius: 2,
              textTransform: 'none',
              fontWeight: 600
            }}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleValidarFactura}
            variant="contained"
            size="large"
            disabled={actionLoading}
            sx={{
              minWidth: 120,
              borderRadius: 2,
              textTransform: 'none',
              fontWeight: 700,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
              '&:hover': {
                background: 'linear-gradient(135deg, #5568d3 0%, #653a8b 100%)',
                boxShadow: '0 6px 16px rgba(102, 126, 234, 0.5)',
              }
            }}
          >
            {actionLoading ? 'Validando...' : '✓ Validar Factura'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* MODAL: DEVOLUCIÓN - DISEÑO PREMIUM */}
      <Dialog
        open={devolucionModalOpen}
        onClose={() => setDevolucionModalOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
          }
        }}
      >
        <DialogTitle sx={{
          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
          color: 'white',
          py: 3
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{
              backgroundColor: 'rgba(255,255,255,0.2)',
              borderRadius: 2,
              p: 1,
              display: 'flex'
            }}>
              <ReplyAll sx={{ fontSize: 32 }} />
            </Box>
            <Box>
              <Typography variant="h5" fontWeight={700}>
                Devolver Factura
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
                Solicitar corrección al responsable
              </Typography>
            </Box>
          </Box>
        </DialogTitle>

        <DialogContent sx={{ p: 4 }}>
          {selectedFactura && (
            <Box>
              {/* Información de la factura - Card Premium */}
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  mb: 3,
                  background: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
                  borderRadius: 2,
                  border: '1px solid rgba(245, 87, 108, 0.2)'
                }}
              >
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      NÚMERO DE FACTURA
                    </Typography>
                    <Typography variant="h6" fontWeight={700} sx={{ mt: 0.5 }}>
                      {selectedFactura.numero_factura}
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      PROVEEDOR
                    </Typography>
                    <Typography variant="body1" fontWeight={600} sx={{ mt: 0.5 }}>
                      {selectedFactura.proveedor?.razon_social}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      NIT: {selectedFactura.proveedor?.nit}
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      TOTAL A PAGAR
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight={700}
                      sx={{
                        mt: 0.5,
                        color: '#f5576c'
                      }}
                    >
                      {formatCurrency(selectedFactura.total_a_pagar)}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>

              {/* Campo de observaciones mejorado */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5 }}>
                  Observaciones (Requerido) *
                </Typography>
                <TextField
                  multiline
                  rows={4}
                  value={devolucionObs}
                  onChange={(e) => setDevolucionObs(e.target.value)}
                  fullWidth
                  required
                  placeholder="Ej: Falta especificar centro de costos. Por favor completar sección de distribución contable..."
                  variant="outlined"
                  error={devolucionObs.length > 0 && devolucionObs.length < 10}
                  helperText={devolucionObs.length > 0 && devolucionObs.length < 10 ? '⚠️ Mínimo 10 caracteres para una descripción clara' : `${devolucionObs.length} caracteres`}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 2,
                      backgroundColor: '#f8f9fa',
                      '&:hover': {
                        backgroundColor: '#fff',
                      },
                      '&.Mui-focused': {
                        backgroundColor: '#fff',
                      }
                    }
                  }}
                />
              </Box>

              {/* Checkbox de notificación mejorado */}
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  mb: 3,
                  backgroundColor: '#f8f9fa',
                  borderRadius: 2,
                  border: '1px solid #e0e0e0'
                }}
              >
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={notificarResponsable}
                      onChange={(e) => setNotificarResponsable(e.target.checked)}
                      sx={{
                        color: '#f5576c',
                        '&.Mui-checked': {
                          color: '#f5576c',
                        }
                      }}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight={600}>
                        Notificar al Responsable que aprobó
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Se enviará un email automático con las observaciones
                      </Typography>
                    </Box>
                  }
                />
              </Paper>

              {/* Alert mejorado */}
              <Alert
                severity="warning"
                icon={<ReplyAll />}
                sx={{
                  borderRadius: 2,
                  backgroundColor: '#fff3e0',
                  border: '1px solid #ff9800',
                  '& .MuiAlert-icon': {
                    color: '#f57c00'
                  }
                }}
              >
                <Typography variant="body2" fontWeight={600}>
                  Al devolver, esta factura:
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  • Cambiará a estado <strong>devuelta_contabilidad</strong>
                  <br />
                  • El Responsable recibirá notificación por email
                  <br />
                  • Deberá ser corregida antes de reenviar
                </Typography>
              </Alert>
            </Box>
          )}
        </DialogContent>

        <DialogActions sx={{ p: 3, backgroundColor: '#f8f9fa', gap: 2 }}>
          <Button
            onClick={() => setDevolucionModalOpen(false)}
            variant="outlined"
            size="large"
            sx={{
              minWidth: 120,
              borderRadius: 2,
              textTransform: 'none',
              fontWeight: 600
            }}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleDevolverFactura}
            variant="contained"
            size="large"
            disabled={actionLoading || !devolucionObs.trim() || devolucionObs.length < 10}
            sx={{
              minWidth: 120,
              borderRadius: 2,
              textTransform: 'none',
              fontWeight: 700,
              background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
              boxShadow: '0 4px 12px rgba(245, 87, 108, 0.4)',
              '&:hover': {
                background: 'linear-gradient(135deg, #e082ea 0%, #e4465b 100%)',
                boxShadow: '0 6px 16px rgba(245, 87, 108, 0.5)',
              },
              '&:disabled': {
                background: '#e0e0e0',
                color: '#9e9e9e'
              }
            }}
          >
            {actionLoading ? 'Devolviendo...' : '↩ Devolver Factura'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* MODAL: DETALLES - Usando componente profesional existente */}
      <FacturaDetailModal
        open={detallesModalOpen}
        onClose={() => setDetallesModalOpen(false)}
        workflow={selectedFactura ? {
          id: 0,
          factura_id: selectedFactura.id,
          factura: {
            ...selectedFactura,
            proveedor_id: selectedFactura.proveedor_id || null,
            moneda: selectedFactura.moneda || 'COP',
          } as any,
          estado: selectedFactura.estado as any,
          responsable_id: 0,
          es_identica_mes_anterior: false,
          porcentaje_similitud: undefined,
          diferencias_detectadas: [],
          factura_referencia: undefined
        } as any : null}
      />
    </Box>
  );
}

export default FacturasPendientesPage;
