import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Grid,
  Divider,
  Chip,
  Alert,
  Paper,
  LinearProgress,
  IconButton,
  Stack,
  Card,
  CardContent,
} from '@mui/material';
import {
  Close,
  CheckCircle,
  Warning,
  CalendarToday,
  Receipt,
  Store,
  AttachMoney,
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Schedule,
  AccountBalance,
  Description,
  PictureAsPdf,
  Person,
  VerifiedUser,
} from '@mui/icons-material';
import type { Workflow, ContextoHistorico } from '../../types/factura.types';
import { zentriaColors } from '../../theme/colors';
import ContextoHistoricoCard from '../ContextoHistorico';
import { facturasService } from '../../features/facturas/services/facturas.service';
import ErrorDialog from '../common/ErrorDialog';

interface FacturaDetailModalProps {
  open: boolean;
  onClose: () => void;
  workflow: Workflow | null;
  contextoHistorico?: ContextoHistorico;
}

/**
 * Modal Profesional para mostrar detalles completos de una factura
 * con diseño moderno y comparación lado a lado
 */
function FacturaDetailModal({ open, onClose, workflow, contextoHistorico }: FacturaDetailModalProps) {
  const [errorDialog, setErrorDialog] = useState<{
    open: boolean;
    title: string;
    message: string;
    severity: 'error' | 'warning' | 'info';
  }>({
    open: false,
    title: '',
    message: '',
    severity: 'error',
  });

  if (!workflow || !workflow.factura) {
    return null;
  }

  const { factura, es_identica_mes_anterior, porcentaje_similitud, diferencias_detectadas, factura_referencia } = workflow;

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '-';
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (date: string | null | undefined) => {
    if (!date) return '-';
    return new Date(date).toLocaleDateString('es-CO', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatDateShort = (date: string | null | undefined) => {
    if (!date) return '-';
    return new Date(date).toLocaleDateString('es-CO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // Calcular diferencias porcentuales
  const calcularDiferencia = (actual: number | undefined, anterior: number | undefined) => {
    if (!actual || !anterior || anterior === 0) return null;
    return ((actual - anterior) / anterior) * 100;
  };

  // Calcular días hasta vencimiento
  const calcularDiasVencimiento = (fechaVencimiento: string | null | undefined) => {
    if (!fechaVencimiento) return null;
    const hoy = new Date();
    const vencimiento = new Date(fechaVencimiento);
    const diff = Math.ceil((vencimiento.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24));
    return diff;
  };

  const diasVencimiento = calcularDiasVencimiento(factura.fecha_vencimiento);
  const diferenciaTotal = factura_referencia
    ? calcularDiferencia(factura.total_a_pagar, factura_referencia.total_a_pagar)
    : null;

  // Determinar color del estado de vencimiento
  const getVencimientoColor = () => {
    if (diasVencimiento === null) return 'default';
    if (diasVencimiento < 0) return 'error';
    if (diasVencimiento <= 5) return 'warning';
    if (diasVencimiento <= 15) return 'info';
    return 'success';
  };

  const getVencimientoTexto = () => {
    if (diasVencimiento === null) return 'Sin fecha de vencimiento';
    if (diasVencimiento < 0) return `Vencida hace ${Math.abs(diasVencimiento)} días`;
    if (diasVencimiento === 0) return 'Vence hoy';
    return `Vence en ${diasVencimiento} días`;
  };

  const getTrendIcon = () => {
    if (diferenciaTotal === null) return null;
    if (Math.abs(diferenciaTotal) < 1) return <TrendingFlat color="action" />;
    if (diferenciaTotal > 0) return <TrendingUp color="error" />;
    return <TrendingDown color="success" />;
  };

  // Handler para abrir PDF en nueva pestaña con autenticación
  const handleVerPDF = async () => {
    if (!factura?.id) return;
    try {
      await facturasService.openPdfInNewTab(factura.id, false);
    } catch (error: any) {
      console.error('Error abriendo PDF:', error);

      // Parsear el mensaje de error para extraer título y descripción
      const errorMessage = error.message || 'Error al procesar la solicitud\n\nNo fue posible cargar el documento PDF. Por favor, verifica tu conexión e intenta nuevamente.';
      const [title, ...messageParts] = errorMessage.split('\n\n');
      const message = messageParts.join('\n\n');

      // Determinar severidad del error
      let severity: 'error' | 'warning' | 'info' = 'error';
      if (title.includes('bloqueada')) {
        severity = 'warning';
      } else if (title.includes('no disponible')) {
        severity = 'info';
      }

      // Mostrar modal de error premium
      setErrorDialog({
        open: true,
        title: title || 'Error al abrir PDF',
        message: message || 'Por favor, intenta nuevamente.',
        severity,
      });
    }
  };

  const handleCloseErrorDialog = () => {
    setErrorDialog({
      open: false,
      title: '',
      message: '',
      severity: 'error',
    });
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
        }
      }}
    >
      {/* Header con gradiente */}
      <Box
        sx={{
          background: `linear-gradient(135deg, ${zentriaColors.violeta.main} 0%, ${zentriaColors.violeta.dark} 100%)`,
          color: 'white',
          p: 3,
          position: 'relative',
        }}
      >
        {/* Botón Cerrar */}
        <IconButton
          onClick={onClose}
          aria-label="Cerrar detalles de factura"
          sx={{
            position: 'absolute',
            right: 16,
            top: 16,
            color: 'white',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.2)',
            },
          }}
        >
          <Close />
        </IconButton>

        <Stack direction="row" spacing={2} alignItems="center" mb={1}>
          <Receipt sx={{ fontSize: 40 }} />
          <Box flex={1}>
            <Typography variant="h4" fontWeight={700}>
              {factura.numero_factura}
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, mb: 1.5 }}>
              CUFE: {factura.cufe}
            </Typography>
            {/* Botón Ver PDF Original - REDISEÑADO 2025-11-18 */}
            <Button
              variant="contained"
              size="small"
              startIcon={<PictureAsPdf />}
              onClick={handleVerPDF}
              sx={{
                backgroundColor: zentriaColors.naranja.main,
                color: 'white',
                fontWeight: 600,
                textTransform: 'none',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                '&:hover': {
                  backgroundColor: zentriaColors.naranja.dark,
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
                  transform: 'translateY(-1px)',
                },
                transition: 'all 0.2s ease-in-out',
              }}
            >
              Ver PDF Original
            </Button>
          </Box>
        </Stack>

        {/* Indicador de similitud en el header */}
        {porcentaje_similitud !== null && porcentaje_similitud !== undefined && (
          <Box mt={2}>
            <Stack direction="row" spacing={1} alignItems="center" mb={1}>
              {es_identica_mes_anterior ? <CheckCircle /> : <Warning />}
              <Typography variant="subtitle2">
                {es_identica_mes_anterior
                  ? 'Factura idéntica al mes anterior'
                  : `Similitud: ${porcentaje_similitud.toFixed(1)}%`}
              </Typography>
            </Stack>
            <LinearProgress
              variant="determinate"
              value={porcentaje_similitud}
              sx={{
                height: 8,
                borderRadius: 1,
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                '& .MuiLinearProgress-bar': {
                  backgroundColor: es_identica_mes_anterior ? '#4caf50' : porcentaje_similitud >= 95 ? '#2196f3' : '#ff9800',
                  borderRadius: 1,
                },
              }}
            />
          </Box>
        )}
      </Box>

      <DialogContent sx={{ p: 0 }}>
        {/* Sección de Fechas y Estado - NUEVO */}
        <Box sx={{ p: 3, backgroundColor: '#f8f9fa' }}>
          <Typography variant="h6" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Schedule color="primary" />
            Fechas Importantes
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card elevation={0} sx={{ borderLeft: `4px solid ${zentriaColors.violeta.main}` }}>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                    <CalendarToday sx={{ fontSize: 20, color: zentriaColors.violeta.main }} />
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      FECHA DE EMISIÓN
                    </Typography>
                  </Stack>
                  <Typography variant="h6" fontWeight={700}>
                    {formatDateShort(factura.fecha_emision)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card elevation={0} sx={{ borderLeft: `4px solid ${getVencimientoColor() === 'error' ? '#f44336' : getVencimientoColor() === 'warning' ? '#ff9800' : '#4caf50'}` }}>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                    <Schedule sx={{ fontSize: 20, color: getVencimientoColor() === 'error' ? '#f44336' : getVencimientoColor() === 'warning' ? '#ff9800' : '#4caf50' }} />
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      FECHA DE VENCIMIENTO
                    </Typography>
                  </Stack>
                  <Typography variant="h6" fontWeight={700}>
                    {formatDateShort(factura.fecha_vencimiento)}
                  </Typography>
                  <Chip
                    label={getVencimientoTexto()}
                    color={getVencimientoColor()}
                    size="small"
                    sx={{ mt: 1, fontWeight: 600 }}
                  />
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card elevation={0} sx={{ borderLeft: `4px solid ${zentriaColors.verde.main}` }}>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                    <Description sx={{ fontSize: 20, color: zentriaColors.verde.main }} />
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      ESTADO
                    </Typography>
                  </Stack>
                  <Typography variant="h6" fontWeight={700} sx={{ textTransform: 'capitalize' }}>
                    {factura.estado?.replace('_', ' ')}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card elevation={0} sx={{ borderLeft: `4px solid ${zentriaColors.naranja.main}` }}>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                    <AttachMoney sx={{ fontSize: 20, color: zentriaColors.naranja.main }} />
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      TOTAL A PAGAR
                    </Typography>
                  </Stack>
                  <Typography variant="h6" fontWeight={700} color="primary">
                    {formatCurrency(factura.total_a_pagar)}
                  </Typography>
                  {diferenciaTotal !== null && (
                    <Stack direction="row" spacing={0.5} alignItems="center" mt={1}>
                      {getTrendIcon()}
                      <Typography variant="caption" fontWeight={600} color={diferenciaTotal > 0 ? 'error' : 'success'}>
                        {diferenciaTotal > 0 ? '+' : ''}{diferenciaTotal.toFixed(1)}% vs anterior
                      </Typography>
                    </Stack>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>

        <Divider />

        {/* Información del Proveedor */}
        <Box sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Store color="primary" />
            Información del Proveedor
          </Typography>
          <Paper elevation={0} sx={{ p: 2, backgroundColor: '#f8f9fa', borderRadius: 2 }}>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 8 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  RAZÓN SOCIAL
                </Typography>
                <Typography variant="h6" fontWeight={600}>
                  {factura.proveedor?.razon_social || '-'}
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  NIT
                </Typography>
                <Typography variant="h6" fontWeight={600}>
                  {factura.proveedor?.nit || factura.nit || '-'}
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </Box>

        <Divider />

        {/* Información de Aprobación */}
        {factura.aprobado_por_workflow && (
          <>
            <Box sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <VerifiedUser color="primary" />
                Información de Aprobación
              </Typography>
              <Paper elevation={0} sx={{ p: 2, backgroundColor: '#f8f9fa', borderRadius: 2 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  APROBADO POR
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center" mt={0.5}>
                  <Person sx={{ fontSize: 20, color: zentriaColors.violeta.main }} />
                  <Typography variant="h6" fontWeight={600}>
                    {factura.aprobado_por_workflow}
                  </Typography>
                </Stack>
              </Paper>
            </Box>

            <Divider />
          </>
        )}

        {/* Comparación Lado a Lado o Detalles Simples */}
        <Box sx={{ p: 3 }}>
          {factura_referencia ? (
            <>
              <Typography variant="h6" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AccountBalance color="primary" />
                Comparación Financiera
              </Typography>
              <Grid container spacing={3}>
                {/* Factura Actual */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper
                    elevation={3}
                    sx={{
                      p: 3,
                      borderRadius: 2,
                      border: `3px solid ${zentriaColors.violeta.main}`,
                      position: 'relative',
                      overflow: 'hidden',
                      '&::before': {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        height: 6,
                        background: `linear-gradient(90deg, ${zentriaColors.violeta.main}, ${zentriaColors.violeta.dark})`,
                      },
                    }}
                  >
                    <Box sx={{ pt: 1 }}>
                      <Chip
                        label="FACTURA ACTUAL"
                        color="primary"
                        size="small"
                        sx={{ fontWeight: 700, mb: 2 }}
                      />
                      <Stack spacing={2}>
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            Número de Factura
                          </Typography>
                          <Typography variant="body1" fontWeight={600}>
                            {factura.numero_factura}
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            Fecha de Emisión
                          </Typography>
                          <Typography variant="body1" fontWeight={600}>
                            {formatDate(factura.fecha_emision)}
                          </Typography>
                        </Box>
                        {factura.fecha_vencimiento && (
                          <Box>
                            <Typography variant="caption" color="text.secondary" fontWeight={600}>
                              Fecha de Vencimiento
                            </Typography>
                            <Typography variant="body1" fontWeight={600}>
                              {formatDate(factura.fecha_vencimiento)}
                            </Typography>
                          </Box>
                        )}
                        <Divider />
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            Subtotal
                          </Typography>
                          <Typography variant="h6" fontWeight={700}>
                            {formatCurrency(factura.subtotal)}
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            IVA
                          </Typography>
                          <Typography variant="h6" fontWeight={700}>
                            {formatCurrency(factura.iva)}
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            Total
                          </Typography>
                          <Typography variant="h6" fontWeight={700}>
                            {formatCurrency(factura.total)}
                          </Typography>
                        </Box>
                        <Box
                          sx={{
                            p: 2,
                            backgroundColor: `${zentriaColors.violeta.main}15`,
                            borderRadius: 2,
                          }}
                        >
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            TOTAL A PAGAR
                          </Typography>
                          <Typography variant="h5" fontWeight={800} color="primary">
                            {formatCurrency(factura.total_a_pagar)}
                          </Typography>
                        </Box>
                      </Stack>
                    </Box>
                  </Paper>
                </Grid>

                {/* Factura Referencia */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper
                    elevation={3}
                    sx={{
                      p: 3,
                      borderRadius: 2,
                      border: `3px solid ${zentriaColors.verde.main}`,
                      position: 'relative',
                      overflow: 'hidden',
                      '&::before': {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        height: 6,
                        background: `linear-gradient(90deg, ${zentriaColors.verde.main}, ${zentriaColors.verde.dark})`,
                      },
                    }}
                  >
                    <Box sx={{ pt: 1 }}>
                      <Chip
                        label="FACTURA ANTERIOR"
                        sx={{ fontWeight: 700, mb: 2, backgroundColor: zentriaColors.verde.main, color: 'white' }}
                        size="small"
                      />
                      <Stack spacing={2}>
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            Número de Factura
                          </Typography>
                          <Typography variant="body1" fontWeight={600}>
                            {factura_referencia.numero_factura}
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            Fecha de Emisión
                          </Typography>
                          <Typography variant="body1" fontWeight={600}>
                            {formatDate(factura_referencia.fecha_emision)}
                          </Typography>
                        </Box>
                        {factura_referencia.fecha_vencimiento && (
                          <Box>
                            <Typography variant="caption" color="text.secondary" fontWeight={600}>
                              Fecha de Vencimiento
                            </Typography>
                            <Typography variant="body1" fontWeight={600}>
                              {formatDate(factura_referencia.fecha_vencimiento)}
                            </Typography>
                          </Box>
                        )}
                        <Divider />
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            Subtotal
                          </Typography>
                          <Typography variant="h6" fontWeight={700}>
                            {formatCurrency(factura_referencia.subtotal)}
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            IVA
                          </Typography>
                          <Typography variant="h6" fontWeight={700}>
                            {formatCurrency(factura_referencia.iva)}
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            Total
                          </Typography>
                          <Typography variant="h6" fontWeight={700}>
                            {formatCurrency(factura_referencia.total)}
                          </Typography>
                        </Box>
                        <Box
                          sx={{
                            p: 2,
                            backgroundColor: `${zentriaColors.verde.main}15`,
                            borderRadius: 2,
                          }}
                        >
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            TOTAL A PAGAR
                          </Typography>
                          <Typography variant="h5" fontWeight={800} sx={{ color: zentriaColors.verde.dark }}>
                            {formatCurrency(factura_referencia.total_a_pagar)}
                          </Typography>
                        </Box>
                      </Stack>
                    </Box>
                  </Paper>
                </Grid>
              </Grid>

              {/* Diferencias Detectadas */}
              {diferencias_detectadas && diferencias_detectadas.length > 0 && (
                <Box mt={3}>
                  <Alert severity="warning" icon={<Warning />} sx={{ borderRadius: 2 }}>
                    <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                      Se detectaron {diferencias_detectadas.length} diferencia(s)
                    </Typography>
                    <Box display="flex" flexWrap="wrap" gap={1} mt={1}>
                      {diferencias_detectadas.map((diff: any, index: number) => (
                        <Chip
                          key={index}
                          label={`${diff.campo}: ${diff.valor_anterior} → ${diff.valor_actual}`}
                          size="small"
                          sx={{ fontWeight: 600 }}
                        />
                      ))}
                    </Box>
                  </Alert>
                </Box>
              )}
            </>
          ) : (
            /* Detalles Sin Comparación */
            <>
              <Typography variant="h6" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AccountBalance color="primary" />
                Detalles Financieros
              </Typography>
              <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
                <Grid container spacing={3}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        Subtotal
                      </Typography>
                      <Typography variant="h6" fontWeight={700}>
                        {formatCurrency(factura.subtotal)}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        IVA
                      </Typography>
                      <Typography variant="h6" fontWeight={700}>
                        {formatCurrency(factura.iva)}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        Total
                      </Typography>
                      <Typography variant="h6" fontWeight={700}>
                        {formatCurrency(factura.total)}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Box
                      sx={{
                        p: 2,
                        backgroundColor: `${zentriaColors.violeta.main}15`,
                        borderRadius: 2,
                      }}
                    >
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        TOTAL A PAGAR
                      </Typography>
                      <Typography variant="h5" fontWeight={800} color="primary">
                        {formatCurrency(factura.total_a_pagar)}
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Paper>
            </>
          )}
        </Box>

        {/* Contexto Histórico */}
        {contextoHistorico && (
          <Box sx={{ p: 3, backgroundColor: '#f8f9fa' }}>
            <ContextoHistoricoCard
              contexto={contextoHistorico}
              montoActual={factura.total || 0}
            />
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 3, backgroundColor: '#f8f9fa', gap: 2 }}>
        <Box sx={{ flex: 1 }} />
        <Button onClick={onClose} variant="outlined" size="large" sx={{ minWidth: 120 }}>
          Cerrar
        </Button>
      </DialogActions>

      {/* Modal de Error Premium */}
      <ErrorDialog
        open={errorDialog.open}
        title={errorDialog.title}
        message={errorDialog.message}
        severity={errorDialog.severity}
        onClose={handleCloseErrorDialog}
      />
    </Dialog>
  );
}

export default FacturaDetailModal;
