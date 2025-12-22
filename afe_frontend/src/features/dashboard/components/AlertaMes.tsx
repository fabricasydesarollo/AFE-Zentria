/**
 * AlertaMes - Campana de notificación para fin de mes
 * Muestra una campana roja 8 días antes del fin de mes
 * Al hacer click, muestra detalles del tiempo restante y facturas pendientes
 */

import { useEffect, useState } from 'react';
import { Box, Badge, IconButton, Popover, Paper, Stack, Typography, Button } from '@mui/material';
import { Notifications, Close } from '@mui/icons-material';
import apiClient from '../../../services/api';
import { zentriaColors } from '../../../theme/colors';

interface AlertaMesResponse {
  mostrar_alerta: boolean;
  dias_restantes: number;
  facturas_pendientes: number;
  mensaje: string;
  nivel_urgencia: 'info' | 'warning' | 'critical';
}

export function AlertaMes() {
  const [alerta, setAlerta] = useState<AlertaMesResponse | null>(null);
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);
  const [loading, setLoading] = useState(true);

  // Cargar alerta al montar componente
  useEffect(() => {
    const cargarAlerta = async () => {
      try {
        const response = await apiClient.get<AlertaMesResponse>(
          '/dashboard/alerta-mes'
        );
        setAlerta(response.data);
      } catch (error) {
        console.error('Error cargando alerta:', error);
      } finally {
        setLoading(false);
      }
    };

    cargarAlerta();

    // Recargar alerta cada 30 minutos
    const interval = setInterval(cargarAlerta, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Manejar click en campana
  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  // Cerrar popover
  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);

  // Mostrar campana siempre (activa o inactiva)
  const isActive = !loading && alerta?.mostrar_alerta;

  return (
    <>
      {/* Campana en header - siempre visible */}
      <IconButton
        onClick={handleClick}
        sx={{
          position: 'relative',
          color: isActive ? zentriaColors.naranja.main : '#ccc',
          transition: 'color 0.2s',
        }}
        title={isActive ? 'Fin de mes próximo' : 'Sin alertas'}
      >
        <Badge
          badgeContent={isActive ? alerta.facturas_pendientes : 0}
          color="error"
          overlap="circular"
        >
          <Notifications sx={{ fontSize: 28 }} />
        </Badge>
      </IconButton>

      {/* Popover con detalles */}
      {alerta && (
        <Popover
          open={open}
          anchorEl={anchorEl}
          onClose={handleClose}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'right',
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
        >
          <Paper
            sx={{
              p: 2.5,
              width: 380,
              backgroundColor: '#fff',
              borderLeft: `5px solid ${isActive ? zentriaColors.naranja.main : '#ccc'}`,
            }}
          >
            {/* Header */}
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: isActive ? zentriaColors.naranja.main : '#999' }}>
                ⏰ Fin de Mes
              </Typography>
              <IconButton size="small" onClick={handleClose}>
                <Close fontSize="small" />
              </IconButton>
            </Stack>

            {isActive ? (
              <>
                {/* Mensaje principal */}
                <Typography variant="body2" sx={{ mb: 2, color: '#333' }}>
                  {alerta.mensaje}
                </Typography>

                {/* Detalles */}
                <Stack spacing={1.5} sx={{ mb: 2, p: 1.5, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
                  {/* Días restantes */}
                  <Box>
                    <Typography variant="caption" sx={{ color: '#666', fontWeight: 600 }}>
                      DÍAS RESTANTES
                    </Typography>
                    <Typography
                      variant="h4"
                      sx={{
                        fontWeight: 800,
                        color: zentriaColors.naranja.main,
                        mt: 0.5,
                      }}
                    >
                      {alerta.dias_restantes}
                      <span style={{ fontSize: '0.6em', marginLeft: '4px' }}>
                        {alerta.dias_restantes === 1 ? 'día' : 'días'}
                      </span>
                    </Typography>
                  </Box>

                  {/* Facturas pendientes */}
                  <Box>
                    <Typography variant="caption" sx={{ color: '#666', fontWeight: 600 }}>
                      FACTURAS PENDIENTES
                    </Typography>
                    <Typography
                      variant="h4"
                      sx={{
                        fontWeight: 800,
                        color: zentriaColors.naranja.main,
                        mt: 0.5,
                      }}
                    >
                      {alerta.facturas_pendientes}
                      <span style={{ fontSize: '0.6em', marginLeft: '4px' }}>
                        {alerta.facturas_pendientes === 1 ? 'factura' : 'facturas'}
                      </span>
                    </Typography>
                  </Box>
                </Stack>

                {/* Botón de acción */}
                <Button
                  variant="contained"
                  fullWidth
                  onClick={handleClose}
                  sx={{
                    background: `linear-gradient(135deg, ${zentriaColors.naranja.main}, ${zentriaColors.naranja.dark})`,
                    textTransform: 'none',
                    fontWeight: 600,
                  }}
                >
                  Entendido
                </Button>

                {/* Nota de urgencia si es critical */}
                {alerta.nivel_urgencia === 'critical' && (
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      mt: 1.5,
                      p: 1,
                      backgroundColor: '#ffe6e6',
                      color: zentriaColors.naranja.dark,
                      borderRadius: 0.5,
                      fontWeight: 600,
                    }}
                  >
                    ⚠️ El mes termina en {alerta.dias_restantes} {alerta.dias_restantes === 1 ? 'día' : 'días'}. ¡Actúa ya!
                  </Typography>
                )}
              </>
            ) : (
              <Typography variant="body2" color="textSecondary" sx={{ textAlign: 'center', py: 2 }}>
                ✓ Sin alertas pendientes
              </Typography>
            )}
          </Paper>
        </Popover>
      )}
    </>
  );
}

export default AlertaMes;
