import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Alert,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
} from '@mui/material';
import {
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  TrendingUp,
  TrendingFlat,
  ShowChart,
} from '@mui/icons-material';
import type { ContextoHistorico } from '../types/factura.types';

interface ContextoHistoricoProps {
  contexto: ContextoHistorico;
  montoActual: number;
}

const ContextoHistoricoCard: React.FC<ContextoHistoricoProps> = ({ contexto, montoActual }) => {
  // Determinar color y icono según tipo de patrón
  const getTipoPatronConfig = () => {
    switch (contexto.tipo_patron) {
      case 'TIPO_A':
        return {
          color: 'success' as const,
          icon: <TrendingFlat />,
          label: 'Tipo A: Pago Fijo',
          descripcion: 'Valor predecible, siempre el mismo monto mensual',
        };
      case 'TIPO_B':
        return {
          color: 'info' as const,
          icon: <ShowChart />,
          label: 'Tipo B: Pago Fluctuante',
          descripcion: 'Valor variable dentro de rango predecible',
        };
      case 'TIPO_C':
        return {
          color: 'warning' as const,
          icon: <TrendingUp />,
          label: 'Tipo C: Excepcional',
          descripcion: 'Proveedor nuevo o monto atípico',
        };
    }
  };

  const tipoConfig = getTipoPatronConfig();

  // Determinar si el monto está dentro del rango
  const dentroRango =
    contexto.rango_esperado &&
    montoActual >= contexto.rango_esperado.inferior &&
    montoActual <= contexto.rango_esperado.superior;

  // Calcular porcentaje de confianza
  const confianzaPorcentaje = Math.round(contexto.confianza * 100);

  return (
    <Card elevation={3} sx={{ mt: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            {tipoConfig.icon}
            <Typography variant="h6" fontWeight="bold">
              Análisis Histórico de Pagos
            </Typography>
          </Box>
          <Chip
            label={tipoConfig.label}
            color={tipoConfig.color}
            icon={tipoConfig.icon}
          />
        </Box>

        <Typography variant="body2" color="text.secondary" mb={2}>
          {tipoConfig.descripcion}
        </Typography>

        {/* Alerta de Recomendación */}
        <Alert
          severity={contexto.recomendacion === 'LISTA_PARA_APROBAR' ? 'success' : 'warning'}
          icon={
            contexto.recomendacion === 'LISTA_PARA_APROBAR' ? (
              <CheckCircle />
            ) : (
              <Warning />
            )
          }
          sx={{ mb: 3 }}
        >
          <Typography variant="subtitle2" fontWeight="bold">
            {contexto.recomendacion === 'LISTA_PARA_APROBAR'
              ? '✅ Lista para Aprobar'
              : '⚠️ Requiere Análisis'}
          </Typography>
          <Typography variant="body2">{contexto.motivo}</Typography>
        </Alert>

        {/* Nivel de Confianza */}
        <Box mb={3}>
          <Box display="flex" justifyContent="space-between" mb={1}>
            <Typography variant="body2" color="text.secondary">
              Nivel de Confianza
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {confianzaPorcentaje}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={confianzaPorcentaje}
            color={confianzaPorcentaje > 80 ? 'success' : confianzaPorcentaje > 50 ? 'warning' : 'error'}
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>

        {/* Estadísticas */}
        <Grid container spacing={2} mb={3}>
          <Grid size={{ xs: 6, md: 3 }}>
            <Box textAlign="center" p={1} bgcolor="background.default" borderRadius={1}>
              <Typography variant="h5" fontWeight="bold" color="primary">
                {contexto.estadisticas.pagos_analizados}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Pagos Analizados
              </Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <Box textAlign="center" p={1} bgcolor="background.default" borderRadius={1}>
              <Typography variant="h5" fontWeight="bold" color="primary">
                {contexto.estadisticas.meses_con_pagos}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Meses con Pagos
              </Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <Box textAlign="center" p={1} bgcolor="background.default" borderRadius={1}>
              <Typography variant="h5" fontWeight="bold" color="primary">
                ${contexto.estadisticas.monto_promedio.toLocaleString('es-CO')}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Promedio Histórico
              </Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <Box textAlign="center" p={1} bgcolor="background.default" borderRadius={1}>
              <Typography variant="h5" fontWeight="bold" color="primary">
                {contexto.estadisticas.coeficiente_variacion.toFixed(1)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Coeficiente Variación
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {/* Rango Esperado (solo para Tipo B) */}
        {contexto.rango_esperado && (
          <Box mb={3} p={2} bgcolor={dentroRango ? 'success.light' : 'error.light'} borderRadius={1}>
            <Typography variant="subtitle2" fontWeight="bold" mb={1}>
              {dentroRango ? '✅ Monto dentro del rango esperado' : '❌ Monto fuera del rango esperado'}
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 4 }}>
                <Typography variant="caption" color="text.secondary">
                  Mínimo Esperado
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  ${contexto.rango_esperado.inferior.toLocaleString('es-CO')}
                </Typography>
              </Grid>
              <Grid size={{ xs: 4 }}>
                <Typography variant="caption" color="text.secondary">
                  Monto Actual
                </Typography>
                <Typography variant="body2" fontWeight="bold" color={dentroRango ? 'success.dark' : 'error.dark'}>
                  ${montoActual.toLocaleString('es-CO')}
                </Typography>
              </Grid>
              <Grid size={{ xs: 4 }}>
                <Typography variant="caption" color="text.secondary">
                  Máximo Esperado
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  ${contexto.rango_esperado.superior.toLocaleString('es-CO')}
                </Typography>
              </Grid>
            </Grid>
          </Box>
        )}

        {/* Último Pago */}
        {contexto.ultimo_pago && (
          <Box mb={3} p={2} bgcolor="background.default" borderRadius={1}>
            <Typography variant="subtitle2" fontWeight="bold" mb={1}>
              📅 Último Pago Registrado
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 6 }}>
                <Typography variant="caption" color="text.secondary">
                  Fecha
                </Typography>
                <Typography variant="body2">
                  {new Date(contexto.ultimo_pago.fecha).toLocaleDateString('es-CO')}
                </Typography>
              </Grid>
              <Grid size={{ xs: 6 }}>
                <Typography variant="caption" color="text.secondary">
                  Monto
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  ${contexto.ultimo_pago.monto.toLocaleString('es-CO')}
                </Typography>
              </Grid>
            </Grid>
          </Box>
        )}

        {/* Historial de Pagos */}
        {contexto.pagos_historicos && contexto.pagos_historicos.length > 0 && (
          <Box>
            <Typography variant="subtitle2" fontWeight="bold" mb={2}>
              📊 Historial de Pagos (últimos 6 meses)
            </Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Período</TableCell>
                    <TableCell>Fecha</TableCell>
                    <TableCell align="right">Total a Pagar</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {contexto.pagos_historicos.map((pago, index) => (
                    <TableRow key={index} hover>
                      <TableCell>
                        <Chip label={pago.periodo} size="small" />
                      </TableCell>
                      <TableCell>
                        {pago.fecha ? new Date(pago.fecha).toLocaleDateString('es-CO') : 'N/A'}
                      </TableCell>
                      <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                        ${pago.monto.toLocaleString('es-CO')}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default ContextoHistoricoCard;
