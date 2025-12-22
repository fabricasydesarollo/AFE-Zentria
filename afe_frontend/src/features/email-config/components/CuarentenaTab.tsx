/**
 * CuarentenaTab - Vista de facturas en cuarentena
 *
 * ARQUITECTURA 2025-12-14:
 * - Reutiliza FacturasTable existente (DRY principle)
 * - Muestra facturas sin grupo_id asignado
 * - Permite configurar NITs directamente
 */

import React, { useEffect, useState } from 'react';
import {
  Box,
  Alert,
  AlertTitle,
  Typography,
  CircularProgress,
  Button,
  Stack,
  Chip,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Settings as SettingsIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { FacturasTable } from '../../dashboard/components/FacturasTable';
import type { Factura } from '../../dashboard/types';
import apiClient from '../../../services/api';

interface CuarentenaTabProps {
  onSwitchToConfig: (nit?: string) => void;
}

export const CuarentenaTab: React.FC<CuarentenaTabProps> = ({ onSwitchToConfig }) => {
  const [facturas, setFacturas] = useState<Factura[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Cargar facturas en cuarentena
  useEffect(() => {
    loadFacturasCuarentena();
  }, []);

  const loadFacturasCuarentena = async () => {
    try {
      setLoading(true);
      setError(null);

      // Endpoint de facturas con filtro de estado
      const response = await apiClient.get('/facturas', {
        params: {
          estado: 'en_cuarentena',
          skip: 0,
          limit: 1000, // Cargar todas para mostrar el total
        },
      });

      setFacturas(response.data);
    } catch (err: any) {
      console.error('Error cargando facturas en cuarentena:', err);
      setError(
        err.response?.data?.detail || 'Error al cargar facturas en cuarentena'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleConfigNIT = (factura: Factura) => {
    // Cambiar al tab de configuración con el NIT pre-llenado
    const nit = factura.proveedor?.nit || factura.nit_emisor;
    onSwitchToConfig(nit);
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, factura: Factura) => {
    // No mostrar menú en cuarentena, solo botón de configurar
  };

  const handleOpenDialog = () => {
    // No permitir edición en cuarentena
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        <AlertTitle>Error</AlertTitle>
        {error}
        <Button onClick={loadFacturasCuarentena} sx={{ ml: 2 }}>
          Reintentar
        </Button>
      </Alert>
    );
  }

  return (
    <Box>
      {/* Header Alert */}
      {facturas.length > 0 ? (
        <Alert
          severity="warning"
          icon={<WarningIcon />}
          sx={{ mb: 3 }}
          action={
            <Button
              color="inherit"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={loadFacturasCuarentena}
            >
              Actualizar
            </Button>
          }
        >
          <AlertTitle>
            <strong>{facturas.length} factura{facturas.length !== 1 ? 's' : ''} en cuarentena</strong>
          </AlertTitle>
          <Typography variant="body2">
            Estas facturas no tienen grupo asignado porque sus NITs no están configurados.
            Configure los NITs para procesarlas automáticamente.
          </Typography>
        </Alert>
      ) : (
        <Alert severity="success" sx={{ mb: 3 }}>
          <AlertTitle>✅ Sin facturas en cuarentena</AlertTitle>
          <Typography variant="body2">
            Todos los NITs están correctamente configurados.
          </Typography>
        </Alert>
      )}

      {/* Estadísticas por NIT */}
      {facturas.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            NITs Pendientes de Configuración
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {Array.from(
              new Set(facturas.map((f) => f.proveedor?.nit || f.nit_emisor || 'Sin NIT'))
            ).map((nit) => {
              const count = facturas.filter(
                (f) => (f.proveedor?.nit || f.nit_emisor) === nit
              ).length;
              return (
                <Chip
                  key={nit}
                  label={`${nit} (${count})`}
                  color="warning"
                  size="small"
                  onClick={() => onSwitchToConfig(nit)}
                  icon={<SettingsIcon />}
                  sx={{ mb: 1 }}
                />
              );
            })}
          </Stack>
        </Box>
      )}

      {/* Tabla de Facturas (Componente Reutilizado) */}
      {facturas.length > 0 && (
        <FacturasTable
          facturas={facturas}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={setPage}
          onRowsPerPageChange={setRowsPerPage}
          onOpenDialog={handleOpenDialog}
          onMenuClick={handleMenuClick}
          isAdmin={true}
          isHistorico={false}
        />
      )}
    </Box>
  );
};
